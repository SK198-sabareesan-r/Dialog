import React, { useState, useCallback, useEffect } from 'react';
import {
  Upload as UploadIcon, File, Loader, CheckCircle, XCircle, FileText,
  Image, FileSpreadsheet, AlertTriangle, Info, X
} from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v1';
const PINK = '#E91E8C';
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

const PageHeader = ({ title, subtitle }) => (
  <div
    className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm"
    style={{ borderColor: '#E8EAF0' }}
  >
    <div>
      <h1 className="text-lg font-semibold" style={{ color: '#1A1A2E' }}>{title}</h1>
      {subtitle && <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>{subtitle}</p>}
    </div>
  </div>
);

const getFileIcon = (fileName) => {
  const ext = fileName.split('.').pop().toLowerCase();
  if (['pdf', 'doc', 'docx', 'txt'].includes(ext)) return FileText;
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return Image;
  if (['xlsx', 'xls', 'csv'].includes(ext)) return FileSpreadsheet;
  return File;
};

const Upload = () => {
  const [file, setFile] = useState(null);
  const [sourceType, setSourceType] = useState('web_ui');
  const [userId, setUserId] = useState('');
  const [teamId, setTeamId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [supportedFormats, setSupportedFormats] = useState(null);

  useEffect(() => {
    // Fetch supported formats from backend
    axios.get(`${API_BASE}/formats/supported`)
      .then(res => setSupportedFormats(res.data))
      .catch(err => console.error('Failed to fetch formats:', err));
  }, []);

  const validateFile = useCallback((selectedFile) => {
    if (!selectedFile) {
      setError('No file selected');
      return false;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError(`File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit`);
      return false;
    }

    const ext = selectedFile.name.split('.').pop().toLowerCase();
    const allowedExts = ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif', 'webp'];

    if (!allowedExts.includes(ext)) {
      setError(`Unsupported file type: .${ext}`);
      return false;
    }

    return true;
  }, []);

  const pickFile = useCallback((selectedFile) => {
    setUploadResult(null);
    setError(null);
    setUploadProgress(0);

    if (validateFile(selectedFile)) {
      setFile(selectedFile);
    }
  }, [validateFile]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) pickFile(selectedFile);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const selectedFile = e.dataTransfer.files[0];
    if (selectedFile) pickFile(selectedFile);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const removeFile = () => {
    setFile(null);
    setUploadProgress(0);
    setError(null);
    setUploadResult(null);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setUploadResult(null);
    setUploadProgress(0);

    try {
      const form = new FormData();
      form.append('file', file);

      // user_id is required by backend
      form.append('user_id', userId.trim() || 'guest');

      // Add optional fields
      if (teamId.trim()) {
        form.append('team_id', teamId.trim());
      }

      const res = await axios.post(`${API_BASE}/upload/direct`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000, // 60 second timeout
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        },
      });

      setUploadResult(res.data);
      setFile(null);
      setUploadProgress(0);
    } catch (err) {
      console.error('Upload error:', err);
      if (err.code === 'ECONNABORTED') {
        setError('Upload timeout. Please try with a smaller file.');
      } else if (err.response?.status === 413) {
        setError('File too large. Maximum size is 100MB.');
      } else {
        setError(err.response?.data?.detail || err.message || 'Upload failed. Please try again.');
      }
    } finally {
      setUploading(false);
    }
  };

  const FileIcon = file ? getFileIcon(file.name) : UploadIcon;

  return (
    <div className="min-h-screen pb-8">
      <PageHeader title="Upload Documents" subtitle="Upload files to the BDA ingestion pipeline" />

      <div className="p-6">
        <div className="max-w-3xl mx-auto">
          {/* Info banner */}
          <div className="dialog-card p-4 mb-6" style={{ background: '#EFF6FF', borderColor: '#DBEAFE' }}>
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: '#3B82F6' }} />
              <div className="flex-1">
                <p className="text-xs leading-relaxed" style={{ color: '#1E40AF' }}>
                  Files are processed through Bedrock Data Automation, automatically parsed, chunked,
                  embedded, and indexed into the knowledge base. Maximum file size: 100MB.
                </p>
              </div>
            </div>
          </div>

          <div className="dialog-card p-8">
            {/* Drop zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              className="rounded-xl p-10 text-center transition-all"
              style={{
                border: `2px dashed ${
                  error ? '#DC2626' : file ? '#059669' : isDragging ? PINK : '#E8EAF0'
                }`,
                background: error
                  ? '#FEF2F2'
                  : file
                  ? '#ECFDF5'
                  : isDragging
                  ? '#FDF0F7'
                  : '#FAFBFC',
                cursor: 'pointer',
              }}
            >
              {file ? (
                <div className="flex flex-col items-center">
                  <div
                    className="p-4 rounded-full mb-3"
                    style={{ background: '#ECFDF5' }}
                  >
                    <FileIcon className="w-10 h-10" style={{ color: '#059669' }} />
                  </div>
                  <p className="font-semibold text-base mb-1" style={{ color: '#1A1A2E' }}>
                    {file.name}
                  </p>
                  <p className="text-xs mb-4" style={{ color: '#9CA3AF' }}>
                    {(file.size / 1024 / 1024).toFixed(2)} MB • {file.type || 'Unknown type'}
                  </p>
                  {uploadProgress > 0 && uploadProgress < 100 && (
                    <div className="w-full max-w-xs mb-4">
                      <div className="h-2 rounded-full" style={{ background: '#E5E7EB' }}>
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            background: PINK,
                            width: `${uploadProgress}%`,
                          }}
                        />
                      </div>
                      <p className="text-xs mt-2" style={{ color: '#9CA3AF' }}>
                        Uploading... {uploadProgress}%
                      </p>
                    </div>
                  )}
                  <button
                    onClick={removeFile}
                    disabled={uploading}
                    className="flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
                    style={{
                      background: '#FEF2F2',
                      color: '#DC2626',
                      opacity: uploading ? 0.5 : 1,
                      cursor: uploading ? 'not-allowed' : 'pointer',
                    }}
                  >
                    <X className="w-3 h-3" />
                    Remove file
                  </button>
                </div>
              ) : (
                <div>
                  <div
                    className="inline-flex p-5 rounded-full mb-4"
                    style={{ background: isDragging ? PINK : `${PINK}12` }}
                  >
                    <UploadIcon
                      className="w-10 h-10"
                      style={{ color: isDragging ? '#FFFFFF' : PINK }}
                    />
                  </div>
                  <p className="font-semibold text-base mb-2" style={{ color: '#1A1A2E' }}>
                    {isDragging ? 'Drop your file here' : 'Drag and drop your file here'}
                  </p>
                  <p className="text-sm mb-6" style={{ color: '#9CA3AF' }}>
                    or browse from your computer
                  </p>
                  <label
                    className="inline-block px-6 py-3 rounded-lg font-semibold text-white text-sm cursor-pointer transition-all"
                    style={{ background: PINK }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#C91578')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = PINK)}
                  >
                    Browse Files
                    <input
                      type="file"
                      onChange={handleFileChange}
                      className="hidden"
                      accept=".pdf,.doc,.docx,.txt,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.gif,.webp"
                      aria-label="Select file to upload"
                    />
                  </label>
                  <p className="text-xs mt-5" style={{ color: '#C4C9D4' }}>
                    Supported: PDF, DOC, DOCX, TXT, XLSX, XLS, CSV, Images (PNG, JPG, GIF, WebP)
                  </p>
                  <p className="text-xs mt-1" style={{ color: '#C4C9D4' }}>
                    Maximum file size: 100MB
                  </p>
                </div>
              )}
            </div>

            {/* Configuration */}
            <div className="mt-6 space-y-4">
              <div>
                <label
                  className="block text-xs font-semibold uppercase tracking-wide mb-2"
                  style={{ color: '#6B7280' }}
                >
                  Source Type
                </label>
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  className="dialog-input"
                  disabled={uploading}
                  style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                    backgroundPosition: 'right 10px center',
                    backgroundRepeat: 'no-repeat',
                    backgroundSize: '18px',
                    paddingRight: '2.5rem',
                    appearance: 'none',
                  }}
                >
                  <option value="web_ui">Web UI Upload</option>
                  <option value="shared_drive">Shared Drive</option>
                  <option value="file_repo">File Repository</option>
                  <option value="s3_direct">S3 Direct</option>
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    className="block text-xs font-semibold uppercase tracking-wide mb-2"
                    style={{ color: '#6B7280' }}
                  >
                    User ID{' '}
                    <span style={{ color: '#C4C9D4', fontWeight: 400, textTransform: 'none' }}>
                      (optional)
                    </span>
                  </label>
                  <input
                    type="text"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="e.g., user123"
                    className="dialog-input"
                    disabled={uploading}
                  />
                </div>
                <div>
                  <label
                    className="block text-xs font-semibold uppercase tracking-wide mb-2"
                    style={{ color: '#6B7280' }}
                  >
                    Team ID{' '}
                    <span style={{ color: '#C4C9D4', fontWeight: 400, textTransform: 'none' }}>
                      (optional)
                    </span>
                  </label>
                  <input
                    type="text"
                    value={teamId}
                    onChange={(e) => setTeamId(e.target.value)}
                    placeholder="e.g., team456"
                    className="dialog-input"
                    disabled={uploading}
                  />
                </div>
              </div>
            </div>

            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="btn-dialog w-full mt-6 py-3.5 text-base"
              aria-label="Upload file and start ingestion"
            >
              {uploading ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Uploading... {uploadProgress}%
                </>
              ) : (
                <>
                  <UploadIcon className="w-5 h-5" />
                  Upload &amp; Start Ingestion
                </>
              )}
            </button>
          </div>

          {/* Success Alert */}
          {uploadResult && (
            <div
              className="dialog-card p-6 mt-5 animate-in"
              style={{ borderLeft: '4px solid #059669' }}
            >
              <div className="flex items-start gap-3">
                <CheckCircle className="w-6 h-6 flex-shrink-0 mt-0.5" style={{ color: '#059669' }} />
                <div className="flex-1">
                  <h3 className="font-semibold text-base mb-2" style={{ color: '#1A1A2E' }}>
                    Upload Successful
                  </h3>
                  <p className="text-sm mb-4" style={{ color: '#6B7280' }}>
                    {uploadResult.message}
                  </p>
                  <div className="space-y-3">
                    <div
                      className="rounded-lg p-4 text-xs space-y-2"
                      style={{ background: '#F9FAFB' }}
                    >
                      <div>
                        <p className="font-semibold mb-1" style={{ color: '#6B7280' }}>
                          S3 Location
                        </p>
                        <p className="font-mono break-all" style={{ color: '#059669' }}>
                          {uploadResult.s3_key}
                        </p>
                      </div>
                      {uploadResult.ingestion_job_id && (
                        <div>
                          <p className="font-semibold mb-1" style={{ color: '#6B7280' }}>
                            Ingestion Job ID
                          </p>
                          <p className="font-mono break-all" style={{ color: PINK }}>
                            {uploadResult.ingestion_job_id}
                          </p>
                        </div>
                      )}
                      {uploadResult.execution?.execution_arn && (
                        <div>
                          <p className="font-semibold mb-1" style={{ color: '#6B7280' }}>
                            Execution ARN
                          </p>
                          <p className="font-mono break-all text-xs" style={{ color: '#6B7280' }}>
                            {uploadResult.execution.execution_arn}
                          </p>
                        </div>
                      )}
                    </div>
                    <p className="text-xs" style={{ color: '#9CA3AF' }}>
                      ℹ️ Your file is being processed. Check the Dashboard or Monitoring page for status updates.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {error && (
            <div
              className="dialog-card p-6 mt-5 animate-in"
              style={{ borderLeft: '4px solid #DC2626' }}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 flex-shrink-0 mt-0.5" style={{ color: '#DC2626' }} />
                <div className="flex-1">
                  <h3 className="font-semibold text-base mb-1" style={{ color: '#1A1A2E' }}>
                    Upload Failed
                  </h3>
                  <p className="text-sm" style={{ color: '#6B7280' }}>
                    {error}
                  </p>
                  <button
                    onClick={() => setError(null)}
                    className="mt-3 text-xs font-medium underline"
                    style={{ color: '#DC2626' }}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Upload;
