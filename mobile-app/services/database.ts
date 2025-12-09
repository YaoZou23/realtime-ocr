// Platform-specific database implementations
// Metro bundler automatically resolves .native.ts for iOS/Android and .web.ts for web
// This file exists for TypeScript type resolution

// Export types (same in both files)
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

// Re-export functions - Metro will resolve to correct platform file
// @ts-ignore - Platform-specific files handled by Metro
export {
  initDatabase,
  migrateFromAsyncStorage,
  insertResult,
  getAllResults,
  getResultById,
  deleteResult,
  deleteAllResults,
  getResultCount,
  searchResults,
} from "./database.native";

