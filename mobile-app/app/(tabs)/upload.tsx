import React, { useState, useEffect } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Image, ActivityIndicator, ScrollView, Modal, FlatList, Alert } from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as ImageManipulator from "expo-image-manipulator";
import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { getApiUrl } from "@/config";
import { insertResult, initDatabase } from "@/services/database";
import { LANGUAGES as IMPORTED_LANGUAGES, getLanguageDisplayName, Language } from "@/config/languages";

// Direct language list to ensure it's loaded correctly
const LANGUAGES: Language[] = [
  { code: "ZH", name: "Chinese", nativeName: "中文" },
  { code: "EN", name: "English", nativeName: "English" },
  { code: "JA", name: "Japanese", nativeName: "日本語" },
  { code: "KO", name: "Korean", nativeName: "한국어" },
  { code: "ES", name: "Spanish", nativeName: "Español" },
  { code: "FR", name: "French", nativeName: "Français" },
  { code: "DE", name: "German", nativeName: "Deutsch" },
  { code: "PT", name: "Portuguese", nativeName: "Português" },
  { code: "RU", name: "Russian", nativeName: "Русский" },
  { code: "AR", name: "Arabic", nativeName: "العربية" },
  { code: "HI", name: "Hindi", nativeName: "हिन्दी" },
  { code: "BN", name: "Bengali", nativeName: "বাংলা" },
  { code: "NL", name: "Dutch", nativeName: "Nederlands" },
  { code: "PL", name: "Polish", nativeName: "Polski" },
  { code: "TH", name: "Thai", nativeName: "ไทย" },
  { code: "ID", name: "Indonesian", nativeName: "Bahasa Indonesia" },
  { code: "PH", name: "Filipino", nativeName: "Filipino" },
  { code: "MY", name: "Malay", nativeName: "Bahasa Melayu" },
  { code: "SG", name: "Singaporean", nativeName: "Singaporean" },
];

// Use imported if available, otherwise use inline
const ACTIVE_LANGUAGES = IMPORTED_LANGUAGES && IMPORTED_LANGUAGES.length > 2 ? IMPORTED_LANGUAGES : LANGUAGES;

type TargetLanguage = string;

export default function Upload() {
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [translatedImages, setTranslatedImages] = useState<(string | null)[]>([]);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [deleteCandidateIndex, setDeleteCandidateIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState<TargetLanguage>("ZH");
  const [languageModalVisible, setLanguageModalVisible] = useState(false);

  // Debug: Log available languages on component mount
  useEffect(() => {
    console.log("[Upload] Imported languages count:", IMPORTED_LANGUAGES?.length || 0);
    console.log("[Upload] Active languages count:", ACTIVE_LANGUAGES.length);
    console.log("[Upload] Languages:", ACTIVE_LANGUAGES.map(l => `${l.code}: ${l.name}`).join(", "));
  }, []);

  const currentImage = selectedImages[selectedImageIndex] || null;
  const currentTranslatedImage = translatedImages[selectedImageIndex] || null;
  const hasAnyTranslation = translatedImages.some((img) => !!img);
  const hasUntranslated =
    translatedImages.length < selectedImages.length ||
    translatedImages.some((img) => img === null);
  const imageUploaded = selectedImages.length > 0;

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
      allowsMultipleSelection: true,
      selectionLimit: 5,
      allowsEditing: false, // keep full image, no forced crop
      quality: 1.0,
      base64: true,
    });

    if (!result.canceled && result.assets.length) {
      const remainingSlots = 5 - selectedImages.length;
      const assetsToAdd = result.assets.slice(0, remainingSlots);
      if (result.assets.length > remainingSlots) {
        alert("You can upload at most 5 images. Extra images were ignored.");
      }

      const newImages = (
        await Promise.all(
          assetsToAdd.map(async (asset) => {
            try {
              const manipulated = await ImageManipulator.manipulateAsync(
                asset.uri,
                [],
                { compress: 1, format: ImageManipulator.SaveFormat.JPEG, base64: true }
              );
              if (!manipulated.base64) return null;
              return `data:image/jpeg;base64,${manipulated.base64}`;
            } catch (err) {
              console.warn("[Upload] Failed to process selected image:", err);
              return null;
            }
          })
        )
      ).filter((img): img is string => Boolean(img));

      const updated = [...selectedImages, ...newImages].slice(0, 5);
      const updatedTranslated = [
        ...translatedImages,
        ...new Array(newImages.length).fill(null),
      ].slice(0, 5);

      setSelectedImages(updated);
      setTranslatedImages(updatedTranslated);
      setSelectedImageIndex(updated.length - 1);
    }
  };

  const pickImageFromCamera = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      alert("Sorry, we need camera permissions to take a photo!");
      return;
    }

    if (selectedImages.length >= 5) {
      alert("You already have 5 images. Remove one to add another.");
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false, // keep full image, no forced crop
      quality: 1.0,
      base64: true,
    });

    if (!result.canceled && result.assets.length) {
      const asset = result.assets[0];
      let newImage: string | null = null;
      try {
        const manipulated = await ImageManipulator.manipulateAsync(
          asset.uri,
          [],
          { compress: 1, format: ImageManipulator.SaveFormat.JPEG, base64: true }
        );
        if (manipulated.base64) {
          newImage = `data:image/jpeg;base64,${manipulated.base64}`;
        }
      } catch (err) {
        console.warn("[Upload] Failed to process captured image:", err);
      }

      if (!newImage) {
        alert("Could not load captured image. Please try again.");
        return;
      }

      const updated = [...selectedImages, newImage].slice(0, 5);
      const updatedTranslated = [
        ...translatedImages,
        null,
      ].slice(0, 5);

      setSelectedImages(updated);
      setTranslatedImages(updatedTranslated);
      setSelectedImageIndex(updated.length - 1);
    }
  };

  const showUploadOptions = () => {
    Alert.alert(
      "Add Images",
      "Choose an option",
      [
        { text: "Take Photo", onPress: pickImageFromCamera },
        { text: "Choose from Gallery", onPress: pickImage },
        { text: "Cancel", style: "cancel" },
      ],
      { cancelable: true }
    );
  };

  const translateImage = async () => {
    if (!imageUploaded) return;

    try {
      setLoading(true);
      const apiUrl = getApiUrl("OCR");

      const total = selectedImages.length;
      const startIndex = selectedImageIndex;

      // Process images starting from the currently selected one, wrapping around
      for (let offset = 0; offset < total; offset += 1) {
        const i = (startIndex + offset) % total;
        if (translatedImages[i]) continue;

        const image = selectedImages[i];
        const base64Data = image
          .replace("data:image/jpeg;base64,", "")
          .replace("data:image/png;base64,", "");

        const requestPayload = {
          image: base64Data,
          target_lang: targetLanguage,
          return_overlay: true,
        };

        const response = await axios.post(
          apiUrl,
          requestPayload,
          {
            headers: { "Content-Type": "application/json" },
            timeout: 60000,
            maxBodyLength: Infinity,
            maxContentLength: Infinity,
          }
        );

        const annotatedImage = response.data.annotated_image || null;

        const ocrResult = {
          id: `${Date.now()}-${i}`,
          text: response.data.text || "",
          translated_text: response.data.translated_text || "",
          annotated_image: annotatedImage,
          confidence: response.data.confidence || 0,
          engine: response.data.engine || "",
          target_lang: targetLanguage,
          timestamp: new Date().toISOString(),
        };

        try {
          await initDatabase();
          await insertResult(ocrResult);
          await AsyncStorage.setItem("last_ocr_result", JSON.stringify(ocrResult));
        } catch (storageError) {
          console.error("[Upload] Failed to save result to database:", storageError);
          try {
            await AsyncStorage.setItem("last_ocr_result", JSON.stringify(ocrResult));
          } catch (fallbackError) {
            console.error("[Upload] Failed to save to AsyncStorage fallback:", fallbackError);
          }
        }

        if (annotatedImage) {
          setTranslatedImages((prev) => {
            const next = [...prev];
            next[i] = annotatedImage;
            return next;
          });
        }
      }
    } catch (err: any) {
      console.error("[ERROR] Translation error:", err);
      console.error("[ERROR] Error details:", {
        message: err.message,
        code: err.code,
        response: err.response ? {
          status: err.response.status,
          data: err.response.data,
        } : null,
        request: err.request ? "Request made but no response" : null,
      });
      
      let errorMsg = "❌ Translation failed: ";
      if (err.code === "ECONNABORTED") {
        errorMsg += "Timeout - server not responding\n\n";
        errorMsg += "Possible issues:\n";
        errorMsg += "1. Backend server is not running\n";
        errorMsg += "2. Network connection is slow\n";
        errorMsg += "3. Firewall blocking the connection";
      } else if (err.response) {
        errorMsg += `Server error ${err.response.status}\n${err.response.data?.error || ""}`;
      } else if (err.request) {
        const apiUrl = getApiUrl("OCR");
        errorMsg += `Cannot connect to server\n\n`;
        errorMsg += `Backend URL: ${apiUrl}\n\n`;
        errorMsg += `Checklist:\n`;
        errorMsg += `1. Backend is running (python app.py)\n`;
        errorMsg += `2. Same WiFi network\n`;
        errorMsg += `3. IP address is correct\n`;
        errorMsg += `4. Port 5003 is not blocked\n`;
        errorMsg += `5. Try: curl ${apiUrl.replace('/api/ocr', '/api/test')}`;
      } else {
        errorMsg += err.message;
      }
      alert(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const removeImageAt = (index: number) => {
    if (!imageUploaded) return;
    const updated = selectedImages.filter((_, idx) => idx !== index);
    const updatedTranslated = translatedImages.filter((_, idx) => idx !== index);

    let nextIndex = selectedImageIndex;
    if (selectedImageIndex === index) {
      nextIndex = Math.max(0, selectedImageIndex - 1);
    } else if (selectedImageIndex > index) {
      nextIndex = selectedImageIndex - 1;
    }

    if (nextIndex >= updated.length) {
      nextIndex = Math.max(0, updated.length - 1);
    }

    setSelectedImages(updated);
    setTranslatedImages(updatedTranslated);
    setSelectedImageIndex(nextIndex);
    setDeleteCandidateIndex(null);

  };

  const resetUpload = () => {
    setSelectedImages([]);
    setTranslatedImages([]);
    setSelectedImageIndex(0);
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Upload Area - Top Half */}
        <View style={[styles.uploadContainer, hasAnyTranslation && styles.uploadContainerCompact]}>
        <TouchableOpacity
          onPress={showUploadOptions}
          style={{
            width: "100%",
            padding: 20,
            backgroundColor: "#4A90E2",
            borderRadius: 10,
            alignItems: "center",
            marginBottom: 20,
          }}
        >
        <Text style={{ color: "white", fontSize: 18, fontWeight: "600" }}>
        Upload Images
        </Text>
        </TouchableOpacity>

          {/* Thumbnail selector for multiple images */}
          {selectedImages.length > 0 && (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.thumbnailScroll}
              contentContainerStyle={styles.thumbnailContent}
            >
              {selectedImages.map((img, idx) => (
                <TouchableOpacity
                  key={`${idx}-${img.slice(0, 10)}`}
                  style={[
                    styles.thumbnailWrapper,
                    idx === selectedImageIndex && styles.thumbnailSelected,
                  ]}
                  onPress={() => {
                    setSelectedImageIndex(idx);
                    setDeleteCandidateIndex(idx);
                  }}
                >
                  <Image source={{ uri: img }} style={styles.thumbnailImage} />
                  <Text style={styles.thumbnailIndex}>{idx + 1}</Text>
                  {deleteCandidateIndex === idx && (
                    <TouchableOpacity
                      style={styles.thumbnailDeleteButton}
                      onPress={() => removeImageAt(idx)}
                      disabled={loading}
                    >
                      <IconSymbol name="xmark.circle.fill" size={20} color="#dc3545" />
                    </TouchableOpacity>
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
          )}
        </View>

        {/* Language Selector - Below Upload Area */}
        {imageUploaded && !currentTranslatedImage && (
          <View style={styles.languageSelectorContainer}>
            <Text style={styles.languageSelectorLabel}>Translate to:</Text>
            <TouchableOpacity
              style={styles.languageSelectorButton}
              onPress={() => setLanguageModalVisible(true)}
              disabled={loading}
            >
              <Text style={styles.languageSelectorButtonText}>
                {getLanguageDisplayName(targetLanguage)}
              </Text>
              <IconSymbol name="chevron.down" size={20} color="#4682B4" />
            </TouchableOpacity>
          </View>
        )}

        {/* Language Selection Modal */}
        <Modal
          visible={languageModalVisible}
          transparent={true}
          animationType="slide"
          onRequestClose={() => setLanguageModalVisible(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <View>
                  <Text style={styles.modalTitle}>Select Language</Text>
                  <Text style={styles.modalSubtitle}>{ACTIVE_LANGUAGES.length} languages available</Text>
                </View>
                <TouchableOpacity
                  onPress={() => setLanguageModalVisible(false)}
                  style={styles.modalCloseButton}
                >
                  <IconSymbol name="xmark" size={24} color="#333" />
                </TouchableOpacity>
              </View>
              <FlatList
                data={ACTIVE_LANGUAGES}
                keyExtractor={(item) => item.code}
                style={styles.languageList}
                contentContainerStyle={styles.languageListContent}
                showsVerticalScrollIndicator={true}
                initialNumToRender={20}
                windowSize={10}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={[
                      styles.languageOption,
                      targetLanguage === item.code && styles.languageOptionSelected,
                    ]}
                    onPress={() => {
                      setTargetLanguage(item.code);
                      setLanguageModalVisible(false);
                    }}
                  >
                    <Text
                      style={[
                        styles.languageOptionText,
                        targetLanguage === item.code && styles.languageOptionTextSelected,
                      ]}
                    >
                      {item.nativeName || item.name}
                    </Text>
                    {targetLanguage === item.code && (
                      <IconSymbol name="checkmark" size={20} color="#4682B4" />
                    )}
                  </TouchableOpacity>
                )}
              />
            </View>
          </View>
        </Modal>

        {/* Translate Button - Below Language Selector */}
        {imageUploaded && hasUntranslated && (
          <View style={styles.buttonContainer}>
            <TouchableOpacity
              style={[styles.translateButton, loading && styles.translateButtonDisabled]}
              onPress={translateImage}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.translateButtonText}>Translate All</Text>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Translated Image Display */}
        {currentTranslatedImage && (
          <View style={styles.resultContainer}>
            <Text style={styles.resultTitle}>Translated Image:</Text>
            <Image source={{ uri: currentTranslatedImage }} style={styles.resultImage} resizeMode="contain" />
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
    paddingBottom: 120,
  },
  uploadContainer: {
    height: "50%",
    minHeight: 300,
    marginBottom: 20,
  },
  uploadContainerCompact: {
    height: undefined,
    minHeight: 0,
    marginBottom: 12,
  },
  thumbnailScroll: {
    marginTop: 10,
  },
  thumbnailContent: {
    gap: 10,
    paddingVertical: 6,
  },
  thumbnailWrapper: {
    width: 64,
    height: 64,
    borderRadius: 8,
    overflow: "hidden",
    borderWidth: 2,
    borderColor: "transparent",
    position: "relative",
  },
  thumbnailSelected: {
    borderColor: "#4682B4",
  },
  thumbnailDeleteButton: {
    position: "absolute",
    top: 4,
    right: 4,
    backgroundColor: "rgba(255,255,255,0.9)",
    borderRadius: 10,
    padding: 2,
  },
  thumbnailImage: {
    width: "100%",
    height: "100%",
    resizeMode: "cover",
  },
  thumbnailIndex: {
    position: "absolute",
    bottom: 4,
    right: 4,
    backgroundColor: "rgba(0,0,0,0.6)",
    color: "#fff",
    fontSize: 12,
    paddingHorizontal: 4,
    paddingVertical: 2,
    borderRadius: 4,
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
  languageSelectorContainer: {
    marginVertical: 20,
    paddingHorizontal: 20,
  },
  languageSelectorLabel: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
    marginBottom: 12,
    textAlign: "center",
  },
  languageSelectorButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 8,
    backgroundColor: "#F0F8FF",
    borderWidth: 2,
    borderColor: "#87CEEB",
  },
  languageSelectorButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#4682B4",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    justifyContent: "flex-end",
  },
  modalContent: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: "70%",
    paddingBottom: 20,
    flex: 1,
  },
  languageList: {
    flex: 1,
  },
  languageListContent: {
    paddingBottom: 20,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#333",
  },
  modalSubtitle: {
    fontSize: 12,
    color: "#666",
    marginTop: 4,
  },
  modalCloseButton: {
    padding: 4,
  },
  languageOption: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f0f0",
  },
  languageOptionSelected: {
    backgroundColor: "#F0F8FF",
  },
  languageOptionText: {
    fontSize: 16,
    color: "#333",
  },
  languageOptionTextSelected: {
    fontWeight: "600",
    color: "#4682B4",
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
    marginTop: 10,
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
