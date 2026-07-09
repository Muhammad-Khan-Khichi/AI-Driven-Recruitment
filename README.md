---
title: HireAI
emoji: 🚀
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---
# HireAI

**AI-powered job search platform — from resume upload to interview-ready, end to end.**

🔗 Live demo: [https://muhammadkhankhihci-hireai.hf.space](https://ai-driven-recruitment-frontend.vercel.app/)

---

## Overview

HireAI is a full-stack AI job search platform built and deployed end-to-end. It takes a candidate from resume upload through job matching, application tracking, and interview preparation — combining LLM-powered resume parsing, semantic job matching, and a suite of AI career tools into one production application.

---

## Key Features

- **Authentication** — JWT + OAuth2 (Google, LinkedIn) login, deployed via Docker on Hugging Face Spaces (backend) and Vercel (React/Vite frontend)
- **Resume-driven job search pipeline** — extracts skills via LLM (Mistral AI), generates smart keyword combinations, and scores/ranks job matches against parsed resume data
- **Resume deduplication** — content-hash-based detection skips redundant LLM processing and cuts unnecessary API costs on repeat uploads
- **AI career tools:**
  - Resume optimization & scoring
  - LinkedIn profile & headline optimization
  - Mock interview question generation with answer evaluation
  - Personalized interview study plans
  - Multi-variant cover letter generation
- **Semantic search** — vector embedding-based job matching layer for retrieving relevant jobs beyond exact keyword matches
- **Admin dashboard** — platform-wide analytics: users, resumes, searches, and applications
- **Application tracking** — status updates, notes, and smart multi-factor job filtering (salary, remote, experience level, keywords)

---

## Tech Stack

**Backend**
- FastAPI
- PostgreSQL ([Neon](https://neon.tech))
- SQLAlchemy
- LangChain
- Mistral AI (LLM)
- Qdrant Cloud (vector database for semantic search)
- sentence-transformers (embeddings)

**Frontend**
- React
- Vite
- Tailwind CSS
- Zustand

**Infrastructure**
- Docker
- Hugging Face Spaces (backend hosting)
- Vercel (frontend hosting)

---

## Architecture

```
Resume Upload → LLM Skill Extraction (Mistral) → Job Board Search
                                                        ↓
                                          Semantic Indexing (Qdrant Cloud)
                                                        ↓
                                        Semantic Search + AI Ranking
                                                        ↓
                                          Ranked Job Matches → User
```

Job postings and resumes are embedded using `sentence-transformers` (`all-MiniLM-L6-v2`) and stored in Qdrant Cloud, enabling semantic similarity search that goes beyond exact keyword matching — surfacing relevant jobs even when the phrasing differs from the resume.

---

## API Overview

The full interactive API reference is available at [`/docs`](https://muhammadkhankhihci-hireai.hf.space/docs).

| Module | Description |
|---|---|
| **Authentication** | Signup, login, OAuth (Google/LinkedIn), password reset |
| **Jobs** | Resume upload, job search, search-by-resume, application tracking, filtering |
| **Semantic Search** | Vector indexing and semantic job search (Qdrant-backed) |
| **Resume** | Resume optimization and quick scoring |
| **LinkedIn** | Profile and headline optimization |
| **Interview** | Question generation, answer evaluation, study plans |
| **Cover Letter** | Generation, listing, editing, deletion |
| **Profile** | Account management, password changes |
| **Admin** | User management, platform stats, resume/search/application oversight |

---

## Environment Variables

```
# Database
DATABASE_URL=

# LLM
MISTRAL_API_KEY=

# Vector Search (Qdrant Cloud)
QDRANT_URL=
QDRANT_API_KEY=

# Auth
JWT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=

# Email (optional — falls back to console logging if unset)
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
```

---

## Running Locally

```bash
# Clone the repo
git clone <repo-url>
cd hireai

# Install dependencies
pip install -r requirements.txt --break-system-packages

# Set up environment variables (see above)
cp .env.example .env

# Run the backend
uvicorn main:app --reload --port 7860
```

Frontend setup (if in a separate repo/directory):
```bash
npm install
npm run dev
```

---

## Deployment

- **Backend** — Dockerized and deployed on Hugging Face Spaces
- **Frontend** — Deployed on Vercel
- **Database** — Neon (serverless PostgreSQL)
- **Vector Store** — Qdrant Cloud

---

## License

This project is for portfolio/demonstration purposes. Contact the author for licensing inquiries.
