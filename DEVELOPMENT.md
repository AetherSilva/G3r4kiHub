# G3r4kiHub Development Guide

## Project Structure

```
G3r4kiHub/
├── config.py                 # Configuration management
├── main.py                   # Bot entry point
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── DEPLOYMENT.md            # Deployment guide
├── Dockerfile               # Docker image definition
│
├── internal/                # Core bot logic
│   ├── models.py           # Database models
│   ├── db_manager.py       # Database operations
│   ├── amazon_api.py       # Amazon API integration
│   ├── deal_fetcher.py     # Deal fetching & formatting
│   └── burn.py             # Legacy (to be removed)
│
├── services/               # External integrations
│   ├── telegram_bot.py     # Telegram bot operations
│   ├── scheduler.py        # Job scheduling & analytics
│   ├── ai/                 # AI services
│   │   └── server.py
│   └── gateway/            # API gateway
│       └── main.py
│
├── web/                    # FastAPI admin panel
│   ├── app.py             # Main FastAPI application
│   └── routes/            # API endpoints
│       ├── deals.py       # Deal management
│       ├── analytics.py   # Analytics endpoints
│       └── system.py      # System management
│
├── tests/                 # Test suite
│   ├── test_risk.py
│   └── test_ledger.py
│
└── deploy/               # Deployment configs
    └── docker/
        └── docker-compose.yml
```

## Key Components

### 1. Configuration (`config.py`)
- Loads settings from `.env`
- Uses Pydantic for validation
- Cached singleton pattern

### 2. Database Layer (`internal/models.py`, `internal/db_manager.py`)
- SQLAlchemy ORM models
- Supports SQLite (dev) and PostgreSQL (prod)
- Models: PostedDeal, Analytics, BotLog, DealCache, Channel

### 3. Deal Management
- **Fetcher** (`internal/deal_fetcher.py`): Fetches from Amazon API
- **Formatter** (`internal/deal_fetcher.py`): Formats for Telegram
- **Validation**: Price, title, discount checks

### 4. Telegram Integration (`services/telegram_bot.py`)
- Async message posting
- Inline button support
- Message pinning/editing/deletion
- Health checks

### 5. Scheduling (`services/scheduler.py`)
- APScheduler for cron jobs
- Post deals job (hourly)
- Analytics job (daily)
- Cleanup job (auto-rotation)

### 6. Admin Dashboard (`web/app.py`)
- FastAPI application
- Real-time analytics
- Deal management
- System monitoring
- Beautiful HTML dashboard

## Development Workflow

### 1. Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with test credentials
nano .env
```

### 2. Database Development

```bash
# Create tables
python -c "from internal.models import create_tables; create_tables()"

# Query database
python -c "from internal.db_manager import DatabaseManager; from internal.models import SessionLocal; db = SessionLocal(); print(db.query(DatabaseManager.get_dashboard_stats(db)))"
```

### 3. Testing New Features

```bash
# Test Amazon API integration
python -c "from internal.amazon_api import get_amazon_client; client = get_amazon_client(); print(client.get_product_by_asin('B0XXXXXXX'))"

# Test deal formatter
python -c "from internal.deal_fetcher import MessageFormatter; deal = {'title': 'Test', 'price': 99.99, 'discount_percent': 20}; print(MessageFormatter.format_deal_message(deal))"

# Test scheduler
python -c "from services.scheduler import get_scheduler; s = get_scheduler(); s.start(); print(s.list_jobs())"
```

### 4. Running the Bot

```bash
# Terminal 1: Start bot and scheduler
python main.py

# Terminal 2: Start admin dashboard
cd web && uvicorn app:app --reload --port 8001

# Terminal 3: Monitor logs
tail -f logs/g3r4kihub.log
```

### 5. Testing Admin Dashboard

```bash
# Access at http://localhost:8001
# API endpoints:
# - GET /api/dashboard          - Dashboard data
# - GET /api/deals              - List deals
# - GET /api/analytics          - Analytics data
# - GET /health                 - Health check
```

## Common Development Tasks

### Adding a New Scheduled Job

```python
# In services/scheduler.py
def add_custom_job(self):
    self.scheduler.add_job(
        self.my_job,
        trigger=CronTrigger(hour="12", minute="0"),
        id="my_job",
        name="My Custom Job"
    )

def my_job(self):
    db = SessionLocal()
    try:
        # Your job logic
        pass
    finally:
        db.close()
```

### Adding a New API Endpoint

```python
# In web/routes/custom.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/custom", tags=["custom"])

@router.get("/endpoint")
async def custom_endpoint():
    return {"status": "ok"}

# Then in web/app.py, add:
from web.routes.custom import router
app.include_router(router)
```

### Adding Database Migration

```python
# In internal/models.py, update your model
class NewModel(Base):
    __tablename__ = "new_table"
    id = Column(Integer, primary_key=True)
    # ... columns ...

# Then create tables:
from internal.models import create_tables
create_tables()
```

### Testing with Real Data

```python
# Test with real Amazon ASIN
from internal.amazon_api import get_amazon_client

client = get_amazon_client()
product = client.get_product_by_asin("B09H8BZLTH")  # Example: iPhone
print(product)
```

## Database Schema

### posted_deals
```sql
id, asin, title, price, original_price, discount_percent, 
image_url, affiliate_url, category, posted_at, telegram_message_id
```

### analytics
```sql
id, deal_id, telegram_message_id, view_count, click_count, 
conversion_count, revenue_amount, ctr, timestamp, last_updated
```

### bot_logs
```sql
id, action, status, message, error_details, created_at
```

### deal_cache
```sql
id, asin, title, price, last_seen, is_active
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=internal --cov=services tests/

# Run specific test
pytest tests/test_risk.py::test_function
```

## Code Style

- **Python**: PEP 8, type hints
- **Async**: asyncio for async operations
- **Logging**: Use `logging` module
- **Errors**: Try/except with proper logging

## Performance Optimization

1. **Database Indexes**: On `asin`, `posted_at`, `created_at`
2. **Caching**: Redis for rate limiting
3. **Async**: Use async for I/O operations
4. **Batch Operations**: Post multiple deals together
5. **Connection Pooling**: SQLAlchemy pool_size

## Debugging

```python
# Enable debug logging in .env
DEBUG_MODE=true
LOG_LEVEL=DEBUG

# Or in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Create feature branch: `git checkout -b feature/name`
2. Make changes with tests
3. Run tests: `pytest`
4. Push and create PR

## Resources

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Amazon PA API](https://webservices.amazon.com/paapi5/documentation/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/orm/)
- [APScheduler](https://apscheduler.readthedocs.io/)
