# 🚀 Getting Started Guide

Complete step-by-step guide to get your OCR app running in under 5 minutes!

## ✅ Prerequisites Checklist

Before starting, make sure you have:

- [ ] **macOS** (or Linux/Windows with adjustments)
- [ ] **Python 3.8+** installed (`python3 --version`)
- [ ] **Node.js 20+** installed (`node --version`)
- [ ] **npm** installed (`npm --version`)
- [ ] **iPhone/Android** with **Expo Go** app installed
- [ ] Mac and phone on **same Wi-Fi network**

---

## 🎯 Step 1: Install Tesseract OCR

Tesseract is the OCR engine that reads text from images.

### macOS:
```bash
brew install tesseract
```

### Ubuntu/Linux:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### Windows:
Download from: https://github.com/UB-Mannheim/tesseract/wiki

**Verify installation:**
```bash
tesseract --version
# Should show: tesseract 5.x.x
```

---

## 🛠️ Step 2: Setup Backend (Flask Server)

### Quick Setup (Recommended):

```bash
cd backend
./start.sh
```

The script will:
- ✅ Check Tesseract installation
- ✅ Create virtual environment
- ✅ Install Python packages
- ✅ Show your IP address
- ✅ Start Flask server

### Manual Setup (Alternative):

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Start server
python app.py
```

**Expected output:**
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://10.195.85.188:5000
```

✅ **Leave this terminal running!**

---

## 📱 Step 3: Setup Mobile App

**Open a NEW terminal window:**

```bash
cd mobile-app

# Install dependencies
npm install

# Start Expo development server
npx expo start
```

**Expected output:**
```
› Metro waiting on exp://192.168.x.x:8081
› Scan the QR code above with Expo Go (Android) or Camera (iOS)
```

✅ **Leave this terminal running too!**

---

## 🔧 Step 4: Configure IP Address

### Find Your Mac's IP Address:

```bash
# Quick command
ipconfig getifaddr en0

# Example output: 10.195.85.188
```

### Update Mobile App:

1. Open: `mobile-app/app/(tabs)/index.tsx`
2. Find line 15:
```typescript
const YOUR_SERVER_IP = "http://10.195.85.188:5000/api/ocr";
```
3. Replace `10.195.85.188` with YOUR Mac's IP address
4. Save the file

**✅ The Expo server will automatically reload the app!**

---

## 📱 Step 5: Run on Your Phone

### iOS:
1. Open **Camera** app
2. Point at QR code in terminal
3. Tap notification → Opens in Expo Go

### Android:
1. Open **Expo Go** app
2. Tap "Scan QR Code"
3. Scan QR code from terminal

### First Time Setup:
- Grant **Camera Permission** when prompted
- Grant **Storage Permission** (if asked)

---

## 🎉 Step 6: Test the App!

1. **Open the app** → You should see live camera view
2. **Point camera** at text (book, sign, document, printed text)
3. **Press** "📸 Capture & Scan"
4. **Wait** for "Processing OCR..." (~2-5 seconds)
5. **View** extracted text! ✨

---

## 🧪 Testing Backend Separately

Want to test if backend is working before using mobile app?

```bash
cd backend

# Run test script
python test_ocr.py
```

Or test with curl:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -H "Content-Type: application/json" \
  -d '{"image": ""}'
```

Expected response:
```json
{"text": ""}
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "Cannot connect to server"

**Symptoms:** Mobile app shows "❌ Cannot connect to server"

**Solutions:**
1. Check both devices are on **same Wi-Fi**
2. Verify Flask server is running (check terminal)
3. Verify IP address is correct
4. Try pinging your Mac from phone
5. Disable Mac firewall temporarily:
   ```bash
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off
   ```

### Issue 2: "ModuleNotFoundError: No module named 'flask'"

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue 3: "TesseractNotFoundError"

**Solution:**
```bash
brew install tesseract
tesseract --version  # Verify
```

If still not working, add to `app.py`:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
```

### Issue 4: "Camera permission denied"

**Solution:**
- Delete Expo Go app
- Reinstall from App Store
- Re-run app and grant permissions

### Issue 5: "Port 5000 already in use"

**Solution:**
```bash
# Find process using port 5000
lsof -ti:5000

# Kill it
lsof -ti:5000 | xargs kill -9

# Restart Flask
python app.py
```

### Issue 6: "Expo Go won't load"

**Solution:**
```bash
cd mobile-app
rm -rf node_modules .expo package-lock.json
npm install
npx expo start --clear
```

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────┐
│           Your Phone (Expo Go)              │
│  ┌──────────────────────────────────────┐   │
│  │  Camera → Capture → Base64 Encoding  │   │
│  └──────────────┬───────────────────────┘   │
└─────────────────┼───────────────────────────┘
                  │ HTTP POST
                  │ (Base64 Image)
                  ▼
┌─────────────────────────────────────────────┐
│        Your Mac (Flask Server)              │
│  ┌──────────────────────────────────────┐   │
│  │  Receive → Decode → Tesseract OCR    │   │
│  │  Process → Return Text (JSON)        │   │
│  └──────────────┬───────────────────────┘   │
└─────────────────┼───────────────────────────┘
                  │ HTTP Response
                  │ {"text": "..."}
                  ▼
┌─────────────────────────────────────────────┐
│           Your Phone (Expo Go)              │
│  ┌──────────────────────────────────────┐   │
│  │  Display Text → "Take Another" btn   │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 📝 Quick Reference Commands

### Backend:
```bash
cd backend
./start.sh                    # Start server (easy way)
python app.py                 # Start server (manual)
python test_ocr.py            # Test OCR endpoint
```

### Mobile App:
```bash
cd mobile-app
npm install                   # Install dependencies
npx expo start                # Start development server
npx expo start --clear        # Clear cache and start
```

### Utilities:
```bash
ipconfig getifaddr en0        # Get Mac IP address
lsof -ti:5000                 # Check port 5000 usage
tesseract --version           # Check Tesseract installation
```

---

## 🎯 Success Checklist

After setup, you should have:

- [ ] ✅ Flask server running on http://0.0.0.0:5000
- [ ] ✅ Expo server running with QR code displayed
- [ ] ✅ Mobile app loaded on phone via Expo Go
- [ ] ✅ Camera permission granted
- [ ] ✅ Able to capture photos
- [ ] ✅ OCR results displayed after capture

---

## 🎓 Next Steps

Once everything is working:

1. **Test with different texts:**
   - Printed text (easiest)
   - Handwritten text (harder)
   - Signs, menus, documents

2. **Experiment with features:**
   - Try different lighting conditions
   - Test image quality settings
   - Measure processing time

3. **Enhance the app:**
   - Add copy-to-clipboard
   - Save OCR history
   - Add multi-language support
   - Implement real-time scanning

---

## 💡 Pro Tips

1. **Best OCR Results:**
   - Use good lighting
   - Keep text horizontal
   - Avoid glare/shadows
   - Use clear, printed text
   - Fill frame with text

2. **Faster Development:**
   - Use `--tunnel` flag for testing outside local network
   - Enable auto-refresh in Expo
   - Check console logs for debugging

3. **Performance:**
   - Reduce image quality if slow
   - Consider image preprocessing
   - Use text detection before OCR

---

## 📞 Need Help?

1. Check the troubleshooting section above
2. Review `backend/README.md` for detailed backend info
3. Review `README.md` for project overview
4. Check terminal logs for errors
5. Verify all prerequisites are met

---

**🎉 Happy OCR-ing! If you see text extracted from your photos, you're all set!**

