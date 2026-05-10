/**
 * Central configuration for the Guardian frontend.
 * VITE_API_URL should be set in the production environment (e.g., Vercel dashboard).
 * Falls back to localhost for development.
 */
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
