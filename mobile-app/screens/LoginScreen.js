import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform } from "react-native";
import { useAuth } from "../App";
import { theme } from "../theme";

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const submit = async () => {
    setBusy(true); setErr(null);
    try { await login(email, password); }
    catch (e) { setErr(e?.response?.data?.detail || "Login failed"); }
    finally { setBusy(false); }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.wrap}>
      <View style={s.inner}>
        <Text style={s.overline}>CoolPet</Text>
        <Text style={s.h1}>Concierge sign in</Text>
        <View style={{ marginTop: 32 }}>
          <Text style={s.label}>Email</Text>
          <TextInput autoCapitalize="none" keyboardType="email-address" value={email} onChangeText={setEmail} style={s.input} placeholder="you@coolpet.io" placeholderTextColor="#444" />
          <Text style={[s.label, { marginTop: 20 }]}>Password</Text>
          <TextInput secureTextEntry value={password} onChangeText={setPassword} style={s.input} placeholder="••••••••" placeholderTextColor="#444" />
        </View>
        {err && <Text style={s.err}>{err}</Text>}
        <TouchableOpacity disabled={busy} onPress={submit} style={s.btn} activeOpacity={0.8}>
          <Text style={s.btnText}>{busy ? "Signing in…" : "Sign in"}</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: theme.colors.bg, paddingHorizontal: 28, justifyContent: "center" },
  inner: {},
  overline: { color: theme.colors.gold, letterSpacing: 4, fontSize: 12, textTransform: "uppercase" },
  h1: { color: "#fff", fontSize: 36, fontWeight: "300", marginTop: 12, letterSpacing: -1 },
  label: { color: "#666", fontSize: 11, letterSpacing: 2, textTransform: "uppercase" },
  input: { color: "#fff", borderBottomColor: theme.colors.border, borderBottomWidth: 1, paddingVertical: 8, fontSize: 15 },
  err: { color: theme.colors.red, marginTop: 16, fontSize: 13 },
  btn: { marginTop: 32, backgroundColor: theme.colors.gold, paddingVertical: 14, borderRadius: 999, alignItems: "center" },
  btnText: { color: "#000", fontWeight: "600" },
});
