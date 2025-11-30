#!/bin/bash

# 🚀 Flask OCR Backend Startup Script

echo "=========================================="
echo "🚀 Starting Flask OCR Backend Server"
echo "=========================================="
echo ""

# Check Tesseract (optional, but good to have)
echo "🔍 Checking Tesseract installation..."
if ! command -v tesseract &> /dev/null; then
    echo "⚠️  Tesseract not found (optional for this project)"
    echo "   Install with: brew install tesseract"
else
    echo "✅ Tesseract found: $(tesseract --version | head -1)"
fi

echo ""
echo "📍 Your Computer's IP Address:"
IP_ADDRESS=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "Could not detect IP")
echo "   $IP_ADDRESS"

echo ""
echo "⚠️  IMPORTANT: Update your frontend with this IP address!"
echo "   Update this file in mobile-app/app/(tabs)/:"
echo "   - upload.tsx: SERVER_IP = \"http://$IP_ADDRESS:5003/api/ocr\""
echo ""
echo "⚠️  Make sure frontend uses the SAME PORT (5003)!"
echo ""

# Check if virtual environment exists
echo "🔧 Setting up virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created"
fi

# Install/update requirements
echo ""
echo "📦 Installing/updating dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ Error: requirements.txt not found!"
    exit 1
fi

echo ""
echo "=========================================="
echo "🚀 Starting Flask server on port 5003..."
echo "=========================================="
echo ""
echo "📍 Server will be accessible at:"
echo "   http://localhost:5003"
echo "   http://$IP_ADDRESS:5003"
echo ""
echo "⚠️  Make sure your frontend uses:"
echo "   http://$IP_ADDRESS:5003/api/ocr"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the Flask server
python app.py
