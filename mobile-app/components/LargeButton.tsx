// mobile-app/components/LargeButton.tsx
import React from "react";
import { TouchableOpacity, Text, StyleSheet, ViewStyle, GestureResponderEvent } from "react-native";
import { useRouter } from "expo-router";

type Props = {
  title: string;
  onPress?: (e?: GestureResponderEvent) => void;
  to?: string;
  style?: ViewStyle | ViewStyle[];
  disabled?: boolean;
};

function mergeStyles(style: ViewStyle | ViewStyle[] | undefined) {
  if (!style) return {};
  if (Array.isArray(style)) {
    // 把数组里的对象合并成一个对象（避免把数组传给 DOM）
    return Object.assign({}, ...style);
  }
  return style;
}

export default function LargeButton({ title, onPress, to, style, disabled }: Props) {
  const router = useRouter();
  const mergedStyle = [styles.button, mergeStyles(style)] as any;

  const handlePress = (e?: GestureResponderEvent) => {
    if (disabled) return;
    if (onPress) {
      onPress(e);
    } else if (to) {
      // 使用 expo-router 编程式导航，避免使用 Link asChild 导致 style 数组被透传到 DOM
      router.push(to);
    }
  };

  return (
    <TouchableOpacity style={mergedStyle} onPress={handlePress} activeOpacity={0.85} disabled={disabled}>
      <Text style={styles.text}>{title}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: "#1E88E5",
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    elevation: 3
  },
  text: { color: "#fff", fontSize: 16, fontWeight: "600" }
});
