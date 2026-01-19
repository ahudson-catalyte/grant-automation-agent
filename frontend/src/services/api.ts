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
  // Upload single grant letter (wrapper for batch with single file)
  uploadGrantLetter: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('files', file);

    const response = await api.post<UploadResponse[]>(
      '/api/grants/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data[0];
  },

  // Upload multiple grant letters at once
  uploadGrantLettersBatch: async (files: File[]): Promise<UploadResponse[]> => {
    const formData = new FormData();
    
    // Append each file with the same field name 'files'
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await api.post<UploadResponse[]>(
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

  // Generate documents for single grant
  generateDocuments: async (
    request: GenerateDocumentsRequest
  ): Promise<GenerateDocumentsResponse> => {
    const response = await api.post<GenerateDocumentsResponse>(
      `/api/grants/generate-documents/${request.file_id}`,
      request
    );
    return response.data;
  },

  // Generate documents for multiple grants
  generateDocumentsBatch: async (
    fileIds: string[],
    options?: Record<string, boolean>
  ): Promise<any> => {
    const response = await api.post(
      '/api/grants/generate-documents-batch',
      {
        file_ids: fileIds,
        ...options
      }
    );
    return response.data;
  },

  // Download document
  downloadDocument: (fileId: string, docType: string): string => {
    return `${API_URL}/api/grants/download/${fileId}/${docType}`;
  },

  // Delete single grant
  deleteGrant: async (fileId: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete(`/api/grants/${fileId}`);
    return response.data;
  },

  // Delete multiple grants
  deleteGrantsBatch: async (fileIds: string[]): Promise<any> => {
    const response = await api.delete('/api/grants/batch', {
      data: { file_ids: fileIds },
    });
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;