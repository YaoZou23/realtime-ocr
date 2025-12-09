// mobile-app/components/CameraPreview.tsx
import React, { useEffect, useRef, useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Image, Platform, Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Camera } from "expo-camera";

type Props = {
  onCapture: (base64Image: string, uri?: string) => void;
  onError?: (e: any) => void;
};

export default function CameraPreview({ onCapture, onError }: Props) {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [type, setType] = useState(Camera.Constants?.Type?.back ?? 1);
  const [previewUri, setPreviewUri] = useState<string | null>(null);
  const cameraRef = useRef<any>(null);

  useEffect(() => {
    (async () => {
      try {
        if (Platform.OS === "web") {
          // 浏览器上不一定支持 Camera API 的全部功能，直接允许 image picker
          setHasPermission(false);
          return;
        }
        const { status } = await Camera.requestCameraPermissionsAsync();
        setHasPermission(status === "granted");
      } catch (e) {
        console.warn("Camera permission error", e);
        setHasPermission(false);
      }
    })();
  }, []);

  async function pickFromLibrary() {
    try {
      const res = await ImagePicker.launchImageLibraryAsync({
        base64: true,
        quality: 0.8
      });
      if (!res.cancelled) {
        // res.base64 may be undefined for some platforms — handle that
        const base64 = (res as any).base64 ?? null;
        setPreviewUri((res as any).uri ?? null);
        if (base64) {
          onCapture(base64, (res as any).uri);
        } else {
          // if no base64 provided, read file via FileSystem (native) - fallback
          onCapture("", (res as any).uri);
        }
      }
    } catch (e) {
      console.warn("ImagePicker error", e);
      onError?.(e);
    }
  }

  async function takePhoto() {
    try {
      if (!cameraRef.current) {
        Alert.alert("相机未准备好");
        return;
      }
      const photo = await cameraRef.current.takePictureAsync({ base64: true, quality: 0.8 });
      setPreviewUri(photo.uri);
      onCapture(photo.base64 ?? "", photo.uri);
    } catch (e) {
      console.warn("takePhoto error", e);
      onError?.(e);
    }
  }

  if (hasPermission === null) {
    return (
      <View style={styles.placeholder}>
        <Text>正在请求相机权限…</Text>
      </View>
    );
  }

  // 如果在 web 或没有相机权限，显示“从相册选择”按钮
  if (Platform.OS === "web" || hasPermission === false) {
    return (
      <View style={styles.container}>
        <TouchableOpacity style={styles.pickBtn} onPress={pickFromLibrary}>
          <Text style={styles.pickBtnText}>从相册选择图片（Web / 未授权）</Text>
        </TouchableOpacity>
        {previewUri && <Image source={{ uri: previewUri }} style={styles.preview} />}
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Camera will render on native iOS/Android */}
      <Camera
        ref={cameraRef}
        style={styles.camera}
        type={type}
        onCameraReady={() => setIsCameraReady(true)}
      />
      <View style={styles.controls}>
        <TouchableOpacity
          style={styles.controlBtn}
          onPress={() => setType((t) => (t === Camera.Constants.Type.back ? Camera.Constants.Type.front : Camera.Constants.Type.back))}
        >
          <Text style={styles.controlText}>切换摄像头</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.controlBtn, { backgroundColor: "#1E88E5" }]} onPress={takePhoto}>
          <Text style={[styles.controlText, { color: "#fff" }]}>拍照</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.controlBtn} onPress={pickFromLibrary}>
          <Text style={styles.controlText}>相册</Text>
        </TouchableOpacity>
      </View>
      {previewUri && <Image source={{ uri: previewUri }} style={styles.preview} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { width: "100%", alignItems: "center" },
  placeholder: { padding: 12, alignItems: "center" },
  camera: { width: 320, height: 220, borderRadius: 8, overflow: "hidden" },
  controls: { flexDirection: "row", marginTop: 8, justifyContent: "space-between", width: "100%", paddingHorizontal: 12 },
  controlBtn: { padding: 10, borderRadius: 8, backgroundColor: "#f0f0f0" },
  controlText: { fontWeight: "600" },
  pickBtn: { padding: 12, backgroundColor: "#f0f0f0", borderRadius: 8 },
  pickBtnText: { fontWeight: "600" },
  preview: { width: 260, height: 146, marginTop: 8, borderRadius: 8 }
});
