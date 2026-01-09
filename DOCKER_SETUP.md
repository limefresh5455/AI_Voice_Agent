# Docker Setup Guide for AI Voice

This guide explains how to run the AI Voice Intake System in Docker containers on any machine.

## Prerequisites

- Docker Desktop (Mac/Windows) or Docker Engine (Linux)
- Docker Compose v2.0+
- Your API keys:
  - Deepgram API key
  - AWS credentials with Bedrock access

## Quick Start

### 1. Clone and Configure

```bash
# Navigate to project directory
cd AI_Voice

# Copy the environment template
cp .env.docker .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

### 2. Start Services

```bash
# Build and start all services (app, PostgreSQL, Redis)
make up

# Or without make:
docker-compose up -d
```

### 3. Verify

```bash
# Check service health
make health

# View logs
make logs

# Check status
make status
```

### 4. Access the Application

Open your browser to: http://localhost:8000

## Available Commands

### Core Operations
```bash
make build          # Build Docker images
make up             # Start all services
make down           # Stop all services
make restart        # Restart services
make logs           # View all logs
make logs-app       # View app logs only
make status         # Show service status
```

### Development
```bash
make dev-setup      # Initial setup (creates .env)
make dev-redis      # Start only Redis
make dev-postgres   # Start only PostgreSQL
make shell          # Open shell in app container
make shell-db       # Open PostgreSQL shell
make test           # Run tests
```

### Maintenance
```bash
make rebuild        # Rebuild from scratch
make clean          # Remove containers and volumes
make health         # Check service health
```

## Architecture

The Docker setup includes three services:

1. **App Container** (`ai_voice_app`)
   - Python 3.11 FastAPI application
   - Handles WebSocket connections
   - Manages AI conversation pipeline
   - Exposed on port 8000

2. **PostgreSQL** (`ai_voice_postgres`)
   - Stores call records and metadata
   - Data persisted in `postgres_data` volume
   - Exposed on port 5432

3. **Redis** (`ai_voice_redis`)
   - Session state management
   - Real-time conversation tracking
   - Data persisted in `redis_data` volume
   - Exposed on port 6379

## Environment Variables

Key variables in `.env`:

### Required
- `DEEPGRAM_API_KEY` - For speech recognition and synthesis
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `AWS_BEDROCK_MODEL_ID` - LLM model (default: deepseek-r1-distill-qwen-32b)

### Optional
- `TWILIO_*` - For phone call support
- `SF_*` - Salesforce integration
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `CORS_ORIGINS` - Allowed origins for CORS

## Data Persistence

Data is persisted in Docker volumes:
- `postgres_data` - Database records
- `redis_data` - Redis snapshots
- `./calls` - Call recordings (mounted from host)

To backup data:
```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U ai_voice ai_voice > backup.sql

# Backup Redis
docker-compose exec redis redis-cli SAVE
docker cp ai_voice_redis:/data/dump.rdb ./redis_backup.rdb
```

## Deploying to Another Machine

### Option 1: Using Docker Compose (Recommended)

1. Copy the project to the target machine:
```bash
# On source machine
tar -czf ai_voice.tar.gz AI_Voice/

# Transfer to target machine (e.g., via scp)
scp ai_voice.tar.gz user@target-machine:/path/

# On target machine
tar -xzf ai_voice.tar.gz
cd AI_Voice
```

2. Configure environment:
```bash
cp .env.docker .env
# Edit .env with your API keys
```

3. Start services:
```bash
docker-compose up -d
```

### Option 2: Using Pre-built Images

1. Build and push to registry (on development machine):
```bash
# Tag and push to Docker Hub or private registry
docker tag ai_voice_app:latest yourusername/ai_voice:latest
docker push yourusername/ai_voice:latest
```

2. On target machine:
```bash
# Update docker-compose.yml to use pre-built image
# Then pull and start
docker-compose pull
docker-compose up -d
```

## Production Deployment

For production deployments:

1. **Secure your environment**:
   ```bash
   # Generate a strong secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update docker-compose.yml**:
   - Set `ENVIRONMENT=production`
   - Set `DEBUG=false`
   - Use strong passwords for PostgreSQL
   - Configure proper CORS origins

3. **Use production-ready database**:
   - Consider managed PostgreSQL (AWS RDS, etc.)
   - Update `DATABASE_URL` accordingly

4. **SSL/TLS**:
   - Add nginx reverse proxy for HTTPS
   - Or deploy behind a load balancer

5. **Monitoring**:
   - Add Prometheus for metrics
   - Configure log aggregation (ELK, CloudWatch)

## Troubleshooting

### Services won't start
```bash
# Check logs
make logs

# Check individual service
docker-compose logs postgres
docker-compose logs redis
docker-compose logs app
```

### Database connection errors
```bash
# Verify PostgreSQL is healthy
docker-compose exec postgres pg_isready -U ai_voice

# Check connection string in .env
# Make sure DATABASE_URL uses the service name: postgres:5432
```

### Redis connection errors
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Should return: PONG
```

### App container crashes
```bash
# Check app logs
make logs-app

# Check health endpoint
curl http://localhost:8000/health

# Restart specific service
docker-compose restart app
```

### Port conflicts
```bash
# If ports 5432, 6379, or 8000 are in use:
# Edit docker-compose.yml to use different ports
# Example: "8001:8000" to expose on port 8001
```

## Development Workflow

For local development with hot-reload:

```bash
# Start only infrastructure
make dev-redis
make dev-postgres

# Run app locally (outside Docker) with hot-reload
source venv/bin/activate
python main.py
```

Or develop inside container:
```bash
# Mount code as volume (edit docker-compose.yml)
volumes:
  - .:/app

# Then changes will reflect immediately with uvicorn --reload
```

## Resource Requirements

Minimum requirements:
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 10GB

Recommended for production:
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 50GB+ (for call recordings)

## Security Considerations

1. **Never commit `.env` file** - Contains sensitive API keys
2. **Use secrets management** in production (AWS Secrets Manager, HashiCorp Vault)
3. **Enable firewall** - Only expose port 8000 (or 443 with nginx)
4. **Regular updates** - Keep Docker images updated
5. **Backup strategy** - Regular database and volume backups

## Next Steps

- [ ] Add nginx for HTTPS termination
- [ ] Implement CI/CD pipeline
- [ ] Add monitoring with Prometheus/Grafana
- [ ] Set up log aggregation
- [ ] Configure auto-scaling (Kubernetes)

## Support

For issues or questions:
1. Check logs: `make logs`
2. Verify health: `make health`
3. Review this documentation
4. Check the main README.md
