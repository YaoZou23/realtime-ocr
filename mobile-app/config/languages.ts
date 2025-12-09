// Language configuration - easily extensible for future languages
export interface Language {
  code: string;
  name: string;
  nativeName: string;
}

export const LANGUAGES: Language[] = [
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
  // Add more languages here in the future:
];

export const getLanguageByCode = (code: string): Language | undefined => {
  return LANGUAGES.find((lang) => lang.code === code);
};

export const getLanguageDisplayName = (code: string): string => {
  const lang = getLanguageByCode(code);
  return lang ? `${lang.nativeName}` : code;
};

