import axios from 'axios';
import type { RAGConfig, QueryRequest, QueryResponse, IndexStats } from '../types/index';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
  query: (request: QueryRequest) => api.post<QueryResponse>('/query', request),
  compare: (question: string, configNames: string[]) =>
    api.post('/query/compare', { question, config_names: configNames }),
};

// Index endpoints
export const indexApi = {
  sync: (notebookIds?: string[], fullSync: boolean = true) =>
    api.post('/index/sync', { notebook_ids: notebookIds, full_sync: fullSync }),
  getStats: () => api.get<IndexStats>('/index/stats'),
  clear: () => api.delete('/index/clear'),
};

// Demo endpoints
export const demoApi = {
  addDocuments: (texts: string[], notebookName: string = 'Demo Notebook') =>
    api.post('/demo/add-documents', { texts, notebook_name: notebookName }),
};

// Health check
export const healthCheck = () => api.get('/health');
