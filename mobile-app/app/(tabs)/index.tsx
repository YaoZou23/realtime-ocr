import React, { useState, useEffect, useRef } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Image, ActivityIndicator, ScrollView } from "react-native";
import { CameraView, CameraType, useCameraPermissions } from "expo-camera";
import axios from "axios";

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [photo, setPhoto] = useState<string | null>(null);
  const [ocrText, setOcrText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const cameraRef = useRef<CameraView>(null);
  const [facing, setFacing] = useState<CameraType>("back");
  const [cameraReady, setCameraReady] = useState(false);

  // ⚠️ REPLACE WITH YOUR MAC'S IP ADDRESS
  const YOUR_SERVER_IP = "http://172.16.134.182:5001/api/ocr";
  const TEST_SERVER_IP = "http://172.16.134.182:5001/api/test";

  if (!permission) {
    return <Text>Loading...</Text>;
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={styles.message}>We need your permission to show the camera</Text>
        <TouchableOpacity style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Test connection to backend
  const testConnection = async () => {
    try {
      setLoading(true);
      setOcrText("Testing connection...");
      
      const response = await axios.get(TEST_SERVER_IP, {
        timeout: 5000,
      });
      
      setOcrText(`✅ Connected! Server: ${response.data.server_ip}:${response.data.port}\nYour IP: ${response.data.ip}`);
    } catch (err: any) {
      console.error("Connection test error:", err);
      let errorMsg = "❌ Connection failed: ";
      if (err.code === "ECONNABORTED") {
        errorMsg += "Timeout - server not responding";
      } else if (err.response) {
        errorMsg += `Server error ${err.response.status}`;
      } else if (err.request) {
        errorMsg += "Cannot reach server - check:\n1. Same WiFi network\n2. IP address: 172.16.134.182\n3. Backend running on port 5001";
      } else {
        errorMsg += err.message;
      }
      setOcrText(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // Send Base64 image to Flask backend
  const sendToBackend = async (base64Image: string) => {
    try {
      setLoading(true);
      setOcrText(null);

      // Remove the data URL prefix if it exists
      const base64Data = base64Image.replace("data:image/jpeg;base64,", "");

      console.log(`Sending request to: ${YOUR_SERVER_IP}`);
      const response = await axios.post(
        YOUR_SERVER_IP,
        { image: base64Data },
        {
          headers: { "Content-Type": "application/json" },
          timeout: 60000, // 60 second timeout (OCR can take time, especially first request)
          maxBodyLength: Infinity,
          maxContentLength: Infinity,
        }
      );

      setOcrText(response.data.text || "No text detected");
    } catch (err: any) {
      console.error("Backend error:", err);
      console.error("Error details:", {
        code: err.code,
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
      
      if (err.code === "ECONNABORTED") {
        setOcrText("❌ Request timeout - check your server");
      } else if (err.response) {
        setOcrText(`❌ Server error: ${err.response.status}\n${err.response.data?.error || ""}`);
      } else if (err.request) {
        setOcrText("❌ Cannot connect to server\nCheck:\n1. Same WiFi network\n2. IP: 172.16.134.182:5001\n3. Backend running");
      } else {
        setOcrText(`❌ Error: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const takePhoto = async () => {
    console.log("takePhoto invoked");
    if (!cameraRef.current) {
      console.warn("Camera ref not ready");
      setOcrText("❌ Camera not ready yet");
      return;
    }
    if (!cameraReady) {
      console.warn("Camera not ready to capture");
      setOcrText("❌ Waiting for camera to be ready");
      return;
    }

    try {
      const result = await cameraRef.current.takePictureAsync({
        quality: 0.7,
        base64: true,
      });
      console.log("Photo capture result:", {
        hasBase64: !!result?.base64,
        width: result?.width,
        height: result?.height,
      });

      if (result?.base64) {
        const base64Image = `data:image/jpeg;base64,${result.base64}`;
        setPhoto(base64Image);

        // Automatically send to backend
        await sendToBackend(base64Image);
      }
    } catch (error) {
      console.error("Photo capture error:", error);
      setOcrText("❌ Failed to capture photo");
    }
  };

  return (
    <View style={styles.container}>
      {!photo ? (
        <>
          <CameraView
            ref={cameraRef}
            style={styles.camera}
            facing={facing}
            onCameraReady={() => {
              console.log("Camera ready");
              setCameraReady(true);
            }}
          />

          <TouchableOpacity style={[styles.button, styles.testButton]} onPress={testConnection}>
            <Text style={styles.buttonText}>🔌 Test Connection</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.button} onPress={takePhoto}>
            <Text style={styles.buttonText}>📸 Capture & Scan</Text>
          </TouchableOpacity>
        </>
      ) : (
        <ScrollView contentContainerStyle={styles.previewContainer}>
          <Image source={{ uri: photo }} style={styles.preview} />

          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#1e90ff" />
              <Text style={styles.loadingText}>Processing OCR...</Text>
            </View>
          ) : ocrText ? (
            <View style={styles.ocrContainer}>
              <Text style={styles.ocrLabel}>📄 Detected Text:</Text>
              <Text style={styles.ocrText}>{ocrText}</Text>
            </View>
          ) : null}

          <TouchableOpacity
            style={styles.button}
            onPress={() => {
              setPhoto(null);
              setOcrText(null);
            }}
          >
            <Text style={styles.buttonText}>📷 Take Another</Text>
          </TouchableOpacity>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "center",
  },
  message: {
    color: "white",
    fontSize: 16,
    textAlign: "center",
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  camera: {
    width: "100%",
    height: "80%",
  },
  button: {
    position: "absolute",
    bottom: 40,
    backgroundColor: "#1e90ff",
    paddingVertical: 14,
    paddingHorizontal: 30,
    borderRadius: 20,
    alignSelf: "center",
  },
  testButton: {
    bottom: 110,
    backgroundColor: "#28a745",
  },
  buttonText: {
    color: "white",
    fontSize: 18,
    fontWeight: "600",
  },
  previewContainer: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 20,
    paddingHorizontal: 10,
  },
  preview: {
    width: "90%",
    height: 300,
    resizeMode: "contain",
    borderRadius: 10,
    marginBottom: 20,
  },
  loadingContainer: {
    alignItems: "center",
    marginVertical: 20,
  },
  loadingText: {
    color: "white",
    fontSize: 16,
    marginTop: 10,
  },
  ocrContainer: {
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: 10,
    padding: 15,
    width: "90%",
    marginBottom: 20,
    maxHeight: 200,
  },
  ocrLabel: {
    color: "#1e90ff",
    fontSize: 16,
    fontWeight: "bold",
    marginBottom: 10,
  },
  ocrText: {
    color: "white",
    fontSize: 16,
    lineHeight: 24,
  },
});
