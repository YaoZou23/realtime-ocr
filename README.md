# 📱 Real-Time OCR Mobile App

A full-stack mobile OCR (Optical Character Recognition) application built with **React Native (Expo)** and **Flask**.

## 🎯 Features

- 📸 **Camera Integration**: Capture photos using your phone's camera
- 🔍 **OCR Processing**: Extract text from images using Tesseract OCR
- 📤 **Real-time Upload**: Automatic image upload and processing
- ✨ **Beautiful UI**: Modern interface with loading states and error handling
- 🚀 **Fast**: Base64 encoding for quick image transfer

## 📁 Project Structure

```
realtime-ocr/
├── mobile-app/          # React Native (Expo) frontend
│   ├── app/
│   │   └── (tabs)/
│   │       └── index.tsx   # Main camera screen
│   ├── package.json
│   └── ...
│
└── backend/             # Flask OCR API
    ├── app.py           # Main Flask server
    ├── requirements.txt # Python dependencies
    ├── start.sh         # Quick start script
    └── README.md        # Backend documentation
```

## 🚀 Quick Start Guide

### 1️⃣ Setup Backend (Flask OCR Server)

```bash
cd backend

# Install Tesseract OCR (macOS)
brew install tesseract

# Quick start (automatic setup)
./start.sh

# OR manual setup:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Server will run on:** `http://0.0.0.0:5000`

### 2️⃣ Setup Mobile App (React Native)

```bash
cd mobile-app

# Install dependencies
npm install

# Start Expo development server
npx expo start
```

### 3️⃣ Configure Network Connection

**Find your Mac's IP address:**
```bash
ipconfig getifaddr en0  # Usually Wi-Fi
```

**Update mobile app** (`mobile-app/app/(tabs)/index.tsx`):
```typescript
const YOUR_SERVER_IP = "http://YOUR_MAC_IP:5000/api/ocr";
// Example: "http://10.195.85.188:5000/api/ocr"
```

### 4️⃣ Run the App

1. Open **Expo Go** app on your phone
2. Scan the QR code from terminal
3. Grant camera permissions
4. Take a photo and watch OCR magic happen! ✨

## 🛠️ Technology Stack

### Frontend (Mobile App)
- **React Native** 0.81.5
- **Expo** 52.0.19
- **Expo Camera** for camera integration
- **Axios** for HTTP requests
- **TypeScript** for type safety

### Backend (API Server)
- **Flask** 3.0.0 - Python web framework
- **Pytesseract** 0.3.10 - OCR engine wrapper
- **Pillow** 10.1.0 - Image processing
- **Flask-CORS** - Cross-origin support

## 📸 How It Works

```
┌─────────────┐
│  Mobile App │
│   (Expo)    │
└──────┬──────┘
       │ 1. Capture Photo
       ▼
┌─────────────┐
│   Camera    │
│   (Base64)  │
└──────┬──────┘
       │ 2. Send to Backend
       ▼
┌─────────────┐
│ Flask API   │
│ /api/ocr    │
└──────┬──────┘
       │ 3. Process with Tesseract
       ▼
┌─────────────┐
│  OCR Result │
│   (JSON)    │
└──────┬──────┘
       │ 4. Display Text
       ▼
┌─────────────┐
│  Mobile App │
│   (Result)  │
└─────────────┘
```

## 🔧 API Documentation

### `POST /api/ocr`

**Request:**
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

## 🐛 Troubleshooting

### Backend Issues

**Tesseract not found:**
```bash
brew install tesseract
# Verify: tesseract --version
```

**Port 5000 already in use:**
```bash
# Find and kill process
lsof -ti:5000 | xargs kill -9
```

### Mobile App Issues

**Cannot connect to server:**
1. ✅ Both devices on same Wi-Fi network
2. ✅ Backend server is running
3. ✅ IP address is correct
4. ✅ Firewall allows port 5000

**Camera permission denied:**
- Delete app and reinstall
- Check phone settings → Expo Go → Camera

**Module not found errors:**
```bash
cd mobile-app
rm -rf node_modules package-lock.json
npm install
```

## 📱 Testing the App

### Quick Test (Backend)
```bash
curl -X POST http://localhost:5000/api/ocr \
  -H "Content-Type: application/json" \
  -d '{"image": ""}'
```

### Screenshot Flow
1. Open app → Camera view
2. Point at text (book, sign, document)
3. Press "📸 Capture & Scan"
4. Wait for "Processing OCR..."
5. View extracted text!

## 🎨 UI Features

- 📸 **Camera View**: Full-screen live camera
- ⏳ **Loading State**: Spinner with "Processing OCR..."
- 📄 **Results Display**: Scrollable text container
- ❌ **Error Handling**: Clear error messages
- 🔄 **Take Another**: Quick retake button

## 🔒 Security Notes

⚠️ **Development Mode Only**

For production deployment:
- [ ] Use HTTPS instead of HTTP
- [ ] Add API authentication (JWT tokens)
- [ ] Implement rate limiting
- [ ] Add input validation
- [ ] Use production WSGI server (Gunicorn)
- [ ] Deploy backend to cloud (AWS, Heroku, etc.)

## 📊 Performance

- **Image Upload**: ~1-3 seconds (depending on network)
- **OCR Processing**: ~1-2 seconds (depending on text complexity)
- **Total Time**: ~2-5 seconds per image

## 🚧 Future Enhancements

- [ ] Real-time OCR (continuous scanning)
- [ ] Multiple language support
- [ ] History of scanned texts
- [ ] Copy to clipboard button
- [ ] Export as PDF
- [ ] Batch image processing
- [ ] Text translation
- [ ] Document scanner mode

## 📄 License

MIT License - Free to use for personal and commercial projects!

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 👨‍💻 Author

Built with ❤️ for the PTOT project

---

## 📞 Support

If you encounter any issues:
1. Check the troubleshooting section
2. Review backend/README.md for detailed setup
3. Verify all dependencies are installed
4. Ensure devices are on the same network

**Happy OCR-ing! 📸✨**

# ocr-realtime
# ocr-realtime
