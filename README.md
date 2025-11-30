# 📱 Real-Time OCR with Translation Overlay

A full-stack mobile OCR (Optical Character Recognition) application with image translation and text overlay, built with **React Native (Expo)** and **Flask (Python)**.

## 🎯 Features

- 📸 **Camera Integration**: Capture photos using your phone's camera
- 📤 **Image Upload**: Upload images from gallery for processing
- 🔍 **OCR Processing**: Extract text from images using EasyOCR
- 🌐 **Translation**: Translate detected text with visual overlay on images
- ✨ **Beautiful UI**: Modern interface with loading states and error handling
- 🚀 **Fast Processing**: Optimized image processing pipeline

## 📁 Project Structure

```
realtime-ocr/
├── mobile-app/          # React Native (Expo) frontend
│   ├── app/
│   │   └── (tabs)/
│   │       ├── index.tsx   # Home tab
│   │       ├── upload.tsx  # Upload & Translation tab
│   │       └── explore.tsx # Profile tab
│   ├── package.json
│   └── README.md
│
└── backend/             # Flask OCR API
    ├── app.py           # Main Flask server
    ├── requirements.txt # Python dependencies
    ├── start.sh         # Quick start script
    └── README.md        # Backend documentation
```

## 🚀 Quick Start Guide

### ⚠️ IMPORTANT SETUP STEPS

Before running the application, you **MUST** complete these steps:

1. **Install all requirements** (both backend and frontend)
2. **Find your computer's IP address**
3. **Update IP addresses in frontend files**
4. **Ensure same port is used** (default: 5003)

---

### 1️⃣ Setup Backend (Flask OCR Server)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Quick start (recommended)
chmod +x start.sh
./start.sh

# OR manual start:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Server will run on:** `http://0.0.0.0:5003`

### 2️⃣ Find Your IP Address

**macOS/Linux:**
```bash
ipconfig getifaddr en0  # Usually en0 for Wi-Fi
# or
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Windows:**
```bash
ipconfig
# Look for IPv4 Address under your active network adapter
```

**Example output:** `10.195.91.229`

### 3️⃣ Update Frontend IP Address

⚠️ **CRITICAL:** Update this file with your IP address:

**File: `mobile-app/app/(tabs)/upload.tsx`**
```typescript
// ⚠️ REPLACE WITH YOUR MAC'S IP ADDRESS
const SERVER_IP = "http://YOUR_IP:5003/api/ocr";
```

Replace `YOUR_IP` with your actual IP address (e.g., `10.195.91.229`)

**Note:** The `index.tsx` file is a blank home tab and doesn't require IP configuration.

### 4️⃣ Setup Mobile App (React Native)

```bash
cd mobile-app

# Install dependencies
npm install

# Start Expo development server
npx expo start
```

### 5️⃣ Run the App

1. Open **Expo Go** app on your phone
2. Scan the QR code from terminal
3. Grant camera and media library permissions
4. Test the connection and start using the app!

## 🔧 Configuration

### Port Configuration

**Default port:** `5003`

⚠️ **IMPORTANT:** 
- Backend runs on port **5003** by default
- Frontend **MUST** use the **same port** (5003)
- If you change the backend port, update it in all frontend files

### Network Configuration

**Requirements:**
- ✅ Both devices (computer and phone) must be on the **same Wi-Fi network**
- ✅ IP address must be correctly set in frontend files
- ✅ Port must match between frontend and backend (5003)
- ✅ Firewall must allow connections on port 5003

## 🛠️ Technology Stack

### Frontend (Mobile App)
- **React Native** 0.81.5
- **Expo** ~54.0.25
- **Expo Router** ~6.0.15 - File-based routing
- **Expo Camera** ~17.0.9 - Camera integration
- **Expo Image Picker** - Image gallery access
- **Axios** ^1.13.2 - HTTP requests
- **TypeScript** ~5.9.2 - Type safety

### Backend (API Server)
- **Flask** - Python web framework
- **EasyOCR** - OCR engine with multi-language support
- **OpenCV** - Image preprocessing and enhancement
- **Pillow** - Image processing library
- **Flask-CORS** - Cross-origin support

## 📸 How It Works

```
┌─────────────┐
│  Mobile App │
│   (Expo)    │
└──────┬──────┘
       │ 1. Capture/Upload Image
       ▼
┌─────────────┐
│   Base64   │
│  Encoding   │
└──────┬──────┘
       │ 2. Send to Backend
       ▼
┌─────────────┐
│ Flask API   │
│ /api/ocr    │
└──────┬──────┘
       │ 3. OCR + Translation
       │    + Overlay Generation
       ▼
┌─────────────┐
│  Result +   │
│  Annotated  │
│   Image     │
└──────┬──────┘
       │ 4. Display
       ▼
┌─────────────┐
│  Mobile App │
│   (Result)  │
└─────────────┘
```

## 🔧 API Documentation

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

**Request:**
```json
{
  "image": "base64_encoded_image_string",
  "target_lang": "ZH",  // Optional: Language code for translation
  "return_overlay": true,  // Optional: Return annotated image
  "include_segment_data": false  // Optional: Include coordinates
}
```

**Response:**
```json
{
  "text": "Extracted text",
  "translated_text": "Translated text",
  "annotated_image": "data:image/png;base64,...",
  "confidence": 0.95
}
```

## 🐛 Troubleshooting

### Backend Issues

**Cannot start server:**
```bash
# Make sure dependencies are installed
cd backend
pip install -r requirements.txt

# Check if port is available
lsof -ti:5003 | xargs kill -9  # Kill process on port 5003
```

**Module not found:**
```bash
# Activate virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Issues

**Cannot connect to backend:**
1. ✅ Backend server is running
2. ✅ Both devices on same Wi-Fi network
3. ✅ IP address is correct in `upload.tsx`
4. ✅ **Port matches:** Frontend uses same port as backend (5003)
5. ✅ Firewall allows port 5003

**Test connection:**
```bash
curl http://YOUR_IP:5003/api/test
```

**Module not found:**
```bash
cd mobile-app
rm -rf node_modules package-lock.json
npm install
```

### Network Issues

**Connection timeout:**
- Verify both devices are on the same network
- Check firewall settings
- Try pinging your computer's IP from the phone
- Ensure backend is listening on `0.0.0.0:5003` (not just `127.0.0.1`)

## 📝 GitHub Upload Instructions

Before uploading to GitHub:

### 1. Create/Update `.gitignore`

**Root `.gitignore`:**
```
# Backend
backend/venv/
backend/__pycache__/
backend/*.pyc
backend/*.log
backend/.env
backend/annotated_results/
backend/dataimages/

# Frontend
mobile-app/node_modules/
mobile-app/.expo/
mobile-app/.expo-shared/
mobile-app/dist/
mobile-app/*.log
mobile-app/.DS_Store

# General
.DS_Store
*.log
.env
```

### 2. Commit and Push

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Add real-time OCR app with translation overlay"

# Add remote (replace with your repository URL)
git remote add origin https://github.com/yourusername/realtime-ocr.git

# Push to GitHub
git push -u origin main
```

### 3. Verify Upload

- Check that all files are uploaded
- Verify `.gitignore` is working (no `node_modules` or `venv` folders)
- Test cloning the repository to ensure it works

## ✅ Pre-Upload Checklist

Before uploading to GitHub:

- [ ] All requirements installed (`pip install -r requirements.txt` and `npm install`)
- [ ] IP addresses updated in frontend files
- [ ] Port configuration matches (5003)
- [ ] `.gitignore` file created/updated
- [ ] No sensitive data (API keys, passwords) in code
- [ ] README files updated with instructions
- [ ] Code tested and working
- [ ] All files committed

## 🚀 Next Steps After Setup

1. ✅ Install all requirements (backend and frontend)
2. ✅ Find your IP address
3. ✅ Update IP addresses in frontend files
4. ✅ Ensure same port (5003) is used
5. ✅ Start backend server
6. ✅ Start frontend app
7. ✅ Test connection
8. ✅ Upload to GitHub

## 📊 Performance

- **Image Upload**: ~1-3 seconds (depending on network)
- **OCR Processing**: ~2-5 seconds (first request may take longer)
- **Translation**: ~1-2 seconds
- **Overlay Generation**: ~1-2 seconds
- **Total Time**: ~5-12 seconds per image

## 🔒 Security Notes

⚠️ **Development Mode Only**

For production deployment:
- [ ] Use HTTPS instead of HTTP
- [ ] Add API authentication (JWT tokens)
- [ ] Implement rate limiting
- [ ] Add input validation
- [ ] Use environment variables for configuration
- [ ] Deploy backend to cloud service
- [ ] Use production WSGI server (Gunicorn)

## 📄 License

MIT License - Free to use for personal and commercial projects!

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

## ⚠️ REMINDER: Before Running

1. **Install Requirements:**
   - Backend: `cd backend && pip install -r requirements.txt`
   - Frontend: `cd mobile-app && npm install`

2. **Update IP Address:**
   - Find your IP: `ipconfig getifaddr en0`
   - Update `mobile-app/app/(tabs)/upload.tsx`

3. **Use Same Port:**
   - Backend default: **5003**
   - Frontend must use: **5003**

4. **Upload to GitHub:**
   - Create `.gitignore`
   - Commit and push all files

**Happy coding! 🎉**
