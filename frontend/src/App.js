import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import "./App.css";
import { AuthProvider, useAuth } from "./lib/auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import PaymentSuccess from "./pages/PaymentSuccess";
import PaymentCancel from "./pages/PaymentCancel";
import AuthCallback from "./pages/AuthCallback";
import { Toaster } from "sonner";

function Private({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-[#050505] text-white/60 flex items-center justify-center">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRouter() {
  // Detect Emergent OAuth callback synchronously during render (not in useEffect —
  // useEffect runs after first render and creates a race with ProtectedRoute).
  const location = useLocation();
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/dashboard" element={<Private><Dashboard /></Private>} />
      <Route path="/payment/success" element={<PaymentSuccess />} />
      <Route path="/payment/cancel" element={<PaymentCancel />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Toaster theme="dark" position="top-right" />
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
