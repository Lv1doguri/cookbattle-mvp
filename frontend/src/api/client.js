import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("cookbattle_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Turns a relative "/uploads/xxx.jpg" path from the API into a full <img src>
export function toImageUrl(relativePath) {
  if (!relativePath) return "";
  return `${API_BASE_URL}${relativePath}`;
}

export default client;
