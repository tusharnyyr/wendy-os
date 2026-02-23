# Wendy OS  
### Event-Driven AI Productivity Operating System

Wendy OS is a modular, backend-first AI system designed to log activity, analyze behavioral patterns, generate weekly summaries, detect productivity drift, and trigger automation workflows.

This is not a chatbot.

It is a structured intelligence engine built with separation of concerns, deterministic routing, and event-driven architecture.

---

## 🧠 Core Architecture

Telegram → n8n → FastAPI Backend → PostgreSQL → Event Bus → n8n → Telegram

The backend is responsible for:
- Intent parsing
- Activity logging
- Analytics computation
- Drift detection
- Suggestion generation
- Event emission

Automation is handled independently through n8n webhooks.

This ensures transport-agnostic and modular design.

---

## 🚀 Key Capabilities

- AI-powered natural language activity logging
- Deterministic intent routing
- Weekly productivity summaries
- Category-level breakdown analytics
- 14-day baseline drift detection
- Streak tracking & milestone alerts
- Event-driven automation triggers
- Cron-secured scheduled workflows

---

## 🏗 System Design Principles

- Backend-first intelligence
- Deterministic routing before AI inference
- Event emission over direct execution
- Idempotent weekly analytics generation
- Strict separation between logic and automation
- Environment-variable-based secret management

---

## 🛠 Tech Stack

Backend:
- Python
- FastAPI
- PostgreSQL

Automation:
- n8n

Integration:
- Telegram Bot API

AI Layer:
- Groq LLM

---

n8n workflow template included in repository.

---

## 🔐 Security

- No API keys stored in repository
- Environment variables required for deployment
- Sanitized workflow JSON
- No hardcoded tokens

---
## Repository Structure

├── main.py
├── requirements.txt
├── database/
│   ├── __init__.py
│   ├── base.py
│   └── models.py
├── services/
│   ├── __init__.py
│   ├── intent_router.py
│   ├── logging_service.py
│   ├── analytics_service.py
│   ├── drift_service.py
│   ├── suggestion_engine.py
│   ├── weekly_summary_service.py
│   ├── event_bus.py
│   └── integrations/
│       ├── __init__.py
│       └── n8n_adapter.py
├── wendy_os_v04_n8n_workflow.json
├── .env.example
└── LICENSE

## 🗺 Version Evolution

v0.1 — Core logging engine  
v0.2 — Conversational intelligence layer  
v0.3 — Event-driven automation integration  
v0.4 — Telegram integration + analytics + drift detection  

---

## 📌 Status

Actively evolving toward production hardening and multi-user deployment.

---

Wendy OS is an exploration in applied system design — combining AI, backend architecture, automation orchestration, and behavioral analytics into a cohesive operating layer.
=======
# \# Wendy OS  

# \### Event-Driven AI Productivity Operating System

# 

# Wendy OS is a modular, backend-first AI system designed to log activity, analyze behavioral patterns, generate weekly summaries, detect productivity drift, and trigger automation workflows.

# 

# This is not a chatbot.

# 

# It is a structured intelligence engine built with separation of concerns, deterministic routing, and event-driven architecture.

# 

# ---

# 

# \## 🧠 Core Architecture

# 

# Telegram → n8n → FastAPI Backend → PostgreSQL → Event Bus → n8n → Telegram

# 

# The backend is responsible for:

# \- Intent parsing

# \- Activity logging

# \- Analytics computation

# \- Drift detection

# \- Suggestion generation

# \- Event emission

# 

# Automation is handled independently through n8n webhooks.

# 

# This ensures transport-agnostic and modular design.

# 

# ---

# 

# \## 🚀 Key Capabilities

# 

# \- AI-powered natural language activity logging

# \- Deterministic intent routing

# \- Weekly productivity summaries

# \- Category-level breakdown analytics

# \- 14-day baseline drift detection

# \- Streak tracking \& milestone alerts

# \- Event-driven automation triggers

# \- Cron-secured scheduled workflows

# 

# ---

# 

# \## 🏗 System Design Principles

# 

# \- Backend-first intelligence

# \- Deterministic routing before AI inference

# \- Event emission over direct execution

# \- Idempotent weekly analytics generation

# \- Strict separation between logic and automation

# \- Environment-variable-based secret management

# 

# ---

# 

# \## 🛠 Tech Stack

# 

# Backend:

# \- Python

# \- FastAPI

# \- PostgreSQL

# 

# Automation:

# \- n8n

# 

# Integration:

# \- Telegram Bot API

# 

# AI Layer:

# \- Groq LLM

# 

# ---

# 

# n8n workflow template included in repository.

# 

# ---

# 

# \## 🔐 Security

# 

# \- No API keys stored in repository

# \- Environment variables required for deployment

# \- Sanitized workflow JSON

# \- No hardcoded tokens

# 

# ---

# \## Repository Structure

# 

# ├── main.py

# ├── requirements.txt

# ├── database/

# │   ├── \_\_init\_\_.py

# │   ├── base.py

# │   └── models.py

# ├── services/

# │   ├── \_\_init\_\_.py

# │   ├── intent\_router.py

# │   ├── logging\_service.py

# │   ├── analytics\_service.py

# │   ├── drift\_service.py

# │   ├── suggestion\_engine.py

# │   ├── weekly\_summary\_service.py

# │   ├── event\_bus.py

# │   └── integrations/

# │       ├── \_\_init\_\_.py

# │       └── n8n\_adapter.py

# ├── wendy\_os\_v04\_n8n\_workflow.json

# ├── .env.example

# └── LICENSE

# 

# \## 🗺 Version Evolution

# 

# v0.1 — Core logging engine  

# v0.2 — Conversational intelligence layer  

# v0.3 — Event-driven automation integration  

# v0.4 — Telegram integration + analytics + drift detection  

# 

# ---

# 

# \## 📌 Status

# 

# Actively evolving toward production hardening and multi-user deployment.

# 

# ---

# 

# Wendy OS is an exploration in applied system design — combining AI, backend architecture, automation orchestration, and behavioral analytics into a cohesive operating layer.



>>>>>>> 0f2d3eb (Minor README update)
