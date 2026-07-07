import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Restore token from localStorage on module load
const stored = localStorage.getItem("cti_access_token");
if (stored) {
  api.defaults.headers.common["Authorization"] = `Bearer ${stored}`;
}

export default api;
