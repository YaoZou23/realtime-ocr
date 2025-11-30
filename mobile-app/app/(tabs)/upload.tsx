import React, { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Image, ActivityIndicator, ScrollView } from "react-native";
import * as ImagePicker from "expo-image-picker";
import axios from "axios";
import { IconSymbol } from "@/components/ui/icon-symbol";

export default function Upload() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [translatedImage, setTranslatedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [imageUploaded, setImageUploaded] = useState(false);

  // ⚠️ REPLACE WITH YOUR MAC'S IP ADDRESS
  const SERVER_IP = "http://10.195.91.229:5003/api/ocr";

  const pickImage = async () => {
    // Request permission
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      alert("Sorry, we need camera roll permissions to upload images!");
      return;
    }

    // Launch image picker
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 1.0,
      base64: true,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      const base64Image = `data:image/jpeg;base64,${asset.base64}`;
      setSelectedImage(base64Image);
      setImageUploaded(true);
      setTranslatedImage(null); // Reset translated image when new image is selected
    }
  };

  const translateImage = async () => {
    if (!selectedImage) return;

    try {
      setLoading(true);
      
      // Remove the data URL prefix if it exists
      const base64Data = selectedImage.replace("data:image/jpeg;base64,", "").replace("data:image/png;base64,", "");

      console.log(`Sending translation request to: ${SERVER_IP}`);
      const response = await axios.post(
        SERVER_IP,
        {
          image: base64Data,
          target_lang: "ZH", // Translate to Chinese
          return_overlay: true, // Request annotated image with overlay
        },
        {
          headers: { "Content-Type": "application/json" },
          timeout: 60000, // 60 second timeout
          maxBodyLength: Infinity,
          maxContentLength: Infinity,
        }
      );

      if (response.data.annotated_image) {
        setTranslatedImage(response.data.annotated_image);
      } else {
        alert("Translation completed but no annotated image was returned");
      }
    } catch (err: any) {
      console.error("Translation error:", err);
      let errorMsg = "❌ Translation failed: ";
      if (err.code === "ECONNABORTED") {
        errorMsg += "Timeout - server not responding";
      } else if (err.response) {
        errorMsg += `Server error ${err.response.status}\n${err.response.data?.error || ""}`;
      } else if (err.request) {
        errorMsg += "Cannot connect to server\nCheck:\n1. Same WiFi network\n2. IP: 10.195.91.229:5003\n3. Backend running";
      } else {
        errorMsg += err.message;
      }
      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const resetUpload = () => {
    setSelectedImage(null);
    setTranslatedImage(null);
    setImageUploaded(false);
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Upload Area - Top Half */}
        <View style={styles.uploadContainer}>
          <TouchableOpacity
            style={styles.uploadBox}
            onPress={pickImage}
            disabled={loading}
            activeOpacity={0.7}
          >
            {selectedImage ? (
              <View style={styles.imagePreviewContainer}>
                <Image source={{ uri: selectedImage }} style={styles.previewImage} />
                {imageUploaded && (
                  <View style={styles.uploadCompleteBadge}>
                    <Text style={styles.uploadCompleteText}>one image upload complete</Text>
                  </View>
                )}
              </View>
            ) : (
              <View style={styles.uploadPlaceholder}>
                <IconSymbol name="arrow.up.circle.fill" size={64} color="#87CEEB" />
                <Text style={styles.uploadText}>Upload image</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

        {/* Translate Button - Below Upload Area */}
        {imageUploaded && !translatedImage && (
          <View style={styles.buttonContainer}>
            <TouchableOpacity
              style={[styles.translateButton, loading && styles.translateButtonDisabled]}
              onPress={translateImage}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.translateButtonText}>press to translate</Text>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Translated Image Display */}
        {translatedImage && (
          <View style={styles.resultContainer}>
            <Text style={styles.resultTitle}>Translated Image:</Text>
            <Image source={{ uri: translatedImage }} style={styles.resultImage} resizeMode="contain" />
            <TouchableOpacity style={styles.resetButton} onPress={resetUpload}>
              <Text style={styles.resetButtonText}>Upload Another Image</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  scrollContent: {
    flexGrow: 1,
    padding: 20,
  },
  uploadContainer: {
    height: "50%",
    minHeight: 300,
    marginBottom: 20,
  },
  uploadBox: {
    flex: 1,
    borderWidth: 2,
    borderColor: "#87CEEB",
    borderStyle: "dashed",
    borderRadius: 12,
    backgroundColor: "#F0F8FF",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  uploadPlaceholder: {
    alignItems: "center",
    justifyContent: "center",
  },
  uploadText: {
    marginTop: 16,
    fontSize: 18,
    color: "#4682B4",
    fontWeight: "500",
  },
  imagePreviewContainer: {
    width: "100%",
    height: "100%",
    position: "relative",
  },
  previewImage: {
    width: "100%",
    height: "100%",
    borderRadius: 8,
    resizeMode: "contain",
  },
  uploadCompleteBadge: {
    position: "absolute",
    bottom: 10,
    left: 10,
    right: 10,
    backgroundColor: "rgba(70, 130, 180, 0.9)",
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 6,
    alignItems: "center",
  },
  uploadCompleteText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  buttonContainer: {
    alignItems: "center",
    marginVertical: 20,
  },
  translateButton: {
    backgroundColor: "#4682B4",
    paddingVertical: 16,
    paddingHorizontal: 40,
    borderRadius: 8,
    minWidth: 200,
    alignItems: "center",
    justifyContent: "center",
  },
  translateButtonDisabled: {
    opacity: 0.6,
  },
  translateButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
  },
  resultContainer: {
    marginTop: 20,
    alignItems: "center",
  },
  resultTitle: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 16,
  },
  resultImage: {
    width: "100%",
    height: 400,
    borderRadius: 8,
    backgroundColor: "#f5f5f5",
  },
  resetButton: {
    marginTop: 20,
    backgroundColor: "#87CEEB",
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  resetButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
