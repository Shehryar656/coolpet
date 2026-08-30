import React, { createContext, useContext, useEffect, useState } from "react";
import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NavigationContainer, DarkTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import LoginScreen from "./screens/LoginScreen";
import MapScreen from "./screens/MapScreen";
import GeofenceScreen from "./screens/GeofenceScreen";
import { theme } from "./theme";

const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8001";
export const api = axios.create({ baseURL: `${API_URL}/api` });
api.interceptors.request.use(async (cfg) => {
  const token = await AsyncStorage.getItem("coolpet_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

const Stack = createNativeStackNavigator();

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const token = await AsyncStorage.getItem("coolpet_token");
      if (!token) return setLoading(false);
      try {
        const r = await api.get("/auth/me");
        setUser(r.data.user);
      } catch {
        await AsyncStorage.removeItem("coolpet_token");
      } finally { setLoading(false); }
    })();
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    await AsyncStorage.setItem("coolpet_token", data.token);
    setUser(data.user);
  };

  const logout = async () => {
    await AsyncStorage.removeItem("coolpet_token");
    setUser(null);
  };

  const navTheme = { ...DarkTheme, colors: { ...DarkTheme.colors, background: theme.colors.bg, card: theme.colors.surface, primary: theme.colors.gold } };

  return (
    <AuthCtx.Provider value={{ user, loading, login, logout }}>
      <StatusBar style="light" />
      <NavigationContainer theme={navTheme}>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          {!user
            ? <Stack.Screen name="Login" component={LoginScreen} />
            : (
              <>
                <Stack.Screen name="Map" component={MapScreen} />
                <Stack.Screen name="Geofence" component={GeofenceScreen} />
              </>
            )}
        </Stack.Navigator>
      </NavigationContainer>
    </AuthCtx.Provider>
  );
}
