#!/bin/bash

# POS Scanner Web - Quick Deploy Script
# Usage: ./deploy.sh [option]
# Options:
#   docker    - Deploy with Docker (recommended)
#   local     - Deploy locally without Docker
#   stop      - Stop running services
#   logs      - Show logs

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== POS Scanner Web Deploy ===${NC}"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your configuration!${NC}"
fi

case "$1" in
    docker)
        echo -e "${GREEN}Deploying with Docker...${NC}"
        docker-compose up -d --build
        echo -e "${GREEN}Deployment complete!${NC}"
        echo -e "Frontend: http://localhost"
        echo -e "Backend:  http://localhost:5000"
        ;;

    local)
        echo -e "${GREEN}Deploying locally...${NC}"

        # Backend
        echo -e "${YELLOW}Starting backend...${NC}"
        cd backend
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate
        pip install -r requirements.txt
        python app.py &
        BACKEND_PID=$!
        cd ..

        # Frontend
        echo -e "${YELLOW}Starting frontend...${NC}"
        cd frontend
        npm install
        npm run dev &
        FRONTEND_PID=$!
        cd ..

        echo -e "${GREEN}Deployment complete!${NC}"
        echo -e "Frontend: http://localhost:3000"
        echo -e "Backend:  http://localhost:5000"
        echo -e "PIDs: Backend=$BACKEND_PID, Frontend=$FRONTEND_PID"
        ;;

    stop)
        echo -e "${YELLOW}Stopping services...${NC}"
        docker-compose down 2>/dev/null || true
        pkill -f "python app.py" 2>/dev/null || true
        pkill -f "vite" 2>/dev/null || true
        echo -e "${GREEN}Services stopped.${NC}"
        ;;

    logs)
        docker-compose logs -f
        ;;

    *)
        echo "Usage: $0 {docker|local|stop|logs}"
        echo ""
        echo "  docker  - Deploy with Docker (recommended)"
        echo "  local   - Deploy locally without Docker"
        echo "  stop    - Stop running services"
        echo "  logs    - Show Docker logs"
        exit 1
        ;;
esac
