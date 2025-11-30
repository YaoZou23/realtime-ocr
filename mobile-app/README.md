# 📱 Real-Time OCR Mobile App (Expo/React Native)

A mobile application for real-time OCR (Optical Character Recognition) and image translation with text overlay, built with **React Native (Expo)**.

## 🎯 Features

- 📸 **Camera Integration**: Capture photos using your phone's camera
- 📤 **Image Upload**: Upload images from gallery for OCR processing
- 🔍 **OCR Processing**: Extract text from images using backend OCR service
- 🌐 **Translation**: Translate detected text with visual overlay on images
- ✨ **Beautiful UI**: Modern interface with loading states and error handling
- 🚀 **Fast**: Base64 encoding for quick image transfer

## 📁 Project Structure

```
mobile-app/
├── app/
│   ├── (tabs)/
│   │   ├── index.tsx      # Home tab (blank)
│   │   ├── upload.tsx     # Upload & Translation tab
│   │   └── explore.tsx    # Profile tab
│   ├── _layout.tsx        # Root layout
│   └── modal.tsx          # Modal screen
├── components/            # Reusable components
├── constants/            # App constants
├── hooks/                # Custom hooks
├── package.json          # Dependencies
└── tsconfig.json         # TypeScript config
```

## 🚀 Quick Start Guide

### Prerequisites

1. **Node.js** 18+ installed
2. **npm** or **yarn** package manager
3. **Expo CLI** (optional, but recommended)
4. **Expo Go** app on your mobile device (for testing)

### Setup Instructions

1. **Navigate to the mobile-app directory:**
```bash
cd mobile-app
```

2. **Install dependencies:**
```bash
npm install
```

⚠️ **IMPORTANT:** Make sure all dependencies are installed before running the app!

3. **Find your backend server's IP address:**
   - Make sure your backend server is running
   - On macOS/Linux: `ipconfig getifaddr en0`
   - On Windows: `ipconfig` (look for IPv4 Address)

4. **Update IP address in the app:**
   
   **File: `app/(tabs)/upload.tsx`** (Upload & Translation tab):
   ```typescript
   // ⚠️ REPLACE WITH YOUR MAC'S IP ADDRESS
   const SERVER_IP = "http://YOUR_IP:5003/api/ocr";
   ```
   
   Replace `YOUR_IP` with your backend server's IP address (e.g., `10.195.91.229`)
   
   ⚠️ **IMPORTANT:** 
   - Use the **same port** as your backend (default: **5003**)
   - Make sure both devices are on the **same Wi-Fi network**
   - **Note:** The `index.tsx` file is a blank home tab and doesn't require IP configuration

5. **Start the Expo development server:**
```bash
npx expo start
```

6. **Run on your device:**
   - Scan the QR code with **Expo Go** app (iOS/Android)
   - Or press `i` for iOS simulator / `a` for Android emulator

## 🔧 Configuration

### Backend Connection

The app connects to a Flask backend server. Make sure:

1. ✅ Backend server is running on port **5003**
2. ✅ Frontend uses the **same port** (5003)
3. ✅ Both devices (computer and phone) are on the **same Wi-Fi network**
4. ✅ IP address is correctly set in `upload.tsx`

### Port Configuration

**Default port:** 5003

If you change the backend port, update it in:
- `app/(tabs)/index.tsx`
- `app/(tabs)/upload.tsx`

**Example:**
```typescript
// If backend runs on port 5000, update to:
const SERVER_IP = "http://YOUR_IP:5000/api/ocr";
```

## 📱 App Tabs

### Home Tab (`index.tsx`)
- Blank welcome screen
- Ready for customization

### Upload Tab (`upload.tsx`)
- Upload images from gallery
- Translate text with visual overlay
- View translated images with overlay text

### Profile Tab (`explore.tsx`)
- User profile screen

## 🛠️ Technology Stack

- **React Native** 0.81.5
- **Expo** ~54.0.25
- **Expo Router** ~6.0.15 - File-based routing
- **Expo Camera** ~17.0.9 - Camera integration
- **Expo Image Picker** - Image gallery access
- **Axios** ^1.13.2 - HTTP requests
- **TypeScript** ~5.9.2 - Type safety

## 🐛 Troubleshooting

### Cannot connect to backend server

**Checklist:**
1. ✅ Backend server is running (`python app.py` in backend directory)
2. ✅ Both devices are on the **same Wi-Fi network**
3. ✅ IP address is correct in `upload.tsx`
4. ✅ **Port matches:** Frontend uses same port as backend (5003)
5. ✅ Firewall isn't blocking port 5003
6. ✅ Using `http://` not `https://`

**Test connection:**
```bash
# From your computer
curl http://YOUR_IP:5003/api/test
```

### Module not found errors

**Solution:**
```bash
cd mobile-app
rm -rf node_modules package-lock.json
npm install
```

### Camera permission denied

- Delete app and reinstall
- Check phone settings → Expo Go → Camera
- Grant permissions when prompted

### Image picker not working

- Grant media library permissions when prompted
- Check phone settings → Expo Go → Photos

### Expo Go connection issues

- Make sure phone and computer are on the same Wi-Fi network
- Try restarting Expo development server
- Clear Expo Go cache and restart

## 📦 Dependencies Installation

If you encounter dependency issues:

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# Or use yarn
yarn install
```

## 🔒 Security Notes

⚠️ **Development Mode Only**

For production deployment:
- [ ] Use HTTPS instead of HTTP
- [ ] Add API authentication (JWT tokens)
- [ ] Implement error handling and validation
- [ ] Use environment variables for API endpoints
- [ ] Add app signing and security measures

## 📝 GitHub Upload

Before uploading to GitHub:

1. **Create/update `.gitignore`** with:
```
node_modules/
.expo/
.expo-shared/
dist/
npm-debug.*
*.jks
*.p8
*.p12
*.key
*.mobileprovision
*.orig.*
web-build/
.DS_Store
```

2. **Commit and push:**
```bash
git add .
git commit -m "Add mobile OCR app with upload and translation features"
git push origin main
```

## 🚀 Next Steps

1. ✅ Install dependencies: `npm install`
2. ✅ Find backend IP address: `ipconfig getifaddr en0`
3. ✅ Update IP addresses in `app/(tabs)/index.tsx` and `upload.tsx`
4. ✅ Ensure port matches backend (default: **5003**)
5. ✅ Start Expo: `npx expo start`
6. ✅ Test on device with Expo Go
7. ✅ Upload to GitHub when ready

## 📸 How It Works

```
┌─────────────┐
│  Mobile App │
│   (Expo)    │
└──────┬──────┘
       │ 1. Capture/Upload Image
       ▼
┌─────────────┐
│   Base64    │
│  Encoding   │
└──────┬──────┘
       │ 2. Send to Backend
       ▼
┌─────────────┐
│ Flask API   │
│ /api/ocr    │
└──────┬──────┘
       │ 3. OCR + Translation
       ▼
┌─────────────┐
│  Result +   │
│  Overlay    │
└──────┬──────┘
       │ 4. Display
       ▼
┌─────────────┐
│  Mobile App │
│   (Result)  │
└─────────────┘
```

## 🎨 UI Features

- 📸 **Camera View**: Full-screen live camera (if implemented)
- 📤 **Upload Area**: Dashed border upload zone with icon
- ⏳ **Loading States**: Spinners during processing
- 📄 **Results Display**: Image with translated text overlay
- ❌ **Error Handling**: Clear error messages
- 🔄 **Reset Options**: Upload another image

---

**Happy coding! 🎉**
