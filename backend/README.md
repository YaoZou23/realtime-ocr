# 📄 Flask OCR Backend

A Flask server that performs OCR (Optical Character Recognition) and image translation with text overlay using EasyOCR.

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+** installed
2. **EasyOCR** (automatically installed via requirements.txt)
3. **OpenCV** and image processing libraries

### Setup Instructions

1. **Navigate to the backend directory:**
```bash
cd backend
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

⚠️ **IMPORTANT:** Make sure all requirements are installed before running the server!

4. **Find your computer's IP address:**
```bash
# macOS/Linux
ipconfig getifaddr en0  # Usually en0 for Wi-Fi, en1 for Ethernet
# or
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
# Look for IPv4 Address under your active network adapter
```

5. **Update the frontend with your IP address:**
   - Open `mobile-app/app/(tabs)/index.tsx`
   - Update `YOUR_SERVER_IP` and `TEST_SERVER_IP` with your IP address
   - Open `mobile-app/app/(tabs)/upload.tsx`
   - Update `SERVER_IP` with your IP address
   - **Make sure the port matches:** The backend runs on port **5003** by default

### Running the Server

**Option 1: Using the start script (recommended):**
```bash
chmod +x start.sh
./start.sh
```

**Option 2: Manual start:**
```bash
python app.py
```

You should see:
```
Starting Flask server on 0.0.0.0:5003 (accessible from network)
```

⚠️ **IMPORTANT:** 
- The server runs on port **5003** by default
- Make sure the frontend uses the **same port** (5003)
- The server is accessible from your local network at `http://YOUR_IP:5003`

## 📱 Frontend Configuration

**Update this file in `mobile-app/app/(tabs)/`:**

**upload.tsx** (Upload/Translation tab):
```typescript
// ⚠️ REPLACE WITH YOUR MAC'S IP ADDRESS
const SERVER_IP = "http://YOUR_IP:5003/api/ocr";
```

Replace `YOUR_IP` with your actual IP address (e.g., `10.195.91.229`)

**Note:** The `index.tsx` file is now a blank home tab and doesn't require IP configuration.

## 🔧 API Endpoints

### `GET /api/test`
Test endpoint to verify connectivity.

**Response:**
```json
{
  "status": "ok",
  "message": "Connection successful",
  "ip": "client_ip",
  "server_ip": "10.195.91.229",
  "port": 5003,
  "easyocr_ready": true
}
```

### `POST /api/ocr`
Perform OCR and optionally translate text with overlay.

**Request Body:**
```json
{
  "image": "base64_encoded_image_string",
  "target_lang": "ZH",  // Optional: Language code for translation (e.g., "ZH" for Chinese)
  "return_overlay": true,  // Optional: Return annotated image with translated text overlay
  "include_segment_data": false  // Optional: Include segment coordinates
}
```

**Response:**
```json
{
  "text": "Extracted text from the image",
  "translated_text": "Translated text (if target_lang provided)",
  "annotated_image": "data:image/png;base64,...",  // If return_overlay is true
  "confidence": 0.95
}
```

**Example using curl:**
```bash
curl -X POST http://localhost:5003/api/ocr \
  -H "Content-Type: application/json" \
  -d '{"image": "base64_string_here", "target_lang": "ZH", "return_overlay": true}'
```

### `POST /api/translate`
Translate text (standalone endpoint).

**Request Body:**
```json
{
  "text": "Text to translate",
  "target_lang": "ZH"
}
```

## 🐛 Troubleshooting

### Issue: "Module not found" or import errors

**Solution:**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows

# Reinstall requirements
pip install -r requirements.txt
```

### Issue: Mobile app can't connect to server

**Checklist:**
1. ✅ Backend server is running (`python app.py` or `./start.sh`)
2. ✅ Both devices are on the **same Wi-Fi network**
3. ✅ IP address in mobile app matches your computer's IP
4. ✅ **Port matches:** Frontend uses port 5003 (same as backend)
5. ✅ Firewall isn't blocking port 5003
6. ✅ Using `http://` not `https://`

**Test connection:**
```bash
# From your computer
curl http://localhost:5003/api/test

# From another device on the same network
curl http://YOUR_IP:5003/api/test
```

### Issue: "Connection timeout"

**Solution:**
- Check if firewall is blocking connections
- Verify both devices are on the same network
- Try pinging your computer's IP from the mobile device
- Check if the backend is actually running and listening on 0.0.0.0:5003

### Issue: EasyOCR initialization is slow

**Note:** The first OCR request may take 15-30 seconds as EasyOCR loads models. Subsequent requests will be faster.

## 📦 Dependencies

See `requirements.txt` for full list. Key dependencies:
- **Flask**: Web framework
- **flask-cors**: Enable CORS for mobile app requests
- **EasyOCR**: OCR engine with multi-language support
- **Pillow**: Image processing library
- **OpenCV**: Image preprocessing and enhancement
- **numpy**: Numerical operations

## 🔐 Security Note

⚠️ This is a **development server**. For production:
- Use a production WSGI server (gunicorn, uWSGI)
- Add authentication/API keys
- Implement rate limiting
- Add input validation
- Use HTTPS
- Deploy to a cloud service

## 📝 GitHub Upload

Before uploading to GitHub:

1. **Create a `.gitignore` file** (if not exists) with:
```
venv/
__pycache__/
*.pyc
*.log
.env
annotated_results/
dataimages/
```

2. **Commit and push:**
```bash
git add .
git commit -m "Add OCR backend with translation support"
git push origin main
```

## 🚀 Next Steps

1. ✅ Install all requirements: `pip install -r requirements.txt`
2. ✅ Find your IP address: `ipconfig getifaddr en0`
3. ✅ Update frontend IP addresses in `mobile-app/app/(tabs)/index.tsx` and `upload.tsx`
4. ✅ Ensure frontend uses port **5003** (same as backend)
5. ✅ Start the server: `./start.sh` or `python app.py`
6. ✅ Test connection from mobile app
7. ✅ Upload to GitHub when ready

---

**Happy coding! 🎉**
