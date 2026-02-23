\# Wendy v0.1 - Step 1: Database Setup



\*\*Completion Date:\*\* \[Add your date]  

\*\*Status:\*\* ✅ Complete



---



\## Overview



Step 1 establishes the PostgreSQL database foundation for Wendy, including all tables, models, and connection management.



---pip install python-docx



\## What Was Built



\### 1. Database Schema



\*\*Database Name:\*\* `wendy`  

\*\*PostgreSQL Version:\*\* 18.x  

\*\*User:\*\* `postgres`  

\*\*Password:\*\* `admin`



\### 2. Tables Created



\#### `users`

\- Stores user accounts

\- Fields: id, name, email, whatsapp\_number, api\_token, created\_at

\- Unique constraints on: email, whatsapp\_number, api\_token



\#### `activity\_logs`

\- Stores user activity entries

\- Fields: id, user\_id, date, activity\_name, category, duration\_minutes, notes, created\_at

\- Categories: Learning, Work, Fitness, Personal, Project



\#### `events`

\- Event tracking for all system actions

\- Fields: id, user\_id, event\_type, payload (JSONB), created\_at



\#### `conversations`

\- Message history (for future use)

\- Fields: id, user\_id, role, message, created\_at



\### 3. Files Created

```

wendy/

├── database/

│   ├── \_\_init\_\_.py          # Module exports

│   ├── base.py              # SQLAlchemy engine and session

│   └── models.py            # Database models (User, ActivityLog, Event, Conversation)

├── services/                # (Empty - for future steps)

├── venv/                    # Python virtual environment

├── .env                     # Environment variables

├── requirements.txt         # Python dependencies

├── init\_database.py         # Database initialization script

└── README\_STEP1.md          # This file

```



---



\## Environment Configuration



\*\*File:\*\* `.env`

```env

DATABASE\_URL=postgresql://postgres:admin@localhost:5432/wendy

```



---



\## Dependencies Installed

```txt

fastapi

uvicorn

sqlalchemy

psycopg2-binary

python-dotenv

pydantic

```



---



\## Key Design Decisions



\### Why UUID Primary Keys?

\- Distributed-friendly

\- No collision risk

\- Better for API exposure



\### Why JSONB for Events?

\- Flexible payload structure

\- PostgreSQL native JSON querying

\- Future-proof for schema evolution



\### Why Enum for Categories?

\- Database-level validation

\- Prevents invalid data

\- Type-safe in Python



\### Why Indexed Columns?

\- `user\_id` - Most queries filter by user

\- `date` - Time-based queries for logs

\- `event\_type` - Event filtering

\- `created\_at` - Chronological sorting



---



\## How to Use



\### Initialize Database (First Time Only)

```bash

\# Activate virtual environment

venv\\Scripts\\activate



\# Run initialization script

python init\_database.py

```



\### Reinitialize Database (Drop and Recreate)

```bash

\# Connect to PostgreSQL

psql -U postgres



\# Drop database

DROP DATABASE wendy;



\# Recreate database

CREATE DATABASE wendy;



\# Exit PostgreSQL

\\q



\# Run initialization script

python init\_database.py

```



\### Verify Tables Exist

```bash

\# Connect to wendy database

psql -U postgres -d wendy



\# List tables

\\dt



\# View table structure

\\d users

\\d activity\_logs

\\d events

\\d conversations



\# Exit

\\q

```



---



\## Database Connection in Code

```python

from database import get\_db, User, ActivityLog



\# In FastAPI endpoint

def some\_endpoint(db = Depends(get\_db)):

&nbsp;   user = db.query(User).filter(User.email == "test@example.com").first()

&nbsp;   return user

```



---



\## Troubleshooting



\### Issue: "database does not exist"

\*\*Solution:\*\*

```bash

psql -U postgres

CREATE DATABASE wendy;

\\q

```



\### Issue: "password authentication failed"

\*\*Solution:\*\* Check `.env` file has correct password (`admin`)



\### Issue: "psql: command not found"

\*\*Solution:\*\* Add PostgreSQL to PATH:

\- `C:\\Program Files\\PostgreSQL\\18\\bin`



\### Issue: Tables already exist

\*\*Solution:\*\*

```bash

psql -U postgres -d wendy

DROP SCHEMA public CASCADE;

CREATE SCHEMA public;

\\q

python init\_database.py

```



---



\## PostgreSQL Useful Commands

```bash

\# Start PostgreSQL service (if stopped)

net start postgresql-x64-18



\# Connect to database

psql -U postgres -d wendy



\# List databases

\\l



\# List tables

\\dt



\# Describe table

\\d table\_name



\# View data

SELECT \* FROM users;



\# Exit

\\q

```



---



\## Next Steps



\- \[ ] Step 2: Authentication Service (`auth\_service.py`)

\- \[ ] Step 3: Intent Router (`intent\_router.py`)

\- \[ ] Step 4: AI Adapter (`ai\_adapter.py`)

\- \[ ] Step 5: Logging Service (`logging\_service.py`)

\- \[ ] Step 6: Event Bus (`event\_bus.py`)

\- \[ ] Step 7: FastAPI Main App (`main.py`)



---



\## Version Scope: v0.1



\*\*Allowed Features:\*\*

\- ✅ Multi-user resolution

\- ✅ Rule-based routing

\- ✅ Log command

\- ✅ AI structured JSON parsing

\- ✅ Database storage

\- ✅ Weekly total calculation

\- ✅ Streak detection

\- ✅ Event emission

\- ✅ Confirmation response



\*\*Not Allowed (Future Versions):\*\*

\- ❌ Tasks

\- ❌ Goals

\- ❌ Scheduled jobs

\- ❌ Async workers

\- ❌ AI intent classification

\- ❌ Docker

\- ❌ Advanced analytics



---



\## Notes



\- Database uses lowercase name (`wendy`) to avoid quoting issues

\- All tables include `user\_id` for multi-tenancy

\- `created\_at` uses UTC timestamps

\- Virtual environment keeps dependencies isolated

\- `.env` file excluded from git (add to `.gitignore`)



---



\*\*Step 1 Status:\*\* ✅ Complete and Verified

