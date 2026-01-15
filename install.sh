#!/bin/bash

# G3r4kiHub Installation Script
# Automates setup for local development or production

set -e

echo "🚀 G3r4kiHub Installation"
echo "========================="

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version detected"

if [[ ! "$python_version" =~ ^3\.[0-9]+ ]]; then
    echo -e "${RED}❌ Python 3.11+ required${NC}"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "ℹ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "✓ Pip upgraded"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env with your credentials${NC}"
    echo ""
    echo "Edit the following in .env:"
    echo "  - TELEGRAM_BOT_TOKEN (from @BotFather)"
    echo "  - AMAZON_ACCESS_KEY (from Amazon Associates)"
    echo "  - AMAZON_SECRET_KEY"
    echo "  - AMAZON_PARTNER_TAG"
else
    echo "✓ .env file already exists"
fi

# Create logs directory
echo ""
echo "Creating logs directory..."
mkdir -p logs
echo "✓ Logs directory created"

# Initialize database
echo ""
echo "Initializing database..."
python -c "from internal.models import create_tables; create_tables(); print('✓ Database tables created')"

# Summary
echo ""
echo "========================="
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo "========================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env with your credentials:"
echo "   nano .env"
echo ""
echo "2. Run the bot:"
echo "   python main.py"
echo ""
echo "3. In another terminal, run the admin dashboard:"
echo "   python run_dashboard.py"
echo ""
echo "4. Access the dashboard at:"
echo "   http://localhost:8001"
echo ""
echo "For more information, see:"
echo "  - DEPLOYMENT.md (Deployment guide)"
echo "  - DEVELOPMENT.md (Development guide)"
echo ""
