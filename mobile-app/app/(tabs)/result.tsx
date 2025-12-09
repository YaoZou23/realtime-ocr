import React, { useEffect, useState } from "react";
import { View, StyleSheet, Image, ScrollView, TouchableOpacity, RefreshControl, Platform, Alert } from "react-native";
import * as MediaLibrary from "expo-media-library";
import * as FileSystem from "expo-file-system/legacy";
import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { IconSymbol } from "@/components/ui/icon-symbol";
import {
  getAllResults,
  deleteResult as deleteResultFromDB,
  deleteAllResults as deleteAllResultsFromDB,
  initDatabase,
  migrateFromAsyncStorage,
  OCRResult,
} from "@/services/database";

export default function ResultPage() {
  const [history, setHistory] = useState<OCRResult[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedResult, setSelectedResult] = useState<OCRResult | null>(null);

  const loadHistory = async () => {
    try {
      // Initialize database and migrate from AsyncStorage if needed
      await initDatabase();
      await migrateFromAsyncStorage();
      
      // Load all results from database
      const results = await getAllResults();
      setHistory(results);
    } catch (err) {
      console.error("[Result] Failed to load OCR history:", err);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  const deleteResult = async (id: string) => {
    try {
      await deleteResultFromDB(id);
      
      // Update local state
      const updatedHistory = history.filter((result) => result.id !== id);
      setHistory(updatedHistory);
      
      // If deleting the selected result, clear selection
      if (selectedResult?.id === id) {
        setSelectedResult(null);
      }
    } catch (err) {
      console.error("[Result] Failed to delete result:", err);
    }
  };

  const clearAllHistory = async () => {
    try {
      await deleteAllResultsFromDB();
      setHistory([]);
      setSelectedResult(null);
    } catch (err) {
      console.error("[Result] Failed to clear history:", err);
    }
  };

  const formatDate = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return timestamp;
    }
  };

  const exportImage = async (result: OCRResult) => {
    if (!result.annotated_image) {
      Alert.alert("Error", "No image to export");
      return;
    }

    try {
      // Request media library permissions
      if (Platform.OS !== "web") {
        const { status } = await MediaLibrary.requestPermissionsAsync();
        if (status !== "granted") {
          Alert.alert("Permission Denied", "Please grant media library access to save images");
          return;
        }
      }

      // Extract base64 data
      let base64Data = result.annotated_image;
      if (base64Data.startsWith("data:image")) {
        base64Data = base64Data.split(",")[1];
      }

      // Create filename with timestamp
      const timestamp = new Date(result.timestamp).toISOString().replace(/[:.]/g, "-");
      const filename = `ocr_translated_${timestamp}.png`;
      
      let fileUri: string;
      if (Platform.OS === "web") {
        // For web, we'll use the data URI directly
        fileUri = result.annotated_image;
      } else {
        // For native, use cache directory
        const cacheDir = (FileSystem as any).cacheDirectory || (FileSystem as any).documentDirectory || "";
        fileUri = `${cacheDir}${filename}`;
        
        // Write file to cache
        await (FileSystem as any).writeAsStringAsync(fileUri, base64Data, {
          encoding: (FileSystem as any).EncodingType?.Base64 || "base64",
        });
      }

      // Save to media library (native) or download (web)
      if (Platform.OS === "web") {
        // For web, create download link
        if (typeof document !== "undefined") {
          const link = document.createElement("a");
          link.href = result.annotated_image;
          link.download = filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          Alert.alert("Success", "Image downloaded successfully");
        }
      } else {
        // For native, save to media library
        const asset = await MediaLibrary.createAssetAsync(fileUri);
        await MediaLibrary.createAlbumAsync("OCR Translations", asset, false);
        Alert.alert("Success", "Image saved to gallery");
        
        // Clean up cache file
        try {
          await (FileSystem as any).deleteAsync(fileUri, { idempotent: true });
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    } catch (error: any) {
      console.error("[Result] Error exporting image:", error);
      Alert.alert("Error", `Failed to export image: ${error.message || "Unknown error"}`);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  if (history.length === 0) {
    return (
      <ThemedView style={styles.container}>
        <View style={styles.emptyContainer}>
          <IconSymbol name="doc.text" size={64} color="#999" />
          <ThemedText type="title" style={styles.emptyTitle}>
            No Translation History
          </ThemedText>
          <ThemedText style={styles.emptyText}>
            Your translated results will appear here
          </ThemedText>
        </View>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <View style={styles.header}>
        <ThemedText type="title" style={styles.headerTitle}> 
          Translation History
        </ThemedText>
        <TouchableOpacity onPress={clearAllHistory} style={styles.clearButton}>
          <ThemedText style={styles.clearButtonText}>Clear All</ThemedText>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {history.map((result) => (
          <TouchableOpacity
            key={result.id}
            style={styles.resultCard}
            onPress={() => setSelectedResult(selectedResult?.id === result.id ? null : result)}
            activeOpacity={0.7}
          >
            <View style={styles.cardHeader}>
              <View style={styles.cardHeaderLeft}>
                <ThemedText style={styles.cardDate}>
                  {formatDate(result.timestamp)}
                </ThemedText>
                <ThemedText style={styles.cardLang}>
                  {result.target_lang === "ZH" ? "中文" : "English"}
                </ThemedText>
              </View>
              <TouchableOpacity
                onPress={() => deleteResult(result.id)}
                style={styles.deleteButton}
                hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              >
                <IconSymbol name="trash" size={20} color="#dc3545" />
              </TouchableOpacity>
            </View>

            <View style={styles.cardContent}>
              <View style={styles.textSection}>
                <ThemedText style={styles.label}>Original Text:</ThemedText>
                <ThemedText style={styles.text} numberOfLines={selectedResult?.id === result.id ? undefined : 2}>
                  {result.text || "No text detected"}
                </ThemedText>
              </View>

              <View style={styles.textSection}>
                <ThemedText style={styles.label}>Translated:</ThemedText>
                <ThemedText style={styles.translatedText} numberOfLines={selectedResult?.id === result.id ? undefined : 2}>
                  {result.translated_text || "No translation"}
                </ThemedText>
              </View>

              {result.annotated_image && (
                <View style={styles.imageSection}>
                  <Image
                    source={{
                      uri: result.annotated_image.startsWith("data:")
                        ? result.annotated_image
                        : `data:image/png;base64,${result.annotated_image}`,
                    }}
                    style={styles.cardImage}
                    resizeMode="contain"
                  />
                  <TouchableOpacity
                    style={styles.exportButton}
                    onPress={() => exportImage(result)}
                  >
                    <IconSymbol name="square.and.arrow.down" size={20} color="#fff" />
                    <ThemedText style={styles.exportButtonText}>Export Image</ThemedText>
                  </TouchableOpacity>
                </View>
              )}

              {selectedResult?.id === result.id && (
                <View style={styles.expandedInfo}>
                  <ThemedText style={styles.infoText}>
                    Confidence: {(result.confidence * 100).toFixed(1)}%
                  </ThemedText>
                  <ThemedText style={styles.infoText}>
                    Engine: {result.engine || "Unknown"}
                  </ThemedText>
                </View>
              )}
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 20,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1E88E5",
  },
  clearButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    backgroundColor: "#f0f0f0",
  },
  clearButtonText: {
    color: "#dc3545",
    fontSize: 14,
    fontWeight: "600",
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  resultCard: {
    backgroundColor: "#f8f9fa",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#e0e0e0",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },
  cardHeaderLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  cardDate: {
    fontSize: 12,
    color: "#666",
    fontWeight: "500",
  },
  cardLang: {
    fontSize: 12,
    color: "#4682B4",
    fontWeight: "600",
    backgroundColor: "#e3f2fd",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  deleteButton: {
    padding: 4,
  },
  cardContent: {
    gap: 12,
  },
  textSection: {
    marginBottom: 8,
  },
  label: {
    fontSize: 12,
    fontWeight: "600",
    color: "#666",
    marginBottom: 4,
    textTransform: "uppercase",
  },
  text: {
    fontSize: 16,
    color: "#333",
    lineHeight: 22,
  },
  translatedText: {
    fontSize: 16,
    color: "#4682B4",
    fontWeight: "500",
    lineHeight: 22,
  },
  imageSection: {
    marginTop: 8,
    alignItems: "center",
  },
  cardImage: {
    width: "100%",
    height: 200,
    borderRadius: 8,
    backgroundColor: "#f0f0f0",
  },
  exportButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#4682B4",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    marginTop: 12,
    gap: 8,
  },
  exportButtonText: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
  },
  expandedInfo: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: "#e0e0e0",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  infoText: {
    fontSize: 12,
    color: "#999",
  },
  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  emptyTitle: {
    marginTop: 20,
    marginBottom: 8,
    color: "#666",
  },
  emptyText: {
    color: "#999",
    textAlign: "center",
  },
});
