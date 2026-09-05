import axios from 'axios';

// Centralized API Base URL: uses VITE_API_BASE_URL if explicitly set, defaults to Vite proxy '/api'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
  timeout: 20000,
});

api.interceptors.request.use(
  (config) => {
    // Dynamic X-Database-Mode injection from localStorage
    const savedMode = localStorage.getItem('razorpay_database_mode') || 'DEMO';
    config.headers['X-Database-Mode'] = savedMode;
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      (error.code === 'ECONNABORTED'
        ? 'Request timed out. Please verify the backend is running.'
        : 'Network connection error. Please ensure the backend server is reachable.');

    const errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail);
    return Promise.reject(new Error(errorMessage));
  }
);
