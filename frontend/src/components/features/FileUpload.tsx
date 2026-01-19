import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, CheckCircle, XCircle, Loader } from 'lucide-react';
import { Button } from '../ui/Button';
import { useUploadGrantBatch } from '../../hooks/useGrants';

interface FileUploadProps {
  onUploadSuccess: (fileIds: string[]) => void;
}

interface SelectedFileInfo {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  message?: string;
  fileId?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [selectedFiles, setSelectedFiles] = useState<SelectedFileInfo[]>([]);
  const uploadMutation = useUploadGrantBatch();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const newFiles: SelectedFileInfo[] = acceptedFiles.map((file) => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
        status: 'pending'
      }));
      setSelectedFiles((prev) => [...prev, ...newFiles]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
    },
    multiple: true,
    maxFiles: 10,
  });

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    const filesToUpload = selectedFiles.filter(f => f.status === 'pending');
    if (filesToUpload.length === 0) return;

    try {
      const results = await uploadMutation.mutateAsync(filesToUpload.map(f => f.file));
      
      // Update file statuses based on results
      setSelectedFiles((prev) =>
        prev.map((fileInfo) => {
          const result = results.find((r) => r.filename === fileInfo.file.name);
          if (result) {
            return {
              ...fileInfo,
              status: result.success ? 'success' : 'error',
              message: result.message,
              fileId: result.file_id,
            };
          }
          return fileInfo;
        })
      );

      // Get successful file IDs
      const successfulFileIds = results
        .filter((r) => r.success)
        .map((r) => r.file_id);

      if (successfulFileIds.length > 0) {
        onUploadSuccess(successfulFileIds);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      
      // Mark all pending files as error
      setSelectedFiles((prev) =>
        prev.map((fileInfo) =>
          fileInfo.status === 'pending'
            ? { ...fileInfo, status: 'error', message: 'Upload failed' }
            : fileInfo
        )
      );
    }
  };

  const handleClear = () => {
    setSelectedFiles([]);
    uploadMutation.reset();
  };

  const removeFile = (id: string) => {
    setSelectedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const pendingCount = selectedFiles.filter((f) => f.status === 'pending').length;
  const successCount = selectedFiles.filter((f) => f.status === 'success').length;
  const errorCount = selectedFiles.filter((f) => f.status === 'error').length;

  return (
    <div className="w-full">
      {selectedFiles.length === 0 ? (
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
            {isDragActive ? 'Drop the files here' : 'Drag & drop grant letters here'}
          </p>
          <p className="text-sm text-gray-500">or click to select files</p>
          <p className="text-xs text-gray-400 mt-2">
            Supports PDF and DOCX files (up to 10 files at once)
          </p>
        </div>
      ) : (
        <div className="border-2 border-gray-200 rounded-lg p-6">
          {/* File List Header */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-medium text-gray-900">
                Selected Files ({selectedFiles.length})
              </h3>
              <p className="text-sm text-gray-500">
                {successCount > 0 && `${successCount} uploaded, `}
                {pendingCount > 0 && `${pendingCount} pending`}
                {errorCount > 0 && `, ${errorCount} failed`}
              </p>
            </div>
            <button
              onClick={handleClear}
              className="text-gray-400 hover:text-gray-600"
              disabled={uploadMutation.isPending}
            >
              <XCircle className="h-6 w-6" />
            </button>
          </div>

          {/* File List */}
          <div className="space-y-2 mb-4 max-h-96 overflow-y-auto">
            {selectedFiles.map((fileInfo) => (
              <div
                key={fileInfo.id}
                className={`flex items-center justify-between p-3 rounded-md ${
                  fileInfo.status === 'success'
                    ? 'bg-green-50 border border-green-200'
                    : fileInfo.status === 'error'
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-gray-50 border border-gray-200'
                }`}
              >
                <div className="flex items-center flex-1 min-w-0">
                  <File className="h-5 w-5 text-primary-600 mr-3 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gray-900 truncate">
                      {fileInfo.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(fileInfo.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                    {fileInfo.message && (
                      <p className={`text-xs mt-1 ${
                        fileInfo.status === 'error' ? 'text-red-600' : 'text-gray-600'
                      }`}>
                        {fileInfo.message}
                      </p>
                    )}
                  </div>
                </div>

                {/* Status Icon */}
                <div className="ml-3 flex-shrink-0">
                  {fileInfo.status === 'pending' && (
                    <button
                      onClick={() => removeFile(fileInfo.id)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <XCircle className="h-5 w-5" />
                    </button>
                  )}
                  {fileInfo.status === 'uploading' && (
                    <Loader className="h-5 w-5 text-primary-600 animate-spin" />
                  )}
                  {fileInfo.status === 'success' && (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  )}
                  {fileInfo.status === 'error' && (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Add More Button */}
          {selectedFiles.length < 10 && (
            <div
              {...getRootProps()}
              className="border-2 border-dashed border-gray-300 rounded-md p-4 text-center cursor-pointer hover:border-primary-400 mb-4"
            >
              <input {...getInputProps()} />
              <p className="text-sm text-gray-600">
                + Add more files (up to {10 - selectedFiles.length} more)
              </p>
            </div>
          )}

          {/* Upload Button */}
          {pendingCount > 0 && (
            <Button
              onClick={handleUpload}
              isLoading={uploadMutation.isPending}
              className="w-full"
            >
              {uploadMutation.isPending
                ? `Uploading ${pendingCount} file${pendingCount > 1 ? 's' : ''}...`
                : `Upload ${pendingCount} file${pendingCount > 1 ? 's' : ''}`}
            </Button>
          )}

          {/* View Results Button */}
          {successCount > 0 && pendingCount === 0 && (
            <Button
              onClick={() => {
                const successfulIds = selectedFiles
                  .filter((f) => f.status === 'success' && f.fileId)
                  .map((f) => f.fileId!);
                onUploadSuccess(successfulIds);
              }}
              className="w-full"
            >
              View {successCount} Processed Grant{successCount > 1 ? 's' : ''}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};