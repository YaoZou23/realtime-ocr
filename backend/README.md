# 📄 Flask OCR Backend

A simple Flask server that performs OCR (Optical Character Recognition) on images sent from a mobile app.

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **Tesseract OCR** installed on your system

### Install Tesseract OCR

**macOS:**
```bash
brew install tesseract
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### Setup Instructions

1. **Navigate to the backend directory:**
```bash
cd "/Users/yao_zou1223/Desktop/PTOT project/realtime-ocr/backend"
```

2. **Create a virtual environment (recommended):**
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

4. **Verify Tesseract installation:**
```bash
tesseract --version
```

### Running the Server

**Start the Flask server:**
```bash
python app.py
```

You should see:
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.195.85.188:5000
```

⚠️ **Note:** The server runs on `0.0.0.0:5000` to accept connections from your mobile device.

## 📱 Mobile App Configuration

Make sure your mobile app's IP address matches your Mac's IP:

**In your mobile app (`index.tsx`):**
```typescript
const YOUR_SERVER_IP = "http://10.195.85.188:5000/api/ocr";
```

### Find Your Mac's IP Address:
```bash
ipconfig getifaddr en0  # Usually en0 for Wi-Fi, en1 for Ethernet
```

## 🔧 API Endpoint

### `POST /api/ocr`

**Request Body:**
```json
{
  "image": "base64_encoded_image_string"
}
```

**Response:**
```json
{
  "text": "Extracted text from the image"
}
```

**Example using curl:**
```bash
curl -X POST http://localhost:5000/api/ocr \
  -H "Content-Type: application/json" \
  -d '{"image": "iVBORw0KGgoAAAANS..."}'
```

## 🐛 Troubleshooting

### Issue: "pytesseract.pytesseract.TesseractNotFoundError"

**Solution:**
```bash
# macOS
brew install tesseract

# If still not found, specify the path in app.py:
# pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
```

### Issue: Mobile app can't connect to server

**Checklist:**
1. ✅ Backend server is running (`python app.py`)
2. ✅ Both devices are on the **same Wi-Fi network**
3. ✅ IP address in mobile app matches your Mac's IP
4. ✅ Firewall isn't blocking port 5000
5. ✅ Using `http://` not `https://`

**Test connection:**
```bash
# From another terminal on your Mac
curl http://localhost:5000/api/ocr -X POST \
  -H "Content-Type: application/json" \
  -d '{"image": ""}'
```

### Issue: "Connection timeout"

**Solution:**
- Check if firewall is blocking connections
- Try disabling firewall temporarily:
  ```bash
  # macOS
  sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
  ```

## 📦 Dependencies

- **Flask**: Web framework
- **flask-cors**: Enable CORS for mobile app requests
- **pytesseract**: Python wrapper for Tesseract OCR
- **Pillow**: Image processing library

## 🔐 Security Note

⚠️ This is a **development server**. For production:
- Use a production WSGI server (gunicorn, uWSGI)
- Add authentication/API keys
- Implement rate limiting
- Add input validation
- Use HTTPS

## 📝 License

MIT License - feel free to use for your project!

