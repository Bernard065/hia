# HIA — API Design

*Derived from the HIA Functional/Non-Functional Requirements and System Architecture Document.*

Base URL: `https://api.hia.app/v1`
Format: JSON over HTTPS. All endpoints (except `/auth/*` and health checks) require a bearer access token and operate on data scoped to the authenticated user's own patient record (or a clinician's authorized patients, once FR-19 is implemented).

This mirrors the backend module layout from the architecture doc: `auth`, `patients`, `reports`, `laboratory`, `symptoms`, `medications`, `timeline`, `monitoring`, `alerts`, `insights`, `assistant`, `search`, `rag`, `safety`, `audit`.

---

## 0. Conventions

**Protocol choice:** REST is the default for the whole client-facing surface — it's client-facing, over/under-fetching isn't a real concern here (each screen maps cleanly to one or two resources), and REST's tooling/familiarity wins. The one internal exception is worth naming explicitly: service-to-service calls between the API and the AI/document/risk workers (architecture doc §6) go over the internal message queue, not HTTP — that boundary is described in the worker sections below rather than as REST endpoints.

**Resource modeling:** every path below names a *thing* (`reports`, `insights`, `alerts`), never a verb — `POST /reports/{id}/reprocess` is the deliberate exception, kept as an action-style endpoint because "reprocessing" isn't a resource a client creates/reads, it's a one-shot command against an existing one. Relationships use path nesting when the parent is required to make the query meaningful (`/monitoring/conditions/{id}/history`), and query parameters when the relationship is an optional filter (`/laboratory/results?test=hba1c`).

**Auth header:** `Authorization: Bearer <access_token>` (JWT — see §1a below for why JWT over API keys here).

**Pagination:** two modes, chosen per resource, not one-size-fits-all:

- **Cursor-based** for anything that grows continuously and is read in recent-first order — `reports`, `symptoms`, `laboratory/results`, `timeline`, `alerts`, `audit/events`, `assistant/conversations`. `?limit=20&cursor=cmd9atj3p...` → `{ "data": [...], "next_cursor": "cmd9b..." }`. This matters here specifically because patient timelines are exactly the "new records keep arriving while you paginate" case offset pagination breaks on.
- **Offset-based** for small, bounded, rarely-growing lists — `patients/me/allergies`, `medications` (active list), `monitoring/conditions`. `?page=1&page_size=20` → `{ "data": [...], "page": 1, "page_size": 20, "total": 14 }`.

**Filtering/sorting:** list endpoints accept `?from=`, `?to=` (ISO 8601 dates) for time-scoped resources, and `?sort=` (`-date` for descending) where relevant. Filter parameter names are kept identical across resources (`?status=`, `?type=`, `?severity=` mean the same thing everywhere they appear) so a client that's learned one endpoint's filters can guess the rest.

**HTTP methods / idempotency:** GET, PUT, DELETE are idempotent and treated as such; POST is not, so anything that creates a record a retry could duplicate — report uploads, symptom/medication entries, `/insights/generate`, `/assistant/conversations/{id}/messages` — accepts an `Idempotency-Key` header, and the server returns the original response for a replayed key instead of doing the work twice. This is the same reasoning as "don't double-book a seat," just applied to "don't double-log a symptom" or "don't run risk analysis twice and get two conflicting insights."

**Standard error shape:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "dosage must be a positive number",
    "field": "dosage",
    "request_id": "req_9f2a..."
  }
}
```
`code` is the stable, machine-readable string clients branch on; `message` is for humans and can change without breaking anyone. Codes: `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `RATE_LIMITED` (429), `INTERNAL_ERROR` (500). Same envelope, every endpoint, no exceptions.

**Versioning:** URL-path major version (`/v1`); breaking changes (renaming/removing/re-meaning a field) ship as `/v2`, additive fields don't require a bump. AI-related resources additionally carry a `model_version` / `ruleset_version` field per NFR-14, which is a data-versioning concern distinct from API versioning — a model can be retrained without touching the API contract at all.

**Every response involving AI output includes a `disclaimer` field** stating it is not a confirmed diagnosis — enforced at the serializer level, not left to callers (NFR-07).

---

## 1. Auth — `/auth` (FR-01, NFR-01)

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account (email/phone + password) |
| POST | `/auth/login` | Returns access + refresh token, or `mfa_required: true` with a `mfa_token` |
| POST | `/auth/mfa/verify` | Exchange `mfa_token` + OTP for tokens |
| POST | `/auth/mfa/enroll` | Enroll TOTP/SMS MFA factor |
| POST | `/auth/refresh` | Exchange refresh token for new access token |
| POST | `/auth/logout` | Revoke current session |
| POST | `/auth/logout-all` | Revoke all sessions/devices |
| POST | `/auth/password/forgot` | Trigger reset email/SMS |
| POST | `/auth/password/reset` | Consume reset token, set new password |
| GET | `/auth/sessions` | List active sessions/devices |
| DELETE | `/auth/sessions/{session_id}` | Revoke a specific session |
| GET | `/auth/me` | Current user identity + roles |

Access tokens are short-lived JWTs; refresh tokens are rotated and stored hashed. All endpoints under `/auth` are rate-limited per IP and per account.

### 1a. Why JWT, not API keys

This is a user-facing product, not a developer platform (that's a Phase 6 concern once EHR/hospital integrations exist) — users authenticate with sessions, not long-lived secrets they'd have to manage. A JWT lets the API gateway and every downstream service (auth, patients, reports, ...) verify identity independently from the signature alone, without a DB round-trip per request, which matters given NFR-04's latency targets. API keys are reserved for the future server-to-server case: a hospital/EHR system or lab-provider integration authenticating machine-to-machine (Phase 6, §16).

### 1b. Roles and authorization (RBAC)

| Role | Can do |
|---|---|
| `patient` | Full CRUD on their own profile, reports, labs, symptoms, medications; read their own insights/alerts/timeline; use the assistant |
| `clinician` | Read-only on patients who've granted access (§16); can write `confirmed_diagnosis` records — the *only* role that can |
| `admin` | Ops/compliance access to audit and safety-check endpoints across patients; cannot read clinical content itself without an explicit access grant |

Every protected endpoint checks both layers, not just one: **authentication** (valid JWT) confirms *who*, **authorization** confirms *this caller may act on this specific resource* — e.g. `GET /medications/{id}` requires a valid token *and* that the medication belongs to the token's patient (or the caller is a clinician with an active grant for that patient). Authorization is enforced per-record, not just per-endpoint, since almost every resource here is patient-scoped.

### 1c. Rate limiting

Endpoints are opt-out of a default limit, not opt-in — every route is limited unless deliberately marked public (there are none besides `/auth/register` and `/auth/login`, which get the stricter IP-based limit to blunt credential stuffing). Beyond the default, a few paths get tighter limits because they're the most compute-expensive or most abuse-prone:

| Scope | Limit | Why |
|---|---|---|
| Default (authenticated) | 1000 req/hour/user | Baseline abuse protection |
| `/auth/login`, `/auth/register` | 20 req/hour/IP | Credential stuffing / enumeration |
| `/assistant/*` | 60 req/hour/user | LLM calls are the most expensive path in the system |
| `/insights/generate` | 10 req/hour/user | Triggers the full risk/RAG pipeline |
| `/reports` (POST) | 30 req/hour/user | Each upload fans out into OCR + extraction work |

Enforced at the gateway/Redis layer (architecture doc §19), returning `429` with the standard error envelope and a `Retry-After` header.

---

## 2. Patient Profile — `/patients` (FR-02)

| Method | Path | Purpose |
|---|---|---|
| GET | `/patients/me` | Full profile: demographics, blood group, lifestyle |
| PATCH | `/patients/me` | Update profile fields |
| GET | `/patients/me/allergies` | List allergies |
| POST | `/patients/me/allergies` | Add allergy |
| DELETE | `/patients/me/allergies/{id}` | Remove allergy |
| GET / POST | `/patients/me/conditions` | Existing conditions |
| PATCH / DELETE | `/patients/me/conditions/{id}` | Update/resolve a condition |
| GET / POST | `/patients/me/diagnoses` | Confirmed diagnoses (clinician-sourced, distinct from AI risk indications) |
| GET / POST | `/patients/me/surgical-history` | Surgical history entries |
| GET / POST | `/patients/me/family-history` | Family history entries |

Every sub-resource follows the same CRUD shape; listed once here rather than repeated per row. All writes append an `audit` event (§14) and, where clinically relevant, invalidate cached trend/risk computations so the next insight generation run picks up the change.

---

## 3. Medical Reports — `/reports` (FR-03, FR-04)

Upload is synchronous (accept + store); analysis is asynchronous (worker pipeline in the architecture doc: OCR → classification → entity extraction → structuring).

| Method | Path | Purpose |
|---|---|---|
| POST | `/reports` | Multipart upload. Validates file type/size, virus-scans, stores original in object storage, creates `Report` record with `status: pending`, enqueues processing. Returns `202` with the report id. |
| GET | `/reports` | List reports (`?type=`, `?from=`, `?to=`, `?status=`) |
| GET | `/reports/{id}` | Report metadata + processing status |
| GET | `/reports/{id}/status` | Lightweight polling endpoint: `pending / processing / completed / failed` |
| GET | `/reports/{id}/download` | Signed, time-limited URL to the original file |
| GET | `/reports/{id}/extracted` | Structured extraction result: entities, lab values, medications, diagnoses mentioned, dates, recommendations, each with a confidence score |
| GET | `/reports/{id}/explanation` | Patient-friendly plain-language explanation of the report (FR-04) |
| DELETE | `/reports/{id}` | Soft-delete (retained per NFR-16 retention policy, hidden from the user) |
| POST | `/reports/{id}/reprocess` | Re-run the pipeline (e.g. after a model upgrade) |

Real-time status: clients subscribe to `GET /reports/{id}/events` (SSE) instead of polling, per the architecture's "SSE/WebSockets where real-time status is required."

Report statuses that reach `completed` automatically feed laboratory results (§4), medications (§8), and trend/insight pipelines — no client action required.

---

## 4. Laboratory Results — `/laboratory` (FR-05)

| Method | Path | Purpose |
|---|---|---|
| GET | `/laboratory/results` | List results (`?test=`, `?from=`, `?to=`) — each item: test name, value, unit, reference range, flag (normal/high/low), date, source (manual or `report_id`) |
| POST | `/laboratory/results` | Manually add a result not tied to an uploaded report |
| GET | `/laboratory/results/{id}` | Single result detail |
| PATCH | `/laboratory/results/{id}` | Correct a manually-entered result (extracted results are corrected via a linked `report` re-review, not direct edit, to preserve provenance) |
| GET | `/laboratory/tests/{test_name}/history` | Time series for one test — this is what feeds the chart views in §11 |

---

## 5. Health Trends — `/laboratory/trends` and `/monitoring/trends` (FR-06)

Trend analysis runs independently of the conversational AI, per the architecture.

| Method | Path | Purpose |
|---|---|---|
| GET | `/trends` | Current trend status for all supported measurements (BP, glucose, HbA1c, cholesterol, weight, heart rate, SpO2, kidney/liver markers) |
| GET | `/trends/{measurement}` | Detail for one measurement: series, direction, rate of change, whether it crosses a clinically meaningful threshold |
| POST | `/trends/{measurement}/recompute` | Force recomputation (e.g. after a bulk data import) — internal/admin use |

Trend results are inputs to the insight and monitoring engines, not diagnoses themselves.

---

## 6. Symptoms — `/symptoms` (FR-07)

| Method | Path | Purpose |
|---|---|---|
| GET | `/symptoms` | List symptom entries (`?from=`, `?to=`, `?symptom=`) |
| POST | `/symptoms` | Log a symptom: name, severity (1–10 or categorical), duration, frequency, onset, associated symptoms, possible triggers |
| GET | `/symptoms/{id}` | Detail |
| PATCH | `/symptoms/{id}` | Update (e.g. mark resolved, add associated symptoms) |
| DELETE | `/symptoms/{id}` | Remove entry |

Symptom writes can optionally trigger an on-demand risk assessment via `?trigger_analysis=true`, otherwise they're picked up by the standard insight-generation trigger (§9).

---

## 7. AI Health Assistant — `/assistant` (FR-08)

Conversational, but every response is grounded through the AI Orchestrator (patient data retrieval → medical RAG → clinical rules → LLM → safety validation), matching §11 of the architecture doc.

| Method | Path | Purpose |
|---|---|---|
| POST | `/assistant/conversations` | Start a conversation |
| GET | `/assistant/conversations` | List past conversations |
| GET | `/assistant/conversations/{id}` | Full message history |
| POST | `/assistant/conversations/{id}/messages` | Send a message. Response includes the answer, `sources` (patient-data references + retrieved knowledge sources used), `safety_flags`, and the standard disclaimer |
| POST | `/assistant/conversations/{id}/messages/stream` | Same, as SSE token stream for a responsive UI |
| DELETE | `/assistant/conversations/{id}` | Delete a conversation |

The assistant never receives raw model output as final — every message passes through `/safety` validation (§13) before being persisted and returned, so the message object always reflects the *approved* response, with an `escalated: true` flag if the safety engine routed it to human-review guidance rather than answering directly.

---

## 8. Medications — `/medications` (FR-12)

| Method | Path | Purpose |
|---|---|---|
| GET | `/medications` | List (`?active=true` filters to current) — name, dosage, frequency, start/end date, prescribing clinician, reason |
| POST | `/medications` | Add a medication |
| GET | `/medications/{id}` | Detail |
| PATCH | `/medications/{id}` | Update (e.g. set end date) |
| DELETE | `/medications/{id}` | Remove |
| GET | `/medications/{id}/info` | Authoritative drug reference info (interactions, common side effects) sourced from a medication database/RAG source — **not** generated freestanding by the LLM, per FR-12 |
| POST | `/medications/interactions/check` | Given a set of medication ids (or a proposed new one), returns known interaction warnings from the authoritative source |

---

## 9. AI Insights — `/insights` (FR-09, FR-14, FR-15)

| Method | Path | Purpose |
|---|---|---|
| GET | `/insights` | List generated insights (`?category=risk|trend|general`, `?severity=`, `?from=`, `?to=`) |
| GET | `/insights/{id}` | Full insight: finding, category (`confirmed_diagnosis` — clinician-sourced only / `possible_condition` / `risk_indication` / `trend` / `general_information`), severity, confidence, supporting evidence, recommended next step, source, `model_version`/`ruleset_version` |
| GET | `/insights/{id}/explanation` | Explainability view (FR-15): supporting patient data points, what changed, reasoning summary at a chosen level of detail (`?detail=simple|detailed`) |
| POST | `/insights/generate` | Manually trigger insight generation for the current patient (normally auto-triggered when new health data arrives, per the architecture's event-driven workers) |
| POST | `/insights/{id}/feedback` | User marks an insight as helpful/not relevant — feeds future tuning, does not alter the stored insight itself |
| POST | `/insights/{id}/dismiss` | Hide from the default view (kept for audit) |

The `category` field is the API-level enforcement of FR-09/NFR-07's requirement to never present an AI possibility as a confirmed diagnosis — clients render each category with distinct visual treatment, and `confirmed_diagnosis` can only be set by a clinician-facing write path (§12, later phase), never by the AI pipeline.

---

## 10. Disease Monitoring — `/monitoring` (FR-10)

| Method | Path | Purpose |
|---|---|---|
| GET | `/monitoring/conditions` | Conditions currently under active monitoring for this patient |
| POST | `/monitoring/conditions` | Enroll a condition for monitoring (e.g. after a diagnosis) |
| GET | `/monitoring/conditions/{id}` | Monitoring detail: tracked measurements, current status, relevant trend links |
| PATCH | `/monitoring/conditions/{id}` | Update monitoring parameters or pause/resume |
| DELETE | `/monitoring/conditions/{id}` | Stop monitoring |
| GET | `/monitoring/conditions/{id}/history` | Longitudinal view of tracked indicators for this condition |

---

## 11. Health Alerts — `/alerts` (FR-11)

| Method | Path | Purpose |
|---|---|---|
| GET | `/alerts` | List alerts (`?status=open|acknowledged|resolved`, `?severity=`) |
| GET | `/alerts/{id}` | Detail: triggering rule/threshold/trend, severity, recommended escalation guidance |
| POST | `/alerts/{id}/acknowledge` | Mark as seen |
| POST | `/alerts/{id}/resolve` | Mark resolved (with optional note) |
| GET | `/alerts/stream` | SSE stream for real-time alert delivery, matching the architecture's real-time requirement for monitoring |

Alerts are generated by the notification workers off the event bus (trend/risk pipeline output), not created directly by clients. They carry escalation guidance text, never an autonomous emergency action, per FR-11.

---

## 12. Health Timeline — `/timeline` (FR-13)

| Method | Path | Purpose |
|---|---|---|
| GET | `/timeline` | Chronological feed merging diagnoses, reports, lab results, medications, measurements, symptoms, and significant health events (`?from=`, `?to=`, `?type=`) — a read-optimized projection, not a separate write path |
| GET | `/timeline/{event_id}` | Detail for one event, with a link back to its source resource (report, lab result, etc.) |

---

## 13. Medical Knowledge Retrieval — `/rag` (FR-16, internal-facing)

Primarily consumed by the AI Orchestrator internally, but exposed for transparency and audit:

| Method | Path | Purpose |
|---|---|---|
| GET | `/rag/sources` | List approved medical knowledge sources currently in the index |
| GET | `/rag/sources/{id}` | Source detail/provenance |
| POST | `/rag/query` | Admin/debug: run a retrieval query directly against the vector store |

End users interact with retrieval indirectly — every insight/assistant response that used retrieval lists the specific sources in its `sources` field (§7, §9), satisfying FR-16's auditability requirement without a separate user-facing RAG UI.

---

## 14. Patient Data Search — `/search` (FR-17)

| Method | Path | Purpose |
|---|---|---|
| GET | `/search` | `?q=` natural-language or structured query across reports, labs, medications, symptoms, timeline events. Returns typed, ranked results grouped by resource type |
| GET | `/search/suggest` | Lightweight autocomplete/typeahead |

Natural-language queries are parsed into structured filters server-side before hitting PostgreSQL/pgvector — this endpoint does not itself invoke the conversational LLM (that's `/assistant`).

---

## 15. Health Data Visualization (FR-18)

No dedicated `/visualization` module — this is a UI concern served by existing data endpoints designed with charting in mind: `/laboratory/tests/{test}/history`, `/trends/{measurement}`, `/timeline`, `/monitoring/conditions/{id}/history` all return time-series-shaped JSON (`{date, value, reference_range}[]`) that the frontend charts directly, avoiding a redundant aggregation layer.

---

## 16. Human/Clinician Review — `/clinicians` (FR-19, Later phase)

Stubbed now, built out post-Phase 4 per the roadmap:

| Method | Path | Purpose |
|---|---|---|
| POST | `/patients/me/clinician-access` | Grant a clinician scoped, time-limited access |
| DELETE | `/patients/me/clinician-access/{grant_id}` | Revoke access |
| GET | `/clinicians/patients/{patient_id}/insights` | Clinician view of a patient's AI-generated insights (clinician-scoped auth) |
| POST | `/clinicians/patients/{patient_id}/diagnoses` | The one path allowed to write a `confirmed_diagnosis` insight/record |

---

## 17. Safety — `/safety` (internal, NFR-07)

Not directly called by clients; every AI-facing response passes through it. Exposed read-only for audit/debugging:

| Method | Path | Purpose |
|---|---|---|
| GET | `/safety/checks/{ai_execution_id}` | The safety checks run against a given AI output: grounding check, unsupported-claim check, diagnosis-language check, urgency detection, medication-safety validation, clinical-rule validation, escalation classification — pass/fail plus resulting action (`approved / modified / escalated`) |

---

## 18. Audit Trail — `/audit` (FR-20, NFR-14)

| Method | Path | Purpose |
|---|---|---|
| GET | `/audit/events` | List audit events for the current user (`?type=`, `?from=`, `?to=`) — uploads, analysis runs, insight generation, access events |
| GET | `/audit/ai-executions/{id}` | Full `AIExecution` record: request, retrieved patient-data references, retrieved knowledge sources, model + version, prompt/version id, clinical-rule version, safety result, generated vs. final output, latency, timestamp — matches the architecture's `AIExecution` schema exactly |

Regular users see their own audit history read-only; compliance/admin roles get a separate scoped endpoint set (not detailed here — out of scope until an admin/ops API is designed).

---

## 19. Cross-cutting notes for implementation

- **Async everywhere it matters:** uploads, insight generation, trend recomputation, and long AI responses are all fire-and-return-202 + poll/SSE, matching NFR-04's requirement to process large reports asynchronously and keep synchronous paths fast.
- **Every mutating endpoint on patient data writes an audit event** — this is easiest to enforce as a decorator/middleware in the `patients`, `reports`, `laboratory`, `symptoms`, `medications` modules rather than per-handler code.
- **Rate limiting** on `/assistant/*` and `/insights/generate` specifically, since these are the most compute-expensive paths (Redis-backed, per the architecture's caching/infra section).
- **OpenAPI spec** should be generated from the FastAPI route definitions directly (FastAPI's built-in `/openapi.json`) rather than hand-maintained, so it can't drift from the implementation — worth publishing at `/docs` in non-prod environments only.
