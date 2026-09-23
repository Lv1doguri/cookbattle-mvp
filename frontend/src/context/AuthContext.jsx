import { createContext, useContext, useEffect, useState } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("cookbattle_user");
    if (stored) setUser(JSON.parse(stored));
    setLoading(false);
  }, []);

  function loginWithToken(token, userData) {
    localStorage.setItem("cookbattle_token", token);
    localStorage.setItem("cookbattle_user", JSON.stringify(userData));
    setUser(userData);
  }

  function logout() {
    localStorage.removeItem("cookbattle_token");
    localStorage.removeItem("cookbattle_user");
    setUser(null);
  }

  async function signup(email, password, nickname, skillTier) {
    const { data } = await client.post("/auth/signup", {
      email,
      password,
      nickname,
      skill_tier: skillTier,
    });
    loginWithToken(data.access_token, data.user);
  }

  async function login(email, password) {
    const { data } = await client.post("/auth/login", { email, password });
    loginWithToken(data.access_token, data.user);
  }

  async function loginWithGoogle(idToken, skillTier) {
    const { data } = await client.post("/auth/google", {
      id_token: idToken,
      skill_tier: skillTier,
    });
    loginWithToken(data.access_token, data.user);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signup, login, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
