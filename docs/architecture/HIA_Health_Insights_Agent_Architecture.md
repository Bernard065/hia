# HIA Health Insights Agent Architecture

**Architecture derived from the HIA Functional and Non-Functional Requirements**

## 1. Architecture Overview

HIA is designed as one unified healthcare and AI health-assistant application. The architecture uses a modular application core supported by event-driven background workers. Specialized internal components handle document analysis, symptom reasoning, risk analysis, trend detection, monitoring, medical retrieval, and safety validation while remaining part of the same product.

The central architectural principle is that the patient record is the source of truth. AI components provide reasoning and explanation, while deterministic clinical rules, validation, retrieval, and safety controls constrain AI-generated outputs.

## 2. High-Level Architecture

```text
HIA Web / Mobile
        |
      HTTPS
        v
API Gateway / Application API
        |
  +-----+------------------+------------------+
  |                        |                  |
  v                        v                  v
Identity & Access     Patient Data        AI Gateway
                                             |
                                             v
                                      AI Orchestrator
                                             |
                              +--------------+--------------+
                              |              |              |
                              v              v              v
                             RAG            Risk          Safety
                           Engine          Engine         Engine

PostgreSQL          Object Storage         Vector Store
Patient Data        Medical Documents     Medical Knowledge

                    EVENT BUS / QUEUE
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
      Document Workers  Insight Workers  Notification Workers
      OCR / Extraction  Trends / Risk    Alerts / Escalation
```

## 3. Architectural Style

- Modular architecture for independently testable domains and intelligence components.
- Event-driven processing for large medical documents and long-running AI tasks.
- Synchronous APIs for normal CRUD and dashboard operations.
- Asynchronous workers for OCR, extraction, trend analysis, risk analysis, insight generation, and notifications.
- Horizontal scaling of API instances and background workers.
- PostgreSQL as the primary system of record.
- Object storage for original medical documents.
- Vector search for approved medical knowledge retrieval.
- Redis for caching, rate limiting, temporary state, and job-related support functions.

## 4. Frontend Architecture

Recommended frontend structure:

- Next.js with TypeScript and the App Router.
- Reusable UI/component library.
- Client-side data fetching and caching for interactive health dashboards.
- Schema validation for client inputs.
- Responsive and accessible interfaces.
- Server-sent events or WebSockets where real-time status or alert updates are required.

## 5. Core User Areas

- Dashboard
- Patient Profile
- Health Timeline
- Medical Reports
- Laboratory Results
- Symptoms
- Medications
- Conditions and Disease Monitoring
- AI Insights
- Alerts
- AI Health Assistant
- Search
- Security and Session Management

## 6. Backend Architecture

Recommended backend: FastAPI/Python, with domain-oriented modules.

```text
API
├── auth
├── patients
├── reports
├── laboratory
├── symptoms
├── medications
├── timeline
├── monitoring
├── alerts
├── insights
├── assistant
├── search
├── rag
├── safety
└── audit

Workers
├── document-processing
├── extraction
├── trend-analysis
├── risk-analysis
├── insight-generation
└── notifications
```

## 7. Medical Document Processing Pipeline

```text
User
  |
  v
Upload API
  |
  +--> Validate file
  +--> Security/virus scan
  +--> Create document metadata
  +--> Store original document
  |
  v
Message Queue
  |
  v
Document Worker
  |
  +--> OCR / text extraction
  +--> Document classification
  +--> Medical entity extraction
  +--> Laboratory extraction
  +--> Medication extraction
  +--> Dates / diagnoses / procedures / recommendations
  |
  v
Structured Medical Data
  |
  +--> Validate
  +--> Persist
  +--> Trigger analysis
  |
  v
Trend / Risk / Insight Pipelines
```

## 8. Data Architecture

Core domain relationships:

```text
User
  |
  +-- PatientProfile
       +-- Allergies
       +-- Conditions
       +-- Diagnoses
       +-- FamilyHistory
       +-- Lifestyle
       +-- MedicalDocuments
       +-- LaboratoryResults
       +-- VitalMeasurements
       +-- Symptoms
       +-- Medications
       +-- HealthEvents
       +-- Insights
       +-- Alerts
       +-- TimelineEvents
```

## 9. PostgreSQL Data Model

- Patient, user identity, and profile data
- Medical documents and processing status
- Structured laboratory results
- Vital measurements
- Symptoms and symptom events
- Medication records
- Conditions and diagnoses
- Health timeline events
- Generated insights
- Alerts
- AI execution and audit records
- Access and security audit events

## 10. Object Storage

Medical documents should be stored outside the relational database in encrypted object storage. PostgreSQL should contain metadata, ownership, processing state, checksums, timestamps, and storage keys.

```text
Object Storage
├── original/
├── processed/
├── extracted/
└── derived/
```

## 11. AI Architecture

```text
User Question
      |
      v
AI Orchestrator
      |
      +--> Patient Data Retrieval
      +--> Medical Knowledge Retrieval
      +--> Clinical Rules
      |
      v
LLM / Reasoning Layer
      |
      v
Safety Validation
      |
      v
Response Builder
      |
      v
User
```

The LLM must not be treated as the authoritative source for patient history, laboratory values, medications, diagnoses, or other patient facts. Patient data must be retrieved from the authorized patient record and supplied to the reasoning layer as controlled context.

## 12. Medical Knowledge RAG

```text
Approved Medical Sources
          |
          v
Knowledge Ingestion
          |
          v
Chunking / Metadata
          |
          v
Embeddings
          |
          v
Vector Store
          |
          v
Retriever
          |
          v
AI Orchestrator
```

Medical retrieval should be restricted to approved sources and should preserve source information so important insights can be supported and audited.

## 13. Risk Analysis Engine

```text
Authorized Patient Data
          |
          v
Feature Extraction
          |
          +--> Demographics
          +--> Symptoms
          +--> Laboratory Results
          +--> Vital Signs
          +--> Medications
          +--> Medical History
          +--> Family History
          +--> Longitudinal Trends
          |
          v
Clinical Rules / Validated Models
          |
          v
Risk Assessment
          |
          v
Safety Validation
```

## 14. Trend Analysis Engine

Trend analysis operates independently from conversational AI. It compares current measurements with historical records and identifies meaningful changes in supported measurements.

Supported measurements include:

- Blood pressure
- Glucose
- HbA1c
- Cholesterol
- Weight
- Heart rate
- Oxygen saturation
- Kidney-function markers
- Liver-function markers

## 15. Safety Architecture

```text
AI Output
    |
    v
Safety Engine
    |
    +--> Patient-data grounding check
    +--> Unsupported-claim check
    +--> Diagnosis-language check
    +--> Urgency detection
    +--> Medication safety validation
    +--> Clinical-rule validation
    +--> Escalation classification
    |
    v
Approved / Modified / Escalated Response
```

HIA must clearly distinguish confirmed diagnoses, possible conditions, risk indications, trends, and general health information. AI-generated possibilities must not be presented as confirmed diagnoses.

## 16. Explainability

Important insights should expose the finding, supporting evidence, severity, uncertainty or confidence, relevant patient data, recommended next step, and source. The UI should allow users to understand why an insight was generated without exposing unsafe or misleading internal reasoning.

## 17. Audit Architecture

```text
AIExecution
├── patient_id
├── request
├── retrieved patient-data references
├── retrieved knowledge sources
├── model
├── model version
├── prompt/version identifier
├── clinical-rule version
├── safety result
├── generated output
├── final output
├── latency
└── timestamp
```

Important patient-data and AI activities should be traceable. Where feasible, retain input data references, model/version, knowledge sources, applicable rules, validation results, and the final insight.

## 18. Security Architecture

- Strong authentication and multi-factor authentication
- Role-based access control
- Secure session and device management
- Encryption in transit
- Encryption at rest
- Secure object storage
- Signed or controlled access to medical files
- API authorization on every protected operation
- Rate limiting
- Input validation and injection protection
- Secrets management
- Security and access audit logging
- Monitoring for security events

## 19. Caching and Infrastructure Services

Redis can support:

- Caching frequently accessed non-authoritative summaries
- Rate limiting
- Temporary processing state
- Job coordination support
- Session-related infrastructure where appropriate

Redis must not become the authoritative store for medical records.

## 20. Interoperability and FHIR Readiness

The internal model should be designed so that future FHIR/EHR integration can be added without replacing the core patient-data architecture.

| HIA entity | FHIR resource |
| --- | --- |
| Patient | Patient |
| Laboratory Result | Observation |
| Medication | MedicationRequest |
| Condition | Condition |
| Allergy | AllergyIntolerance |
| Medical Document | DocumentReference |
| Procedure | Procedure |
| Encounter | Encounter |

## 21. Deployment Architecture

```text
Internet
   |
Cloudflare / WAF
   |
Load Balancer
   |
   +----------------------+----------------------+----------------------+
   |                      |                      |
   v                      v                      v
Next.js              API Instances            Workers
                          |                      |
                          +----------+-----------+
                                     |
                 +-------------------+-------------------+
                 |                   |                   |
                 v                   v                   v
            PostgreSQL             Redis              Queue
                 |
                 v
            Object Storage
```

## 22. Recommended Technology Stack

- Next.js and TypeScript
- FastAPI and Python
- PostgreSQL with pgvector
- Redis
- RabbitMQ or another durable message queue
- S3-compatible object storage
- Docker
- Terraform
- GitHub Actions

## 23. Repository Structure

```text
hia/
├── apps/
│   ├── web/
│   └── api/
├── packages/
│   ├── ui/
│   ├── types/
│   └── config/
├── services/
│   ├── document-worker/
│   ├── ai-worker/
│   ├── risk-worker/
│   └── notification-worker/
├── infrastructure/
│   ├── docker/
│   ├── terraform/
│   └── kubernetes/
└── docs/
    ├── architecture/
    ├── api/
    ├── security/
    └── ai-safety/
```

## 24. Implementation Phases

1. **Secure Foundation:** Authentication, patient profile, RBAC, MFA, audit logging, PostgreSQL, and object storage.
2. **Medical Records:** Report uploads, document processing, OCR, extraction, laboratory records, medication records, and timeline.
3. **Intelligence:** AI assistant, patient context retrieval, medical RAG, trend engine, insight generation, and explainability.
4. **Safety:** Clinical rules, risk engine, urgency detection, safety validation, escalation, and AI audit trail.
5. **Monitoring:** Disease monitoring, alerts, notifications, and longitudinal analysis.
6. **Expansion:** FHIR/EHR integrations, clinician portal, wearables, predictive models, remote monitoring, and provider collaboration.

## 25. Core Architectural Principle

The LLM is an intelligence component, not the authority. The patient record remains the source of truth; validated rules and analysis engines perform structured health analysis; retrieval supplies approved medical knowledge; the AI orchestrator coordinates reasoning; and the safety layer validates outputs before they reach users.

## 26. Requirements Alignment

This architecture is based on the supplied HIA requirements. It directly addresses requirements for secure authentication, patient profiles, medical report processing, structured laboratory data, longitudinal analysis, symptoms, medications, AI assistance, risk assessment, monitoring, alerts, explainability, medical knowledge retrieval, auditability, availability, performance, scalability, reliability, AI safety, interoperability, accessibility, observability, and disaster recovery.
