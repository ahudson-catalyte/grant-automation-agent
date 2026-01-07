# Grant Automation Agent

A local development setup for the **Grant Automation Agent** — a full‑stack application that uses FastAPI on the backend and a modern frontend to help automate grant‑related processing with OpenAI and LangChain.

## 🚀 Overview

This project combines:

- A **FastAPI backend** powered by Python and OpenAI/LangChain for document processing and AI workflows.
- A **Frontend** (React/Vite) to interact with the backend and provide the user interface.
- Document ingestion and utility libraries to support multiple file formats.

---

## 📦 Prerequisites

- Python 3.10+
- Node.js + npm
- OpenAI API Key

---

## 📁 Project Structure

```
grant-automation-agent/
├── backend/
├── frontend/
├── README.md
```

---

## 🛠️ Local Setup

### Clone Repository

```bash
git clone https://github.com/ahudson-catalyte/grant-automation-agent.git
cd grant-automation-agent
```

---

## 🔑 Backend Setup and Environment Variables

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### API Plugin

Create `backend/.env`:

```
OPENAI_API_KEY=your_openai_api_key_here
```

---

### Install Dependencies

```bash
python -m pip install fastapi "uvicorn[standard]" python-multipart
python -m pip install openai langchain langchain-openai langchain-community langchain-core
python -m pip install python-docx openpyxl pypdf python-pptx reportlab
python -m pip install icalendar python-dotenv pydantic pydantic-settings fastapi-cors
```

---

### Run Backend

```bash
python -m uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000

---

## 💻 Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000

---

## ✅ Usage

Open your browser at http://localhost:3000 to use the application.

---

## 📚 Resources

- FastAPI: https://fastapi.tiangolo.com
- LangChain: https://langchain.com
- OpenAI: https://platform.openai.com/docs
