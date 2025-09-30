#!/bin/bash

# GuessWithEmojiBot VPS Startup Script
# This script sets up and starts the bot on a VPS

set -e

echo "🤖 Starting GuessWithEmojiBot Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_warning "Running as root. Consider creating a dedicated user for the bot."
fi

# Update system packages
print_status "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Python and dependencies
print_status "Installing Python and system dependencies..."
apt-get install -y python3 python3-pip python3-venv git curl wget

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Please create one based on .env.example"
    print_status "Copying .env.example to .env..."
    cp .env.example .env
    print_error "Please edit .env file with your configuration before starting the bot!"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Set up systemd service (optional)
setup_systemd() {
    print_status "Setting up systemd service..."

    # Update WorkingDirectory in service file
    sed -i "s|/root/GuessWithEmojiBot|$(pwd)|g" systemd.service
    sed -i "s|/root/GuessWithEmojiBot|$(pwd)|g" systemd.service

    # Copy service file
    cp systemd.service /etc/systemd/system/guesswithemojibot.service

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable guesswithemojibot.service

    print_status "Systemd service installed. Use 'systemctl start guesswithemojibot' to start."
}

# Ask user if they want to set up systemd service
read -p "Do you want to set up systemd service for auto-start? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    setup_systemd
fi

# Start the bot
print_status "Starting GuessWithEmojiBot..."
python main.py

print_status "🎉 Bot setup complete!"
