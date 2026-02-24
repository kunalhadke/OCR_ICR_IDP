● Now I have the full picture. This is a Protean/NSDL-grade PAN processing system with very specific SLAs. Let me give you a complete breakdown.

  ---
  Complete Requirements Analysis

  What The Document Demands

  ┌────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────┐
  │          Requirement           │                                   Detail                                    │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Volume                         │ 5K-6K/hr normal, 8K-12K/hr peak months                                      │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Mode 1 - Scanned/Physical      │ Match Name (100%), Address (100% PIN+State, 70% rest), DOB (100%)           │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Mode 2 - eKYC                  │ Match only DOB (100%)                                                       │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ TAT - L1 Auto Approved (>75%)  │ 1 hour                                                                      │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ TAT - L2 Second Level (40-75%) │ 1-2 hours                                                                   │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ TAT - Manual Review (<40%)     │ 2-4 hours                                                                   │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Document Types                 │ 30+ types (not just 5)                                                      │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Features                       │ Data correction screens, re-submission, bulk export, FIFO dashboard, alerts │
  ├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ Source                         │ Scanned PDFs from Protean DMS via server path                               │
  └────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────┘

  Critical Observations

  1. ICR (Intelligent Character Recognition) is MANDATORY - PAN 49A forms have handwritten fields (name, address, DOB in boxes)
  2. 30+ document types - Not just Aadhaar/Passport/DL/Voter, but also ration cards, utility bills, property docs, marriage certificates, affidavits,      
  company registrations, trust deeds, etc.
  3. 1-hour TAT for L1 means your pipeline must process + verify within 60 minutes including queue time
  4. Interruption alerts - Need real-time monitoring with alerting

  ---
  Complete Tech Stack Recommendation

  1. OCR / ICR / IDP Engine (The Core Brain)

  ┌──────────────────────────┬──────────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────┐  
  │          Layer           │                          Technology                          │                            Why                            │  
  ├──────────────────────────┼──────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤  
  │ Printed Text OCR         │ PaddleOCR (current) OR Google Document AI OR Azure Form      │ High accuracy on printed Indian docs                      │  
  │                          │ Recognizer                                                   │                                                           │  
  ├──────────────────────────┼──────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤  
  │ Handwritten ICR          │ Microsoft Azure AI Document Intelligence OR Google Document  │ PAN 49A has handwritten box fields - PaddleOCR alone      │  
  │                          │ AI OR Custom TrOCR model                                     │ CANNOT handle this reliably                               │  
  ├──────────────────────────┼──────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤  
  │ Document Classification  │ Custom ML model (LayoutLMv3 / Donut) + Rule-based fallback   │ 30+ doc types need ML, not just regex                     │  
  │ (IDP)                    │                                                              │                                                           │  
  ├──────────────────────────┼──────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤  
  │ Table/Form Extraction    │ Azure Form Recognizer OR DocTR + LayoutParser                │ Structured field extraction from forms                    │  
  ├──────────────────────────┼──────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤  
  │ Image Pre-processing     │ OpenCV + Pillow                                              │ Deskew, denoise, binarize scanned docs                    │  
  └──────────────────────────┴──────────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┘  

  Option A: Cloud AI (Faster to Deploy, Per-Call Cost)

  ┌─────────────────────────────────────────────────────┐
  │           CLOUD AI APPROACH                         │
  ├─────────────────────────────────────────────────────┤
  │                                                     │
  │  Azure AI Document Intelligence (Form Recognizer)   │
  │  ├─ Prebuilt: ID Document model (Aadhaar, Passport) │
  │  ├─ Custom: Train for PAN 49A form                  │
  │  └─ Handles BOTH printed + handwritten              │
  │                                                     │
  │  Cost: ~$1.5 per 1000 pages (Read API)              │
  │        ~$50 per 1000 pages (Custom model)           │
  │                                                     │
  │  At 12K PDFs/hr × 6 pages = 72K pages/hr            │
  │  Monthly: ~50M pages = $75K-$150K/month             │
  │                                                     │
  │  ⚠️  EXPENSIVE at this scale                        │
  └─────────────────────────────────────────────────────┘

  Option B: Self-Hosted (Recommended for This Scale)

  ┌─────────────────────────────────────────────────────┐
  │          SELF-HOSTED APPROACH (RECOMMENDED)          │
  ├─────────────────────────────────────────────────────┤
  │                                                     │
  │  PaddleOCR (Printed Text)      ← You already have   │
  │  + TrOCR / Custom CNN-LSTM     ← For handwritten    │
  │  + LayoutLMv3                  ← Doc classification  │
  │  + Custom Field Extractors     ← Per doc type        │
  │  + OpenCV Pipeline             ← Image preprocessing │
  │                                                     │
  │  Cost: Server infra only (~$8K-15K/month cloud)     │
  │                                                     │
  │  ✅ MUCH cheaper at 50M+ pages/month                │
  └─────────────────────────────────────────────────────┘

  Option C: Hybrid (Best Balance)

  ┌─────────────────────────────────────────────────────┐
  │            HYBRID APPROACH (BEST)                    │
  ├─────────────────────────────────────────────────────┤
  │                                                     │
  │  Self-Hosted PaddleOCR     → Printed text (80% docs)│
  │  Self-Hosted TrOCR/Custom  → Handwritten PAN forms  │
  │  Self-Hosted LayoutLMv3    → Doc classification      │
  │  Azure Form Recognizer     → Fallback for low-conf  │
  │                             only (~5-10% of volume)  │
  │                                                     │
  │  Cost: ~$10K-12K/month (infra + minimal cloud API)  │
  │                                                     │
  │  ✅ RECOMMENDED                                     │
  └─────────────────────────────────────────────────────┘

  ---
  2. Complete Tech Stack

  ╔══════════════════════════════════════════════════════════════╗
  ║                    COMPLETE TECH STACK                       ║
  ╠══════════════════════╦═══════════════════════════════════════╣
  ║                      ║                                       ║
  ║  ── BACKEND ──       ║                                       ║
  ║  Language            ║  Python 3.11+                         ║
  ║  API Framework       ║  FastAPI + Uvicorn + Gunicorn         ║
  ║  Task Queue          ║  Celery 5.4+                          ║
  ║  Message Broker      ║  RabbitMQ (or Kafka for >10K/hr)      ║
  ║  Cache               ║  Redis 7+ (result cache + sessions)   ║
  ║                      ║                                       ║
  ║  ── OCR/ICR/IDP ──   ║                                       ║
  ║  Printed OCR         ║  PaddleOCR 2.9+ (GPU)                 ║
  ║  Handwritten ICR     ║  TrOCR (fine-tuned on PAN forms)      ║
  ║                      ║  OR EasyOCR + Custom CRNN model       ║
  ║  Doc Classification  ║  LayoutLMv3 (fine-tuned on 30+ types) ║
  ║  Form Extraction     ║  DocTR + Custom extractors per type    ║
  ║  Image Preprocessing ║  OpenCV 4.9+ (deskew, denoise, crop)  ║
  ║  PDF Processing      ║  pdf2image + Poppler                  ║
  ║  Fuzzy Matching      ║  RapidFuzz 3.9+                       ║
  ║  ML Framework        ║  PyTorch 2.2+ / Paddl2ePaddle 3.0+    ║
  ║  Cloud Fallback      ║  Azure Form Recognizer (optional)     ║
  ║                      ║                                       ║
  ║  ── DATABASE ──      ║                                       ║
  ║  Primary DB          ║  PostgreSQL 16 + PgBouncer            ║
  ║  Search/Analytics    ║  Elasticsearch 8 (optional, for logs) ║
  ║  File Metadata       ║  PostgreSQL (JSONB columns)           ║
  ║                      ║                                       ║
  ║  ── STORAGE ──       ║                                       ║
  ║  Object Storage      ║  MinIO (S3-compatible, self-hosted)   ║
  ║                      ║  OR AWS S3                            ║
  ║  Hot Storage         ║  NVMe SSD (processing temp files)     ║
  ║  Cold Archive        ║  S3 Glacier / Tape (>90 day old)      ║
  ║                      ║                                       ║
  ║  ── FRONTEND ──      ║                                       ║
  ║  Dashboard           ║  React.js / Next.js                   ║
  ║  Data Correction UI  ║  React + Custom form components       ║
  ║  Real-time Updates   ║  WebSocket (FastAPI WebSocket)        ║
  ║  Export              ║  Apache POI / openpyxl (bulk export)  ║
  ║                      ║                                       ║
  ║  ── INFRA ──         ║                                       ║
  ║  Container           ║  Docker                               ║
  ║  Orchestration       ║  Kubernetes (K8s)                     ║
  ║  Auto-Scaling        ║  K8s HPA + KEDA                       ║
  ║  Load Balancer       ║  Nginx / HAProxy / AWS ALB            ║
  ║  CI/CD               ║  GitLab CI / Jenkins                  ║
  ║                      ║                                       ║
  ║  ── MONITORING ──    ║                                       ║
  ║  Metrics             ║  Prometheus + Grafana                  ║
  ║  Logging             ║  ELK Stack (Elasticsearch+Logstash+   ║
  ║                      ║  Kibana) OR Loki+Promtail             ║
  ║  Alerting            ║  Grafana Alerts / PagerDuty           ║
  ║  APM                 ║  Jaeger (distributed tracing)         ║
  ║                      ║                                       ║
  ║  ── SECURITY ──      ║                                       ║
  ║  Auth                ║  Keycloak / LDAP (enterprise SSO)     ║
  ║  API Security        ║  OAuth 2.0 + JWT                      ║
  ║  Encryption          ║  TLS 1.3 + AES-256 at rest           ║
  ║  Audit               ║  Complete audit trail (DB + logs)     ║
  ║  PII Handling        ║  Data masking, access controls        ║
  ╚══════════════════════╩═══════════════════════════════════════╝

  ---
  3. Server / Deployment Architecture

  ┌──────────────────────────────────────────────────────────────────┐
  │                    PRODUCTION ARCHITECTURE                        │
  └──────────────────────────────────────────────────────────────────┘

    Protean DMS ──► Shared Server Path (NFS/SMB Mount)
                           │
                           ▼
    ┌──────────────────────────────────────┐
    │        FILE WATCHER SERVICE          │
    │   (inotify / watchdog daemon)        │
    │   Detects new PDFs on server path    │
    │   Pushes jobs to Message Queue       │
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │     RABBITMQ / KAFKA CLUSTER        │
    │          (3-node HA)                 │
    │                                      │
    │   Queues:                           │
    │   ├─ pdf.intake        (raw PDFs)   │
    │   ├─ ocr.processing    (OCR jobs)   │
    │   ├─ matching.verify   (match jobs) │
    │   ├─ review.l2         (L2 queue)   │
    │   └─ export.bulk       (exports)    │
    └──────────────────┬───────────────────┘
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
    ┌─────────┐  ┌─────────┐   ┌─────────┐
    │ STAGE 1 │  │ STAGE 1 │   │ STAGE 1 │    ×8-12 pods
    │ PDF →   │  │ PDF →   │   │ PDF →   │
    │ Images  │  │ Images  │   │ Images  │
    │ +Preproc│  │ +Preproc│   │ +Preproc│
    └────┬────┘  └────┬────┘   └────┬────┘
         │            │              │
         ▼            ▼              ▼
    ┌─────────┐  ┌─────────┐   ┌─────────┐
    │ STAGE 2 │  │ STAGE 2 │   │ STAGE 2 │    ×15-20 pods (GPU)
    │ OCR/ICR │  │ OCR/ICR │   │ OCR/ICR │
    │ Engine  │  │ Engine  │   │ Engine  │
    │ (GPU)   │  │ (GPU)   │   │ (GPU)   │
    └────┬────┘  └────┬────┘   └────┬────┘
         │            │              │
         ▼            ▼              ▼
    ┌─────────┐  ┌─────────┐   ┌─────────┐
    │ STAGE 3 │  │ STAGE 3 │   │ STAGE 3 │    ×8-10 pods
    │Classify │  │Classify │   │Classify │
    │+Extract │  │+Extract │   │+Extract │
    │+Match   │  │+Match   │   │+Match   │
    └────┬────┘  └────┬────┘   └────┬────┘
         │            │              │
         ▼            ▼              ▼
    ┌──────────────────────────────────────┐
    │         POSTGRESQL CLUSTER           │
    │    Primary + 2 Read Replicas         │
    │    + PgBouncer (connection pool)     │
    └──────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │         APPLICATION LAYER            │
    │                                      │
    │  ├─ Dashboard API (FastAPI ×3)       │
    │  ├─ Data Correction UI (React)       │
    │  ├─ Bulk Export Service              │
    │  ├─ Alert Service (PagerDuty/Email)  │
    │  └─ WebSocket (real-time updates)    │
    └──────────────────────────────────────┘

  ---
  4. Server Specifications

  For 12K PDFs/Hour (Peak) Capacity

  ┌──────────────────────────┬─────┬──────┬────────┬───────────────────────────────────┬────────────────────────┬──────────────┐
  │       Server Role        │ Qty │ vCPU │  RAM   │                GPU                │        Storage         │      OS      │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ OCR/ICR Workers (GPU)    │ 6-8 │ 16   │ 64 GB  │ 1× NVIDIA A10 (24GB) or T4 (16GB) │ 500 GB NVMe            │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ PDF Processing Workers   │ 4-6 │ 8    │ 32 GB  │ None                              │ 256 GB SSD             │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ Classification/Matching  │ 4-6 │ 8    │ 32 GB  │ None (or 1× T4 for LayoutLMv3)    │ 256 GB SSD             │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ API/Web Servers          │ 3   │ 8    │ 16 GB  │ None                              │ 128 GB SSD             │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ PostgreSQL Primary       │ 1   │ 16   │ 128 GB │ None                              │ 2 TB NVMe              │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ PostgreSQL Replicas      │ 2   │ 16   │ 64 GB  │ None                              │ 2 TB NVMe              │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ RabbitMQ/Kafka Cluster   │ 3   │ 8    │ 32 GB  │ None                              │ 512 GB SSD             │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ Redis Cache              │ 2   │ 4    │ 32 GB  │ None                              │ 128 GB SSD             │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ MinIO Storage            │ 3   │ 8    │ 32 GB  │ None                              │ 10 TB HDD + 512 GB SSD │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ Monitoring (Grafana/ELK) │ 2   │ 8    │ 32 GB  │ None                              │ 1 TB SSD               │ Ubuntu 22.04 │
  ├──────────────────────────┼─────┼──────┼────────┼───────────────────────────────────┼────────────────────────┼──────────────┤
  │ Load Balancer            │ 2   │ 4    │ 8 GB   │ None                              │ 64 GB SSD              │ Ubuntu 22.04 │
  └──────────────────────────┴─────┴──────┴────────┴───────────────────────────────────┴────────────────────────┴──────────────┘

  | TOTAL | 32-38 servers | | | 6-8 GPUs | | |

  ---
  5. The 30+ Document Type Challenge

  Your document lists these categories that OCR/ICR/IDP must handle:

  ══════════════════════════════════════════════════════════════
    CATEGORY 1: Identity Proofs (Printed + Photo)
  ══════════════════════════════════════════════════════════════
    ✅ Aadhaar Card                    ← Structured, OCR-friendly
    ✅ Indian Passport                 ← Structured, MRZ readable
    ✅ Driving Licence                 ← Semi-structured, varies by state
    ✅ Voter ID (EPIC)                 ← Semi-structured
    🆕 Ration Card (with photo)       ← VERY varied format per state
    🆕 Transgender ID Card            ← New document type
    🆕 Govt Photo ID (Central/State)  ← Multiple formats
    🆕 Pensioner Card                 ← Varied formats
    🆕 CGHS / ECHS Card              ← Specific format
    🆕 Bank Certificate (letterhead)  ← Unstructured, handwritten possible
    🆕 MP/MLA/Gazetted Officer Cert   ← Handwritten/typed certificate

  ══════════════════════════════════════════════════════════════
    CATEGORY 2: Address Proofs (Printed)
  ══════════════════════════════════════════════════════════════
    🆕 Post Office Passbook           ← Semi-structured
    🆕 Domicile Certificate           ← Govt format, varies by state
    🆕 Govt Accommodation Letter      ← Typed/printed letter
    🆕 Property Registration          ← Legal document, complex
    🆕 Property Tax Order             ← Govt format
    🆕 Electricity Bill               ← Varies by provider
    🆕 Telephone/Broadband Bill       ← Varies by provider
    🆕 Water Bill                     ← Varies by provider
    🆕 Gas Connection Card/Bill       ← Varies by provider
    🆕 Bank Statement                 ← Tabular, varies by bank
    🆕 Depository Statement           ← Financial document
    🆕 Credit Card Statement          ← Financial document
    🆕 Employer Certificate           ← Letterhead, unstructured

  ══════════════════════════════════════════════════════════════
    CATEGORY 3: DOB Proofs
  ══════════════════════════════════════════════════════════════
    🆕 Birth Certificate              ← Govt, varies massively by state
    🆕 Marriage Certificate           ← Govt format
    🆕 Matriculation Certificate      ← Board exam, varies by board
    🆕 Pension Payment Order          ← Govt format
    🆕 Affidavit (sworn before court) ← HANDWRITTEN/typed, legal stamp

  ══════════════════════════════════════════════════════════════
    CATEGORY 4: Entity Documents (Non-Individual)
  ══════════════════════════════════════════════════════════════
    🆕 Company Registration Cert      ← MCA format
    🆕 LLP Registration               ← MCA format
    🆕 Partnership Deed               ← Legal, unstructured
    🆕 Trust Deed                     ← Legal, unstructured
    🆕 Charity Commissioner Cert      ← Govt format
    🆕 Cooperative Society Cert       ← Varies by state
    🆕 Govt Dept Certificate          ← Various
    🆕 HUF Affidavit                  ← Handwritten/typed

  ══════════════════════════════════════════════════════════════
    TOTAL: 35+ DOCUMENT TYPES (your current system handles 5)
  ══════════════════════════════════════════════════════════════

  This means you need LayoutLMv3 or similar ML-based classifier, not just regex patterns.

  ---
  6. Processing Pipeline (Per The TAT Requirements)

  ═══════════════════════════════════════════════════════
    TAT: 1 HOUR for L1 (Auto Approved >75%)
    That means: Intake → OCR → Match → Result in <60 min
    At 12K/hr = 200 PDFs/min = 3.3 PDFs/sec
  ═══════════════════════════════════════════════════════

    TIME BUDGET PER PDF (must be <60 min end-to-end):

    ┌────────────────────────┬───────────────┐
    │ Step                   │ Target Time   │
    ├────────────────────────┼───────────────┤
    │ Queue wait time        │ < 5 min       │
    │ PDF → Images           │ < 3 sec       │
    │ Image preprocessing    │ < 2 sec       │
    │ OCR/ICR (5-6 pages)    │ < 10 sec      │
    │ Doc classification     │ < 2 sec       │
    │ Field extraction       │ < 3 sec       │
    │ Matching + scoring     │ < 1 sec       │
    │ DB write + result      │ < 1 sec       │
    ├────────────────────────┼───────────────┤
    │ TOTAL PROCESSING       │ ~22 sec       │
    │ TOTAL WITH QUEUE       │ < 10 min      │
    └────────────────────────┴───────────────┘

    ✅ Easily within 1-hour TAT with proper infra

  ---
  7. Cost Summary

  ┌────────────────────────────────────┬────────────────────────────────────────────────┬────────────┐
  │             Deployment             │                  Monthly Cost                  │ Setup Time │
  ├────────────────────────────────────┼────────────────────────────────────────────────┼────────────┤
  │ On-Premise (32-38 servers)         │ CapEx: $350K-$500K one-time, OpEx: ~$15K/month │ 4-6 months │
  ├────────────────────────────────────┼────────────────────────────────────────────────┼────────────┤
  │ Cloud (AWS/Azure)                  │ $12K-$20K/month (with reserved instances)      │ 2-3 months │
  ├────────────────────────────────────┼────────────────────────────────────────────────┼────────────┤
  │ Hybrid (GPU on-prem + cloud infra) │ CapEx: $150K + $8K-12K/month                   │ 3-4 months │
  └────────────────────────────────────┴────────────────────────────────────────────────┴────────────┘

  ---
  8. What You Must Build Beyond Current MVP

  ┌───────────────────────┬─────────────────┬───────────────────────────────────────────────┐
  │        Feature        │  Current State  │                   Required                    │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Document Types        │ 5 types (regex) │ 35+ types (ML model)                          │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Handwriting OCR       │ None            │ ICR engine (TrOCR/Custom)                     │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Data Correction UI    │ None            │ Full React UI with form editing               │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Re-submission         │ None            │ Modified records → re-verify pipeline         │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Bulk Export           │ None            │ CSV/Excel export for Ack Nos                  │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ FIFO Dashboard        │ Basic           │ Real-time, WebSocket, FIFO tracking           │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Alert System          │ None            │ Red flag alerts, email/SMS/PagerDuty          │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Processing Modes      │ Single          │ Scanned mode + eKYC mode (DOB only)           │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Auth/RBAC             │ None            │ Role-based access (operator, reviewer, admin) │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Audit Trail           │ None            │ Complete logging of who did what when         │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Concurrent Processing │ Single-thread   │ 35-84 parallel workers                        │
  ├───────────────────────┼─────────────────┼───────────────────────────────────────────────┤
  │ Database              │ SQLite          │ PostgreSQL cluster                            │
  └───────────────────────┴─────────────────┴───────────────────────────────────────────────┘

  ---
  This is a 4-6 month enterprise project requiring a team of 8-12 engineers. Want me to create a detailed phase-wise implementation roadmap, or start with 
  any specific component (like the Celery worker setup, or the LayoutLMv3 document classifier)?