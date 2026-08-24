# HIA — Health Insights Agent

HIA is a unified healthcare and AI health-assistant application that analyzes authorized
patient health information (reports, labs, symptoms, medications, vitals, history) to
generate explainable health insights, identify potential health risks, monitor supported
conditions, and provide next-step guidance — with human clinical oversight and safety
mechanisms throughout.

AI-generated possibilities are never presented as confirmed diagnoses.

## Repository layout

```
hia/
├── apps/
│   ├── web/            # Next.js + TypeScript frontend
│   └── api/             # FastAPI backend (auth, patients, reports, laboratory, ...)
├── packages/
│   ├── ui/               # Shared UI component library
│   ├── types/            # Shared TypeScript types
│   └── config/           # Shared config (lint, tsconfig, etc.)
├── services/
│   ├── document-worker/  # OCR / extraction
│   ├── ai-worker/        # Insight generation, RAG
│   ├── risk-worker/       # Risk / trend analysis
│   └── notification-worker/ # Alerts / escalation
├── infrastructure/
│   ├── docker/
│   ├── terraform/
│   └── kubernetes/
└── docs/
    ├── architecture/     # Requirements + system architecture docs
    ├── api/               # API design + implementation checklist
    ├── security/
    └── ai-safety/
```

## Status

Early scaffolding. See `docs/api/HIA_API_Implementation_Checklist.md` for build progress,
phased per `docs/architecture/`.

## Tech stack

Next.js + TypeScript · FastAPI + Python · PostgreSQL + pgvector · Redis · RabbitMQ ·
S3-compatible object storage · Docker · Terraform · GitHub Actions
