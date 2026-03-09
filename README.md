# Talksy

AI-powered mock exam and English conversation practice platform for **IELTS**, **PTE**, and **TOEFL** preparation.

## Features

- **Voice Practice**: Natural AI conversations for speaking improvement
- **Mock Exams**: Full practice tests for IELTS, PTE, and TOEFL
- **AI Feedback**: Instant analysis and band score predictions
- **Progress Tracking**: Monitor improvement with analytics
- **Admin Dashboard**: Manage users, exams, and questions

## Tech Stack

### Backend
- [Litestar](https://litestar.dev/) - High-performance async Python framework
- [Piccolo ORM](https://piccolo-orm.com/) - Async-native with migrations
- [LangChain](https://langchain.com/) + OpenAI for AI features
- Uvicorn server with hot reload

### Frontend
- [Vite](https://vite.dev/) + React 19 + TypeScript
- [shadcn/ui](https://ui.shadcn.com/) components
- [TailwindCSS v4](https://tailwindcss.com/)
- [TanStack Query](https://tanstack.com/query) for data fetching
- [Remix Icons](https://remixicon.com/)

## Project Structure

```
talksy/
├── src/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/           # API routes
│   │   │   ├── core/          # Logging, exceptions
│   │   │   ├── db/            # Piccolo tables
│   │   │   ├── schemas/       # Pydantic models
│   │   │   ├── services/      # Business logic
│   │   │   └── main.py        # App factory
│   │   └── piccolo_conf.py
│   └── web/                   # React frontend
│       ├── src/
│       │   ├── components/    # UI components
│       │   ├── pages/         # Route pages
│       │   │   ├── marketing/ # Landing page
│       │   │   ├── app/       # User app
│       │   │   └── admin/     # Admin dashboard
│       │   └── lib/           # Utilities
│       └── package.json
├── dev.py                     # Development server script
├── .env                       # Environment variables
├── .env.example               # Environment template
└── pyproject.toml
```

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+ with pnpm
- uv (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/hrmasss/talksy.git
cd talksy

# Install Python dependencies
uv sync

# Install frontend dependencies
cd src/web && pnpm install
cd ../..
```

### Environment Setup

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key environment variables:
- `OPENAI_API_KEY` - Required for AI features
- `JWT_SECRET` - Change in production

### Running the Development Server

```bash
# Run both API and frontend with hot reload
python dev.py
```

This starts:
- **API**: http://localhost:8000
- **Frontend**: http://localhost:5173

Or run separately:

```bash
# Backend only
cd src/backend && uvicorn app.main:app --reload

# Frontend only
cd src/web && pnpm dev
```

### Database Setup

```bash
# Create database tables
cd src/backend && python create_tables.py
```

## API Documentation

- Swagger UI: http://localhost:8000/docs/swagger
- ReDoc: http://localhost:8000/docs/redoc

## Routes

- `/` - Marketing/landing page
- `/app` - User application (voice chat, practice)

## License

MIT
