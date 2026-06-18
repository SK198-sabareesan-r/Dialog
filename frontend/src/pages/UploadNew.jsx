import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Upload as UploadIcon, File, Loader, CheckCircle, FileText,
  Image, FileSpreadsheet, AlertTriangle, Info, X,
  FolderOpen, Folder, ChevronRight, Home, RefreshCw,
  Link2, Clock, Database, Calendar, Play, Pause,
  Trash2, Plus, RotateCcw, Activity, Zap, Settings,
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const RED = '#E4002B';
const MAX_FILE_SIZE = 500 * 1024 * 1024;

// ── Brand icons ───────────────────────────────────────────────────────────────
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
  <svg viewBox="0 0 80 80" className="w-5 h-5">
    <path d="M40 4L8 16v48l32 12 32-12V16z" fill="#E25444"/>
    <path d="M40 4v72l32-12V16z" fill="#C9271B"/>
    <ellipse cx="40" cy="16" rx="32" ry="8" fill="#F2A58E"/>
    <ellipse cx="40" cy="40" rx="32" ry="8" fill="#F2A58E" opacity=".5"/>
  </svg>
);

const IconConfluence = () => (
  <svg viewBox="0 0 496 512" className="w-5 h-5">
    <path d="M38.6 270.6c-5.8 9.4-11.6 20.3-16.2 28.5-4.4 7.8-1.6 17.6 6.1 22.1l102.9 59.4c7.7 4.4 17.5 1.7 22-6 4-7 9.3-16.2 15.1-26 20.8-34.6 41.9-30.3 79.7-12.6l102.1 46.8c8.3 3.8 18 .1 21.8-8.2l46.2-100.5c3.8-8.3.1-18-8.2-21.8-16.3-7.5-48.8-22.4-79.5-36.5-117.1-54-217.7-45.9-292 54.8zm419.9-29.2c5.8-9.4 11.6-20.3 16.2-28.5 4.4-7.8 1.6-17.6-6.1-22.1L365.7 131.4c-7.7-4.4-17.5-1.7-22 6-4 7-9.3 16.2-15.1 26-20.8 34.6-41.9 30.3-79.7 12.6L146.8 129.2c-8.3-3.8-18-.1-21.8 8.2L78.8 238c-3.8 8.3-.1 18 8.2 21.8 16.3 7.5 48.8 22.4 79.5 36.5 117.2 53.9 217.8 45.8 292-54.9z" fill="url(#cg)"/>
    <defs><linearGradient id="cg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stopColor="#2684FF"/><stop offset="100%" stopColor="#0052CC"/></linearGradient></defs>
  </svg>
);

// ── Config ────────────────────────────────────────────────────────────────────
const SOURCES = [
  { id: 'web',        label: 'Local Upload',  desc: 'Drag & drop or browse',     color: RED,       bg: '#FFF1F3', Icon: () => <UploadIcon className="w-5 h-5" style={{color:RED}} /> },
  { id: 'drive',      label: 'Google Drive',  desc: 'Sync from My Drive',        color: '#4285F4', bg: '#EFF6FF', Icon: IconGoogleDrive },
  { id: 's3',         label: 'AWS S3',        desc: 'Sync from S3 bucket',       color: '#E25444', bg: '#FFF5F3', Icon: IconS3 },
  { id: 'confluence', label: 'Confluence',    desc: 'Sync from spaces',          color: '#0052CC', bg: '#EFF6FF', Icon: IconConfluence },
];

const SCHEDULE_OPTIONS = [
  { value: '2m',     label: 'Every 2 min',  cron: '*/2 * * * *' },
  { value: '5m',     label: 'Every 5 min',  cron: '*/5 * * * *' },
  { value: 'hourly', label: 'Every hour',   cron: '0 * * * *'   },
  { value: '6h',     label: 'Every 6h',     cron: '0 */6 * * *' },
  { value: '12h',    label: 'Every 12h',    cron: '0 */12 * * *'},
  { value: 'daily',  label: 'Daily',        cron: '0 9 * * *'   },
  { value: 'weekly', label: 'Weekly',       cron: '0 9 * * 1'   },
];

const SYNC_STATUS_CONFIG = {
  STARTING:    { label: 'Starting…',     color: '#D97706', bg: '#FFFBEB', pulse: true  },
  IN_PROGRESS: { label: 'Indexing…',     color: '#3B82F6', bg: '#EFF6FF', pulse: true  },
  COMPLETE:    { label: 'Indexed ✓',     color: '#059669', bg: '#ECFDF5', pulse: false },
  FAILED:      { label: 'Failed',        color: '#DC2626', bg: '#FEF2F2', pulse: false },
  STOPPED:     { label: 'Stopped',       color: '#6B7280', bg: '#F9FAFB', pulse: false },
  PENDING:     { label: 'Waiting…',      color: '#D97706', bg: '#FFFBEB', pulse: true  },
};

const STATUS_STYLE = {
  active: { label: 'Active',  bg: '#ECFDF5', color: '#059669', dot: '#059669' },
  paused: { label: 'Paused',  bg: '#F9FAFB', color: '#6B7280', dot: '#9CA3AF' },
  error:  { label: 'Error',   bg: '#FEF2F2', color: '#DC2626', dot: '#DC2626' },
};

const SOURCE_COLORS = { gdrive: '#4285F4', confluence: '#0052CC', s3: '#E25444' };
const SOURCE_ICONS  = { gdrive: IconGoogleDrive, confluence: IconConfluence, s3: IconS3 };
const SOURCE_LABELS = { gdrive: 'Google Drive', confluence: 'Confluence', s3: 'AWS S3' };

const fmt = (b) => !b ? '—' : b < 1024 ? `${b} B` : b < 1048576 ? `${(b/1024).toFixed(0)} KB` : `${(b/1048576).toFixed(1)} MB`;
const fmtDate = (iso) => !iso ? 'Never' : new Date(iso).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
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
  <button onClick={onClick} className="flex items-center gap-3 px-4 py-3 rounded-xl border-2 transition-all w-full text-left"
    style={{ borderColor: active ? source.color : '#E8EAF0', background: active ? source.bg : '#fff', boxShadow: active ? `0 2px 8px ${source.color}18` : 'none' }}>
    <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
      style={{ background: active ? '#fff' : source.bg, boxShadow: active ? `0 1px 4px ${source.color}20` : 'none' }}>
      <source.Icon />
    </div>
    <div className="min-w-0">
      <p className="text-sm font-semibold truncate" style={{ color: active ? source.color : '#374151' }}>{source.label}</p>
      <p className="text-xs truncate" style={{ color: '#9CA3AF' }}>{source.desc}</p>
    </div>
    {active && <div className="w-2 h-2 rounded-full ml-auto flex-shrink-0" style={{ background: source.color }} />}
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

const Input = ({ type = 'text', value, onChange, placeholder, className = '' }) => (
  <input type={type} value={value} onChange={onChange} placeholder={placeholder}
    className={`w-full px-3 py-2.5 border rounded-xl text-sm transition-all focus:outline-none ${className}`}
    style={{ borderColor: '#E5E7EB' }}
    onFocus={e => e.target.style.borderColor = RED}
    onBlur={e => e.target.style.borderColor = '#E5E7EB'} />
);

const Btn = ({ onClick, disabled, color = RED, children, outline, className = '', style = {} }) => (
  <button onClick={onClick} disabled={disabled} className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${className}`}
    style={{ background: disabled ? '#E5E7EB' : outline ? 'transparent' : color, color: disabled ? '#9CA3AF' : outline ? color : '#fff', border: outline ? `2px solid ${color}` : 'none', cursor: disabled ? 'not-allowed' : 'pointer', ...style }}>
    {children}
  </button>
);

const Alert = ({ type = 'error', children }) => {
  const styles = { error: { bg: '#FEF2F2', border: '#FECACA', color: '#DC2626', Icon: AlertTriangle }, success: { bg: '#ECFDF5', border: '#A7F3D0', color: '#059669', Icon: CheckCircle }, info: { bg: '#EFF6FF', border: '#BFDBFE', color: '#2563EB', Icon: Info } };
  const s = styles[type];
  return (
    <div className="flex items-start gap-2.5 p-3 rounded-xl border" style={{ background: s.bg, borderColor: s.border }}>
      <s.Icon className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: s.color }} />
      <p className="text-xs" style={{ color: s.color }}>{children}</p>
    </div>
  );
};

// ── KB Ingestion Status ───────────────────────────────────────────────────────
const KBStatusCard = ({ s3Key }) => {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('PENDING');
  const [stats, setStats] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef(null);
  const startRef = useRef(Date.now());

  useEffect(() => {
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let stopped = false;
    const poll = async (id) => {
      try {
        const r = await axios.get(`${API_BASE}/api/upload/sync-status/${id}`, { timeout: 10000 });
        if (stopped) return;
        setStatus(r.data.status); setStats(r.data);
        if (['COMPLETE','FAILED','STOPPED'].includes(r.data.status)) clearInterval(intervalRef.current);
      } catch { clearInterval(intervalRef.current); }
    };
    const fetchJob = async () => {
      try {
        const r = await axios.get(`${API_BASE}/api/kb/sync/latest`, { timeout: 10000 });
        if (stopped || !r.data?.ingestion_job_id) return;
        setJobId(r.data.ingestion_job_id); setStatus(r.data.status || 'STARTING');
        intervalRef.current = setInterval(() => poll(r.data.ingestion_job_id), 8000);
        poll(r.data.ingestion_job_id);
      } catch {}
    };
    const t = setTimeout(fetchJob, 2000);
    return () => { stopped = true; clearTimeout(t); clearInterval(intervalRef.current); };
  }, [s3Key]);

  const cfg = SYNC_STATUS_CONFIG[status] || SYNC_STATUS_CONFIG.PENDING;
  const fmtE = (s) => s < 60 ? `${s}s` : `${Math.floor(s/60)}m ${s%60}s`;

  return (
    <div className="rounded-xl p-4 border-l-4" style={{ background: cfg.bg, borderLeftColor: cfg.color, borderTop: `1px solid ${cfg.color}30`, borderRight: `1px solid ${cfg.color}30`, borderBottom: `1px solid ${cfg.color}30` }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4" style={{ color: cfg.color }} />
          <span className="text-xs font-semibold" style={{ color: cfg.color }}>KB Ingestion</span>
          {cfg.pulse && <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: cfg.color }} />}
        </div>
        <span className="text-xs flex items-center gap-1" style={{ color: '#9CA3AF' }}><Clock className="w-3 h-3" />{fmtE(elapsed)}</span>
      </div>
      <p className="text-sm font-medium" style={{ color: '#1A1A2E' }}>{cfg.label}</p>
      <p className="text-xs font-mono mt-1 truncate" style={{ color: '#9CA3AF' }}>{s3Key}</p>
      {cfg.pulse && <div className="h-1 mt-3 rounded-full overflow-hidden" style={{ background: '#E5E7EB' }}><div className="h-full rounded-full" style={{ background: cfg.color, width: '40%', animation: 'indeterminate 1.5s ease-in-out infinite' }} /></div>}
      {stats?.status === 'COMPLETE' && (
        <div className="grid grid-cols-3 gap-2 mt-3">
          {[['Scanned', stats.documents_scanned], ['Indexed', stats.new_documents_indexed], ['Failed', stats.documents_failed]].map(([l,v]) => (
            <div key={l} className="rounded-lg p-2 text-center" style={{ background: 'rgba(255,255,255,0.8)' }}>
              <p className="text-base font-bold" style={{ color: '#1A1A2E' }}>{v ?? '—'}</p>
              <p className="text-xs" style={{ color: '#9CA3AF' }}>{l}</p>
            </div>
          ))}
        </div>
      )}
      {jobId && <p className="text-xs mt-2 font-mono" style={{ color: '#C4C9D4' }}>Job: {jobId}</p>}
    </div>
  );
};

// ── Local Upload Tab ──────────────────────────────────────────────────────────
const WebUploadTab = () => {
  const { user } = useAuth();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);

  const pick = (f) => {
    setResult(null); setError(null); setProgress(0);
    if (!f) return;
    if (f.size > MAX_FILE_SIZE) { setError('File exceeds 500 MB limit'); return; }
    setFile(f);
  };

  const upload = async () => {
    if (!file) return;
    setUploading(true); setError(null); setResult(null); setProgress(0);
    try {
      const fd = new FormData();
      fd.append('file', file); fd.append('user_id', user?.email || 'guest');
      const res = await axios.post(`${API_BASE}/api/upload/direct`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000,
        onUploadProgress: e => setProgress(Math.round(e.loaded * 100 / e.total)),
      });
      setResult(res.data); setFile(null); setProgress(0);
    } catch (e) { setError(e.response?.data?.detail || e.message || 'Upload failed'); }
    finally { setUploading(false); }
  };

  const FileIcon = file ? getFileIcon(file.name) : UploadIcon;

  return (
    <div className="space-y-4">
      <div onDrop={e => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files[0]); }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
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
              <div className="w-full max-w-xs mb-3">
                <div className="h-2 rounded-full" style={{ background: '#E5E7EB' }}>
                  <div className="h-full rounded-full transition-all" style={{ background: RED, width: `${progress}%` }} />
                </div>
              </div>
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
                accept=".pdf,.doc,.docx,.txt,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.gif,.webp,.mp4,.mp3,.wav" />
            </label>
            <p className="text-xs mt-4" style={{ color: '#C4C9D4' }}>PDF · DOCX · XLSX · Images · MP4 · MP3 — Max 500 MB</p>
          </div>
        )}
      </div>

      <Btn onClick={upload} disabled={!file || uploading} color={RED} style={{ width: '100%', padding: '12px' }}>
        {uploading ? <><Loader className="w-5 h-5 animate-spin" />Uploading {progress}%</> : <><UploadIcon className="w-5 h-5" />Upload & Ingest</>}
      </Btn>

      {result && <Alert type="success">Uploaded successfully — {result.message || 'Ingestion running in background'}</Alert>}
      {error && <Alert type="error">{error}</Alert>}
      {result?.s3_key && <KBStatusCard s3Key={result.s3_key} />}
    </div>
  );
};

// ── File browser shared ───────────────────────────────────────────────────────
const FileBrowserRow = ({ item, isFolder, selected, onSelect, onOpen }) => {
  const Icon = isFolder ? Folder : getFileIcon(item.name);
  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b transition-colors hover:bg-gray-50"
      style={{ borderColor: '#F3F4F6', background: selected ? `${RED}06` : '' }}>
      {!isFolder && <input type="checkbox" checked={selected} onChange={onSelect} className="flex-shrink-0 w-4 h-4 cursor-pointer" style={{ accentColor: RED }} />}
      {isFolder && <div className="w-4 flex-shrink-0" />}
      <Icon className="w-4 h-4 flex-shrink-0" style={{ color: isFolder ? '#F7941D' : '#9CA3AF' }} />
      <span className="flex-1 text-sm truncate" style={{ color: '#1A1A2E', fontWeight: isFolder ? 500 : 400, cursor: isFolder ? 'pointer' : 'default' }} onClick={isFolder ? onOpen : undefined}>
        {item.name}
      </span>
      {isFolder && <button onClick={onOpen} className="text-xs px-2 py-1 rounded-lg flex items-center gap-1" style={{ color: RED, background: `${RED}10` }}>Open <ChevronRight className="w-3 h-3" /></button>}
      {!isFolder && <span className="text-xs flex-shrink-0" style={{ color: '#C4C9D4' }}>{fmt(item.size || item.Size)}</span>}
    </div>
  );
};

const Breadcrumb = ({ crumbs, onNavigate }) => (
  <div className="flex items-center gap-1 flex-wrap px-3 py-2">
    {crumbs.map((c, i) => (
      <React.Fragment key={c.id || c.prefix || i}>
        {i > 0 && <ChevronRight className="w-3 h-3 flex-shrink-0" style={{ color: '#D1D5DB' }} />}
        <button onClick={() => onNavigate(i)} className="flex items-center gap-1 text-xs font-medium rounded px-1.5 py-0.5 transition-colors"
          style={{ color: i === crumbs.length-1 ? '#374151' : RED, cursor: i === crumbs.length-1 ? 'default' : 'pointer', background: i === crumbs.length-1 ? '#F3F4F6' : 'transparent' }}>
          {i === 0 && <Home className="w-3 h-3" />}{c.name}
        </button>
      </React.Fragment>
    ))}
  </div>
);

const ImportBar = ({ count, total, onSelectAll, onClear, onImport, importing }) => (
  <div className="flex items-center justify-between px-4 py-3 rounded-xl" style={{ background: count > 0 ? `${RED}08` : '#F9FAFB', border: `1px solid ${count > 0 ? `${RED}25` : '#E5E7EB'}` }}>
    <div className="flex items-center gap-3">
      <span className="text-sm font-semibold" style={{ color: count > 0 ? RED : '#9CA3AF' }}>{count > 0 ? `${count} selected` : 'No files selected'}</span>
      {total > 0 && <><button onClick={onSelectAll} className="text-xs underline" style={{ color: RED }}>All ({total})</button>{count > 0 && <button onClick={onClear} className="text-xs underline" style={{ color: '#6B7280' }}>Clear</button>}</>}
    </div>
    <Btn onClick={onImport} disabled={count === 0 || importing} color={RED}>
      {importing ? <Loader className="w-4 h-4 animate-spin" /> : <UploadIcon className="w-4 h-4" />}
      {importing ? 'Importing…' : `Import${count > 0 ? ` ${count}` : ''}`}
    </Btn>
  </div>
);

// ── Google Drive Tab — folder picker for sync + file import ──────────────────
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

  // Sync state
  const [syncName, setSyncName] = useState('');
  const [schedule, setSchedule] = useState('daily');
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [saving, setSaving] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState('');
  const [syncConfigs, setSyncConfigs] = useState([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);

  // View mode: 'mydrive' | 'shared'
  const [viewMode, setViewMode] = useState('mydrive');
  const [sharedFolders, setSharedFolders] = useState([]);
  const [loadingShared, setLoadingShared] = useState(false);

  const userId = user?.id || user?.email;
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

  const currentFolderId = crumbs[crumbs.length - 1]?.id || 'root';

  const fetchConfigs = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs`, { params: { user_id: userId } });
      setSyncConfigs((res.data.configs || []).filter(c => c.source_type === 'gdrive'));
    } catch { setSyncConfigs([]); } finally { setLoadingConfigs(false); }
  }, [userId]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const fetchSharedFolders = useCallback(async () => {
    if (!liveToken) return;
    setLoadingShared(true);
    try {
      const res = await withRetry(t =>
        axios.get(`${API_BASE}/api/google-drive/shared-with-me`, { params: { google_access_token: t } })
      );
      setSharedFolders(res.data.folders || []);
    } catch { setSharedFolders([]); }
    finally { setLoadingShared(false); }
  }, [liveToken, withRetry]);

  useEffect(() => {
    if (viewMode === 'shared' && liveToken) fetchSharedFolders();
  }, [viewMode, liveToken, fetchSharedFolders]);

  useEffect(() => {
    if (!liveToken) return;
    withRetry(t => axios.get(`${API_BASE}/api/google-drive/shared-drives`, { params: { google_access_token: t } }))
      .then(r => setDrives(r.data.shared_drives || [])).catch(() => {});
  }, [liveToken]);

  const browse = useCallback(async (folderId, driveId) => {
    setLoading(true); setError(null);
    try {
      const res = await withRetry(t => axios.get(`${API_BASE}/api/google-drive/browse`, {
        params: { google_access_token: t, folder_id: folderId, ...(driveId ? { drive_id: driveId } : {}) }
      }));
      setFolders(res.data.folders); setFiles(res.data.files);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load folder'); }
    finally { setLoading(false); }
  }, [withRetry]);

  useEffect(() => {
    if (!liveToken) return;
    const rootName = selectedDriveId ? (drives.find(d => d.id === selectedDriveId)?.name || 'Shared Drive') : 'My Drive';
    setCrumbs([{ id: selectedDriveId || 'root', name: rootName }]);
    setSelectedFolder(null);
    browse(selectedDriveId || 'root', selectedDriveId || undefined);
  }, [selectedDriveId, liveToken]);

  const openFolder = (f) => {
    setCrumbs(p => [...p, { id: f.id, name: f.name }]);
    browse(f.id, selectedDriveId || undefined);
  };
  const navTo = (i) => {
    const nc = crumbs.slice(0, i + 1);
    setCrumbs(nc);
    browse(nc[nc.length - 1].id, selectedDriveId || undefined);
  };

  const handleSelectFolder = (f) => {
    setSelectedFolder(f);
    setSyncName(`${f.name} Sync`);
    setSyncSuccess('');
    setError(null);
  };

  const handleSelectCurrentFolder = () => {
    const current = crumbs[crumbs.length - 1];
    // don't select root — require explicit folder
    if (current.id === 'root' || current.id === selectedDriveId) {
      setSelectedFolder({ id: current.id, name: current.name, isRoot: true });
      setSyncName(`My Drive Sync`);
    } else {
      setSelectedFolder({ id: current.id, name: current.name });
      setSyncName(`${current.name} Sync`);
    }
    setSyncSuccess(''); setError(null);
  };

  const handleSaveSync = async () => {
    if (!syncName.trim()) { setError('Give this sync a name'); return; }
    if (!selectedFolder) { setError('Select a folder to sync'); return; }
    setSaving(true); setError(null); setSyncSuccess('');
    try {
      await axios.post(`${API_BASE}/api/sync/configs`, {
        user_id: userId,
        source_type: 'gdrive',
        display_name: syncName,
        credentials: { access_token: liveToken, drive_id: selectedDriveId || null },
        schedule,
        space_or_path: selectedFolder.id,
      });
      setSyncSuccess(`"${selectedFolder.name}" scheduled for sync!`);
      setSelectedFolder(null); setSyncName('');
      fetchConfigs();
    } catch (e) { setError(e.response?.data?.detail || 'Failed to save'); }
    finally { setSaving(false); }
  };

  if (!liveToken) return <Alert type="error">Google Drive session expired — sign out and sign back in to restore access.</Alert>;

  return (
    <div className="space-y-4">

      {/* Connected banner */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl border" style={{ background: '#EFF6FF', borderColor: '#BFDBFE' }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: '#fff' }}><IconGoogleDrive /></div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Google Drive connected</p>
          <p className="text-xs truncate" style={{ color: '#9CA3AF' }}>{user?.email}</p>
        </div>
        <CheckCircle className="w-4 h-4 flex-shrink-0" style={{ color: '#4285F4' }} />
      </div>

      {/* View mode switcher */}
      <div className="flex gap-1 p-1 rounded-xl" style={{ background: '#F3F4F6' }}>
        {[
          { id: 'mydrive', label: 'My Drive' },
          { id: 'shared',  label: 'Shared with me' },
        ].map(v => (
          <button key={v.id} onClick={() => { setViewMode(v.id); setSelectedFolder(null); setSyncSuccess(''); }}
            className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all"
            style={{ background: viewMode === v.id ? '#fff' : 'transparent', color: viewMode === v.id ? '#1A1A2E' : '#9CA3AF', boxShadow: viewMode === v.id ? '0 1px 3px rgba(0,0,0,0.08)' : 'none' }}>
            {v.label}
          </button>
        ))}
      </div>

      {viewMode === 'mydrive' && drives.length > 0 && (
        <Field label="Drive">
          <select value={selectedDriveId} onChange={e => setSelectedDriveId(e.target.value)}
            className="w-full px-3 py-2.5 border rounded-xl text-sm focus:outline-none" style={{ borderColor: '#E5E7EB' }}>
            <option value="">My Drive (personal)</option>
            {drives.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </Field>
      )}

      {/* Folder browser with sync select */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: '#9CA3AF' }}>Browse & Select Folder to Sync</p>
          {viewMode === 'mydrive' && (
            <button onClick={handleSelectCurrentFolder}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-semibold transition-all"
              style={{ background: '#EFF6FF', color: '#4285F4', border: '1px solid #BFDBFE' }}>
              <Folder className="w-3 h-3" /> Sync current folder
            </button>
          )}
        </div>

        <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E8EAF0' }}>
          {viewMode === 'shared' ? (
            // ── Shared with me ──
            <>
              <div className="px-4 py-2.5 border-b flex items-center justify-between" style={{ borderColor: '#E8EAF0', background: '#FAFBFC' }}>
                <p className="text-xs font-medium" style={{ color: '#374151' }}>Folders shared with {user?.email}</p>
                <button onClick={fetchSharedFolders} disabled={loadingShared} className="p-1.5 rounded-lg" style={{ color: '#9CA3AF' }}>
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingShared ? 'animate-spin' : ''}`} />
                </button>
              </div>
              <div style={{ maxHeight: 280, overflowY: 'auto' }}>
                {loadingShared ? (
                  <div className="flex items-center justify-center py-10">
                    <Loader className="w-5 h-5 animate-spin" style={{ color: '#4285F4' }} />
                    <span className="ml-2 text-sm" style={{ color: '#9CA3AF' }}>Loading shared folders…</span>
                  </div>
                ) : sharedFolders.length === 0 ? (
                  <div className="flex flex-col items-center py-10" style={{ color: '#D1D5DB' }}>
                    <FolderOpen className="w-8 h-8 mb-2" />
                    <p className="text-sm">No folders shared with you</p>
                    <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>Ask others to share their folders with {user?.email}</p>
                  </div>
                ) : (
                  sharedFolders.map(f => (
                    <div key={f.id}
                      className="flex items-center gap-3 px-4 py-3 border-b transition-all cursor-pointer"
                      style={{ borderColor: '#F3F4F6', background: selectedFolder?.id === f.id ? '#EFF6FF' : 'transparent' }}
                      onClick={() => handleSelectFolder(f)}>
                      <Folder className="w-4 h-4 flex-shrink-0" style={{ color: selectedFolder?.id === f.id ? '#4285F4' : '#F7941D' }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: selectedFolder?.id === f.id ? '#4285F4' : '#1A1A2E' }}>{f.name}</p>
                        <p className="text-xs truncate" style={{ color: '#9CA3AF' }}>
                          {f.shared_by ? `Shared by ${f.shared_by}` : f.owner ? `Owner: ${f.owner}` : ''}
                          {f.owner_email ? ` (${f.owner_email})` : ''}
                        </p>
                      </div>
                      {selectedFolder?.id === f.id && (
                        <span className="text-xs px-2 py-0.5 rounded-full font-semibold flex-shrink-0" style={{ background: '#4285F4', color: '#fff' }}>Selected</span>
                      )}
                    </div>
                  ))
                )}
              </div>
            </>
          ) : (
            // ── My Drive browser ──
            <>
              <div className="flex items-center justify-between border-b" style={{ borderColor: '#E8EAF0', background: '#FAFBFC' }}>
                <Breadcrumb crumbs={crumbs} onNavigate={navTo} />
                <button onClick={() => browse(currentFolderId, selectedDriveId || undefined)} disabled={loading} className="p-2 mr-1 rounded-lg" style={{ color: '#9CA3AF' }}>
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
              <div style={{ maxHeight: 280, overflowY: 'auto' }}>
                {loading ? (
                  <div className="flex items-center justify-center py-10">
                    <Loader className="w-5 h-5 animate-spin" style={{ color: '#4285F4' }} />
                    <span className="ml-2 text-sm" style={{ color: '#9CA3AF' }}>Loading…</span>
                  </div>
                ) : folders.length === 0 && files.length === 0 ? (
                  <div className="flex flex-col items-center py-10" style={{ color: '#D1D5DB' }}>
                    <FolderOpen className="w-8 h-8 mb-2" /><p className="text-sm">Empty folder</p>
                  </div>
                ) : (
                  <div>
                    {folders.map(f => (
                      <div key={f.id}
                        className="flex items-center gap-3 px-4 py-2.5 border-b transition-all cursor-pointer"
                        style={{ borderColor: '#F3F4F6', background: selectedFolder?.id === f.id ? '#EFF6FF' : 'transparent' }}
                        onClick={() => handleSelectFolder(f)}>
                        <Folder className="w-4 h-4 flex-shrink-0" style={{ color: selectedFolder?.id === f.id ? '#4285F4' : '#F7941D' }} />
                        <span className="flex-1 text-sm font-medium truncate" style={{ color: selectedFolder?.id === f.id ? '#4285F4' : '#1A1A2E' }}>{f.name}</span>
                        <div className="flex items-center gap-2">
                          {selectedFolder?.id === f.id && (
                            <span className="text-xs px-2 py-0.5 rounded-full font-semibold" style={{ background: '#4285F4', color: '#fff' }}>Selected</span>
                          )}
                          <button onClick={e => { e.stopPropagation(); openFolder(f); }}
                            className="text-xs px-2 py-1 rounded-lg flex items-center gap-1 flex-shrink-0"
                            style={{ color: '#9CA3AF', background: '#F3F4F6' }}>
                            Open <ChevronRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))}
                    {files.length > 0 && (
                      <div className="px-4 py-2 border-t" style={{ borderColor: '#F3F4F6', background: '#FAFBFC' }}>
                        <p className="text-xs" style={{ color: '#9CA3AF' }}>{files.length} file{files.length !== 1 ? 's' : ''} in this folder — syncing includes all files</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      {selectedFolder && (
        <div className="p-4 rounded-xl border-2 space-y-4" style={{ borderColor: '#4285F4', background: '#F8FBFF' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: '#EFF6FF' }}>
              <Folder className="w-5 h-5" style={{ color: '#4285F4' }} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold" style={{ color: '#1A1A2E' }}>{selectedFolder.name}</p>
              <p className="text-xs" style={{ color: '#9CA3AF' }}>Selected for sync</p>
            </div>
            <button onClick={() => { setSelectedFolder(null); setSyncName(''); }} style={{ color: '#9CA3AF' }}>
              <X className="w-4 h-4" />
            </button>
          </div>

          <Field label="Sync Name" required>
            <Input value={syncName} onChange={e => setSyncName(e.target.value)} placeholder="e.g. HR Google Drive" />
          </Field>

          <Field label="Schedule">
            <div className="grid grid-cols-4 gap-2">
              {SCHEDULE_OPTIONS.map(o => (
                <button key={o.value} onClick={() => setSchedule(o.value)}
                  className="px-2 py-2 rounded-xl text-xs font-medium border-2 transition-all"
                  style={{ borderColor: schedule === o.value ? '#4285F4' : '#E5E7EB', background: schedule === o.value ? '#EFF6FF' : '#fff', color: schedule === o.value ? '#4285F4' : '#374151' }}>
                  {o.label}
                </button>
              ))}
            </div>
          </Field>

          <Btn onClick={handleSaveSync} disabled={saving || !syncName.trim()} color="#4285F4" style={{ width: '100%' }}>
            {saving ? <><Loader className="w-4 h-4 animate-spin" />Saving…</> : <><Calendar className="w-4 h-4" />Schedule Sync</>}
          </Btn>
        </div>
      )}

      {syncSuccess && <Alert type="success">{syncSuccess}</Alert>}
      {error && <Alert type="error">{error}</Alert>}

      <SyncConfigList configs={syncConfigs} loading={loadingConfigs} userId={userId} onRefresh={fetchConfigs} sourceColor="#4285F4" />
    </div>
  );
};

// ── S3 Sync Tab — manual entry ────────────────────────────────────────────────
const S3SyncTab = ({ userId }) => {
  const [creds, setCreds] = useState({ bucket: '', prefix: '', aws_access_key_id: '', aws_secret_access_key: '', aws_session_token: '', aws_region: 'ap-south-1' });
  const [name, setName] = useState('');
  const [schedule, setSchedule] = useState('daily');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [configs, setConfigs] = useState([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);

  const set = (k, v) => setCreds(p => ({ ...p, [k]: v }));

  const fetchConfigs = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs`, { params: { user_id: userId } });
      setConfigs((res.data.configs || []).filter(c => c.source_type === 's3'));
    } catch { setConfigs([]); } finally { setLoadingConfigs(false); }
  }, [userId]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const handleSave = async () => {
    if (!name.trim()) { setError('Give this sync a name'); return; }
    if (!creds.bucket.trim()) { setError('Bucket name is required'); return; }
    if (!creds.aws_access_key_id.trim() || !creds.aws_secret_access_key.trim()) { setError('AWS credentials are required'); return; }
    setSaving(true); setError(''); setSuccess('');
    try {
      const credentials = { bucket: creds.bucket.trim(), prefix: creds.prefix.trim(), aws_access_key_id: creds.aws_access_key_id.trim(), aws_secret_access_key: creds.aws_secret_access_key.trim(), aws_region: creds.aws_region || 'ap-south-1', ...(creds.aws_session_token.trim() ? { aws_session_token: creds.aws_session_token.trim() } : {}) };
      await axios.post(`${API_BASE}/api/sync/configs`, { user_id: userId, source_type: 's3', display_name: name, credentials, schedule, space_or_path: creds.prefix || null });
      setSuccess('S3 sync scheduled successfully!');
      setName(''); setCreds({ bucket: '', prefix: '', aws_access_key_id: '', aws_secret_access_key: '', aws_session_token: '', aws_region: 'ap-south-1' });
      fetchConfigs();
    } catch (e) { setError(e.response?.data?.detail || 'Failed to save'); } finally { setSaving(false); }
  };

  return (
    <div className="space-y-5">
      <Alert type="info">Enter your S3 bucket credentials — files will be automatically synced to the Knowledge Base on your chosen schedule.</Alert>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Sync Name" required>
          <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. HR Docs from S3" />
        </Field>
        <Field label="S3 Bucket" required>
          <Input value={creds.bucket} onChange={e => set('bucket', e.target.value)} placeholder="my-company-bucket" />
        </Field>
        <Field label="Prefix / Folder" hint="optional">
          <Input value={creds.prefix} onChange={e => set('prefix', e.target.value)} placeholder="documents/hr/" />
        </Field>
        <Field label="AWS Region">
          <Input value={creds.aws_region} onChange={e => set('aws_region', e.target.value)} placeholder="ap-south-1" />
        </Field>
        <Field label="AWS Access Key ID" required>
          <Input value={creds.aws_access_key_id} onChange={e => set('aws_access_key_id', e.target.value)} placeholder="AKIA..." />
        </Field>
        <Field label="AWS Secret Access Key" required>
          <Input type="password" value={creds.aws_secret_access_key} onChange={e => set('aws_secret_access_key', e.target.value)} placeholder="••••••••" />
        </Field>
        <div className="sm:col-span-2">
          <Field label="AWS Session Token" hint="optional — for SSO/temporary credentials">
            <Input type="password" value={creds.aws_session_token} onChange={e => set('aws_session_token', e.target.value)} placeholder="IQoJb3Jp..." />
          </Field>
        </div>
      </div>

      {/* Schedule */}
      <Field label="Sync Schedule">
        <div className="grid grid-cols-4 gap-2">
          {SCHEDULE_OPTIONS.map(o => (
            <button key={o.value} onClick={() => setSchedule(o.value)}
              className="px-2 py-2 rounded-xl text-xs font-medium border-2 transition-all"
              style={{ borderColor: schedule === o.value ? RED : '#E5E7EB', background: schedule === o.value ? `${RED}08` : '#fff', color: schedule === o.value ? RED : '#374151' }}>
              {o.label}
            </button>
          ))}
        </div>
      </Field>

      {error && <Alert type="error">{error}</Alert>}
      {success && <Alert type="success">{success}</Alert>}
      <Btn onClick={handleSave} disabled={saving} color={RED} style={{ width: '100%', padding: '12px' }}>
        {saving ? <><Loader className="w-4 h-4 animate-spin" />Saving…</> : <><Calendar className="w-4 h-4" />Schedule S3 Sync</>}
      </Btn>

      <SyncConfigList configs={configs} loading={loadingConfigs} userId={userId} onRefresh={fetchConfigs} sourceColor="#E25444" />
    </div>
  );
};

// ── Confluence Sync Tab ───────────────────────────────────────────────────────
const ConfluenceSyncTab = ({ userId }) => {
  const [creds, setCreds] = useState({ site_url: '', email: '', api_token: '' });
  const [name, setName] = useState('');
  const [schedule, setSchedule] = useState('daily');
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [spaces, setSpaces] = useState([]);
  const [selectedSpace, setSelectedSpace] = useState(null); // { key, name }
  const [pages, setPages] = useState([]);
  const [loadingPages, setLoadingPages] = useState(false);
  const [parentStack, setParentStack] = useState([]); // breadcrumb: [{id, title}]
  const [searchTerm, setSearchTerm] = useState('');
  const [syncScope, setSyncScope] = useState('space'); // 'space' | 'pages'
  const [selectedPageIds, setSelectedPageIds] = useState(new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [configs, setConfigs] = useState([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);

  const set = (k, v) => { setCreds(p => ({ ...p, [k]: v })); setConnected(false); setSpaces([]); setSelectedSpace(null); };

  const fetchConfigs = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs`, { params: { user_id: userId } });
      setConfigs((res.data.configs || []).filter(c => c.source_type === 'confluence'));
    } catch { setConfigs([]); } finally { setLoadingConfigs(false); }
  }, [userId]);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);

  const handleConnect = async () => {
    if (!creds.site_url || !creds.email || !creds.api_token) { setError('Fill in all fields first'); return; }
    setConnecting(true); setError('');
    try {
      const res = await axios.post(`${API_BASE}/api/sync/confluence/list-spaces`, {
        site_url: creds.site_url, email: creds.email, api_token: creds.api_token,
      });
      setSpaces(res.data.spaces || []); setConnected(true);
    } catch (e) { setError(e.response?.data?.detail || 'Connection failed'); }
    finally { setConnecting(false); }
  };

  const loadPages = async (parentId = null, search = '') => {
    if (!selectedSpace) return;
    setLoadingPages(true);
    try {
      const credParams = `site_url=${encodeURIComponent(creds.site_url)}&email=${encodeURIComponent(creds.email)}&api_token=${encodeURIComponent(creds.api_token)}`;
      const extra = `${parentId ? `&parent_id=${parentId}` : ''}${search ? `&search=${encodeURIComponent(search)}` : ''}`;
      const res = await axios.get(`${API_BASE}/api/confluence/pages?${credParams}&space_key=${encodeURIComponent(selectedSpace.key)}${extra}`);
      setPages(res.data.pages || []);
    } catch { setPages([]); }
    finally { setLoadingPages(false); }
  };

  const selectSpace = (s) => {
    setSelectedSpace(s);
    setName(`${s.name} Sync`);
    setPages([]); setParentStack([]); setSearchTerm(''); setSelectedPageIds(new Set()); setSyncScope('space');
    // load root pages immediately
    setTimeout(() => loadPages(null, ''), 50);
  };

  const openPage = (p) => {
    setParentStack(prev => [...prev, { id: p.id, title: p.title }]);
    setPages([]); loadPages(p.id, '');
  };

  const navToParent = (index) => {
    const newStack = parentStack.slice(0, index + 1);
    setParentStack(newStack);
    loadPages(newStack[newStack.length - 1]?.id || null, '');
  };

  const navToRoot = () => { setParentStack([]); loadPages(null, ''); };

  const togglePage = (id) => {
    setSelectedPageIds(prev => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
    setSyncScope('pages');
  };

  const handleSave = async () => {
    if (!name.trim()) { setError('Give this sync a name'); return; }
    if (!selectedSpace) { setError('Select a space to sync'); return; }
    setSaving(true); setError(''); setSuccess('');
    try {
      // space_or_path: space key if syncing whole space, or comma-separated page IDs
      const space_or_path = syncScope === 'pages' && selectedPageIds.size > 0
        ? `pages:${[...selectedPageIds].join(',')}`
        : selectedSpace.key;
      await axios.post(`${API_BASE}/api/sync/configs`, {
        user_id: userId, source_type: 'confluence', display_name: name,
        credentials: creds, schedule, space_or_path,
      });
      setSuccess(`Confluence sync scheduled — syncing ${syncScope === 'pages' ? `${selectedPageIds.size} page(s)` : `"${selectedSpace.name}" space`}!`);
      setName(''); setCreds({ site_url: '', email: '', api_token: '' });
      setConnected(false); setSpaces([]); setSelectedSpace(null); setPages([]);
      setParentStack([]); setSelectedPageIds(new Set()); setSyncScope('space');
      fetchConfigs();
    } catch (e) { setError(e.response?.data?.detail || 'Failed to save'); } finally { setSaving(false); }
  };

  return (
    <div className="space-y-5">
      {/* Header banner */}
      <div className="flex items-center gap-3 p-4 rounded-xl border" style={{ background: '#EFF6FF', borderColor: '#BFDBFE' }}>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: '#0052CC' }}><IconConfluence /></div>
        <div>
          <p className="text-sm font-semibold" style={{ color: '#1E3A5F' }}>Connect to Confluence</p>
          <p className="text-xs mt-0.5" style={{ color: '#3B82F6' }}>Need an <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noreferrer" className="underline font-medium">API token</a>?</p>
        </div>
      </div>

      <Field label="Sync Name" required>
        <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. HR Confluence Space" />
      </Field>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <Field label="Confluence Site URL" required hint="e.g. yourcompany.atlassian.net">
            <Input value={creds.site_url} onChange={e => set('site_url', e.target.value)} placeholder="yourcompany.atlassian.net" />
          </Field>
        </div>
        <Field label="Atlassian Email" required>
          <Input type="email" value={creds.email} onChange={e => set('email', e.target.value)} placeholder="you@company.com" />
        </Field>
        <Field label="API Token" required>
          <Input type="password" value={creds.api_token} onChange={e => set('api_token', e.target.value)} placeholder="••••••••" />
        </Field>
      </div>

      {!connected ? (
        <Btn onClick={handleConnect} disabled={connecting || !creds.site_url || !creds.email || !creds.api_token} color="#0052CC" style={{ width: '100%' }}>
          {connecting ? <><Loader className="w-4 h-4 animate-spin" />Connecting…</> : <><IconConfluence />Connect & List Spaces</>}
        </Btn>
      ) : !selectedSpace ? (
        /* Step 2 — Space selector */
        <div>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="w-4 h-4" style={{ color: '#059669' }} />
            <span className="text-xs font-semibold" style={{ color: '#059669' }}>Connected — {spaces.length} space{spaces.length !== 1 ? 's' : ''} found</span>
            <button onClick={() => { setConnected(false); setSpaces([]); }} className="ml-auto text-xs underline" style={{ color: '#9CA3AF' }}>Disconnect</button>
          </div>
          <Field label="Select Space" required>
            <div className="space-y-1.5 max-h-56 overflow-y-auto">
              {spaces.map(s => (
                <button key={s.key} onClick={() => selectSpace(s)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border-2 text-left transition-all hover:border-blue-400"
                  style={{ borderColor: '#E5E7EB', background: '#fff' }}>
                  <span className="text-xs font-mono px-1.5 py-0.5 rounded flex-shrink-0" style={{ background: '#E5E7EB', color: '#374151' }}>{s.key}</span>
                  <span className="text-sm truncate flex-1" style={{ color: '#374151' }}>{s.name}</span>
                  <ChevronRight className="w-4 h-4 flex-shrink-0" style={{ color: '#D1D5DB' }} />
                </button>
              ))}
            </div>
          </Field>
        </div>
      ) : (
        /* Step 3 — Page browser inside space */
        <div className="space-y-3">
          {/* Space header + back */}
          <div className="flex items-center gap-2">
            <button onClick={() => { setSelectedSpace(null); setPages([]); setParentStack([]); }}
              className="text-xs flex items-center gap-1 px-2 py-1 rounded-lg" style={{ color: '#0052CC', background: '#EFF6FF' }}>
              ← Spaces
            </button>
            <span className="text-xs" style={{ color: '#D1D5DB' }}>/</span>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: '#E5E7EB', color: '#374151' }}>{selectedSpace.key}</span>
              <span className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>{selectedSpace.name}</span>
            </div>
          </div>

          {/* Sync scope toggle */}
          <div className="flex gap-2">
            <button onClick={() => setSyncScope('space')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border-2 transition-all"
              style={{ borderColor: syncScope === 'space' ? '#0052CC' : '#E5E7EB', background: syncScope === 'space' ? '#EFF6FF' : '#fff', color: syncScope === 'space' ? '#0052CC' : '#6B7280' }}>
              Sync entire space
            </button>
            <button onClick={() => setSyncScope('pages')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border-2 transition-all"
              style={{ borderColor: syncScope === 'pages' ? '#0052CC' : '#E5E7EB', background: syncScope === 'pages' ? '#EFF6FF' : '#fff', color: syncScope === 'pages' ? '#0052CC' : '#6B7280' }}>
              Pick specific pages {syncScope === 'pages' && selectedPageIds.size > 0 && `(${selectedPageIds.size})`}
            </button>
          </div>

          {/* Page browser */}
          <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E8EAF0' }}>
            {/* Breadcrumb */}
            <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: '#E8EAF0', background: '#FAFBFC' }}>
              <div className="flex items-center gap-1 flex-wrap">
                <button onClick={navToRoot} className="text-xs font-medium flex items-center gap-1" style={{ color: parentStack.length ? '#0052CC' : '#374151' }}>
                  <Home className="w-3 h-3" /> Root
                </button>
                {parentStack.map((p, i) => (
                  <React.Fragment key={p.id}>
                    <ChevronRight className="w-3 h-3" style={{ color: '#D1D5DB' }} />
                    <button onClick={() => navToParent(i)} className="text-xs font-medium truncate max-w-[120px]"
                      style={{ color: i < parentStack.length - 1 ? '#0052CC' : '#374151' }}>
                      {p.title}
                    </button>
                  </React.Fragment>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <input value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && loadPages(parentStack.at(-1)?.id || null, searchTerm)}
                  placeholder="Search…" className="text-xs px-2 py-1 border rounded-lg focus:outline-none w-28"
                  style={{ borderColor: '#E5E7EB' }} />
                <button onClick={() => loadPages(parentStack.at(-1)?.id || null, searchTerm)} disabled={loadingPages}
                  className="p-1.5 rounded-lg" style={{ color: '#9CA3AF' }}>
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingPages ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {/* Pages list */}
            <div style={{ maxHeight: 280, overflowY: 'auto' }}>
              {loadingPages ? (
                <div className="flex items-center justify-center py-10">
                  <Loader className="w-5 h-5 animate-spin" style={{ color: '#0052CC' }} />
                  <span className="ml-2 text-sm" style={{ color: '#9CA3AF' }}>Loading pages…</span>
                </div>
              ) : pages.length === 0 ? (
                <div className="flex flex-col items-center py-10" style={{ color: '#D1D5DB' }}>
                  <FileText className="w-8 h-8 mb-2" /><p className="text-sm">No pages found</p>
                </div>
              ) : (
                pages.map(p => (
                  <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 border-b transition-all"
                    style={{ borderColor: '#F3F4F6', background: selectedPageIds.has(p.id) ? '#EFF6FF' : 'transparent' }}>
                    {syncScope === 'pages' && (
                      <input type="checkbox" checked={selectedPageIds.has(p.id)} onChange={() => togglePage(p.id)}
                        className="flex-shrink-0 w-4 h-4 cursor-pointer" style={{ accentColor: '#0052CC' }} />
                    )}
                    <FileText className="w-4 h-4 flex-shrink-0" style={{ color: selectedPageIds.has(p.id) ? '#0052CC' : '#9CA3AF' }} />
                    <span className="flex-1 text-sm truncate" style={{ color: selectedPageIds.has(p.id) ? '#0052CC' : '#1A1A2E', fontWeight: selectedPageIds.has(p.id) ? 600 : 400 }}>
                      {p.title}
                    </span>
                    <button onClick={() => openPage(p)}
                      className="text-xs px-2 py-1 rounded-lg flex items-center gap-1 flex-shrink-0"
                      style={{ color: '#0052CC', background: '#EFF6FF' }}>
                      Open <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Select all bar */}
            {syncScope === 'pages' && pages.length > 0 && (
              <div className="px-4 py-2 border-t flex items-center gap-3" style={{ borderColor: '#E8EAF0', background: '#FAFBFC' }}>
                <button onClick={() => setSelectedPageIds(prev => { const n = new Set(prev); pages.forEach(p => n.add(p.id)); return n; })}
                  className="text-xs underline" style={{ color: '#0052CC' }}>Select all on page</button>
                {selectedPageIds.size > 0 && (
                  <button onClick={() => setSelectedPageIds(new Set())} className="text-xs underline" style={{ color: '#6B7280' }}>Clear</button>
                )}
                <span className="ml-auto text-xs" style={{ color: '#9CA3AF' }}>{selectedPageIds.size} page{selectedPageIds.size !== 1 ? 's' : ''} selected</span>
              </div>
            )}
          </div>

          {/* Schedule */}
          <Field label="Sync Schedule">
            <div className="grid grid-cols-4 gap-2">
              {SCHEDULE_OPTIONS.map(o => (
                <button key={o.value} onClick={() => setSchedule(o.value)}
                  className="px-2 py-2 rounded-xl text-xs font-medium border-2 transition-all"
                  style={{ borderColor: schedule === o.value ? '#0052CC' : '#E5E7EB', background: schedule === o.value ? '#EFF6FF' : '#fff', color: schedule === o.value ? '#0052CC' : '#374151' }}>
                  {o.label}
                </button>
              ))}
            </div>
          </Field>

          {error && <Alert type="error">{error}</Alert>}
          {success && <Alert type="success">{success}</Alert>}

          <Btn onClick={handleSave} disabled={saving || (syncScope === 'pages' && selectedPageIds.size === 0)} color="#0052CC" style={{ width: '100%', padding: '12px' }}>
            {saving ? <><Loader className="w-4 h-4 animate-spin" />Saving…</> : (
              syncScope === 'pages' && selectedPageIds.size > 0
                ? <><Calendar className="w-4 h-4" />Sync {selectedPageIds.size} Page{selectedPageIds.size !== 1 ? 's' : ''}</>
                : <><Calendar className="w-4 h-4" />Sync Entire Space</>
            )}
          </Btn>
        </div>
      )}

      {!connected && error && <Alert type="error">{error}</Alert>}
      {!connected && success && <Alert type="success">{success}</Alert>}

      <SyncConfigList configs={configs} loading={loadingConfigs} userId={userId} onRefresh={fetchConfigs} sourceColor="#0052CC" />
    </div>
  );
};

// ── Sync Config List — shared by S3 and Confluence tabs ──────────────────────
const SyncConfigList = ({ configs, loading, userId, onRefresh, sourceColor }) => {
  const [expandedHistory, setExpandedHistory] = useState(null);
  const [historyData, setHistoryData] = useState({});
  const [loadingHistory, setLoadingHistory] = useState({});

  const loadHistory = async (configId) => {
    if (expandedHistory === configId) { setExpandedHistory(null); return; }
    setExpandedHistory(configId);
    if (historyData[configId]) return; // already loaded
    setLoadingHistory(p => ({ ...p, [configId]: true }));
    try {
      const res = await axios.get(`${API_BASE}/api/sync/configs/${configId}/history`, { params: { user_id: userId } });
      setHistoryData(p => ({ ...p, [configId]: res.data.history || [] }));
    } catch { setHistoryData(p => ({ ...p, [configId]: [] })); }
    finally { setLoadingHistory(p => ({ ...p, [configId]: false })); }
  };

  const handleAction = async (action, id) => {
    try {
      if (action === 'run')    await axios.post(`${API_BASE}/api/sync/configs/${id}/run`, null, { params: { user_id: userId } });
      if (action === 'pause')  await axios.put(`${API_BASE}/api/sync/configs/${id}/pause`, null, { params: { user_id: userId } });
      if (action === 'resume') await axios.put(`${API_BASE}/api/sync/configs/${id}/resume`, null, { params: { user_id: userId } });
      if (action === 'delete') { await axios.delete(`${API_BASE}/api/sync/configs/${id}`, { params: { user_id: userId } }); setExpandedHistory(null); }
      if (action === 'run') {
        // Refresh history after a short delay for the new run to appear
        setTimeout(() => { setHistoryData(p => { const n = {...p}; delete n[id]; return n; }); loadHistory(id); }, 4000);
      }
      setTimeout(onRefresh, action === 'run' ? 3500 : 500);
    } catch {}
  };

  if (loading) return <div className="flex justify-center py-6"><Loader className="w-5 h-5 animate-spin" style={{ color: '#9CA3AF' }} /></div>;
  if (configs.length === 0) return null;

  const runStatusStyle = {
    running:  { color: '#3B82F6', bg: '#EFF6FF', label: 'Running' },
    success:  { color: '#059669', bg: '#ECFDF5', label: 'Success' },
    partial:  { color: '#D97706', bg: '#FFFBEB', label: 'Partial' },
    failed:   { color: '#DC2626', bg: '#FEF2F2', label: 'Failed'  },
    skipped:  { color: '#6B7280', bg: '#F9FAFB', label: 'Skipped' },
    manual:   { color: '#7C3AED', bg: '#F5F3FF', label: 'Manual'  },
  };

  return (
    <div className="pt-5 border-t" style={{ borderColor: '#E8EAF0' }}>
      <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: '#9CA3AF' }}>
        Active Syncs ({configs.length})
      </p>
      <div className="space-y-3">
        {configs.map(cfg => {
          const st = STATUS_STYLE[cfg.status] || STATUS_STYLE.active;
          const schLabel = SCHEDULE_OPTIONS.find(o => o.value === cfg.schedule)?.label || cfg.schedule;
          const isHistOpen = expandedHistory === cfg.id;
          const runs = historyData[cfg.id] || [];

          return (
            <div key={cfg.id} className="rounded-xl border overflow-hidden transition-all"
              style={{ borderColor: isHistOpen ? sourceColor + '40' : '#E8EAF0', background: cfg.status === 'error' ? '#FFF8F8' : '#FAFBFC' }}>

              {/* Main row */}
              <div className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <p className="text-sm font-semibold truncate" style={{ color: '#1A1A2E' }}>{cfg.display_name}</p>
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0"
                        style={{ background: st.bg, color: st.color }}>
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: st.dot }} />{st.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="text-xs flex items-center gap-1" style={{ color: '#9CA3AF' }}><Calendar className="w-3 h-3" />{schLabel}</span>
                      <span className="text-xs flex items-center gap-1" style={{ color: '#9CA3AF' }}><Clock className="w-3 h-3" />Last: {fmtDate(cfg.last_run_at)}</span>
                      <span className="text-xs flex items-center gap-1" style={{ color: '#9CA3AF' }}><Activity className="w-3 h-3" />{cfg.files_synced || 0} files</span>
                    </div>
                    {cfg.last_error && (
                      <p className="text-xs mt-1.5 truncate" style={{ color: '#DC2626' }}>{cfg.last_error}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={() => handleAction('run', cfg.id)} title="Run now"
                      className="p-2 rounded-lg transition-all" style={{ background: `${sourceColor}12`, color: sourceColor }}>
                      <Zap className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={() => loadHistory(cfg.id)} title="View run history"
                      className="p-2 rounded-lg transition-all"
                      style={{ background: isHistOpen ? sourceColor + '15' : '#F3F4F6', color: isHistOpen ? sourceColor : '#6B7280' }}>
                      <Activity className="w-3.5 h-3.5" />
                    </button>
                    {cfg.status === 'paused'
                      ? <button onClick={() => handleAction('resume', cfg.id)} title="Resume" className="p-2 rounded-lg" style={{ background: '#ECFDF5', color: '#059669' }}><Play className="w-3.5 h-3.5" /></button>
                      : <button onClick={() => handleAction('pause', cfg.id)} title="Pause" className="p-2 rounded-lg" style={{ background: '#F9FAFB', color: '#9CA3AF' }}><Pause className="w-3.5 h-3.5" /></button>
                    }
                    <button onClick={() => handleAction('delete', cfg.id)} title="Delete" className="p-2 rounded-lg" style={{ background: '#FEF2F2', color: '#DC2626' }}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* History panel */}
              {isHistOpen && (
                <div className="border-t px-4 py-3" style={{ borderColor: '#F3F4F6', background: '#F8F9FB' }}>
                  <p className="text-xs font-semibold mb-2.5" style={{ color: '#6B7280' }}>Run History</p>
                  {loadingHistory[cfg.id] ? (
                    <div className="flex items-center gap-2 py-3">
                      <Loader className="w-4 h-4 animate-spin" style={{ color: '#9CA3AF' }} />
                      <span className="text-xs" style={{ color: '#9CA3AF' }}>Loading…</span>
                    </div>
                  ) : runs.length === 0 ? (
                    <p className="text-xs py-3 text-center" style={{ color: '#9CA3AF' }}>No runs yet — click ⚡ to trigger a manual run</p>
                  ) : (
                    <div className="space-y-2">
                      {runs.map(run => {
                        const rs = runStatusStyle[run.status] || runStatusStyle.skipped;
                        return (
                          <div key={run.id} className="flex items-center gap-3 px-3 py-2 rounded-lg"
                            style={{ background: '#fff', border: '1px solid #E5E7EB' }}>
                            <span className="text-xs px-2 py-0.5 rounded-full font-semibold flex-shrink-0"
                              style={{ background: rs.bg, color: rs.color }}>{rs.label}</span>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs" style={{ color: '#374151' }}>
                                {run.started_at ? new Date(run.started_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
                              </p>
                              {run.error && <p className="text-xs truncate mt-0.5" style={{ color: '#DC2626' }}>{run.error}</p>}
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0">
                              {run.files_synced > 0 && (
                                <span className="text-xs" style={{ color: '#059669' }}>↑ {run.files_synced} synced</span>
                              )}
                              {run.duration_s != null && (
                                <span className="text-xs" style={{ color: '#9CA3AF' }}>{run.duration_s}s</span>
                              )}
                              <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: '#F3F4F6', color: '#9CA3AF' }}>
                                {run.trigger === 'manual' ? '👆 manual' : '⏰ auto'}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── Main Upload Page ──────────────────────────────────────────────────────────
const Upload = () => {
  const { user } = useAuth();
  const [activeSource, setActiveSource] = useState('web');
  const active = SOURCES.find(s => s.id === activeSource);

  return (
    <div className="min-h-screen pb-10" style={{ background: '#F8F9FB' }}>
      <style>{`
        @keyframes indeterminate { 0% { transform: translateX(-100%); } 100% { transform: translateX(350%); } }
      `}</style>

      {/* Page header */}
      <div className="px-6 py-5 bg-white border-b" style={{ borderColor: '#E8EAF0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <h1 className="text-lg font-bold" style={{ color: '#1A1A2E' }}>Document Ingestion</h1>
        <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>Upload or sync documents to the Knowledge Base from any source</p>
      </div>

      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-5 items-start">

            {/* Left: Source selector */}
            <div className="flex-shrink-0 w-52 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-widest px-1 mb-3" style={{ color: '#C4C9D4' }}>Source</p>
              {SOURCES.map(s => (
                <SourceTab key={s.id} source={s} active={activeSource === s.id} onClick={() => setActiveSource(s.id)} />
              ))}
            </div>

            {/* Right: Content area */}
            <div className="flex-1 min-w-0">
              <Card>
                {/* Card header */}
                <div className="flex items-center gap-3 px-6 py-4 border-b" style={{ borderColor: '#F3F4F6' }}>
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                    style={{ background: active.bg, boxShadow: `0 2px 8px ${active.color}20` }}>
                    <active.Icon />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold" style={{ color: '#1A1A2E' }}>{active.label}</h2>
                    <p className="text-xs" style={{ color: '#9CA3AF' }}>
                      {activeSource === 'web' ? 'Upload a file directly from your computer' :
                       activeSource === 'drive' ? `Browsing as ${user?.email}` :
                       activeSource === 's3' ? 'Configure S3 credentials to schedule sync' :
                       'Connect Confluence and schedule space sync'}
                    </p>
                  </div>
                </div>

                {/* Tab content */}
                <div className="p-6">
                  {activeSource === 'web'        && <WebUploadTab />}
                  {activeSource === 'drive'      && <DriveTab />}
                  {activeSource === 's3'         && <S3SyncTab userId={user?.id || user?.email} />}
                  {activeSource === 'confluence' && <ConfluenceSyncTab userId={user?.id || user?.email} />}
                </div>
              </Card>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
