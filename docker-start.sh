#!/bin/bash
# Quick start script for Docker deployment
# This script sets up and runs the entire application in Docker

set -e

echo "=========================================="
echo "Call Center Audio Intelligence"
echo "Docker Deployment Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    if [ -f .env.production ]; then
        cp .env.production .env
        echo "✓ Created .env from .env.production"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
        echo "   - REPLICATE_API_KEY"
        echo "   - OPENROUTER_API_KEY"
        echo ""
        read -p "Press Enter after you've added your API keys..."
    else
        echo "❌ Error: .env.production template not found"
        exit 1
    fi
fi

# Check if API keys are set
if grep -q "your_replicate_api_key_here" .env || grep -q "your_openrouter_api_key_here" .env; then
    echo "❌ Error: API keys not configured in .env"
    echo "Please edit .env and add your actual API keys"
    exit 1
fi

echo "1. Building Docker images..."
docker-compose -f docker-compose.prod.yml build

echo ""
echo "2. Starting services..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "3. Waiting for services to be healthy (30 seconds)..."
sleep 30

echo ""
echo "4. Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T backend alembic -c backend/alembic.ini upgrade head

echo ""
echo "5. Seeding database with sample data..."
docker-compose -f docker-compose.prod.yml exec -T backend python -m backend.app.db.seed

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Access the application:"
echo "  Frontend:  http://localhost"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  View logs:    docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop:         docker-compose -f docker-compose.prod.yml down"
echo "  Restart:      docker-compose -f docker-compose.prod.yml restart"
echo ""
