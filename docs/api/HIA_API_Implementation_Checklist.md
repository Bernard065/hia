# HIA API — Implementation Checklist

Tracks build progress against `HIA_API_Design.md`, ordered by the six implementation phases from the architecture doc. We'll check items off here as we complete them together.

**Progress:** 0 / 74 endpoints

---

## Phase 1 — Secure Foundation

*Auth, patient profile, RBAC, MFA, audit logging. Nothing else can be safely built until this layer exists.*

**Setup**

- [ ] PostgreSQL schema: users, sessions, roles
- [ ] JWT signing/verification, refresh-token rotation
- [ ] RBAC middleware (`patient` / `clinician` / `admin`)
- [ ] Audit-log write path (used by every module from here on)

**Auth — `/auth`**

- [ ] `POST /auth/register`
- [ ] `POST /auth/login`
- [ ] `POST /auth/mfa/enroll`
- [ ] `POST /auth/mfa/verify`
- [ ] `POST /auth/refresh`
- [ ] `POST /auth/logout`
- [ ] `POST /auth/logout-all`
- [ ] `POST /auth/password/forgot`
- [ ] `POST /auth/password/reset`
- [ ] `GET /auth/sessions`
- [ ] `DELETE /auth/sessions/{session_id}`
- [ ] `GET /auth/me`

**Patient Profile — `/patients`**

- [ ] `GET /patients/me`
- [ ] `PATCH /patients/me`
- [ ] `GET`/`POST /patients/me/allergies`, `DELETE /patients/me/allergies/{id}`
- [ ] `GET`/`POST /patients/me/conditions`, `PATCH`/`DELETE /patients/me/conditions/{id}`
- [ ] `GET`/`POST /patients/me/diagnoses`
- [ ] `GET`/`POST /patients/me/surgical-history`
- [ ] `GET`/`POST /patients/me/family-history`

---

## Phase 2 — Medical Records

*Report uploads, document processing, structured lab/medication/symptom data, timeline. Depends on Phase 1's auth + audit layer and object storage being wired up.*

**Setup**

- [ ] Object storage bucket + signed-URL generation
- [ ] Message queue + document-processing worker skeleton (OCR → extraction)

**Medical Reports — `/reports`**

- [ ] `POST /reports` (upload)
- [ ] `GET /reports` (list)
- [ ] `GET /reports/{id}`
- [ ] `GET /reports/{id}/status`
- [ ] `GET /reports/{id}/events` (SSE)
- [ ] `GET /reports/{id}/download`
- [ ] `GET /reports/{id}/extracted`
- [ ] `GET /reports/{id}/explanation`
- [ ] `DELETE /reports/{id}`
- [ ] `POST /reports/{id}/reprocess`

**Laboratory Results — `/laboratory`**

- [ ] `GET`/`POST /laboratory/results`
- [ ] `GET`/`PATCH /laboratory/results/{id}`
- [ ] `GET /laboratory/tests/{test_name}/history`

**Symptoms — `/symptoms`**

- [ ] `GET`/`POST /symptoms`
- [ ] `GET`/`PATCH`/`DELETE /symptoms/{id}`

**Medications — `/medications`**

- [ ] `GET`/`POST /medications`
- [ ] `GET`/`PATCH`/`DELETE /medications/{id}`
- [ ] `GET /medications/{id}/info`
- [ ] `POST /medications/interactions/check`

**Health Timeline — `/timeline`**

- [ ] `GET /timeline`
- [ ] `GET /timeline/{event_id}`

---

## Phase 3 — Intelligence

*AI assistant, medical RAG, trend engine, insight generation, explainability, search. Depends on Phase 2 data existing to reason over.*

**Setup**

- [ ] AI Orchestrator skeleton (patient-data retrieval → RAG → clinical rules → LLM)
- [ ] Vector store + knowledge ingestion pipeline

**Health Trends — `/trends`**

- [ ] `GET /trends`
- [ ] `GET /trends/{measurement}`
- [ ] `POST /trends/{measurement}/recompute`

**Medical Knowledge Retrieval — `/rag`**

- [ ] `GET /rag/sources`, `GET /rag/sources/{id}`
- [ ] `POST /rag/query` (admin/debug)

**AI Insights — `/insights`**

- [ ] `GET /insights`
- [ ] `GET /insights/{id}`
- [ ] `GET /insights/{id}/explanation`
- [ ] `POST /insights/generate`
- [ ] `POST /insights/{id}/feedback`
- [ ] `POST /insights/{id}/dismiss`

**AI Health Assistant — `/assistant`**

- [ ] `POST`/`GET /assistant/conversations`
- [ ] `GET /assistant/conversations/{id}`
- [ ] `POST /assistant/conversations/{id}/messages`
- [ ] `POST /assistant/conversations/{id}/messages/stream`
- [ ] `DELETE /assistant/conversations/{id}`

**Patient Data Search — `/search`**

- [ ] `GET /search`
- [ ] `GET /search/suggest`

---

## Phase 4 — Safety

*Clinical rules, risk engine, safety validation, escalation, AI audit trail. Depends on Phase 3's orchestrator existing to wrap.*

**Setup**

- [ ] Clinical rules engine (versioned rulesets)
- [ ] Safety Engine wired into the orchestrator's response path (§17 of the design doc)

**Safety — `/safety`**

- [ ] `GET /safety/checks/{ai_execution_id}`

**Audit Trail — `/audit`**

- [ ] `GET /audit/events`
- [ ] `GET /audit/ai-executions/{id}`

---

## Phase 5 — Monitoring

*Disease monitoring, alerts, notification workers. Depends on Phase 3's trend/insight pipelines and Phase 4's safety layer.*

**Setup**

- [ ] Notification worker + alert-generation rules off the event bus

**Disease Monitoring — `/monitoring`**

- [ ] `GET`/`POST /monitoring/conditions`
- [ ] `GET`/`PATCH`/`DELETE /monitoring/conditions/{id}`
- [ ] `GET /monitoring/conditions/{id}/history`

**Health Alerts — `/alerts`**

- [ ] `GET /alerts`
- [ ] `GET /alerts/{id}`
- [ ] `POST /alerts/{id}/acknowledge`
- [ ] `POST /alerts/{id}/resolve`
- [ ] `GET /alerts/stream` (SSE)

---

## Phase 6 — Expansion (later)

*FHIR/EHR, clinician portal, wearables, predictive models. Not blocking anything above — pick up when Phases 1–5 are stable in production.*

**Human/Clinician Review — `/clinicians`**

- [ ] `POST`/`DELETE /patients/me/clinician-access`(`/{grant_id}`)
- [ ] `GET /clinicians/patients/{patient_id}/insights`
- [ ] `POST /clinicians/patients/{patient_id}/diagnoses`

---

## How we'll use this

Each time we finish an endpoint (or a logical group of them) in this conversation, I'll flip its checkbox here and update the progress count at the top. If you jump ahead and build something yourself between sessions, just tell me and I'll mark it done.
