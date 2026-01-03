import React, { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { useGenerateDocuments } from '../../hooks/useGrants';
import { Download, FileText, DollarSign, Calendar, ClipboardList, CheckCircle } from 'lucide-react';
import { grantApi } from '../../services/api';

interface DocumentGeneratorProps {
  fileId: string;
}

export const DocumentGenerator: React.FC<DocumentGeneratorProps> = ({ fileId }) => {
  const [options, setOptions] = useState({
    generate_workplan: true,
    generate_budget: true,
    generate_report_template: true,
    generate_calendar: true,
  });

  const [downloadingDoc, setDownloadingDoc] = useState<string | null>(null);

  const generateMutation = useGenerateDocuments();

  const handleGenerate = async () => {
    try {
      await generateMutation.mutateAsync({
        file_id: fileId,
        ...options,
      });
    } catch (error) {
      console.error('Generation failed:', error);
    }
  };

  const handleDownload = async (type: string, filename: string) => {
    try {
      setDownloadingDoc(type);
      const url = grantApi.downloadDocument(fileId, type);
      
      // Fetch the file as a blob
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/octet-stream',
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      // Get the blob
      const blob = await response.blob();
      
      // Create blob URL
      const blobUrl = window.URL.createObjectURL(blob);
      
      // Create temporary link and trigger download
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      
      setDownloadingDoc(null);
    } catch (error) {
      console.error('Download failed:', error);
      alert(`Failed to download ${filename}. Please try again.`);
      setDownloadingDoc(null);
    }
  };

  const documentTypes = [
    {
      key: 'generate_workplan' as const,
      label: 'Work Plan (PDF)',
      icon: ClipboardList,
      description: 'Timeline and deliverables',
    },
    {
      key: 'generate_budget' as const,
      label: 'Budget Template (Excel)',
      icon: DollarSign,
      description: 'Budget breakdown and disbursement schedule',
    },
    {
      key: 'generate_report_template' as const,
      label: 'Report Template (Word)',
      icon: FileText,
      description: 'Progress report template',
    },
    {
      key: 'generate_calendar' as const,
      label: 'Calendar Events (ICS)',
      icon: Calendar,
      description: 'Important dates and deadlines',
    },
  ];

  return (
    <Card title="Generate Documents">
      <div className="space-y-4 mb-6">
        {documentTypes.map((doc) => {
          const Icon = doc.icon;
          return (
            <label
              key={doc.key}
              className="flex items-start p-3 border border-gray-200 rounded-md cursor-pointer hover:bg-gray-50 transition-colors"
            >
              <input
                type="checkbox"
                checked={options[doc.key]}
                onChange={(e) =>
                  setOptions({ ...options, [doc.key]: e.target.checked })
                }
                className="mt-1 mr-3 h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <Icon className="h-5 w-5 text-primary-600 mt-0.5 mr-3" />
              <div className="flex-1">
                <p className="font-medium text-gray-900">{doc.label}</p>
                <p className="text-sm text-gray-600">{doc.description}</p>
              </div>
            </label>
          );
        })}
      </div>

      <Button
        onClick={handleGenerate}
        isLoading={generateMutation.isPending}
        className="w-full mb-4"
        disabled={!Object.values(options).some((v) => v)}
      >
        {generateMutation.isPending ? 'Generating Documents...' : 'Generate Selected Documents'}
      </Button>

      {generateMutation.isError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md mb-4">
          <p className="text-sm text-red-800">
            Failed to generate documents. Please try again.
          </p>
        </div>
      )}

      {generateMutation.isSuccess && generateMutation.data && (
        <div className="space-y-2">
          <div className="flex items-center mb-3">
            <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
            <p className="text-sm font-medium text-green-700">
              Documents generated successfully!
            </p>
          </div>
          
          {Object.entries(generateMutation.data.files)
            .filter(([_, doc]) => doc && typeof doc === 'object' && 'filename' in doc)
            .map(([type, doc]) => {
              const typedDoc = doc as { filename: string; download_url: string };
              const isDownloading = downloadingDoc === type;
              
              return (
                <button
                  key={type}
                  onClick={() => handleDownload(type, typedDoc.filename)}
                  disabled={isDownloading}
                  className="w-full flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-md hover:bg-green-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="text-sm font-medium text-green-900">
                    {typedDoc.filename}
                  </span>
                  {isDownloading ? (
                    <svg className="animate-spin h-4 w-4 text-green-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <Download className="h-4 w-4 text-green-700" />
                  )}
                </button>
              );
            })}
        </div>
      )}
    </Card>
  );
};
