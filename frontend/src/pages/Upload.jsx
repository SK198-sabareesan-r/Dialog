import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Upload as UploadIcon, File, Loader, CheckCircle, FileText,
  Image, FileSpreadsheet, AlertTriangle, Info, X, Film,
  Database, Clock
} from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://localhost:8001/api';
const PINK = '#E91E8C';
const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

// ─── helpers ────────────────────────────────────────────────────────────────

const PageHeader = ({ title, subtitle }) => (
  <div
    className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm"
    style={{ borderColor: '#E8EAF0' }}
  >
    <div>
      <h1 className="text-lg font-semibold" style={{ color: '#343a40' }}>{title}</h1>
      {subtitle && <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>{subtitle}</p>}
    </div>
  </div>
);

const VIDEO_EXTENSIONS = ['mp4', 'avi', 'mov', 'mkv', 'webm'];

const getFileIcon = (fileName) => {
  const ext = fileName.split('.').pop().toLowerCase();
  if (['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx'].includes(ext)) return FileText;
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return Image;
  if (['xlsx', 'xls', 'csv'].includes(ext)) return FileSpreadsheet;
  if (VIDEO_EXTENSIONS.includes(ext)) return Film;
  return File;
};

// Status → display config
const SYNC_STATUS_CONFIG = {
  STARTING:    { label: 'Starting ingestion…',        color: '#D97706', bg: '#FFFBEB', pulse: true  },
  IN_PROGRESS: { label: 'Indexing into knowledge base…', color: '#3B82F6', bg: '#EFF6FF', pulse: true  },
  COMPLETE:    { label: 'Indexed — document is queryable', color: '#059669', bg: '#ECFDF5', pulse: false },
  FAILED:      { label: 'Ingestion failed',            color: '#DC2626', bg: '#FEF2F2', pulse: false },
  STOPPED:     { label: 'Ingestion stopped',           color: '#6B7280', bg: '#F9FAFB', pulse: false },
  PENDING:     { label: 'Waiting for ingestion job…',  color: '#D97706', bg: '#FFFBEB', pulse: true  },
};

// ─── SyncStatusCard ──────────────────────────────────────────────────────────
// Shown after a successful upload; polls /api/upload/sync-status/{jobId}
// until the job reaches a terminal state.

const SyncStatusCard = ({ s3Key, filename }) => {
  const [jobId,    setJobId]    = useState(null);
  const [status,   setStatus]   = useState('PENDING');
  const [stats,    setStats]    = useState(null);
  const [elapsed,  setElapsed]  = useState(0);
  const [error,    setError]    = useState(null);
  const intervalRef = useRef(null);
  const timerRef    = useRef(null);
  const startRef    = useRef(Date.now());

  // Tick the elapsed timer every second
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  // Poll the backend for job ID first (it appears in the background task log
  // very quickly), then poll status until terminal
  useEffect(() => {
    let stopped = false;

    const pollStatus = async (id) => {
      try {
        const res = await axios.get(`${API_BASE}/upload/sync-status/${id}`, { timeout: 10000 });
        if (stopped) return;
        const data = res.data;
        setStatus(data.status);
        setStats(data);

        if (['COMPLETE', 'FAILED', 'STOPPED'].includes(data.status)) {
          clearInterval(intervalRef.current);
          clearInterval(timerRef.current);
        }
      } catch (err) {
        if (!stopped) setError('Could not fetch sync status — check backend logs.');
        clearInterval(intervalRef.current);
      }
    };

    // The backend logs the job_id under event=kb_sync_triggered right after
    // background_sync starts. We can't get it from the upload response because
    // it's assigned inside the background task. So we expose a small helper:
    // GET /api/kb/sync/status/latest?s3_key=... — but we don't have that yet.
    //
    // For now we poll /api/kb/tracker/stats to detect STARTING state, then
    // let the user see progress. When the job_id endpoint is added this can
    // be wired directly.
    //
    // PRACTICAL APPROACH: the upload response doesn't include a job_id because
    // the background task hasn't started yet. Instead, expose a lightweight
    // endpoint that returns the latest ingestion job for the KB datasource.
    // Until then, show a "syncing" state and let the user know to check logs.
    //
    // We poll /api/kb/sync/status/latest (added to app.py) for the latest job.
    const fetchLatestJobId = async () => {
      try {
        const res = await axios.get(`${API_BASE}/kb/sync/latest`, { timeout: 10000 });
        if (stopped) return;
        if (res.data?.ingestion_job_id) {
          setJobId(res.data.ingestion_job_id);
          setStatus(res.data.status || 'STARTING');
          // Start polling every 8 seconds
          intervalRef.current = setInterval(() => pollStatus(res.data.ingestion_job_id), 8001);
          // Poll immediately too
          pollStatus(res.data.ingestion_job_id);
        }
      } catch {
        // If the endpoint doesn't respond, fall back to showing generic syncing state
      }
    };

    // Wait 2s for the background task to start and register the job
    const kickoff = setTimeout(fetchLatestJobId, 2000);

    return () => {
      stopped = true;
      clearTimeout(kickoff);
      clearInterval(intervalRef.current);
    };
  }, [s3Key]);

  const cfg = SYNC_STATUS_CONFIG[status] || SYNC_STATUS_CONFIG.PENDING;

  const formatElapsed = (s) => {
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  return (
    <div
      className="dialog-card p-5 mt-5"
      style={{ borderLeft: `4px solid ${cfg.color}`, background: cfg.bg }}
    >
      {/* Header row */}
      <div className="flex items-center gap-2 mb-3">
        <Database className="w-4 h-4 flex-shrink-0" style={{ color: cfg.color }} />
        <span className="text-sm font-semibold" style={{ color: cfg.color }}>
          KB Ingestion
        </span>
        {cfg.pulse && (
          <span
            className="ml-1 w-2 h-2 rounded-full animate-pulse"
            style={{ background: cfg.color }}
          />
        )}
        <div className="ml-auto flex items-center gap-1.5 text-xs" style={{ color: '#9CA3AF' }}>
          <Clock className="w-3 h-3" />
          {formatElapsed(elapsed)}
        </div>
      </div>

      {/* Status label */}
      <p className="text-sm font-medium mb-1" style={{ color: '#343a40' }}>
        {cfg.label}
      </p>

      {/* File info */}
      <p className="text-xs mb-3 font-mono truncate" style={{ color: '#6B7280' }}>
        {s3Key}
      </p>

      {/* Progress bar — indeterminate while running */}
      {cfg.pulse && (
        <div className="h-1.5 rounded-full overflow-hidden mb-3" style={{ background: '#E5E7EB' }}>
          <div
            className="h-full rounded-full"
            style={{
              background: cfg.color,
              width: '40%',
              animation: 'indeterminate 1.5s ease-in-out infinite',
            }}
          />
        </div>
      )}

      {/* Stats (shown once COMPLETE) */}
      {stats && status === 'COMPLETE' && (
        <div className="grid grid-cols-3 gap-3 mt-2">
          {[
            { label: 'Scanned',  value: stats.documents_scanned },
            { label: 'Indexed',  value: stats.new_documents_indexed },
            { label: 'Failed',   value: stats.documents_failed },
          ].map(({ label, value }) => (
            <div
              key={label}
              className="rounded-lg p-2.5 text-center"
              style={{ background: 'rgba(255,255,255,0.7)' }}
            >
              <p className="text-lg font-bold" style={{ color: '#343a40' }}>{value ?? '—'}</p>
              <p className="text-xs" style={{ color: '#9CA3AF' }}>{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Failure reasons */}
      {stats?.failure_reasons?.length > 0 && (
        <div className="mt-2 p-3 rounded-lg text-xs" style={{ background: '#FEF2F2', color: '#DC2626' }}>
          {stats.failure_reasons.join('; ')}
        </div>
      )}

      {/* Job ID */}
      {jobId && (
        <p className="text-xs mt-3 font-mono" style={{ color: '#9CA3AF' }}>
          Job: {jobId}
        </p>
      )}

      {/* No job ID yet — generic note */}
      {!jobId && !error && status === 'PENDING' && (
        <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>
          Ingestion job is starting in the background — check backend logs for real-time progress.
        </p>
      )}

      {error && (
        <p className="text-xs mt-2" style={{ color: '#DC2626' }}>{error}</p>
      )}
    </div>
  );
};

// ─── Main Upload page ────────────────────────────────────────────────────────

const Upload = () => {
  const [file,           setFile]           = useState(null);
  const [sourceType,     setSourceType]     = useState('web_ui');
  const [uploading,      setUploading]      = useState(false);
  const [uploadResult,   setUploadResult]   = useState(null); // { s3_key, filename, ... }
  const [error,          setError]          = useState(null);
  const [isDragging,     setIsDragging]     = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const validateFile = useCallback((selectedFile) => {
    if (!selectedFile) { setError('No file selected'); return false; }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setError(`File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit`);
      return false;
    }

    const ext = selectedFile.name.split('.').pop().toLowerCase();
    const allowed = [
      'pdf','doc','docx','ppt','pptx','txt','html','htm',
      'xlsx','xls','csv',
      'png','jpg','jpeg','gif','webp',
      'mp4','avi','mov','mkv','webm',
    ];
    if (!allowed.includes(ext)) {
      setError(`Unsupported file type: .${ext}`);
      return false;
    }
    return true;
  }, []);

  const pickFile = useCallback((selectedFile) => {
    setUploadResult(null);
    setError(null);
    setUploadProgress(0);
    if (validateFile(selectedFile)) setFile(selectedFile);
  }, [validateFile]);

  const handleFileChange = (e) => { if (e.target.files[0]) pickFile(e.target.files[0]); };
  const handleDrop       = (e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files[0]) pickFile(e.dataTransfer.files[0]); };
  const handleDragOver   = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave  = (e) => { e.preventDefault(); setIsDragging(false); };
  const removeFile       = ()  => { setFile(null); setUploadProgress(0); setError(null); setUploadResult(null); };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setUploadResult(null);
    setUploadProgress(0);

    try {
      const form = new FormData();
      form.append('file', file);
      form.append('user_id', 'guest');

      // Timeout only needs to cover the S3 PUT — the sync runs in the background.
      // 5 minutes is generous even for a 500MB file upload.
      const res = await axios.post(`${API_BASE}/upload/direct`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 minutes for S3 upload transfer
        onUploadProgress: (e) => {
          setUploadProgress(Math.round((e.loaded * 100) / e.total));
        },
      });

      setUploadResult({ ...res.data, filename: file.name });
      setFile(null);
      setUploadProgress(0);
    } catch (err) {
      console.error('Upload error:', err);
      if (err.code === 'ECONNABORTED')      setError('Upload timeout. Please try with a smaller file.');
      else if (err.response?.status === 413) setError('File too large. Maximum size is 500MB.');
      else setError(err.response?.data?.detail || err.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const FileIcon = file ? getFileIcon(file.name) : UploadIcon;
  const isVideo  = file ? VIDEO_EXTENSIONS.includes(file.name.split('.').pop().toLowerCase()) : false;

  return (
    <div className="min-h-screen pb-8">
      {/* Indeterminate progress bar CSS */}
      <style>{`
        @keyframes indeterminate {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(350%); }
        }
      `}</style>

      <PageHeader title="Upload Documents" subtitle="Upload files to the ingestion pipeline" />

      <div className="p-6">
        <div className="max-w-3xl mx-auto">

          {/* Info banner */}
          <div className="dialog-card p-4 mb-6" style={{ background: '#EFF6FF', borderColor: '#DBEAFE' }}>
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: '#3B82F6' }} />
              <p className="text-xs leading-relaxed" style={{ color: '#1E40AF' }}>
                Files are stored in S3 then automatically parsed, chunked, embedded, and indexed.
                Videos are transcribed automatically. Ingestion runs in the background — the upload
                response returns immediately. Maximum file size: 500MB.
              </p>
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
                  error ? '#DC2626' : isVideo && file ? '#3B82F6' : file ? '#059669' : isDragging ? PINK : '#E8EAF0'
                }`,
                background: error ? '#FEF2F2' : isVideo && file ? '#EFF6FF' : file ? '#ECFDF5' : isDragging ? '#FDF0F7' : '#FAFBFC',
                cursor: 'pointer',
              }}
            >
              {file ? (
                <div className="flex flex-col items-center">
                  <div className="p-4 rounded-full mb-3" style={{ background: isVideo ? '#EFF6FF' : '#ECFDF5' }}>
                    <FileIcon className="w-10 h-10" style={{ color: isVideo ? '#3B82F6' : '#059669' }} />
                  </div>
                  <p className="font-semibold text-base mb-1" style={{ color: '#343a40' }}>{file.name}</p>
                  <p className="text-xs mb-1" style={{ color: '#9CA3AF' }}>
                    {(file.size / 1024 / 1024).toFixed(2)} MB • {file.type || 'Unknown type'}
                  </p>
                  {isVideo && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold mb-3"
                      style={{ background: '#EFF6FF', color: '#3B82F6' }}>
                      <Film className="w-3 h-3" />
                      Video — audio will be transcribed automatically
                    </span>
                  )}
                  {uploadProgress > 0 && uploadProgress < 100 && (
                    <div className="w-full max-w-xs mb-4">
                      <div className="h-2 rounded-full" style={{ background: '#E5E7EB' }}>
                        <div className="h-full rounded-full transition-all duration-300"
                          style={{ background: PINK, width: `${uploadProgress}%` }} />
                      </div>
                      <p className="text-xs mt-2" style={{ color: '#9CA3AF' }}>Uploading… {uploadProgress}%</p>
                    </div>
                  )}
                  <button onClick={removeFile} disabled={uploading}
                    className="flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-lg"
                    style={{ background: '#FEF2F2', color: '#DC2626', opacity: uploading ? 0.5 : 1, cursor: uploading ? 'not-allowed' : 'pointer' }}>
                    <X className="w-3 h-3" /> Remove file
                  </button>
                </div>
              ) : (
                <div>
                  <div className="inline-flex p-5 rounded-full mb-4"
                    style={{ background: isDragging ? PINK : `${PINK}12` }}>
                    <UploadIcon className="w-10 h-10" style={{ color: isDragging ? '#FFFFFF' : PINK }} />
                  </div>
                  <p className="font-semibold text-base mb-2" style={{ color: '#343a40' }}>
                    {isDragging ? 'Drop your file here' : 'Drag and drop your file here'}
                  </p>
                  <p className="text-sm mb-6" style={{ color: '#9CA3AF' }}>or browse from your computer</p>
                  <label className="inline-block px-6 py-3 rounded-lg font-semibold text-white text-sm cursor-pointer"
                    style={{ background: PINK }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#C91578')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = PINK)}>
                    Browse Files
                    <input type="file" onChange={handleFileChange} className="hidden"
                      accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.html,.htm,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.gif,.webp,.mp4,.avi,.mov,.mkv,.webm"
                      aria-label="Select file to upload" />
                  </label>
                  <p className="text-xs mt-5" style={{ color: '#C4C9D4' }}>
                    PDF, DOC, DOCX, PPT, PPTX, TXT, HTML, XLSX, XLS, CSV, Images, Videos (MP4, AVI, MOV, MKV, WebM)
                  </p>
                  <p className="text-xs mt-1" style={{ color: '#C4C9D4' }}>Maximum file size: 500MB</p>
                </div>
              )}
            </div>

            {/* Configuration */}
            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#6B7280' }}>
                  Source Type
                </label>
                <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}
                  className="dialog-input" disabled={uploading}
                  style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236B7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`, backgroundPosition: 'right 10px center', backgroundRepeat: 'no-repeat', backgroundSize: '18px', paddingRight: '2.5rem', appearance: 'none' }}>
                  <option value="web_ui">Web UI Upload</option>
                  <option value="shared_drive">Shared Drive</option>
                  <option value="file_repo">File Repository</option>
                  <option value="s3_direct">S3 Direct</option>
                </select>
              </div>
            </div>

            <button onClick={handleUpload} disabled={!file || uploading}
              className="btn-dialog w-full mt-6 py-3.5 text-base"
              aria-label="Upload file and start ingestion">
              {uploading ? (
                <><Loader className="w-5 h-5 animate-spin" /> Uploading… {uploadProgress}%</>
              ) : (
                <><UploadIcon className="w-5 h-5" /> Upload &amp; Start Ingestion</>
              )}
            </button>
          </div>

          {/* ── Upload success + live sync status ───────────────────────── */}
          {uploadResult && (
            <>
              {/* Success card */}
              <div className="dialog-card p-6 mt-5" style={{ borderLeft: '4px solid #059669' }}>
                <div className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 flex-shrink-0 mt-0.5" style={{ color: '#059669' }} />
                  <div className="flex-1">
                    <h3 className="font-semibold text-base mb-1" style={{ color: '#343a40' }}>
                      File uploaded to S3
                    </h3>
                    <p className="text-xs font-mono break-all mb-2" style={{ color: '#059669' }}>
                      {uploadResult.s3_key}
                    </p>
                    <p className="text-xs" style={{ color: '#9CA3AF' }}>
                      {(uploadResult.size_bytes / 1024 / 1024).toFixed(2)} MB •{' '}
                      {uploadResult.filename}
                    </p>
                  </div>
                </div>
              </div>

              {/* Live KB ingestion status card */}
              <SyncStatusCard
                s3Key={uploadResult.s3_key}
                filename={uploadResult.filename}
              />
            </>
          )}

          {/* Error */}
          {error && (
            <div className="dialog-card p-6 mt-5" style={{ borderLeft: '4px solid #DC2626' }}>
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 flex-shrink-0 mt-0.5" style={{ color: '#DC2626' }} />
                <div className="flex-1">
                  <h3 className="font-semibold text-base mb-1" style={{ color: '#343a40' }}>Upload Failed</h3>
                  <p className="text-sm" style={{ color: '#6B7280' }}>{error}</p>
                  <button onClick={() => setError(null)} className="mt-3 text-xs font-medium underline" style={{ color: '#DC2626' }}>
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
