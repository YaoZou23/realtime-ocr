import * as SQLite from "expo-sqlite";
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

let db: SQLite.SQLiteDatabase | null = null;

/**
 * Initialize the database and create tables if they don't exist
 */
export const initDatabase = async (): Promise<SQLite.SQLiteDatabase> => {
  if (db) {
    return db;
  }

  try {
    db = await SQLite.openDatabaseAsync("ocr_history.db");
    
    // Create the OCR results table
    await db.execAsync(`
      CREATE TABLE IF NOT EXISTS ocr_results (
        id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        translated_text TEXT,
        annotated_image TEXT,
        confidence REAL,
        engine TEXT,
        target_lang TEXT,
        timestamp TEXT NOT NULL
      );
      
      CREATE INDEX IF NOT EXISTS idx_timestamp ON ocr_results(timestamp DESC);
    `);

    console.log("[Database] SQLite database initialized successfully");
    return db;
  } catch (error) {
    console.error("[Database] Error initializing database:", error);
    throw error;
  }
};

/**
 * Migrate data from AsyncStorage to SQLite (one-time migration)
 */
export const migrateFromAsyncStorage = async (): Promise<void> => {
  try {
    // Check if migration has already been done
    const migrationDone = await AsyncStorage.getItem("db_migration_done");
    if (migrationDone === "true") {
      return;
    }

    const database = await initDatabase();
    
    // Get old data from AsyncStorage
    const historyData = await AsyncStorage.getItem("ocr_history");
    const lastResultData = await AsyncStorage.getItem("last_ocr_result");

    let resultsToMigrate: OCRResult[] = [];

    // Migrate history array
    if (historyData) {
      try {
        const history = JSON.parse(historyData);
        if (Array.isArray(history)) {
          resultsToMigrate = history;
        }
      } catch (e) {
        console.warn("[Database] Failed to parse history data:", e);
      }
    }

    // Migrate last result if not already in history
    if (lastResultData) {
      try {
        const lastResult = JSON.parse(lastResultData);
        // Check if this result is already in the history
        const exists = resultsToMigrate.some((r) => r.id === lastResult.id);
        if (!exists) {
          resultsToMigrate.unshift(lastResult);
        }
      } catch (e) {
        console.warn("[Database] Failed to parse last result data:", e);
      }
    }

    // Insert migrated data into SQLite
    if (resultsToMigrate.length > 0) {
      for (const result of resultsToMigrate) {
        await insertResult(result);
      }
      console.log(`[Database] Migrated ${resultsToMigrate.length} results from AsyncStorage`);
    }

    // Mark migration as done
    await AsyncStorage.setItem("db_migration_done", "true");
  } catch (error) {
    console.error("[Database] Error during migration:", error);
  }
};

/**
 * Insert a new OCR result into the database
 */
export const insertResult = async (result: OCRResult): Promise<void> => {
  try {
    const database = await initDatabase();
    
    await database.runAsync(
      `INSERT OR REPLACE INTO ocr_results 
       (id, text, translated_text, annotated_image, confidence, engine, target_lang, timestamp)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        result.id,
        result.text,
        result.translated_text || null,
        result.annotated_image || null,
        result.confidence || 0,
        result.engine || "",
        result.target_lang || "ZH",
        result.timestamp,
      ]
    );
  } catch (error) {
    console.error("[Database] Error inserting result:", error);
    throw error;
  }
};

/**
 * Get all OCR results, ordered by timestamp (newest first)
 */
export const getAllResults = async (limit?: number): Promise<OCRResult[]> => {
  try {
    const database = await initDatabase();
    
    const query = limit
      ? `SELECT * FROM ocr_results ORDER BY timestamp DESC LIMIT ?`
      : `SELECT * FROM ocr_results ORDER BY timestamp DESC`;
    
    const params = limit ? [limit] : [];
    
    const results = await database.getAllAsync(query, params) as any[];
    
    return results.map((row: any) => ({
      id: row.id,
      text: row.text,
      translated_text: row.translated_text || "",
      annotated_image: row.annotated_image || null,
      confidence: row.confidence || 0,
      engine: row.engine || "",
      target_lang: row.target_lang || "ZH",
      timestamp: row.timestamp,
    }));
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
    const database = await initDatabase();
    
    const result = await database.getFirstAsync(
      `SELECT * FROM ocr_results WHERE id = ?`,
      [id]
    ) as any;
    
    if (!result) {
      return null;
    }
    
    return {
      id: result.id,
      text: result.text,
      translated_text: result.translated_text || "",
      annotated_image: result.annotated_image || null,
      confidence: result.confidence || 0,
      engine: result.engine || "",
      target_lang: result.target_lang || "ZH",
      timestamp: result.timestamp,
    };
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
    const database = await initDatabase();
    await database.runAsync(`DELETE FROM ocr_results WHERE id = ?`, [id]);
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
    const database = await initDatabase();
    await database.runAsync(`DELETE FROM ocr_results`);
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
    const database = await initDatabase();
    const result = await database.getFirstAsync(
      `SELECT COUNT(*) as count FROM ocr_results`
    ) as { count: number } | null;
    
    return result?.count || 0;
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
    const database = await initDatabase();
    const searchTerm = `%${query}%`;
    const results = await database.getAllAsync(
      `SELECT * FROM ocr_results 
       WHERE text LIKE ? OR translated_text LIKE ?
       ORDER BY timestamp DESC`,
      [searchTerm, searchTerm]
    ) as any[];
    
    return results.map((row: any) => ({
      id: row.id,
      text: row.text,
      translated_text: row.translated_text || "",
      annotated_image: row.annotated_image || null,
      confidence: row.confidence || 0,
      engine: row.engine || "",
      target_lang: row.target_lang || "ZH",
      timestamp: row.timestamp,
    }));
  } catch (error) {
    console.error("[Database] Error searching results:", error);
    throw error;
  }
};

