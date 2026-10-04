# Panna Biryani CRM — Backend Service

High-performance internal API service for Panna Biryani CRM built with FastAPI, SQLAlchemy 2.x, Pydantic v2, and MySQL.

## Architecture

```
app/
├── main.py              # Application entrypoint, lifespan, CORS, error handling
├── core/                # Core configurations, database, security, logging, exceptions
├── api/v1/              # Versioned API routes (health, auth, orders, menu, etc.)
├── models/              # SQLAlchemy 2.x ORM models
├── schemas/             # Pydantic validation and serialization schemas
├── services/            # Pure business logic layer
├── repositories/        # Database access and query encapsulation
├── dependencies/        # FastAPI dependency injection (DB sessions, Auth, Roles)
└── utils/               # Shared helper functions
```

## Quick Start (Local Development)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   ```
   By default, local development uses SQLite (`sqlite:///./panna_crm.db`).
   For MySQL, update `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL="mysql+pymysql://panna_user:panna_secure_pass@localhost:3306/panna_crm"
   ```

3. **Start the API Server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **Default Credentials**:
   On initial startup, an administrator account is seeded automatically:
   - **Username**: `admin`
   - **Password**: `admin123`

5. **API Documentation**:
   - Interactive Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Alternative ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

6. **Run Tests**:
   ```bash
   pytest tests/ -v
   ```
