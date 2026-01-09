# Docker Deployment Checklist

Use this checklist when deploying AI Voice to a new machine.

## Pre-Deployment

- [ ] Docker and Docker Compose installed on target machine
- [ ] Required ports available (8000, 5432, 6379)
- [ ] API keys ready:
  - [ ] Deepgram API key
  - [ ] AWS Access Key ID
  - [ ] AWS Secret Access Key
- [ ] Network/firewall configured to allow access

## Deployment Steps

### 1. Transfer Project

```bash
# Option A: Clone from Git (if using version control)
git clone <your-repo-url>
cd AI_Voice

# Option B: Copy files directly
# On source machine:
tar -czf ai_voice.tar.gz AI_Voice/
scp ai_voice.tar.gz user@target-machine:/path/

# On target machine:
tar -xzf ai_voice.tar.gz
cd AI_Voice
```

### 2. Configure Environment

```bash
# Copy and edit environment file
cp .env.docker .env
nano .env  # or vim/code

# Required variables:
# - DEEPGRAM_API_KEY
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - SECRET_KEY (generate new for production!)

# Optional but recommended:
# - CORS_ORIGINS (your domain)
# - LOG_LEVEL=WARNING (for production)
```

### 3. Start Services

```bash
# Quick start (recommended for first time)
./docker-start.sh

# Or manually:
docker compose build
docker compose up -d
```

### 4. Verify Deployment

```bash
# Check service status
docker compose ps

# Check health
curl http://localhost:8000/health

# View logs
docker compose logs -f app

# Test endpoints
curl http://localhost:8000/
```

### 5. Monitor Initial Run

```bash
# Watch logs for any errors
docker compose logs -f

# Check resource usage
docker stats

# Test a call from web interface
open http://localhost:8000
```

## Post-Deployment

- [ ] Test voice call flow
- [ ] Verify data persistence (stop/start containers)
- [ ] Set up backups for PostgreSQL
- [ ] Configure monitoring/alerting
- [ ] Document any custom configuration
- [ ] Set up log rotation
- [ ] Configure SSL/HTTPS (if needed)

## Production-Specific Steps

### Security Hardening

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Add to .env as SECRET_KEY

# Update PostgreSQL password
# Edit docker-compose.yml:
# - POSTGRES_PASSWORD: <strong-password>
# - Update DATABASE_URL in app service
```

### SSL/HTTPS Setup

```bash
# Option 1: Use nginx reverse proxy
docker compose -f docker-compose.yml -f docker-compose.nginx.yml up -d

# Option 2: Deploy behind load balancer (AWS ALB, etc.)
# Update CORS_ORIGINS with your domain
```

### Backup Setup

```bash
# PostgreSQL backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec -T postgres pg_dump -U ai_voice ai_voice > backup_$DATE.sql
gzip backup_$DATE.sql
# Upload to S3 or backup location
EOF

chmod +x backup.sh

# Add to cron for daily backups
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

### Monitoring

```bash
# Check logs regularly
docker compose logs --tail=100 app

# Monitor resource usage
docker stats --no-stream

# Set up health check monitoring
# (e.g., UptimeRobot, AWS CloudWatch, etc.)
```

## Troubleshooting

### Services won't start
```bash
# Check Docker daemon
docker info

# Check logs
docker compose logs

# Verify ports are available
netstat -tulpn | grep -E '8000|5432|6379'
```

### Database connection issues
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
docker compose exec postgres psql -U ai_voice -d ai_voice -c "SELECT 1"

# Verify DATABASE_URL in .env
```

### Redis connection issues
```bash
# Check Redis is running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping

# Should return: PONG
```

### App crashes or errors
```bash
# View recent logs
docker compose logs --tail=50 app

# Check app health
curl http://localhost:8000/health

# Restart app only
docker compose restart app

# Rebuild if needed
docker compose up -d --build app
```

### High memory usage
```bash
# Check stats
docker stats

# Adjust worker count in Dockerfile.prod if using production image
# Default is 4 workers, reduce if memory constrained
```

## Updating/Redeploying

```bash
# Pull latest code
git pull  # or transfer new files

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d

# Or use make command
make rebuild
```

## Rollback Procedure

```bash
# Stop current deployment
docker compose down

# Restore previous version (if using Git)
git checkout <previous-commit>

# Or restore from backup
tar -xzf ai_voice_backup.tar.gz

# Start services
docker compose up -d
```

## Common Issues and Solutions

### Issue: "Port already in use"
**Solution:** 
```bash
# Check what's using the port
lsof -i :8000  # or 5432, 6379

# Either stop the conflicting service or change port in docker-compose.yml
```

### Issue: "Permission denied" errors
**Solution:**
```bash
# Ensure Docker can access files
sudo chown -R $USER:$USER .

# Or run with sudo (not recommended)
sudo docker compose up -d
```

### Issue: "Out of disk space"
**Solution:**
```bash
# Clean up Docker resources
docker system prune -a

# Remove old volumes (WARNING: deletes data)
docker volume prune
```

### Issue: API keys not working
**Solution:**
```bash
# Verify .env is loaded
docker compose config | grep -E 'DEEPGRAM|AWS'

# Check for typos or extra spaces in .env
cat .env | grep API_KEY

# Restart after fixing
docker compose restart app
```

## Performance Tuning

### For High-Volume Production

Edit `docker-compose.yml` to increase resources:

```yaml
app:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G
      reservations:
        cpus: '2'
        memory: 4G
```

### Database Optimization

```bash
# Increase PostgreSQL connections if needed
docker compose exec postgres psql -U ai_voice -d ai_voice -c "ALTER SYSTEM SET max_connections = 200;"
docker compose restart postgres
```

## Support

If issues persist:
1. Check logs: `docker compose logs -f`
2. Review [DOCKER_SETUP.md](DOCKER_SETUP.md)
3. Check [README.md](README.md)
4. Verify all prerequisites are met
