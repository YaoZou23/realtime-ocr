// Backend server configuration
// ⚠️ REPLACE WITH YOUR BACKEND SERVER'S IP ADDRESS
// Find your IP address:
// - macOS/Linux: `ifconfig | grep "inet " | grep -v 127.0.0.1` or `ipconfig getifaddr en0`
// - Windows: `ipconfig` (look for IPv4 Address)

export const BACKEND_CONFIG = {
  // Replace with your backend server's IP address
  // Make sure both your computer and mobile device are on the same Wi-Fi network
  BASE_URL: "http://10.195.66.31:5003",
  
  // API endpoints
  ENDPOINTS: {
    OCR: "/api/ocr",
    TRANSLATE: "/api/translate",
    TEST: "/api/test",
  },
};

// Helper function to get full API URL
export const getApiUrl = (endpoint: keyof typeof BACKEND_CONFIG.ENDPOINTS): string => {
  return `${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS[endpoint]}`;
};

