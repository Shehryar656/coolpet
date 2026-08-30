import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { theme } from "../theme";

// Simplified static bottom sheet — production would wrap @gorhom/bottom-sheet.
export default function HealthBottomSheet({ pet }) {
  return (
    <View style={s.sheet}>
      <View style={s.grabber} />
      <Text style={s.overline}>Now tracking</Text>
      <Text style={s.name}>{pet.name}</Text>
      <View style={s.row}>
        <Stat label="BPM" value={pet.latest_bpm} color={theme.colors.red} />
        <Stat label="BAT" value={`${pet.latest_battery}%`} color={theme.colors.gold} />
        <Stat label="M/S" value={pet.latest_speed?.toFixed?.(1) ?? "0.0"} color={theme.colors.cyan} />
      </View>
    </View>
  );
}

const Stat = ({ label, value, color }) => (
  <View style={s.stat}>
    <Text style={[s.statLabel, { color }]}>{label}</Text>
    <Text style={s.statValue}>{value}</Text>
  </View>
);

const s = StyleSheet.create({
  sheet: { position: "absolute", left: 0, right: 0, bottom: 0, backgroundColor: "rgba(15,15,19,0.94)", borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, borderTopColor: theme.colors.border, borderTopWidth: 1 },
  grabber: { alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: "#333", marginBottom: 12 },
  overline: { color: theme.colors.gold, fontSize: 11, letterSpacing: 3, textTransform: "uppercase" },
  name: { color: "#fff", fontSize: 24, fontWeight: "300", marginTop: 4 },
  row: { flexDirection: "row", marginTop: 16, gap: 12 },
  stat: { flex: 1, backgroundColor: "#0B0B0F", borderRadius: 16, padding: 12, borderColor: theme.colors.border, borderWidth: 1 },
  statLabel: { fontSize: 10, letterSpacing: 2 },
  statValue: { color: "#fff", fontSize: 22, marginTop: 4, fontFamily: "monospace" },
});
