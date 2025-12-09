import AsyncStorage from "@react-native-async-storage/async-storage";

export interface OCRResult {
  id: string;
  text: string;
  translated_text: string;
  annotated_image: string | null;
  confidence: number;
  engine: string;
  target_lang: string;
  timestamp: string;
}

/**
 * Initialize the database (web uses AsyncStorage)
 */
export const initDatabase = async (): Promise<null> => {
  console.log("[Database] Using AsyncStorage (web platform)");
  return null;
};

/**
 * Migrate data from AsyncStorage (no-op on web, already using AsyncStorage)
 */
export const migrateFromAsyncStorage = async (): Promise<void> => {
  // No migration needed on web, already using AsyncStorage
  return;
};

/**
 * Insert a new OCR result into AsyncStorage
 */
export const insertResult = async (result: OCRResult): Promise<void> => {
  try {
    const historyData = await AsyncStorage.getItem("ocr_history");
    let history: OCRResult[] = [];
    if (historyData) {
      history = JSON.parse(historyData);
    }
    history.unshift(result);
    // Keep only last 100 results on web
    if (history.length > 100) {
      history = history.slice(0, 100);
    }
    await AsyncStorage.setItem("ocr_history", JSON.stringify(history));
  } catch (error) {
    console.error("[Database] Error inserting result:", error);
    throw error;
  }
};

/**
 * Get all OCR results from AsyncStorage
 */
export const getAllResults = async (limit?: number): Promise<OCRResult[]> => {
  try {
    const historyData = await AsyncStorage.getItem("ocr_history");
    if (historyData) {
      let history = JSON.parse(historyData);
      if (limit) {
        history = history.slice(0, limit);
      }
      return history;
    }
    return [];
  } catch (error) {
    console.error("[Database] Error getting results:", error);
    throw error;
  }
};

/**
 * Get a single result by ID
 */
export const getResultById = async (id: string): Promise<OCRResult | null> => {
  try {
    const historyData = await AsyncStorage.getItem("ocr_history");
    if (historyData) {
      const history = JSON.parse(historyData);
      return history.find((r: OCRResult) => r.id === id) || null;
    }
    return null;
  } catch (error) {
    console.error("[Database] Error getting result by ID:", error);
    throw error;
  }
};

/**
 * Delete a result by ID
 */
export const deleteResult = async (id: string): Promise<void> => {
  try {
    const historyData = await AsyncStorage.getItem("ocr_history");
    if (historyData) {
      const history = JSON.parse(historyData);
      const filtered = history.filter((r: OCRResult) => r.id !== id);
      await AsyncStorage.setItem("ocr_history", JSON.stringify(filtered));
    }
  } catch (error) {
    console.error("[Database] Error deleting result:", error);
    throw error;
  }
};

/**
 * Delete all results
 */
export const deleteAllResults = async (): Promise<void> => {
  try {
    await AsyncStorage.removeItem("ocr_history");
  } catch (error) {
    console.error("[Database] Error deleting all results:", error);
    throw error;
  }
};

/**
 * Get the count of results
 */
export const getResultCount = async (): Promise<number> => {
  try {
    const historyData = await AsyncStorage.getItem("ocr_history");
    if (historyData) {
      const history = JSON.parse(historyData);
      return history.length;
    }
    return 0;
  } catch (error) {
    console.error("[Database] Error getting result count:", error);
    return 0;
  }
};

/**
 * Search results by text (searches in both original and translated text)
 */
export const searchResults = async (query: string): Promise<OCRResult[]> => {
  try {
    const historyData = await AsyncStorage.getItem("ocr_history");
    if (historyData) {
      const history = JSON.parse(historyData);
      const lowerQuery = query.toLowerCase();
      return history.filter(
        (r: OCRResult) =>
          r.text.toLowerCase().includes(lowerQuery) ||
          r.translated_text.toLowerCase().includes(lowerQuery)
      );
    }
    return [];
  } catch (error) {
    console.error("[Database] Error searching results:", error);
    throw error;
  }
};

