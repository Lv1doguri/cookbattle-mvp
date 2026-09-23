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

// FastAPI's `detail` is a string for most errors, but a list of
// {type, loc, msg, ...} objects for 422 validation errors — rendering
// that list directly as a React child crashes the page.
export function errorMessage(err, fallback) {
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
  return fallback;
}

export default client;
