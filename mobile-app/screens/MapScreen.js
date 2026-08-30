import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import MapView, { Marker, Circle, PROVIDER_DEFAULT } from "react-native-maps";
import { api } from "../App";
import HealthBottomSheet from "./HealthBottomSheet";
import { theme } from "../theme";

export default function MapScreen({ navigation }) {
  const [pets, setPets] = useState([]);
  const [selected, setSelected] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    (async () => {
      const { data } = await api.get("/pets");
      setPets(data.pets);
      setSelected(data.pets[0] || null);
    })();
  }, []);

  useEffect(() => {
    // TODO: connect to wss:// {apiHost} /api/ws/live and update state.
    // Omitted here so the scaffold compiles without a live backend.
    return () => { try { wsRef.current?.close(); } catch { /* noop */ } };
  }, []);

  if (!selected) {
    return (
      <View style={s.empty}>
        <Text style={s.emptyText}>No collars enrolled yet.</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.colors.bg }}>
      <MapView
        provider={PROVIDER_DEFAULT}
        style={{ flex: 1 }}
        region={{
          latitude: selected.latest_lat,
          longitude: selected.latest_lng,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        }}
      >
        <Circle
          center={{ latitude: selected.geofence_lat, longitude: selected.geofence_lng }}
          radius={selected.geofence_radius}
          strokeColor={theme.colors.gold}
          fillColor="rgba(212,175,55,0.08)"
        />
        <Marker coordinate={{ latitude: selected.latest_lat, longitude: selected.latest_lng }}>
          <View style={s.marker} />
        </Marker>
      </MapView>

      <TouchableOpacity
        style={s.geofenceBtn}
        onPress={() => navigation.navigate("Geofence", { pet: selected, onSave: (p) => setSelected(p) })}
      >
        <Text style={s.geofenceBtnText}>Adjust geofence</Text>
      </TouchableOpacity>

      <HealthBottomSheet pet={selected} />
    </View>
  );
}

const s = StyleSheet.create({
  marker: { width: 18, height: 18, borderRadius: 999, backgroundColor: theme.colors.cyan, borderWidth: 2, borderColor: "#000" },
  geofenceBtn: { position: "absolute", top: 60, right: 16, backgroundColor: "rgba(15,15,19,0.85)", paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, borderColor: theme.colors.border, borderWidth: 1 },
  geofenceBtnText: { color: theme.colors.gold, fontSize: 12, letterSpacing: 1 },
  empty: { flex: 1, backgroundColor: theme.colors.bg, alignItems: "center", justifyContent: "center" },
  emptyText: { color: theme.colors.muted },
});
