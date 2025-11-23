#!/bin/bash

# 🚀 Flask OCR Backend Startup Script

echo "🔍 Checking Tesseract installation..."
if ! command -v tesseract &> /dev/null; then
    echo "❌ Tesseract not found! Install it with:"
    echo "   brew install tesseract"
    exit 1
fi

echo "✅ Tesseract found: $(tesseract --version | head -1)"

echo ""
echo "📍 Your Mac's IP Address:"
ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "Could not detect IP"

echo ""
echo "⚠️  Make sure your mobile app uses:"
echo "   http://$(ipconfig getifaddr en0 || ipconfig getifaddr en1):5000/api/ocr"

echo ""
echo "🔧 Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "🚀 Starting Flask server on port 5000..."
echo "   Press Ctrl+C to stop"
echo ""

python app.py

