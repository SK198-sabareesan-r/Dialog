import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Upload as UploadIcon, File, Loader, CheckCircle, FileText,
  Image, FileSpreadsheet, AlertTriangle, Info, X,
  FolderOpen, Folder, ChevronRight, Home, RefreshCw,
  Clock, Database, Calendar, Play, Pause,
  Trash2, Activity, Zap, Search,
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';
const RED = '#E4002B';
const MAX_FILE_SIZE = 500 * 1024 * 1024;

// ── Brand Icons ───────────────────────────────────────────────────────────────
const IconGoogleDrive = () => (
  <svg viewBox="0 0 87.3 78" className="w-5 h-5">
    <path d="M6.6 66.85l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8H0c0 1.55.4 3.1 1.2 4.5z" fill="#0066DA"/>
    <path d="M43.65 25L29.9 1.2C28.55 2 27.4 3.1 26.6 4.5L1.2 49.5c-.8 1.4-1.2 2.95-1.2 4.5h27.5z" fill="#00AC47"/>
    <path d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5H60.1l5.85 11.5z" fill="#EA4335"/>
    <path d="M43.65 25L57.4 1.2C56.05.4 54.5 0 52.9 0H34.4c-1.6 0-3.15.45-4.5 1.2z" fill="#00832D"/>
    <path d="M60.1 54H27.5L13.75 77.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684FC"/>
    <path d="M73.4 26.5l-12.5-21.65c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25l16.45 29H87.3c0-1.55-.4-3.1-1.2-4.5z" fill="#FFBA00"/>
  </svg>
);

const IconS3 = () => (
  <img src="/s3.png" alt="AWS S3" className="w-5 h-5 object-contain" />
);

const IconConfluence = () => (
  <img src="/confluence.webp" alt="Confluence" className="w-5 h-5 object-contain" />
);

// ── Config ────────────────────────────────────────────────────────────────────
const SOURCES = [
  { id: 'web',        label: 'Local Upload', desc: 'Drag & drop or browse',  color: RED,       bg: '#FFF1F3', Icon: () => <UploadIcon className="w-5 h-5" style={{ color: RED }} /> },
  { id: 'drive',      label: 'Google Drive', desc: 'Sync from My Drive',     color: '#4285F4', bg: '#EFF6FF', Icon: IconGoogleDrive },
  { id: 's3',         label: 'AWS S3',       desc: 'Sync from S3 bucket',    color: '#E25444', bg: '#FFF5F3', Icon: IconS3 },
  { id: 'confluence', label: 'Confluence',   desc: 'Sync from spaces',       color: '#0052CC', bg: '#EFF6FF', Icon: IconConfluence },
];

const SCHEDULE_OPTIONS = [
  { value: '2m',     label: 'Every 2 min' },
  { value: '5m',     label: 'Every 5 min' },
  { value: 'hourly', label: 'Every hour'  },
  { value: '6h',     label: 'Every 6h'   },
  { value: '12h',    label: 'Every 12h'  },
  { value: 'daily',  label: 'Daily'      },
  { value: 'weekly', label: 'Weekly'     },
];


const STATUS_STYLE = {
  active: { label: 'Active', bg: '#ECFDF5', color: '#059669', dot: '#059669' },
  paused: { label: 'Paused', bg: '#F9FAFB', color: '#6B7280', dot: '#9CA3AF' },
  error:  { label: 'Error',  bg: '#FEF2F2', color: '#DC2626', dot: '#DC2626' },
};


const fmt = (b) => !b ? '—' : b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(0)} KB` : `${(b/1048576).toFixed(1)} MB`;
const fmtDate = (iso) => !iso ? 'Never' : new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });

// Shorten long error messages — strip URLs, keep the meaningful part
const fmtError = (msg) => {
  if (!msg) return '';
  // Extract just the HTTP error code and message before the URL
  const match = msg.match(/^(\d{3}\s+\w[\w\s]+?)(?:\s+for\s+url:|:\s+https?:\/\/)/i);
  if (match) return match[1].trim();
  // Remove any URL from the message
  const noUrl = msg.replace(/https?:\/\/\S+/g, '').replace(/\s{2,}/g, ' ').trim();
  return noUrl.length > 120 ? noUrl.slice(0, 120) + '…' : noUrl;
};
const getFileIcon = (name) => {
  const ext = (name||'').split('.').pop().toLowerCase();
  if (['pdf','doc','docx','txt','html'].includes(ext)) return FileText;
  if (['png','jpg','jpeg','gif','webp'].includes(ext)) return Image;
  if (['xlsx','xls','csv'].includes(ext)) return FileSpreadsheet;
  return File;
};

// ── Shared UI ─────────────────────────────────────────────────────────────────
const Card = ({ children, className = '', style = {} }) => (
  <div className={`bg-white rounded-2xl border ${className}`} style={{ borderColor: '#E8EAF0', boxShadow: '0 1px 4px rgba(0,0,0,0.04)', ...style }}>
    {children}
  </div>
);

const SourceTab = ({ source, active, onClick }) => (
  <button onClick={onClick} className="flex items-center gap-3 px-4 py-3.5 rounded-2xl border-2 transition-all w-full text-left group"
    style={{
      borderColor: active ? source.color : '#E8EAF0',
      background: active ? source.bg : '#fff',
      boxShadow: active ? `0 4px 12px ${source.color}22` : '0 1px 3px rgba(0,0,0,0.04)',
      transform: active ? 'translateY(-1px)' : 'none',
    }}>
    <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 transition-all"
      style={{ background: active ? '#fff' : source.bg, boxShadow: active ? `0 2px 8px ${source.color}25` : 'none' }}>
      <source.Icon />
    </div>
    <div className="min-w-0 flex-1">
      <p className="text-sm font-bold truncate" style={{ color: active ? source.color : '#374151' }}>{source.label}</p>
      <p className="text-xs truncate mt-0.5" style={{ color: active ? source.color + 'aa' : '#9CA3AF' }}>{source.desc}</p>
    </div>
    {active && (
      <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: source.color }} />
    )}
  </button>
);

const Field = ({ label, required, children, hint }) => (
  <div>
    <label className="block text-xs font-semibold mb-1.5" style={{ color: '#374151' }}>
      {label}{required && <span style={{ color: RED }}> *</span>}
      {hint && <span className="font-normal ml-1" style={{ color: '#9CA3AF' }}>({hint})</span>}
    </label>
    {children}
  </div>
);

const Input = ({ type = 'text', value, onChange, placeholder }) => (
  <input type={type} value={value} onChange={onChange} placeholder={placeholder}
    className="w-full px-3 py-2.5 border rounded-xl text-sm transition-all focus:outline-none"
    style={{ borderColor: '#E5E7EB' }}
    onFocus={e => (e.target.style.borderColor = RED)}
    onBlur={e => (e.target.style.borderColor = '#E5E7EB')} />
);

const Btn = ({ onClick, disabled, color = RED, children, style = {} }) => (
  <button onClick={onClick} disabled={disabled}
    className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all"
    style={{ background: disabled ? '#E5E7EB' : color, color: disabled ? '#9CA3AF' : '#fff', border: 'none', cursor: disabled ? 'not-allowed' : 'pointer', ...style }}>
    {children}
  </button>
);

const Alert = ({ type = 'error', children }) => {
  const s = { error: { bg: '#FEF2F2', border: '#FECACA', color: '#DC2626', Icon: AlertTriangle }, success: { bg: '#ECFDF5', border: '#A7F3D0', color: '#059669', Icon: CheckCircle }, info: { bg: '#EFF6FF', border: '#BFDBFE', color: '#2563EB', Icon: Info } }[type] || { bg: '#FEF2F2', border: '#FECACA', color: '#DC2626', Icon: AlertTriangle };
  return (
    <div className="flex items-start gap-2.5 p-3 rounded-xl border" style={{ background: s.bg, borderColor: s.border }}>
      <s.Icon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: s.color }} />
      <p className="text-xs" style={{ color: s.color }}>{children}</p>
    </div>
  );
};

// ── Local Upload Tab ──────────────────────────────────────────────────────────
const WebUploadTab = () => {
  const { user } = useAuth();
  const toast = useToast();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState('');
  const [kbStatus, setKbStatus] = useState(''); // eslint-disable-line no-unused-vars
  const [kbJobId, setKbJobId] = useState(null); // eslint-disable-line no-unused-vars
  const [showProgress, setShowProgress] = useState(false); // eslint-disable-line no-unused-vars
  const intervalRef = useRef(null); // eslint-disable-line no-unused-vars

  const pick = (f) => {
    setError(null); setProgress(0); setUploadStage(''); setKbStatus(''); setShowProgress(false);
    if (!f) return;
    if (f.size > MAX_FILE_SIZE) { setError('File exceeds 500 MB limit'); return; }
    setFile(f);
  };

  const upload = async () => {
    if (!file) return;
    setUploading(true); setError(null); setProgress(0); setShowProgress(true);
    try {
      // Stage 1: Processing
      setUploadStage('processing');
      await new Promise(resolve => setTimeout(resolve, 500));

      // Stage 2: Extracting metadata
      setUploadStage('metadata');
      await new Promise(resolve => setTimeout(resolve, 800));

      // Stage 3: Uploading to S3
      setUploadStage('uploading');
      const fd = new FormData();
      fd.append('file', file); fd.append('user_id', user?.email || 'guest');
      await axios.post(`${API_BASE}/api/upload/direct`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000,
        onUploadProgress: (e) => setProgress(Math.round((e.loaded * 100) / e.total)),
      });

      // Stage 4: Syncing to KB
      setUploadStage('kbsync');
      setKbStatus('STARTING');
      setFile(null); setProgress(0);
      toast('File uploaded — syncing to Knowledge Base…', 'success');

      // Start polling KB status
      setTimeout(async () => {
        try {
          const r = await axios.get(`${API_BASE}/api/kb/sync/latest`, { timeout: 10000 });
          if (r.data?.ingestion_job_id) {
            setKbJobId(r.data.ingestion_job_id);
            setKbStatus(r.data.status || 'STARTING');
            // Poll every 8 seconds
            intervalRef.current = setInterval(async () => {
              try {
                const status = await axios.get(`${API_BASE}/api/upload/sync-status/${r.data.ingestion_job_id}`, { timeout: 10000 });
                setKbStatus(status.data.status);
                if (['COMPLETE','FAILED','STOPPED'].includes(status.data.status)) {
                  clearInterval(intervalRef.current);
                  if (status.data.status === 'COMPLETE') {
                    setTimeout(() => setShowProgress(false), 3000);
                  }
                }
              } catch {}
            }, 8001);
          }
        } catch {}
      }, 2000);
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Upload failed';
      setError(msg);
      toast(msg, 'error');
      setUploadStage('');
      setShowProgress(false);
    } finally { setUploading(false); }
  };

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const FileIcon = file ? getFileIcon(file.name) : UploadIcon;

  return (
    <div className="space-y-4">
      <div onDrop={e => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files[0]); }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
        className="rounded-2xl p-10 text-center transition-all"
        style={{ border: `2px dashed ${error ? '#DC2626' : file ? '#059669' : dragging ? RED : '#D1D5DB'}`, background: file ? '#F0FDF4' : dragging ? '#FFF1F3' : '#FAFBFC', cursor: 'pointer' }}>
        {file ? (
          <div className="flex flex-col items-center">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3" style={{ background: '#DCFCE7', border: '2px solid #A7F3D0' }}>
              <FileIcon className="w-8 h-8" style={{ color: '#059669' }} />
            </div>
            <p className="font-semibold text-sm mb-1" style={{ color: '#1A1A2E' }}>{file.name}</p>
            <p className="text-xs mb-4" style={{ color: '#9CA3AF' }}>{fmt(file.size)}</p>
            {progress > 0 && progress < 100 && (
              <div className="w-full max-w-xs mb-3"><div className="h-2 rounded-full" style={{ background: '#E5E7EB' }}><div className="h-full rounded-full transition-all" style={{ background: RED, width: `${progress}%` }} /></div></div>
            )}
            <button onClick={() => setFile(null)} className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg" style={{ background: '#FEE2E2', color: '#DC2626' }}>
              <X className="w-3 h-3" /> Remove
            </button>
          </div>
        ) : (
          <div>
            <div className="inline-flex w-16 h-16 rounded-2xl items-center justify-center mb-4" style={{ background: `${RED}12` }}>
              <UploadIcon className="w-8 h-8" style={{ color: RED }} />
            </div>
            <p className="font-semibold text-base mb-1" style={{ color: '#1A1A2E' }}>Drop your file here</p>
            <p className="text-sm mb-5" style={{ color: '#9CA3AF' }}>or click to browse</p>
            <label className="inline-block px-6 py-2.5 rounded-xl font-semibold text-white text-sm cursor-pointer" style={{ background: RED }}>
              Browse Files
              <input type="file" onChange={e => pick(e.target.files[0])} className="hidden"
                accept=".pdf,.doc,.docx,.txt,.html,.htm,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.gif,.webp,.bmp,.mp4,.avi,.mov,.wmv,.mkv,.flv,.webm,.mp3,.wav,.m4a" />
            </label>
            <p className="text-xs mt-4" style={{ color: '#C4C9D4' }}>PDF · DOCX · HTML · Excel · Images (JPG, PNG) · Videos (MP4, AVI, MOV) · Audio — Max 500 MB</p>
          </div>
        )}
      </div>
      <Btn onClick={upload} disabled={!file || uploading} color={RED} style={{ width: '100%', padding: '12px' }}>
        {uploading ? <><Loader className="w-5 h-5 animate-spin" />Processing...</> : <><UploadIcon className="w-5 h-5" />Upload &amp; Sync to KB</>}
      </Btn>
      {showProgress && (
        <div className="rounded-xl p-4 border" style={{ background: '#EFF6FF', borderColor: '#BFDBFE' }}>
          {/* Horizontal Progress Steps */}
          <div className="flex items-center justify-between mb-4">
            {[
              { id: 'processing', label: 'Processing', icon: '🔄' },
              { id: 'metadata', label: 'Extracting', icon: '📋' },
              { id: 'uploading', label: 'Uploading', icon: '☁️' },
              { id: 'kbsync', label: 'KB Sync', icon: '🗄️' }
            ].map((stage, idx) => {
              const stageOrder = ['processing', 'metadata', 'uploading', 'kbsync'];
              const currentIdx = stageOrder.indexOf(uploadStage);
              const isActive = uploadStage === stage.id;
              const isComplete = currentIdx > idx;
              const isCurrent = currentIdx >= idx;

              return (
                <React.Fragment key={stage.id}>
                  <div className="flex flex-col items-center flex-1">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-all ${isActive ? 'animate-pulse' : ''}`}
                      style={{
                        background: isActive ? '#3B82F6' : isComplete ? '#059669' : '#E5E7EB',
                        border: `2px solid ${isActive ? '#3B82F6' : isComplete ? '#059669' : '#D1D5DB'}`,
                        transform: isActive ? 'scale(1.1)' : 'scale(1)'
                      }}>
                      {isComplete ? (
                        <CheckCircle className="w-5 h-5" style={{ color: '#fff' }} />
                      ) : (
                        <span className="text-base">{stage.icon}</span>
                      )}
                    </div>
                    <p className="text-xs font-semibold text-center" style={{ color: isCurrent ? '#3B82F6' : '#9CA3AF' }}>
                      {stage.label}
                    </p>
                  </div>
                  {idx < 3 && (
                    <div className="w-12 h-0.5 mb-8 transition-all" style={{
                      background: isComplete ? '#059669' : '#E5E7EB',
                      marginLeft: '-8px',
                      marginRight: '-8px'
                    }} />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Current Stage Info */}
          <div className="text-center">
            <p className="text-sm font-semibold mb-1" style={{ color: '#1A1A2E' }}>
              {uploadStage === 'processing' && 'Processing file...'}
              {uploadStage === 'metadata' && 'Extracting metadata...'}
              {uploadStage === 'uploading' && 'Uploading to S3...'}
              {uploadStage === 'kbsync' && (
                kbStatus === 'COMPLETE' ? 'Synced to Knowledge Base ✓' :
                kbStatus === 'FAILED' ? 'KB Sync Failed' :
                kbStatus === 'STOPPED' ? 'KB Sync Stopped' :
                'Syncing to Knowledge Base...'
              )}
            </p>
            <div className="h-2 rounded-full overflow-hidden" style={{ background: '#DBEAFE' }}>
              <div className="h-full rounded-full transition-all"
                style={{
                  background: kbStatus === 'COMPLETE' ? '#059669' : kbStatus === 'FAILED' ? '#DC2626' : '#3B82F6',
                  width: uploadStage === 'processing' ? '25%' :
                         uploadStage === 'metadata' ? '50%' :
                         uploadStage === 'uploading' ? '75%' :
                         uploadStage === 'kbsync' && kbStatus === 'COMPLETE' ? '100%' :
                         uploadStage === 'kbsync' ? '85%' : '0%',
                  animation: (uploadStage !== 'kbsync' || kbStatus !== 'COMPLETE') ? 'indeterminate 1.5s ease-in-out infinite' : 'none'
                }}
              />
            </div>
            {kbJobId && <p className="text-xs mt-2 font-mono" style={{ color: '#C4C9D4' }}>Job: {kbJobId}</p>}
          </div>
        </div>
      )}
      {error && <Alert type="error">{error}</Alert>}
    </div>
  );
};

// ── Breadcrumb ────────────────────────────────────────────────────────────────
const Breadcrumb = ({ crumbs, onNavigate }) => (
  <div className="flex items-center gap-1 flex-wrap">
    {crumbs.map((c, i) => (
      <React.Fragment key={c.id || i}>
        {i > 0 && <ChevronRight className="w-3 h-3 flex-shrink-0" style={{ color: '#D1D5DB' }} />}
        <button onClick={() => onNavigate(i)} className="flex items-center gap-1 text-xs font-medium px-1.5 py-0.5 rounded"
          style={{ color: i === crumbs.length-1 ? '#374151' : RED, cursor: i === crumbs.length-1 ? 'default' : 'pointer', background: i === crumbs.length-1 ? '#F3F4F6' : 'transparent' }}>
          {i === 0 && <Home className="w-3 h-3" />}{c.name}
        </button>
      </React.Fragment>
    ))}
  </div>
);

// ── Google Drive Tab ──────────────────────────────────────────────────────────
const DriveTab = () => {
  const { driveToken, user, token, refreshDriveToken } = useAuth();
  const [liveToken, setLiveToken] = useState(driveToken);
  const [drives, setDrives] = useState([]);
  const [selectedDriveId, setSelectedDriveId] = useState('');
  const [crumbs, setCrumbs] = useState([{ id: 'root', name: 'My Drive' }]);
  const [folders, setFolders] = useState([]);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [syncName, setSyncName] = useState('');
  const [schedule, setSchedule] = useState('daily');
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [saving, setSaving] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState('');
  const [syncConfigs, setSyncConfigs] = useState([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);
  const [viewMode, setViewMode] = useState('mydrive');
  const [sharedFolders, setSharedFolders] = useState([]);
  const [loadingShared, setLoadingShared] = useState(false);
  const userId = user?.id || user?.email;

  const toast = useToast();

  useEffect(() => { setLiveToken(driveToken); }, [driveToken]);

  const withRetry = useCallback(async (fn) => {
    try { return await fn(liveToken); }
    catch (e) {
      if (e.response?.status === 401 && token) {
        const fresh = await refreshDriveToken(token);
        if (fresh) { setLiveToken(fresh); return await fn(fresh); }
        setLiveToken(null);
      }
      throw e;
    }
  }, [liveToken, token, refreshDriveToken]);

  const fetchConfigs = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs`, { params: { user_id: userId } });
      setSyncConfigs((res.data.configs || []).filter(c => c.source_type === 'gdrive'));
    } catch { setSyncConfigs([]); } finally { setLoadingConfigs(false); }
  }, [userId]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const browse = useCallback(async (folderId, driveId) => {
    setLoading(true); setError(null);
    try {
      const res = await withRetry(t => axios.get(`${API_BASE}/api/google-drive/browse`, {
        params: { google_access_token: t, folder_id: folderId, ...(driveId ? { drive_id: driveId } : {}) },
      }));
      setFolders(res.data.folders || []);
      setFiles(res.data.files || []);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load folder'); }
    finally { setLoading(false); }
  }, [withRetry]);

  useEffect(() => {
    if (!liveToken) return;
    withRetry(t => axios.get(`${API_BASE}/api/google-drive/shared-drives`, { params: { google_access_token: t } }))
      .then(r => setDrives(r.data.shared_drives || [])).catch(() => {});
  }, [liveToken, withRetry]);

  useEffect(() => {
    if (!liveToken) return;
    const rootName = selectedDriveId ? (drives.find(d => d.id === selectedDriveId)?.name || 'Shared Drive') : 'My Drive';
    setCrumbs([{ id: selectedDriveId || 'root', name: rootName }]);
    setSelectedFolder(null);
    browse(selectedDriveId || 'root', selectedDriveId || undefined);
  }, [selectedDriveId, liveToken]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchSharedFolders = useCallback(async () => {
    if (!liveToken) return;
    setLoadingShared(true);
    try {
      const res = await withRetry(t => axios.get(`${API_BASE}/api/google-drive/shared-with-me`, { params: { google_access_token: t } }));
      setSharedFolders(res.data.folders || []);
    } catch { setSharedFolders([]); } finally { setLoadingShared(false); }
  }, [liveToken, withRetry]);

  useEffect(() => { if (viewMode === 'shared' && liveToken) fetchSharedFolders(); }, [viewMode, liveToken, fetchSharedFolders]);

  const openFolder = (f) => { setCrumbs(p => [...p, { id: f.id, name: f.name }]); browse(f.id, selectedDriveId || undefined); };
  const navTo = (i) => { const nc = crumbs.slice(0, i+1); setCrumbs(nc); browse(nc[nc.length-1].id, selectedDriveId || undefined); };

  const handleSelectFolder = (f) => { setSelectedFolder(f); setSyncName(`${f.name} Sync`); setSyncSuccess(''); setError(null); };
  const handleSelectCurrentFolder = () => {
    const cur = crumbs[crumbs.length-1];
    setSelectedFolder({ id: cur.id, name: cur.name });
    setSyncName(`${cur.name} Sync`);
    setSyncSuccess(''); setError(null);
  };

  const handleSaveSync = async () => {
    if (!syncName.trim()) { setError('Give this sync a name'); return; }
    if (!selectedFolder) { setError('Select a folder to sync'); return; }
    setSaving(true); setError(null); setSyncSuccess('');
    try {
      await axios.post(`${API_BASE}/api/sync/configs`, {
        user_id: userId, source_type: 'gdrive', display_name: syncName,
        credentials: { access_token: liveToken, drive_id: selectedDriveId || null },
        schedule, space_or_path: selectedFolder.id,
      });
      setSyncSuccess(`"${selectedFolder.name}" scheduled!`);
      toast(`"${selectedFolder.name}" sync scheduled`, 'success');
      setSelectedFolder(null); setSyncName(''); fetchConfigs();
    } catch (e) {
      const msg = e.response?.data?.detail || 'Failed to save';
      setError(msg);
      toast(msg, 'error');
    }
    finally { setSaving(false); }
  };

  if (!liveToken) return <Alert type="error">Google Drive session expired — sign out and sign back in.</Alert>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border" style={{ background: '#EFF6FF', borderColor: '#BFDBFE' }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#fff' }}><IconGoogleDrive /></div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Google Drive connected</p>
          <p className="text-xs truncate" style={{ color: '#9CA3AF' }}>{user?.email}</p>
        </div>
        <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#4285F4' }} />
      </div>

      {/* View toggle */}
      <div className="flex gap-1 p-1 rounded-xl" style={{ background: '#F3F4F6' }}>
        {[{ id: 'mydrive', label: 'My Drive' }, { id: 'shared', label: 'Shared with me' }].map(v => (
          <button key={v.id} onClick={() => setViewMode(v.id)} className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={{ background: viewMode === v.id ? '#fff' : 'transparent', color: viewMode === v.id ? '#1A1A2E' : '#9CA3AF', boxShadow: viewMode === v.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}>
            {v.label}
          </button>
        ))}
      </div>

      {viewMode === 'mydrive' && drives.length > 0 && (
        <div>
          <label className="block text-xs font-semibold mb-1.5" style={{ color: '#374151' }}>Shared Drive (optional)</label>
          <select value={selectedDriveId} onChange={e => setSelectedDriveId(e.target.value)}
            className="w-full px-3 py-2.5 border rounded-xl text-sm focus:outline-none" style={{ borderColor: '#E5E7EB' }}>
            <option value="">My Drive</option>
            {drives.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
      )}

      {viewMode === 'mydrive' && (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E5E7EB' }}>
          <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: '#F3F4F6', background: '#FAFBFC' }}>
            <Breadcrumb crumbs={crumbs} onNavigate={navTo} />
            <div className="flex items-center gap-2 flex-shrink-0">
              <button onClick={handleSelectCurrentFolder} className="text-xs px-2 py-1 rounded-lg font-semibold" style={{ background: `${RED}12`, color: RED }}>
                Sync this folder
              </button>              <button onClick={() => browse(crumbs[crumbs.length-1].id, selectedDriveId || undefined)} className="p-1.5 rounded-lg" style={{ color: '#9CA3AF' }}>
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
          <div className="max-h-56 overflow-y-auto">
            {loading ? (
              <div className="flex justify-center py-8"><Loader className="w-5 h-5 animate-spin" style={{ color: RED }} /></div>
            ) : folders.length === 0 && files.length === 0 ? (
              <div className="py-8 text-center"><FolderOpen className="w-8 h-8 mx-auto mb-2 opacity-30" /><p className="text-xs" style={{ color: '#9CA3AF' }}>No files or folders</p></div>
            ) : (
              <>
                {folders.map(f => (
                  <div key={f.id} className="flex items-center gap-3 px-4 py-2.5 border-b hover:bg-gray-50 transition-colors cursor-pointer" style={{ borderColor: '#F3F4F6', background: selectedFolder?.id === f.id ? '#EFF6FF' : '' }} onClick={() => handleSelectFolder(f)}>
                    <Folder className="w-4 h-4 flex-shrink-0" style={{ color: '#F7941D' }} />
                    <span className="flex-1 text-sm font-medium truncate" style={{ color: selectedFolder?.id === f.id ? '#4285F4' : '#1A1A2E' }}>
                      {f.name}{selectedFolder?.id === f.id && <span className="ml-2 text-xs px-1.5 py-0.5 rounded" style={{ background: '#EFF6FF', color: '#4285F4' }}>Selected</span>}
                    </span>
                    <button onClick={e => { e.stopPropagation(); openFolder(f); }} className="text-xs px-2 py-1 rounded-lg flex items-center gap-1 flex-shrink-0" style={{ color: RED, background: `${RED}10` }}>
                      Open <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                {files.map(f => (
                  <div key={f.id} className="flex items-center gap-3 px-4 py-2 border-b" style={{ borderColor: '#F3F4F6' }}>
                    <FileText className="w-4 h-4 flex-shrink-0" style={{ color: '#9CA3AF' }} />
                    <span className="flex-1 text-xs truncate" style={{ color: '#374151' }}>{f.name}</span>
                    <span className="text-xs flex-shrink-0" style={{ color: '#C4C9D4' }}>{fmt(f.size)}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {viewMode === 'shared' && (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E5E7EB' }}>
          <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: '#F3F4F6', background: '#FAFBFC' }}>
            <p className="text-xs font-medium" style={{ color: '#374151' }}>Shared with {user?.email}</p>
            <button onClick={fetchSharedFolders} className="p-1.5 rounded-lg" style={{ color: '#9CA3AF' }}>
              <RefreshCw className={`w-3.5 h-3.5 ${loadingShared ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="max-h-56 overflow-y-auto">
            {loadingShared ? (
              <div className="flex justify-center py-8"><Loader className="w-5 h-5 animate-spin" style={{ color: '#4285F4' }} /></div>
            ) : sharedFolders.length === 0 ? (
              <div className="py-8 text-center"><FolderOpen className="w-8 h-8 mx-auto mb-2 opacity-30" /><p className="text-xs" style={{ color: '#9CA3AF' }}>No shared folders</p></div>
            ) : (
              sharedFolders.map(f => (
                <div key={f.id} className="flex items-center gap-3 px-4 py-2.5 border-b hover:bg-gray-50 transition-colors" style={{ borderColor: '#F3F4F6' }}>
                  <FolderOpen className="w-4 h-4 flex-shrink-0" style={{ color: '#4285F4' }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: '#1A1A2E' }}>{f.name}</p>
                    {f.shared_by && <p className="text-xs" style={{ color: '#9CA3AF' }}>by {f.shared_by}</p>}
                  </div>
                  <button onClick={() => handleSelectFolder(f)} className="text-xs px-3 py-1.5 rounded-lg font-semibold flex-shrink-0"
                    style={{ background: selectedFolder?.id === f.id ? '#EFF6FF' : `${RED}10`, color: selectedFolder?.id === f.id ? '#4285F4' : RED }}>
                    {selectedFolder?.id === f.id ? 'Selected ✓' : 'Select'}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {selectedFolder && (
        <div className="rounded-xl p-4 space-y-3 border-2" style={{ borderColor: '#4285F4', background: '#EFF6FF' }}>
          <div className="flex items-center gap-2">
            <Folder className="w-4 h-4" style={{ color: '#4285F4' }} />
            <span className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>{selectedFolder.name}</span>
            <button onClick={() => setSelectedFolder(null)} className="ml-auto" style={{ color: '#9CA3AF' }}><X className="w-4 h-4" /></button>
          </div>
          <Field label="Sync Name" required>
            <Input value={syncName} onChange={e => setSyncName(e.target.value)} placeholder="e.g. HR Documents" />
          </Field>
          <Field label="Schedule">
            <div className="grid grid-cols-4 gap-1.5">
              {SCHEDULE_OPTIONS.map(o => (
                <button key={o.value} onClick={() => setSchedule(o.value)} className="py-1.5 rounded-lg text-xs font-semibold border transition-all"
                  style={{ borderColor: schedule === o.value ? '#4285F4' : '#E5E7EB', background: schedule === o.value ? '#EFF6FF' : '#fff', color: schedule === o.value ? '#4285F4' : '#6B7280' }}>
                  {o.label}
                </button>
              ))}
            </div>
          </Field>
          {error && <Alert type="error">{error}</Alert>}
          {syncSuccess && <Alert type="success">{syncSuccess}</Alert>}
          <Btn onClick={handleSaveSync} disabled={saving} color="#4285F4" style={{ width: '100%' }}>
            {saving ? <><Loader className="w-4 h-4 animate-spin" />Saving…</> : <><Calendar className="w-4 h-4" />Schedule Sync</>}
          </Btn>
        </div>
      )}

      <SyncConfigList configs={syncConfigs} loading={loadingConfigs} userId={userId} onRefresh={fetchConfigs} sourceColor="#4285F4" />
    </div>
  );
};

// ── AWS S3 Sync Tab ───────────────────────────────────────────────────────────
const S3SyncTab = ({ userId }) => {
  const [form, setForm] = useState({ syncName: '', bucket: '', prefix: '', region: 'ap-south-1', accessKeyId: '', secretAccessKey: '', sessionToken: '' });
  const [schedule, setSchedule] = useState('daily');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState('');
  const [syncConfigs, setSyncConfigs] = useState([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);

  const toast = useToast();
  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }));

  const fetchConfigs = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs`, { params: { user_id: userId } });
      setSyncConfigs((res.data.configs || []).filter(c => c.source_type === 's3'));
    } catch { setSyncConfigs([]); } finally { setLoadingConfigs(false); }
  }, [userId]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const handleSave = async () => {
    if (!form.syncName.trim()) { setError('Sync name is required'); return; }
    if (!form.bucket.trim()) { setError('S3 bucket name is required'); return; }
    if (!form.accessKeyId.trim()) { setError('AWS Access Key ID is required'); return; }
    if (!form.secretAccessKey.trim()) { setError('AWS Secret Access Key is required'); return; }
    setSaving(true); setError(null); setSuccess('');
    try {
      await axios.post(`${API_BASE}/api/sync/configs`, {
        user_id: userId, source_type: 's3', display_name: form.syncName,
        credentials: { bucket: form.bucket, prefix: form.prefix || '', region: form.region || 'ap-south-1', aws_access_key_id: form.accessKeyId, aws_secret_access_key: form.secretAccessKey, ...(form.sessionToken ? { aws_session_token: form.sessionToken } : {}) },
        schedule, space_or_path: form.bucket + (form.prefix ? `/${form.prefix}` : ''),
      });
      setSuccess(`S3 sync "${form.syncName}" scheduled!`);
      toast(`S3 sync "${form.syncName}" scheduled`, 'success');
      setForm({ syncName: '', bucket: '', prefix: '', region: 'ap-south-1', accessKeyId: '', secretAccessKey: '', sessionToken: '' });
      fetchConfigs();
    } catch (e) {
      const msg = e.response?.data?.detail || 'Failed to save';
      setError(msg);
      toast(msg, 'error');
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Sync Name" required><Input value={form.syncName} onChange={set('syncName')} placeholder="e.g. Marketing Assets" /></Field>
        <Field label="S3 Bucket" required><Input value={form.bucket} onChange={set('bucket')} placeholder="my-bucket-name" /></Field>
        <Field label="Prefix / Folder" hint="optional"><Input value={form.prefix} onChange={set('prefix')} placeholder="folder/subfolder/" /></Field>
        <Field label="Region"><Input value={form.region} onChange={set('region')} placeholder="ap-south-1" /></Field>
        <Field label="AWS Access Key ID" required><Input value={form.accessKeyId} onChange={set('accessKeyId')} placeholder="AKIAIOSFODNN7EXAMPLE" /></Field>
        <Field label="AWS Secret Access Key" required><Input type="password" value={form.secretAccessKey} onChange={set('secretAccessKey')} placeholder="••••••••" /></Field>
      </div>
      <Field label="AWS Session Token" hint="optional for SSO">
        <Input type="password" value={form.sessionToken} onChange={set('sessionToken')} placeholder="Temporary session token" />
      </Field>
      <Field label="Schedule">
        <div className="grid grid-cols-4 gap-1.5">
          {SCHEDULE_OPTIONS.map(o => (
            <button key={o.value} onClick={() => setSchedule(o.value)} className="py-1.5 rounded-lg text-xs font-semibold border transition-all"
              style={{ borderColor: schedule === o.value ? '#E25444' : '#E5E7EB', background: schedule === o.value ? '#FFF5F3' : '#fff', color: schedule === o.value ? '#E25444' : '#6B7280' }}>
              {o.label}
            </button>
          ))}
        </div>
      </Field>
      {error && <Alert type="error">{error}</Alert>}
      {success && <Alert type="success">{success}</Alert>}
      <Btn onClick={handleSave} disabled={saving} color="#E25444" style={{ width: '100%' }}>
        {saving ? <><Loader className="w-4 h-4 animate-spin" />Saving…</> : <><Database className="w-4 h-4" />Schedule S3 Sync</>}
      </Btn>
      <SyncConfigList configs={syncConfigs} loading={loadingConfigs} userId={userId} onRefresh={fetchConfigs} sourceColor="#E25444" />
    </div>
  );
};

// ── Confluence Sync Tab ───────────────────────────────────────────────────────
const ConfluenceSyncTab = ({ userId }) => {
  const [step, setStep] = useState(1);
  const [creds, setCreds] = useState({ site_url: '', email: '', api_token: '', syncName: '' });
  const [connecting, setConnecting] = useState(false);
  const [spaces, setSpaces] = useState([]);
  const [selectedSpace, setSelectedSpace] = useState(null);
  const [syncScope, setSyncScope] = useState('space');
  const [pageCrumbs, setPageCrumbs] = useState([{ id: null, name: 'Root' }]);
  const [pages, setPages] = useState([]);
  const [selectedPages, setSelectedPages] = useState([]);
  const [loadingPages, setLoadingPages] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [schedule, setSchedule] = useState('daily');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState('');
  const [syncConfigs, setSyncConfigs] = useState([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);

  const toast = useToast();
  const setCred = (k) => (e) => setCreds(p => ({ ...p, [k]: e.target.value }));

  const fetchConfigs = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs`, { params: { user_id: userId } });
      setSyncConfigs((res.data.configs || []).filter(c => c.source_type === 'confluence'));
    } catch { setSyncConfigs([]); } finally { setLoadingConfigs(false); }
  }, [userId]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const handleConnect = async () => {
    if (!creds.site_url || !creds.email || !creds.api_token) { setError('All credential fields are required'); return; }
    setConnecting(true); setError(null);
    try {
      const res = await axios.post(`${API_BASE}/api/sync/confluence/list-spaces`, { site_url: creds.site_url, email: creds.email, api_token: creds.api_token });
      setSpaces(res.data.spaces || []); setStep(2);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to connect to Confluence');
      toast(e.response?.data?.detail || 'Failed to connect to Confluence', 'error');
    }
    finally { setConnecting(false); }
  };

  const handleSelectSpace = (space) => {
    setSelectedSpace(space); setSyncScope('space'); setSelectedPages([]);
    setPageCrumbs([{ id: null, name: 'Root' }]); setPages([]); setStep(3);
  };

  const loadPages = useCallback(async (parentId, search) => {
    if (!selectedSpace) return;
    setLoadingPages(true);
    try {
      const res = await axios.get(`${API_BASE}/api/confluence/pages`, {
        params: { site_url: creds.site_url, email: creds.email, api_token: creds.api_token, space_key: selectedSpace.key, ...(parentId ? { parent_id: parentId } : {}), ...(search ? { search } : {}) },
      });
      setPages(res.data.pages || []);
    } catch { setPages([]); }
    finally { setLoadingPages(false); }
  }, [selectedSpace, creds]);

  useEffect(() => {
    if (step === 3 && syncScope === 'pages') loadPages(pageCrumbs[pageCrumbs.length-1].id, '');
  }, [step, syncScope]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (step === 3 && syncScope === 'pages') loadPages(pageCrumbs[pageCrumbs.length-1].id, searchQuery);
  }, [pageCrumbs]); // eslint-disable-line react-hooks/exhaustive-deps

  const navPageTo = (i) => setPageCrumbs(p => p.slice(0, i+1));
  const togglePage = (id) => setSelectedPages(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  const handleSave = async () => {
    if (!creds.syncName.trim()) { setError('Sync name is required'); return; }
    const space_or_path = syncScope === 'space' ? selectedSpace.key : `pages:${selectedPages.join(',')}`;
    setSaving(true); setError(null); setSuccess('');
    try {
      await axios.post(`${API_BASE}/api/sync/configs`, {
        user_id: userId, source_type: 'confluence', display_name: creds.syncName,
        credentials: { site_url: creds.site_url, email: creds.email, api_token: creds.api_token },
        schedule, space_or_path,
      });
      setSuccess(`Confluence sync "${creds.syncName}" scheduled!`);
      toast(`Confluence sync "${creds.syncName}" scheduled`, 'success');
      setStep(1); setCreds({ site_url: '', email: '', api_token: '', syncName: '' });
      setSelectedSpace(null); setSelectedPages([]); fetchConfigs();
    } catch (e) {
      const msg = e.response?.data?.detail || 'Failed to save';
      setError(msg);
      toast(msg, 'error');
    } finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      {/* Step 1 */}
      {step === 1 && (
        <div className="space-y-3">
          <Field label="Confluence Site URL" required><Input value={creds.site_url} onChange={setCred('site_url')} placeholder="yourcompany.atlassian.net" /></Field>
          <Field label="Email" required><Input value={creds.email} onChange={setCred('email')} placeholder="you@company.com" /></Field>
          <Field label="API Token" required><Input type="password" value={creds.api_token} onChange={setCred('api_token')} placeholder="Your Confluence API token" /></Field>
          <Field label="Sync Name" required><Input value={creds.syncName} onChange={setCred('syncName')} placeholder="e.g. Engineering Wiki" /></Field>
          {error && <Alert type="error">{error}</Alert>}
          <Btn onClick={handleConnect} disabled={connecting} color="#0052CC" style={{ width: '100%' }}>
            {connecting ? <><Loader className="w-4 h-4 animate-spin" />Connecting…</> : 'Connect to Confluence'}
          </Btn>
        </div>
      )}

      {/* Step 2: Space list */}
      {step === 2 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button onClick={() => setStep(1)} className="text-xs underline" style={{ color: '#9CA3AF' }}>← Back</button>
            <span className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Select a Space</span>
          </div>
          <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E5E7EB' }}>
            {spaces.length === 0 ? (
              <p className="py-8 text-center text-xs" style={{ color: '#9CA3AF' }}>No spaces found</p>
            ) : spaces.map(s => (
              <div key={s.key} className="flex items-center gap-3 px-4 py-3 border-b cursor-pointer hover:bg-blue-50 transition-colors" style={{ borderColor: '#F3F4F6' }} onClick={() => handleSelectSpace(s)}>
                <FileText className="w-4 h-4 flex-shrink-0" style={{ color: '#0052CC' }} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: '#1A1A2E' }}>{s.name}</p>
                  <p className="text-xs" style={{ color: '#9CA3AF' }}>Key: {s.key}</p>
                </div>
                <ChevronRight className="w-4 h-4 flex-shrink-0" style={{ color: '#9CA3AF' }} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step 3: Scope + pages */}
      {step === 3 && selectedSpace && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <button onClick={() => setStep(2)} className="text-xs underline" style={{ color: '#9CA3AF' }}>← Spaces</button>
            <span className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>{selectedSpace.name}</span>
          </div>
          <div className="flex gap-1 p-1 rounded-xl" style={{ background: '#F3F4F6' }}>
            {[{ id: 'space', label: 'Sync entire space' }, { id: 'pages', label: 'Pick specific files' }].map(v => (
              <button key={v.id} onClick={() => setSyncScope(v.id)} className="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={{ background: syncScope === v.id ? '#fff' : 'transparent', color: syncScope === v.id ? '#1A1A2E' : '#9CA3AF', boxShadow: syncScope === v.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}>
                {v.label}
              </button>
            ))}
          </div>
          {syncScope === 'pages' && (
            <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E5E7EB' }}>
              <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: '#F3F4F6', background: '#FAFBFC' }}>
                <Breadcrumb crumbs={pageCrumbs} onNavigate={navPageTo} />
                <div className="flex items-center gap-1 ml-auto flex-shrink-0">
                  <div className="flex items-center gap-1 px-2 py-1 rounded-lg border" style={{ borderColor: '#E5E7EB' }}>
                    <Search className="w-3 h-3" style={{ color: '#9CA3AF' }} />
                    <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && loadPages(pageCrumbs[pageCrumbs.length-1].id, searchQuery)}
                      placeholder="Search…" className="w-24 focus:outline-none text-xs" />
                  </div>
                  <button onClick={() => loadPages(pageCrumbs[pageCrumbs.length-1].id, searchQuery)} className="p-1.5 rounded-lg" style={{ color: '#9CA3AF' }}>
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingPages ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>
              <div className="max-h-56 overflow-y-auto">
                {loadingPages ? (
                  <div className="flex justify-center py-8"><Loader className="w-5 h-5 animate-spin" style={{ color: RED }} /></div>
                ) : pages.length === 0 ? (
                  <p className="py-8 text-center text-xs" style={{ color: '#9CA3AF' }}>No files found</p>
                ) : pages.map(p => (
                  <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 border-b hover:bg-gray-50" style={{ borderColor: '#F3F4F6' }}>
                    <input type="checkbox" checked={selectedPages.includes(p.id)} onChange={() => togglePage(p.id)} className="w-4 h-4 flex-shrink-0 cursor-pointer" style={{ accentColor: '#0052CC' }} />
                    <FileText className="w-4 h-4 flex-shrink-0" style={{ color: '#0052CC' }} />
                    <span className="flex-1 text-sm truncate" style={{ color: '#1A1A2E' }}>{p.title}</span>
                    <button onClick={() => setPageCrumbs(prev => [...prev, { id: p.id, name: p.title }])} className="text-xs px-2 py-1 rounded-lg flex items-center gap-1 flex-shrink-0" style={{ color: '#0052CC', background: '#EFF6FF' }}>
                      Open →
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between px-4 py-2 border-t" style={{ borderColor: '#F3F4F6', background: '#FAFBFC' }}>
                <span className="text-xs" style={{ color: '#9CA3AF' }}>{selectedPages.length} file{selectedPages.length !== 1 ? 's' : ''} selected</span>
                <div className="flex gap-3">
                  <button onClick={() => setSelectedPages(pages.map(p => p.id))} className="text-xs underline" style={{ color: '#0052CC' }}>Select all</button>
                  <button onClick={() => setSelectedPages([])} className="text-xs underline" style={{ color: '#6B7280' }}>Clear</button>
                </div>
              </div>
            </div>
          )}
          <Field label="Schedule">
            <div className="grid grid-cols-4 gap-1.5">
              {SCHEDULE_OPTIONS.map(o => (
                <button key={o.value} onClick={() => setSchedule(o.value)} className="py-1.5 rounded-lg text-xs font-semibold border transition-all"
                  style={{ borderColor: schedule === o.value ? '#0052CC' : '#E5E7EB', background: schedule === o.value ? '#EFF6FF' : '#fff', color: schedule === o.value ? '#0052CC' : '#6B7280' }}>
                  {o.label}
                </button>
              ))}
            </div>
          </Field>
          {error && <Alert type="error">{error}</Alert>}
          {success && <Alert type="success">{success}</Alert>}
          <Btn onClick={handleSave} disabled={saving || (syncScope === 'pages' && selectedPages.length === 0)} color="#0052CC" style={{ width: '100%' }}>
            {saving ? <><Loader className="w-4 h-4 animate-spin" />Saving…</> : syncScope === 'pages' ? <><Calendar className="w-4 h-4" />Sync {selectedPages.length} File{selectedPages.length !== 1 ? 's' : ''}</> : <><Calendar className="w-4 h-4" />Sync Entire Space</>}
          </Btn>
        </div>
      )}
      <SyncConfigList configs={syncConfigs} loading={loadingConfigs} userId={userId} onRefresh={fetchConfigs} sourceColor="#0052CC" />
    </div>
  );
};

// ── Sync Config List ──────────────────────────────────────────────────────────
const SyncConfigList = ({ configs, loading, userId, onRefresh, sourceColor }) => {
  const toast = useToast();
  const [expandedHistory, setExpandedHistory] = useState({});
  const [history, setHistory] = useState({});
  const [loadingHistory, setLoadingHistory] = useState({});
  const [syncedFiles, setSyncedFiles] = useState({});
  const [loadingFiles, setLoadingFiles] = useState({});
  const [activeTab, setActiveTab] = useState({}); // 'runs' | 'files'

  const color = sourceColor || RED;

  const toggleHistory = async (configId) => {
    const isOpen = expandedHistory[configId];
    setExpandedHistory(p => ({ ...p, [configId]: !isOpen }));
    if (!isOpen) {
      // default to 'runs' tab and load runs
      setActiveTab(p => ({ ...p, [configId]: 'runs' }));
      loadRuns(configId);
    }
  };

  const loadRuns = async (configId) => {
    setLoadingHistory(p => ({ ...p, [configId]: true }));
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs/${configId}/history`, { params: { user_id: userId } });
      setHistory(p => ({ ...p, [configId]: res.data.history || [] }));
    } catch { setHistory(p => ({ ...p, [configId]: [] })); }
    finally { setLoadingHistory(p => ({ ...p, [configId]: false })); }
  };

  const loadFiles = async (configId) => {
    if (syncedFiles[configId]) return; // cached
    setLoadingFiles(p => ({ ...p, [configId]: true }));
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs/${configId}/files`, { params: { user_id: userId } });
      setSyncedFiles(p => ({ ...p, [configId]: res.data.files || [] }));
    } catch { setSyncedFiles(p => ({ ...p, [configId]: [] })); }
    finally { setLoadingFiles(p => ({ ...p, [configId]: false })); }
  };

  const switchTab = (configId, tab) => {
    setActiveTab(p => ({ ...p, [configId]: tab }));
    if (tab === 'files') loadFiles(configId);
    if (tab === 'runs') loadRuns(configId);
  };

  const doAction = async (action, configId) => {
    try {
      if (action === 'run') {
        await axios.post(`${API_BASE}/api/sync/configs/${configId}/run`, null, { params: { user_id: userId } });
        toast('Sync triggered — running in background', 'info');
      }
      if (action === 'pause') {
        await axios.put(`${API_BASE}/api/sync/configs/${configId}/pause`, null, { params: { user_id: userId } });
        toast('Sync paused', 'info');
      }
      if (action === 'resume') {
        await axios.put(`${API_BASE}/api/sync/configs/${configId}/resume`, null, { params: { user_id: userId } });
        toast('Sync resumed', 'success');
      }
      if (action === 'delete') {
        if (!window.confirm('Delete this sync?')) return;
        await axios.delete(`${API_BASE}/api/sync/configs/${configId}`, { params: { user_id: userId } });
        toast('Sync config deleted', 'info');
      }
      setTimeout(onRefresh, action === 'run' ? 3500 : 500);
      if (action === 'run') {
        // Refresh history after run completes
        setTimeout(() => {
          setHistory(p => { const n = {...p}; delete n[configId]; return n; });
          setSyncedFiles(p => { const n = {...p}; delete n[configId]; return n; });
          loadRuns(configId);
        }, 5000);
      }
    } catch (e) {
      toast(e.response?.data?.detail || `Action failed: ${action}`, 'error');
    }
  };

  if (loading) return <div className="flex justify-center py-6"><Loader className="w-5 h-5 animate-spin" style={{ color }} /></div>;
  if (!configs || configs.length === 0) return null;

  const schedLabel = (v) => SCHEDULE_OPTIONS.find(o => o.value === v)?.label || v || '—';

  const RUN_STATUS = {
    running:  { label: 'Running',  bg: '#EFF6FF', color: '#3B82F6' },
    success:  { label: 'Success',  bg: '#ECFDF5', color: '#059669' },
    partial:  { label: 'Partial',  bg: '#FFFBEB', color: '#D97706' },
    failed:   { label: 'Failed',   bg: '#FEF2F2', color: '#DC2626' },
    skipped:  { label: 'Skipped',  bg: '#F9FAFB', color: '#6B7280' },
  };

  return (
    <div className="space-y-2 pt-4 border-t" style={{ borderColor: '#E8EAF0' }}>
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: '#9CA3AF' }}>Active Syncs ({configs.length})</p>
        <button onClick={onRefresh} className="p-1 rounded" style={{ color: '#9CA3AF' }}><RefreshCw className="w-3.5 h-3.5" /></button>
      </div>

      {configs.map(cfg => {
        const ss = STATUS_STYLE[cfg.status] || STATUS_STYLE.active;
        const isOpen = expandedHistory[cfg.id];
        const runs = history[cfg.id] || [];

        return (
          <div key={cfg.id} className="rounded-xl border overflow-hidden" style={{ borderColor: isOpen ? `${color}40` : '#E5E7EB' }}>
            <div className="px-4 py-3">
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <p className="text-sm font-semibold truncate" style={{ color: '#1A1A2E' }}>{cfg.display_name}</p>
                    <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full flex-shrink-0" style={{ background: ss.bg, color: ss.color }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: ss.dot }} />{ss.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="flex items-center gap-1 text-xs" style={{ color: '#9CA3AF' }}><Clock className="w-3 h-3" />{schedLabel(cfg.schedule)}</span>
                    <span className="flex items-center gap-1 text-xs" style={{ color: '#9CA3AF' }}><Calendar className="w-3 h-3" />Last: {fmtDate(cfg.last_run_at)}</span>
                    {cfg.files_synced != null && <span className="flex items-center gap-1 text-xs" style={{ color: '#9CA3AF' }}><Database className="w-3 h-3" />{cfg.files_synced} files</span>}
                  </div>
                  {cfg.last_error && <p className="text-xs mt-1 break-words" style={{ color: '#DC2626', maxWidth: '100%', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{fmtError(cfg.last_error)}</p>}
                </div>

                <div className="flex items-center gap-1 flex-shrink-0">
                  <button onClick={() => doAction('run', cfg.id)} className="p-1.5 rounded-lg transition-colors hover:bg-gray-100" title="Sync now" style={{ color }}>
                    <Zap className="w-3.5 h-3.5" />
                  </button>
                  <button onClick={() => toggleHistory(cfg.id)} className="p-1.5 rounded-lg transition-colors hover:bg-gray-100" title="History"
                    style={{ color: isOpen ? color : '#9CA3AF' }}>
                    <Activity className="w-3.5 h-3.5" />
                  </button>
                  {cfg.status === 'paused'
                    ? <button onClick={() => doAction('resume', cfg.id)} className="p-1.5 rounded-lg transition-colors" title="Resume" style={{ color: '#059669' }}><Play className="w-3.5 h-3.5" /></button>
                    : <button onClick={() => doAction('pause', cfg.id)} className="p-1.5 rounded-lg transition-colors" title="Pause" style={{ color: '#9CA3AF' }}><Pause className="w-3.5 h-3.5" /></button>
                  }
                  <button onClick={() => doAction('delete', cfg.id)} className="p-1.5 rounded-lg transition-colors hover:bg-red-50" title="Delete" style={{ color: '#DC2626' }}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            {isOpen && (
              <div className="border-t" style={{ borderColor: '#F0F2F5', background: '#F8F9FB' }}>
                {/* Tab bar */}
                <div className="flex items-center gap-1 px-4 pt-3 pb-0">
                  <div className="flex gap-1 p-0.5 rounded-lg flex-1" style={{ background: '#EBEBEB' }}>
                    {[{ id: 'runs', label: 'Run History' }, { id: 'files', label: 'Synced Files' }].map(tab => (
                      <button key={tab.id} onClick={() => switchTab(cfg.id, tab.id)}
                        className="flex-1 py-1 rounded-md text-xs font-semibold transition-all"
                        style={{ background: (activeTab[cfg.id] || 'runs') === tab.id ? '#fff' : 'transparent', color: (activeTab[cfg.id] || 'runs') === tab.id ? '#1A1A2E' : '#9CA3AF', boxShadow: (activeTab[cfg.id] || 'runs') === tab.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none' }}>
                        {tab.label}
                      </button>
                    ))}
                  </div>
                  <button onClick={() => (activeTab[cfg.id] || 'runs') === 'runs' ? loadRuns(cfg.id) : loadFiles(cfg.id)}
                    className="p-1.5 rounded-lg ml-1 flex-shrink-0" style={{ color: '#9CA3AF' }}>
                    <RefreshCw className="w-3 h-3" />
                  </button>
                </div>

                {/* Runs tab */}
                {(activeTab[cfg.id] || 'runs') === 'runs' && (
                  <div className="px-4 py-3 space-y-2">
                    {loadingHistory[cfg.id] ? (
                      <div className="flex items-center gap-2 justify-center py-5">
                        <Loader className="w-4 h-4 animate-spin" style={{ color }} />
                        <span className="text-xs" style={{ color: '#9CA3AF' }}>Loading runs…</span>
                      </div>
                    ) : (runs || []).length === 0 ? (
                      <div className="flex flex-col items-center py-5">
                        <Activity className="w-7 h-7 mb-2 opacity-20" style={{ color: '#9CA3AF' }} />
                        <p className="text-xs" style={{ color: '#9CA3AF' }}>No runs yet — click ⚡ to sync now</p>
                      </div>
                    ) : (runs || []).map((run, i) => {
                      const rs = RUN_STATUS[run.status] || RUN_STATUS.skipped;
                      const started = run.started_at ? new Date(run.started_at) : null;
                      const dateStr = started ? started.toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';
                      return (
                        <div key={i} className="rounded-xl border overflow-hidden" style={{ background: '#fff', borderColor: '#E5E7EB' }}>
                          <div className="flex items-center gap-2 px-3 py-2.5">
                            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: rs.color }} />
                            <span className="text-xs font-semibold" style={{ color: rs.color }}>{rs.label}</span>
                            <span className="text-xs" style={{ color: '#9CA3AF' }}>{dateStr}</span>
                            <div className="ml-auto flex items-center gap-2">
                              <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: '#F3F4F6', color: '#9CA3AF' }}>
                                {run.trigger === 'manual' ? '👆 manual' : '⏰ auto'}
                              </span>
                              {run.duration_s != null && <span className="text-xs" style={{ color: '#9CA3AF' }}>{run.duration_s}s</span>}
                            </div>
                          </div>
                          {(run.files_synced > 0 || run.files_failed > 0 || run.files_skipped > 0) && (
                            <div className="flex items-center gap-4 px-3 py-2 border-t" style={{ borderColor: '#F3F4F6', background: '#FAFBFC' }}>
                              {run.files_synced > 0 && <span className="text-xs font-semibold flex items-center gap-1" style={{ color: '#059669' }}><span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: '#059669' }} />{run.files_synced} synced</span>}
                              {run.files_skipped > 0 && <span className="text-xs flex items-center gap-1" style={{ color: '#D97706' }}><span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: '#D97706' }} />{run.files_skipped} skipped</span>}
                              {run.files_failed > 0 && <span className="text-xs flex items-center gap-1" style={{ color: '#DC2626' }}><span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: '#DC2626' }} />{run.files_failed} failed</span>}
                            </div>
                          )}
                          {run.error && (
                            <div className="px-3 py-2 border-t" style={{ borderColor: '#FEE2E2', background: '#FEF2F2' }}>
                              <p className="text-xs" style={{ color: '#DC2626' }}>{fmtError(run.error)}</p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Files tab */}
                {(activeTab[cfg.id] || 'runs') === 'files' && (
                  <div className="px-4 py-3">
                    {loadingFiles[cfg.id] ? (
                      <div className="flex items-center gap-2 justify-center py-5">
                        <Loader className="w-4 h-4 animate-spin" style={{ color }} />
                        <span className="text-xs" style={{ color: '#9CA3AF' }}>Loading files…</span>
                      </div>
                    ) : (syncedFiles[cfg.id] || []).length === 0 ? (
                      <div className="flex flex-col items-center py-5">
                        <FileText className="w-7 h-7 mb-2 opacity-20" style={{ color: '#9CA3AF' }} />
                        <p className="text-xs" style={{ color: '#9CA3AF' }}>No files synced yet</p>
                      </div>
                    ) : (
                      <div className="space-y-1 max-h-56 overflow-y-auto">
                        {(syncedFiles[cfg.id] || []).map((f, i) => {
                          const filename = f.s3_key ? f.s3_key.split('/').pop() : f.source_file_id;
                          const statusColor = f.status === 'synced' ? '#059669' : f.status === 'failed' ? '#DC2626' : '#D97706';
                          return (
                            <div key={i} className="flex items-center gap-2.5 px-3 py-2 rounded-lg" style={{ background: '#fff', border: '1px solid #F3F4F6' }}>
                              <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: statusColor }} />
                              <FileText className="w-3.5 h-3.5 flex-shrink-0" style={{ color: '#9CA3AF' }} />
                              <span className="text-xs flex-1 truncate font-medium" style={{ color: '#374151' }}>{filename}</span>
                              <span className="text-xs flex-shrink-0" style={{ color: statusColor }}>{f.status}</span>
                              {f.last_synced_at && (
                                <span className="text-xs flex-shrink-0" style={{ color: '#C4C9D4' }}>
                                  {new Date(f.last_synced_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                </span>
                              )}
                            </div>
                          );
                        })}
                        <p className="text-xs text-center pt-1" style={{ color: '#C4C9D4' }}>{(syncedFiles[cfg.id] || []).length} file{(syncedFiles[cfg.id] || []).length !== 1 ? 's' : ''} total</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

// ── Main Upload Page ──────────────────────────────────────────────────────────
const Upload = () => {
  const { user } = useAuth();
  const [activeSource, setActiveSource] = useState('web');
  const active = SOURCES.find(s => s.id === activeSource) || SOURCES[0];

  const subtitles = {
    web:        'Upload a file directly from your computer',
    drive:      `Browsing as ${user?.email || '…'}`,
    s3:         'Configure S3 credentials to schedule sync',
    confluence: 'Connect Confluence and schedule space sync',
  };

  return (
    <>
      <style>{`@keyframes indeterminate { 0% { transform: translateX(-100%); } 50% { transform: translateX(0%); } 100% { transform: translateX(100%); } }`}</style>

      {/* Page header */}
      <div className="flex items-center justify-between px-6 py-4 bg-white border-b" style={{ borderColor: '#E8EAF0', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
        <div>
          <h1 className="text-lg font-bold" style={{ color: '#1A1A2E' }}>Document Ingestion</h1>
          <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>Upload or sync documents into the Knowledge Base from any source</p>
        </div>
      </div>

      <div className="flex gap-5 p-6" style={{ background: '#F8F9FB', minHeight: 'calc(100vh - 73px)' }}>
        {/* Left sidebar */}
        <div className="w-56 flex-shrink-0 space-y-2.5">
          <p className="text-xs font-semibold uppercase tracking-widest px-1 mb-3" style={{ color: '#C4C9D4' }}>Select Source</p>
          {SOURCES.map(s => (
            <SourceTab key={s.id} source={s} active={activeSource === s.id} onClick={() => setActiveSource(s.id)} />
          ))}
        </div>

        {/* Right content */}
        <Card className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <div className="flex items-center gap-4 px-6 py-4 border-b" style={{ borderColor: '#F0F2F5', background: `linear-gradient(135deg, ${active.bg} 0%, #ffffff 60%)` }}>
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0"
              style={{ background: '#fff', boxShadow: `0 2px 12px ${active.color}30`, border: `1px solid ${active.color}20` }}>
              <active.Icon />
            </div>
            <div className="flex-1">
              <h2 className="text-base font-bold" style={{ color: '#1A1A2E' }}>{active.label}</h2>
              <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>{subtitles[activeSource]}</p>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
              style={{ background: active.bg, color: active.color, border: `1px solid ${active.color}30` }}>
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: active.color }} />
              {activeSource === 'web' ? 'One-time upload' : 'Scheduled sync'}
            </div>
          </div>
          <div className="flex-1 p-6 overflow-y-auto">
            {activeSource === 'web'        && <WebUploadTab />}
            {activeSource === 'drive'      && <DriveTab />}
            {activeSource === 's3'         && <S3SyncTab userId={user?.id || user?.email} />}
            {activeSource === 'confluence' && <ConfluenceSyncTab userId={user?.id || user?.email} />}
          </div>
        </Card>
      </div>
    </>
  );
};

export default Upload;
