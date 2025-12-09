// mobile-app/app/(tabs)/index.tsx
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import LargeButton from "../../components/LargeButton";

export default function Home() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Realtime OCR</Text>
      <Text style={styles.subtitle}>照片识别 · 实时预览 · 翻译 · 导出</Text>

      <LargeButton title="开始识别" to="/(tabs)/upload" style={{ marginTop: 24 }} />
      <LargeButton title="查看最近结果" to="/(tabs)/result" style={{ marginTop: 12, backgroundColor: "#FFC107" } as any} />

      <View style={{ flex: 1 }} />
      <Text style={styles.footer}>提示：请确认后端地址已设置 (config.ts)</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: "#F7F9FC" },
  title: { fontSize: 28, fontWeight: "700", color: "#1E88E5", marginTop: 20 },
  subtitle: { color: "#666", marginTop: 6 },
  footer: { textAlign: "center", color: "#999", marginBottom: 12 }
});
