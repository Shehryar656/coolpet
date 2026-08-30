import React, { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import Slider from "@react-native-community/slider";
import { api } from "../App";
import { theme } from "../theme";

export default function GeofenceScreen({ route, navigation }) {
  const { pet, onSave } = route.params;
  const [radius, setRadius] = useState(pet.geofence_radius);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/pets/${pet.id}/geofence`, {
        geofence_lat: pet.latest_lat,
        geofence_lng: pet.latest_lng,
        geofence_radius: radius,
      });
      onSave?.(data.pet);
      navigation.goBack();
    } finally { setSaving(false); }
  };

  return (
    <View style={s.wrap}>
      <Text style={s.overline}>Adjust perimeter</Text>
      <Text style={s.h1}>Set a safe territory</Text>
      <Text style={s.body}>Anywhere outside this radius will trigger a discreet push alert.</Text>

      <View style={{ marginTop: 40 }}>
        <Text style={s.mono}>{radius} m</Text>
        <Slider
          minimumValue={50}
          maximumValue={2000}
          step={25}
          value={radius}
          onValueChange={setRadius}
          minimumTrackTintColor={theme.colors.cyan}
          maximumTrackTintColor="#222"
          thumbTintColor={theme.colors.cyan}
        />
      </View>

      <TouchableOpacity onPress={save} disabled={saving} style={s.btn}>
        <Text style={s.btnText}>{saving ? "Saving…" : "Save geofence"}</Text>
      </TouchableOpacity>
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: theme.colors.bg, padding: 28, paddingTop: 80 },
  overline: { color: theme.colors.gold, fontSize: 11, letterSpacing: 3, textTransform: "uppercase" },
  h1: { color: "#fff", fontSize: 30, fontWeight: "300", marginTop: 12 },
  body: { color: theme.colors.muted, marginTop: 8 },
  mono: { color: "#fff", fontFamily: "monospace", fontSize: 32, marginBottom: 12 },
  btn: { marginTop: 40, backgroundColor: theme.colors.gold, paddingVertical: 14, borderRadius: 999, alignItems: "center" },
  btnText: { color: "#000", fontWeight: "600" },
});
