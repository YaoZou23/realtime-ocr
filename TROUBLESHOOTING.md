# 🔧 Troubleshooting: Backend Not Receiving Requests

## Quick Checklist

1. ✅ **Backend is running**
   ```bash
   cd backend
   python app.py
   # Should see: "Starting Flask server on 0.0.0.0:5003"
   ```

2. ✅ **IP Address is correct**
   - Find your IP: `ipconfig getifaddr en0` (macOS) or `ipconfig` (Windows)
   - Update `mobile-app/config.ts` with your actual IP
   - Current config: `http://10.195.91.229:5003`

3. ✅ **Same WiFi network**
   - Both computer and mobile device must be on the same network

4. ✅ **Port 5003 is accessible**
   - Check firewall settings
   - Test locally: `curl http://localhost:5003/api/test`

5. ✅ **Use Test Connection button**
   - In the upload tab, click "Test Backend Connection"
   - This will verify connectivity before sending images

## Debugging Steps

### 1. Test Backend Locally
```bash
# From your computer
curl http://localhost:5003/api/test
```

### 2. Test from Mobile Device Network
```bash
# Replace with your actual IP
curl http://10.195.91.229:5003/api/test
```

### 3. Check Backend Logs
When you make a request, you should see in the backend console:
```
INFO: Received OCR request from 10.195.91.XXX
INFO: Request headers: {...}
INFO: Image data length: XXXXX
```

If you don't see these logs, the request isn't reaching the backend.

### 4. Check Frontend Console
In Expo/React Native, check the console for:
- `[DEBUG] Sending translation request to: http://...`
- `[DEBUG] Image data length: ...`
- `[ERROR] Translation error: ...`

### 5. Common Issues

#### Issue: "Cannot connect to server"
**Solutions:**
- Verify backend is running
- Check IP address matches your computer's IP
- Ensure both devices on same WiFi
- Try the Test Connection button first

#### Issue: "Timeout - server not responding"
**Solutions:**
- Backend might be slow to respond (first OCR request takes 15-30s)
- Check if backend process is still running
- Check backend logs for errors

#### Issue: "CORS error" (if you see this)
**Solutions:**
- Backend has CORS enabled, but check if it's working
- Check backend logs for CORS preflight requests

## Network Configuration

### Find Your IP Address

**macOS/Linux:**
```bash
ipconfig getifaddr en0  # Usually en0 for WiFi
# or
ifconfig | grep "inet " | grep -v 127.0.0.1
```

**Windows:**
```bash
ipconfig
# Look for IPv4 Address under your active network adapter
```

### Update Frontend Config

Edit `mobile-app/config.ts`:
```typescript
BASE_URL: "http://YOUR_IP:5003",
```

## Testing the Connection

1. **Start the backend:**
   ```bash
   cd backend
   python app.py
   ```

2. **In the mobile app:**
   - Go to Upload tab
   - Click "Test Backend Connection" button
   - Should see success message with server details

3. **If test fails:**
   - Check the error message
   - Verify IP address
   - Check backend is running
   - Check network connectivity

## Backend Logging

The backend now logs:
- All incoming requests with IP address
- Request headers
- Image data length
- Target language
- Any errors

Watch the backend console when making requests to see what's happening.

## Still Not Working?

1. Check backend console for any error messages
2. Check mobile app console (Expo logs) for request details
3. Try testing with curl from your computer first
4. Verify firewall isn't blocking port 5003
5. Make sure you're using `http://` not `https://`
