# G3r4kiHub Deployment Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Telegram Bot Token
- Amazon API Credentials
- PostgreSQL (or SQLite for development)

### Local Development Setup

1. **Clone and setup environment:**
```bash
git clone https://github.com/AetherSilva/G3r4kiHub.git
cd G3r4kiHub

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Initialize database:**
```bash
python -c "from internal.models import create_tables; create_tables(); print('✓ Tables created')"
```

4. **Run bot and scheduler:**
```bash
python main.py
```

5. **In another terminal, run admin dashboard:**
```bash
cd web
uvicorn app:app --reload --port 8001
```

### Docker Deployment

1. **Build and run with Docker Compose:**
```bash
# Copy environment file
cp .env.example .env

# Edit .env with your credentials
nano .env

# Build and start services
docker-compose -f deploy/docker/docker-compose.yml up -d

# View logs
docker-compose -f deploy/docker/docker-compose.yml logs -f bot
```

2. **Access the admin panel:**
- Navigate to `http://localhost:8001`
- Login with credentials from `.env`

3. **Stop services:**
```bash
docker-compose -f deploy/docker/docker-compose.yml down
```

## Production Deployment

### Option 1: Render.com (Recommended for Free Tier)

1. **Create Render account** at render.com
2. **Connect GitHub repository**
3. **Create Web Service:**
   - Build: `pip install -r requirements.txt`
   - Start: `python main.py`
   - Environment: Add variables from `.env`

4. **Create PostgreSQL database:**
   - Add connection string to environment

### Option 2: Railway.app

1. **Create Railway account** at railway.app
2. **Connect GitHub**
3. **Deploy bot service with environment variables**

### Option 3: AWS/DigitalOcean

1. **SSH into VPS**
2. **Install Docker & Docker Compose**
3. **Clone repository**
4. **Deploy with compose file:**
```bash
docker-compose -f deploy/docker/docker-compose.yml up -d
```

## Environment Variables

See `.env.example` for all available configuration options:

### Critical Variables
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `AMAZON_ACCESS_KEY` - From Amazon Associates
- `AMAZON_SECRET_KEY` - From Amazon Associates
- `AMAZON_PARTNER_TAG` - Your affiliate tag
- `DATABASE_URL` - PostgreSQL or SQLite connection string

### Optional Variables
- `ENABLE_REDIS` - Enable Redis caching
- `SCHEDULER_ENABLED` - Enable automated posting
- `DEBUG_MODE` - Enable debug logging

## Database

### SQLite (Development)
```
DATABASE_URL=sqlite:///./g3r4kihub.db
```

### PostgreSQL (Production)
```
DATABASE_URL=postgresql://user:password@host:5432/g3r4kihub
```

## Monitoring & Logs

### View logs
```bash
docker-compose logs -f bot
```

### Access dashboard
```
http://localhost:8001
```

### Health check
```bash
curl http://localhost:8000/health
```

## Backup & Maintenance

### Backup database
```bash
docker-compose exec postgres pg_dump -U g3r4kihub g3r4kihub > backup.sql
```

### Restore database
```bash
docker-compose exec -T postgres psql -U g3r4kihub g3r4kihub < backup.sql
```

## Troubleshooting

### Bot not posting
1. Check Telegram token in `.env`
2. Verify channel ID is correct
3. Check scheduler logs: `docker-compose logs bot | grep scheduler`

### Database connection error
1. Verify PostgreSQL is running
2. Check connection string in `.env`
3. Ensure database exists: `psql -l`

### Admin dashboard not loading
1. Check if port 8001 is open
2. Verify admin credentials
3. Check API health: `curl http://localhost:8000/health`

## Support

For issues, check:
- Bot logs: `logs/g3r4kihub.log`
- Admin Dashboard Logs section
- GitHub Issues

## Security Notes

1. **Never commit `.env` with real credentials**
2. **Use strong passwords** for admin panel
3. **Keep dependencies updated** - run `pip install -U -r requirements.txt`
4. **Rotate API keys** regularly
5. **Use HTTPS** in production (via reverse proxy like Nginx)

## Performance Tips

1. Enable Redis for rate limiting
2. Use PostgreSQL instead of SQLite
3. Increase `POST_INTERVAL_HOURS` for stability
4. Monitor memory usage with `docker stats`
5. Set up log rotation for `logs/g3r4kihub.log`
