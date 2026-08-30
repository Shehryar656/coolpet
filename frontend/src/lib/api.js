import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("coolpet_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export const wsURL = () => {
  const base = BACKEND_URL.replace(/^http/, "ws");
  return `${base}/api/ws/live`;
};
