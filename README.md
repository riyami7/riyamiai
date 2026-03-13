# AI Chatbot LLM

A FastAPI-based AI chatbot application with a clean architecture (routes, services, repositories), JWT authentication, and role-based access control (RBAC).

## Requirements

- Python 3.11+
- PostgreSQL 16+
- Docker & Docker Compose (for database)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ai-chatbot-llm
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file for environment variables:
   ```bash
   cp .env.example .env
   ```

## Database Setup

### Start PostgreSQL with Docker Compose

```bash
docker-compose up -d
```

This starts a PostgreSQL 16 container with the configuration from your `.env` file.

### Stop the database

```bash
docker-compose down
```

### View database logs

```bash
docker-compose logs -f postgres
```

## Database Migrations

We use Alembic for database migrations.

### Run all pending migrations

```bash
alembic upgrade head
```

### Rollback last migration

```bash
alembic downgrade -1
```

### Rollback all migrations

```bash
alembic downgrade base
```

### Check current migration status

```bash
alembic current
```

### View migration history

```bash
alembic history
```

### Create a new migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "description_of_changes"

# Create empty migration
alembic revision -m "description_of_changes"
```

## Running the Application

Start the development server:

```bash
uvicorn app.main:app --reload --host localhost --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/docs
- Alternative docs (ReDoc): http://localhost:8000/redoc

## API Endpoints

### Root

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Welcome message |

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | No | Login with email and password, returns JWT token |
| GET | `/auth/me` | Yes | Get current authenticated user's profile |

### System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/system/health` | No | Health check |
| GET | `/system/info` | No | System information |

### Users

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/users/` | Yes | Admin | Create a new user |
| GET | `/users/` | Yes | Any | List all users (with pagination) |
| GET | `/users/{id}` | Yes | Any | Get a user by ID |
| PUT | `/users/{id}` | Yes | Any | Update a user |
| DELETE | `/users/{id}` | Yes | Any | Delete a user |

## Authentication & Authorization

The API uses JWT (JSON Web Tokens) for authentication and role-based access control (RBAC) for authorization. Protected endpoints require a valid Bearer token in the `Authorization` header.

### Roles

| Role | Description |
|------|-------------|
| `admin` | Can create users and access all endpoints |
| `user` | Can access all endpoints except user creation |

### Initial Setup: Create the First Admin

Since `POST /users/` requires admin authentication, you need to bootstrap the first admin user using the seed script:

```bash
python -m scripts.create_admin
```

This will interactively prompt you for email, name, and password, then create an admin user directly in the database.

### Authentication Flow

1. **Login** to get an access token via `POST /auth/login`:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@example.com", "password": "securepassword123"}'
   ```
   Response:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIs...",
     "token_type": "bearer"
   }
   ```

2. **Create users** via `POST /users/` (admin only):
   ```bash
   curl -X POST http://localhost:8000/users/ \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <admin_token>" \
     -d '{"email": "user@example.com", "name": "John Doe", "password": "securepassword123", "role": "user"}'
   ```

3. **Use the token** to access protected endpoints:
   ```bash
   curl http://localhost:8000/auth/me \
     -H "Authorization: Bearer <your_token>"

   curl http://localhost:8000/users/ \
     -H "Authorization: Bearer <your_token>"
   ```

### Token Details

- Algorithm: HS256
- Default expiration: 30 minutes
- Payload includes: `sub` (user ID), `role` (user role), `exp`, `iat`
- Configurable via `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `JWT_EXPIRATION_MINUTES` environment variables

### Error Responses

| Status | Error Code | Description |
|--------|------------|-------------|
| 401 | `INVALID_TOKEN` | Missing, invalid, or expired JWT token |
| 401 | `USER_NOT_FOUND` | Token belongs to a deleted user |
| 401 | `USER_DISABLED` | User account is disabled |
| 403 | `INSUFFICIENT_ROLE` | User does not have the required role |

## Testing

### Run all tests

```bash
pytest
```

### Run tests with verbose output

```bash
pytest -v
```

### Run specific test file

```bash
pytest tests/integration/test_users.py
pytest tests/integration/test_auth.py
```

### Run specific test class

```bash
pytest tests/integration/test_users.py::TestUserCRUD
pytest tests/integration/test_users.py::TestRBAC
pytest tests/integration/test_auth.py::TestAuthLogin
```

### Run specific test

```bash
pytest tests/integration/test_users.py::TestRBAC::test_create_user_as_regular_user_forbidden
```

### Generate HTML test report

```bash
pytest --html=reports/report.html --self-contained-html
```

Then open `reports/report.html` in your browser.

### Run tests with coverage (if pytest-cov is installed)

```bash
pytest --cov=app --cov-report=html
```

## Project Structure

```
ai-chatbot-llm/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Application configuration (incl. JWT settings)
│   ├── db.py                # Database connection and session
│   ├── exceptions.py        # Custom exception classes
│   ├── handlers.py          # Global exception handlers
│   ├── dependencies/        # Dependency injection modules
│   │   ├── __init__.py
│   │   └── auth.py          # get_current_user(), require_role() dependencies
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   └── user.py
│   ├── schemas/             # Pydantic schemas (request/response)
│   │   ├── __init__.py
│   │   ├── auth.py          # LoginRequest, TokenResponse
│   │   ├── error.py
│   │   ├── health.py
│   │   ├── system.py
│   │   └── user.py
│   ├── routes/              # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py          # POST /auth/login, GET /auth/me
│   │   ├── system.py
│   │   └── users.py
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth.py          # AuthService (authenticate)
│   │   └── user.py
│   ├── repositories/        # Data access layer
│   │   ├── __init__.py
│   │   └── user.py
│   └── utils/               # Utility modules
│       ├── __init__.py
│       └── security.py      # Password hashing, JWT token create/decode
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   ├── env.py
│   └── script.py.mako
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── integration/
│       ├── __init__.py
│       ├── test_auth.py     # Auth endpoint tests
│       └── test_users.py    # User endpoint tests (with auth)
├── scripts/                 # Utility scripts
│   └── create_admin.py      # Bootstrap the first admin user
├── reports/                 # Test reports (generated)
├── .env                     # Environment variables
├── .env.example             # Example environment variables
├── .gitignore
├── alembic.ini              # Alembic configuration
├── docker-compose.yml       # Docker Compose for PostgreSQL
├── pytest.ini               # Pytest configuration
├── README.md
└── requirements.txt
```

## Architecture

The application follows a layered architecture:

```
Routes (HTTP) → Services (Business Logic) → Repositories (Data Access) → Database
```

- **Routes**: Handle HTTP requests/responses, input validation, auth dependencies
- **Services**: Business logic, orchestration, exception handling
- **Repositories**: Database operations (CRUD)
- **Models**: SQLAlchemy ORM models
- **Schemas**: Pydantic models for validation and serialization
- **Dependencies**: Reusable FastAPI dependencies (JWT auth, role-based access)
- **Utils**: Shared utilities (password hashing, JWT tokens)

## Telegram Notifications (Optional)

The application can send Telegram notifications when RAG ingestion jobs complete. This is optional — if not configured, notifications are silently skipped.

### Setup Instructions

#### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts:
   - Choose a name for your bot (e.g., "My RAG Notifier")
   - Choose a username (must end in `bot`, e.g., `my_rag_notifier_bot`)
3. BotFather will give you a **token** like:
   ```
   8575345130:AAFsqDAnhsuixfmZS3BEH1csUPNKHNRvMtg
   ```
4. Save this as `TELEGRAM_BOT_TOKEN` in your `.env`

#### 2. Get Your Chat ID

1. Open Telegram and **start a conversation** with your new bot (search for it and click "Start")
2. Send any message to the bot (e.g., "hello")
3. Open this URL in your browser (replace `<YOUR_TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Look for your chat ID in the response:
   ```json
   {
     "result": [{
       "message": {
         "chat": {
           "id": 178331797,  <-- This is your chat ID
           "first_name": "Your Name",
           "type": "private"
         }
       }
     }]
   }
   ```
5. Save this as `TELEGRAM_CHAT_ID` in your `.env`

#### 3. Add to .env

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### What You'll Receive

When a RAG ingestion job completes:
```
RAG Ingestion Complete

Files: 2/2 succeeded
Chunks created: 45
```

When a RAG ingestion job fails:
```
RAG Ingestion Failed

Error: <error details>
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | AI Chatbot API |
| `APP_VERSION` | Application version | 0.1.0 |
| `ENV` | Environment (development/production) | development |
| `DEBUG` | Debug mode | false |
| `DATABASE_URL` | PostgreSQL connection string | - |
| `POSTGRES_USER` | PostgreSQL username | - |
| `POSTGRES_PASSWORD` | PostgreSQL password | - |
| `POSTGRES_DB` | PostgreSQL database name | - |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | (change in production) |
| `JWT_ALGORITHM` | JWT signing algorithm | HS256 |
| `JWT_EXPIRATION_MINUTES` | Token expiration time in minutes | 30 |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (optional) | - |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications (optional) | - |

## Development

### Adding New Dependencies

```bash
pip install <package-name>
pip freeze > requirements.txt
```

### Code Style

The project uses standard Python conventions. Consider using:
- `black` for code formatting
- `isort` for import sorting
- `flake8` or `ruff` for linting

## License

MIT
