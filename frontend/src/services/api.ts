import axios from 'axios';
import type {
  UploadResponse,
  GrantData,
  GenerateDocumentsRequest,
  GenerateDocumentsResponse,
  GrantListItem,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const grantApi = {
  // Upload grant letter
  uploadGrantLetter: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UploadResponse>(
      '/api/grants/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  // Get grant data
  getGrantData: async (fileId: string): Promise<GrantData> => {
    const response = await api.get<GrantData>(`/api/grants/data/${fileId}`);
    return response.data;
  },

  // List all grants
  listGrants: async (): Promise<{ grants: GrantListItem[] }> => {
    const response = await api.get<{ grants: GrantListItem[] }>('/api/grants/list');
    return response.data;
  },

  // Generate documents
  generateDocuments: async (
    request: GenerateDocumentsRequest
  ): Promise<GenerateDocumentsResponse> => {
    const response = await api.post<GenerateDocumentsResponse>(
      `/api/grants/generate-documents/${request.file_id}`,
      request
    );
    return response.data;
  },

  // Download document
  downloadDocument: (fileId: string, docType: string): string => {
    return `${API_URL}/api/grants/download/${fileId}/${docType}`;
  },

  // Delete grant
  deleteGrant: async (fileId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete(`/api/grants/${fileId}`);
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;