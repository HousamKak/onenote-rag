import axios from 'axios';
import type { RAGConfig, QueryRequest, QueryResponse, IndexStats, IndexedPage, Notebook, Section, Page } from '../types/index';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle 401 errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If error is 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh the token
        const token = localStorage.getItem('access_token');
        if (!token) {
          // No token to refresh, redirect to login
          window.location.href = '/login';
          return Promise.reject(error);
        }

        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const newToken = response.data.access_token;
        localStorage.setItem('access_token', newToken);

        // Retry the original request with new token
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear token and redirect to login
        localStorage.removeItem('access_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
 
// Configuration endpoints
export const configApi = {
  getPresets: () => api.get<Record<string, RAGConfig>>('/config/presets'),
  getPreset: (name: string) => api.get<RAGConfig>(`/config/presets/${name}`),
  getDefault: () => api.get<RAGConfig>('/config/default'),
  getModels: () => api.get<string[]>('/config/models'),
  validate: (config: RAGConfig) => api.post('/config/validate', config),
};
 
// Query endpoints
export const queryApi = {
  query: (request: QueryRequest) => api.post<QueryResponse>('/query/multimodal', request),
  queryTextOnly: (request: QueryRequest) => api.post<QueryResponse>('/query', request),
  compare: (question: string, configNames: string[]) =>
    api.post('/query/compare', { question, config_names: configNames }),
};
 
// Index endpoints
export const indexApi = {
  sync: (notebookIds?: string[], fullSync: boolean = false, multimodal: boolean = true) =>
    api.post('/index/sync', {
      notebook_ids: notebookIds,
      full_sync: fullSync,
      multimodal: multimodal
    }),
  getStats: () => api.get<IndexStats>('/index/stats'),
  getPages: () => api.get<{ pages: IndexedPage[] }>('/index/pages'),
  clear: () => api.delete('/index/clear'),
};
 
// Demo endpoints
export const demoApi = {
  addDocuments: (texts: string[], notebookName: string = 'Demo Notebook') =>
    api.post('/demo/add-documents', { texts, notebook_name: notebookName }),
};
 
// OneNote endpoints
export const oneNoteApi = {
  listNotebooks: () => api.get<{ notebooks: Notebook[] }>('/onenote/notebooks'),
  listSections: (notebookId: string) => api.get<{ sections: Section[] }>(`/onenote/sections/${notebookId}`),
  listPages: (sectionId: string) => api.get<{ pages: Page[] }>(`/onenote/pages/${sectionId}`),
};
 
// Settings endpoints
export const settingsApi = {
  getAll: () => api.get('/settings'),
  get: (key: string) => api.get(`/settings/${key}`),
  update: (key: string, value: string) => api.put(`/settings/${key}`, { value }),
};

// Health check
export const healthCheck = () => api.get('/health');
 