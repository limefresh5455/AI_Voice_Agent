#!/bin/bash
# Quick start script for AI Voice Docker deployment

set -e

echo "🚀 AI Voice Docker Quick Start"
echo "=============================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop first."
    echo "   Visit: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please update Docker Desktop."
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.docker .env
    echo "⚠️  IMPORTANT: You need to edit .env and add your API keys!"
    echo ""
    echo "Required keys:"
    echo "  - DEEPGRAM_API_KEY"
    echo "  - AWS_ACCESS_KEY_ID"
    echo "  - AWS_SECRET_ACCESS_KEY"
    echo ""
    read -p "Press Enter when you've updated .env with your API keys..."
fi

# Validate required environment variables
echo "🔍 Validating environment variables..."
source .env

if [ -z "$DEEPGRAM_API_KEY" ] || [ "$DEEPGRAM_API_KEY" = "your_deepgram_api_key_here" ]; then
    echo "❌ DEEPGRAM_API_KEY is not set in .env"
    exit 1
fi

if [ -z "$AWS_ACCESS_KEY_ID" ] || [ "$AWS_ACCESS_KEY_ID" = "your_aws_access_key" ]; then
    echo "❌ AWS_ACCESS_KEY_ID is not set in .env"
    exit 1
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ "$AWS_SECRET_ACCESS_KEY" = "your_aws_secret_key" ]; then
    echo "❌ AWS_SECRET_ACCESS_KEY is not set in .env"
    exit 1
fi

echo "✅ Environment variables are set"
echo ""

# Build and start services
echo "🏗️  Building Docker images..."
docker compose build

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check service health
echo ""
echo "🏥 Checking service health..."

# Check PostgreSQL
if docker compose exec postgres pg_isready -U ai_voice > /dev/null 2>&1; then
    echo "✅ PostgreSQL is ready"
else
    echo "⚠️  PostgreSQL is starting up..."
fi

# Check Redis
if docker compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "⚠️  Redis is starting up..."
fi

# Wait a bit more for app to start
sleep 10

# Check app health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ App is ready"
else
    echo "⚠️  App is starting up (this may take a minute)..."
fi

echo ""
echo "=============================="
echo "🎉 AI Voice is ready!"
echo ""
echo "📱 Access the application:"
echo "   http://localhost:8000"
echo ""
echo "📊 View logs:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker compose down"
echo ""
echo "📖 For more commands, see DOCKER_SETUP.md or run: make help"
echo ""
