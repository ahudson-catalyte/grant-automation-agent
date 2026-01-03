import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { useUploadGrant } from '../../hooks/useGrants';

interface FileUploadProps {
  onUploadSuccess: (fileId: string) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const uploadMutation = useUploadGrant();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
    },
    maxFiles: 1,
  });

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      const result = await uploadMutation.mutateAsync(selectedFile);
      onUploadSuccess(result.file_id);
      setSelectedFile(null);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    uploadMutation.reset();
  };

  return (
    <div className="w-full">
      {!selectedFile ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-primary-400'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-lg font-medium text-gray-700 mb-2">
            {isDragActive ? 'Drop the file here' : 'Drag & drop grant letter here'}
          </p>
          <p className="text-sm text-gray-500">or click to select file</p>
          <p className="text-xs text-gray-400 mt-2">Supports PDF and DOCX files</p>
        </div>
      ) : (
        <div className="border-2 border-gray-200 rounded-lg p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center">
              <File className="h-8 w-8 text-primary-600 mr-3" />
              <div>
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={handleClear}
              className="text-gray-400 hover:text-gray-600"
              disabled={uploadMutation.isPending}
            >
              <XCircle className="h-6 w-6" />
            </button>
          </div>

          {uploadMutation.isError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">
                Upload failed. Please try again.
              </p>
            </div>
          )}

          {uploadMutation.isSuccess && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md flex items-center">
              <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
              <p className="text-sm text-green-800">File uploaded successfully!</p>
            </div>
          )}

          <Button
            onClick={handleUpload}
            isLoading={uploadMutation.isPending}
            className="w-full"
          >
            {uploadMutation.isPending ? 'Uploading & Processing...' : 'Upload & Process'}
          </Button>
        </div>
      )}
    </div>
  );
};