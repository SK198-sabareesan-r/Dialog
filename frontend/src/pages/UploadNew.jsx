import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Upload as UploadIcon, File, Loader, CheckCircle, FileText,
  Image, FileSpreadsheet, AlertTriangle, Info, X,
  HardDrive, Database, FolderOpen, Folder, ChevronRight,
  Home, RefreshCw, Link2, Clock
} from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const RED = '#ED1C24';
const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

// Status → display config
const SYNC_STATUS_CONFIG = {
  STARTING:    { label: 'Starting ingestion…',        color: '#D97706', bg: '#FFFBEB', pulse: true  },
  IN_PROGRESS: { label: 'Indexing into knowledge base…', color: '#3B82F6', bg: '#EFF6FF', pulse: true  },
  COMPLETE:    { label: 'Indexed — document is queryable', color: '#059669', bg: '#ECFDF5', pulse: false },
  FAILED:      { label: 'Ingestion failed',            color: '#DC2626', bg: '#FEF2F2', pulse: false },
  STOPPED:     { label: 'Ingestion stopped',           color: '#6B7280', bg: '#F9FAFB', pulse: false },
  PENDING:     { label: 'Waiting for ingestion job…',  color: '#D97706', bg: '#FFFBEB', pulse: true  },
};

// ── helpers ──────────────────────────────────────────────────────────────────
const PageHeader = ({ title, subtitle }) => (
  <div className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm" style={{ borderColor: '#E8EAF0' }}>
    <div>
      <h1 className="text-lg font-semibold" style={{ color: '#1A1A2E' }}>{title}</h1>
      {subtitle && <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>{subtitle}</p>}
    </div>
  </div>
);

const getFileIcon = (name) => {
  const ext = (name || '').split('.').pop().toLowerCase();
  if (['pdf','doc','docx','txt'].includes(ext)) return FileText;
  if (['png','jpg','jpeg','gif','webp'].includes(ext)) return Image;
  if (['xlsx','xls','csv'].includes(ext)) return FileSpreadsheet;
  return File;
};

const fmt = (bytes) => {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const Tab = ({ active, onClick, icon: Icon, label }) => (
  <button onClick={onClick}
    className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg transition-all"
    style={{ background: active ? RED : 'transparent', color: active ? '#fff' : '#6B7280', border: `1px solid ${active ? RED : '#E5E7EB'}` }}>
    <Icon className="w-4 h-4" />{label}
  </button>
);

// ── SyncStatusCard ──────────────────────────────────────────────────────────
// Shown after a successful upload; polls /api/upload/sync-status/{jobId}
// until the job reaches a terminal state.
const SyncStatusCard = ({ s3Key, filename }) => {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('PENDING');
  const [stats, setStats] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const timerRef = useRef(null);
  const startRef = useRef(Date.now());

  // Tick the elapsed timer every second
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  // Poll the backend for job ID first, then poll status until terminal
  useEffect(() => {
    let stopped = false;

    const pollStatus = async (id) => {
      try {
        const res = await axios.get(`${API_BASE}/api/upload/sync-status/${id}`, { timeout: 10000 });
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

    const fetchLatestJobId = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/kb/sync/latest`, { timeout: 10000 });
        if (stopped) return;
        if (res.data?.ingestion_job_id) {
          setJobId(res.data.ingestion_job_id);
          setStatus(res.data.status || 'STARTING');
          intervalRef.current = setInterval(() => pollStatus(res.data.ingestion_job_id), 8000);
          pollStatus(res.data.ingestion_job_id);
        }
      } catch {
        // If the endpoint doesn't respond, fall back to showing generic syncing state
      }
    };

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
    <div className="dialog-card p-5 mt-5" style={{ borderLeft: `4px solid ${cfg.color}`, background: cfg.bg }}>
      {/* Header row */}
      <div className="flex items-center gap-2 mb-3">
        <Database className="w-4 h-4 flex-shrink-0" style={{ color: cfg.color }} />
        <span className="text-sm font-semibold" style={{ color: cfg.color }}>KB Ingestion</span>
        {cfg.pulse && <span className="ml-1 w-2 h-2 rounded-full animate-pulse" style={{ background: cfg.color }} />}
        <div className="ml-auto flex items-center gap-1.5 text-xs" style={{ color: '#9CA3AF' }}>
          <Clock className="w-3 h-3" />
          {formatElapsed(elapsed)}
        </div>
      </div>

      {/* Status label */}
      <p className="text-sm font-medium mb-1" style={{ color: '#1A1A2E' }}>{cfg.label}</p>

      {/* File info */}
      <p className="text-xs mb-3 font-mono truncate" style={{ color: '#6B7280' }}>{s3Key}</p>

      {/* Progress bar — indeterminate while running */}
      {cfg.pulse && (
        <div className="h-1.5 rounded-full overflow-hidden mb-3" style={{ background: '#E5E7EB' }}>
          <div className="h-full rounded-full" style={{ background: cfg.color, width: '40%', animation: 'indeterminate 1.5s ease-in-out infinite' }} />
        </div>
      )}

      {/* Stats (shown once COMPLETE) */}
      {stats && status === 'COMPLETE' && (
        <div className="grid grid-cols-3 gap-3 mt-2">
          {[
            { label: 'Scanned', value: stats.documents_scanned },
            { label: 'Indexed', value: stats.new_documents_indexed },
            { label: 'Failed', value: stats.documents_failed },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg p-2.5 text-center" style={{ background: 'rgba(255,255,255,0.7)' }}>
              <p className="text-lg font-bold" style={{ color: '#1A1A2E' }}>{value ?? '—'}</p>
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
      {jobId && <p className="text-xs mt-3 font-mono" style={{ color: '#9CA3AF' }}>Job: {jobId}</p>}

      {/* No job ID yet — generic note */}
      {!jobId && !error && status === 'PENDING' && (
        <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>
          Ingestion job is starting in the background — check backend logs for real-time progress.
        </p>
      )}

      {error && <p className="text-xs mt-2" style={{ color: '#DC2626' }}>{error}</p>}
    </div>
  );
};

const ResultPanel = ({ result, error, onDismissError }) => (
  <>
    {result && (
      <div className="dialog-card p-4 mt-4" style={{ borderLeft: `4px solid ${RED}`, background: '#FFF5F5' }}>
        <div className="flex gap-3">
          <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: RED }} />
          <div>
            <p className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Success</p>
            <p className="text-xs mt-1" style={{ color: '#6B7280' }}>{result.message || 'Completed'}</p>
            {result.s3_key && <p className="text-xs mt-1 font-mono break-all" style={{ color: RED }}>{result.s3_key}</p>}
            {result.ingestion_job_id && <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>Job: <span className="font-mono" style={{ color: RED }}>{result.ingestion_job_id}</span></p>}
          </div>
        </div>
      </div>
    )}
    {error && (
      <div className="dialog-card p-4 mt-4" style={{ borderLeft: '4px solid #DC2626' }}>
        <div className="flex gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: '#DC2626' }} />
          <div className="flex-1">
            <p className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Error</p>
            <p className="text-xs mt-1" style={{ color: '#6B7280' }}>{error}</p>
            <button onClick={onDismissError} className="mt-2 text-xs underline" style={{ color: '#DC2626' }}>Dismiss</button>
          </div>
        </div>
      </div>
    )}
  </>
);

// ── Breadcrumb ────────────────────────────────────────────────────────────────
const Breadcrumb = ({ crumbs, onNavigate }) => (
  <div className="flex items-center gap-1 flex-wrap px-1 py-2">
    {crumbs.map((c, i) => (
      <React.Fragment key={c.id || c.prefix || i}>
        {i > 0 && <ChevronRight className="w-3 h-3 flex-shrink-0" style={{ color: '#C4C9D4' }} />}
        <button
          onClick={() => onNavigate(i)}
          className="flex items-center gap-1 text-xs font-medium rounded px-1.5 py-0.5 transition-colors"
          style={{
            color: i === crumbs.length - 1 ? '#1A1A2E' : RED,
            background: i === crumbs.length - 1 ? '#F3F4F6' : 'transparent',
            cursor: i === crumbs.length - 1 ? 'default' : 'pointer',
          }}
        >
          {i === 0 && <Home className="w-3 h-3" />}
          <span>{c.name}</span>
        </button>
      </React.Fragment>
    ))}
  </div>
);

// ── File row ─────────────────────────────────────────────────────────────────
const FileRow = ({ item, isFolder, selected, onSelect, onOpen }) => {
  const Icon = isFolder ? Folder : getFileIcon(item.name);
  return (
    <div
      className="flex items-center gap-3 px-4 py-2.5 border-b transition-colors"
      style={{ borderColor: '#F3F4F6', background: selected ? 'rgba(228,0,43,0.04)' : 'transparent' }}
    >
      {!isFolder && (
        <input type="checkbox" checked={selected} onChange={onSelect}
          className="flex-shrink-0 w-4 h-4 cursor-pointer" style={{ accentColor: RED }} />
      )}
      {isFolder && <div className="w-4 flex-shrink-0" />}
      <Icon className="w-4 h-4 flex-shrink-0" style={{ color: isFolder ? '#F7941D' : '#9CA3AF' }} />
      <span
        className="flex-1 text-sm truncate"
        style={{ color: '#1A1A2E', cursor: isFolder ? 'pointer' : 'default', fontWeight: isFolder ? 500 : 400 }}
        onClick={isFolder ? onOpen : undefined}
      >
        {item.name}
      </span>
      {isFolder && (
        <button onClick={onOpen} className="flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors"
          style={{ color: RED, background: 'rgba(228,0,43,0.06)' }}>
          Open <ChevronRight className="w-3 h-3" />
        </button>
      )}
      {!isFolder && (
        <span className="text-xs flex-shrink-0" style={{ color: '#C4C9D4' }}>
          {fmt(item.size || item.Size)}
        </span>
      )}
    </div>
  );
};

// ── Selection toolbar ─────────────────────────────────────────────────────────
const SelectionBar = ({ count, total, onSelectAll, onClear, onImport, importing }) => (
  <div className="flex items-center justify-between px-4 py-3 rounded-lg mt-1"
    style={{ background: count > 0 ? 'rgba(228,0,43,0.06)' : '#F9FAFB', border: `1px solid ${count > 0 ? 'rgba(228,0,43,0.2)' : '#E5E7EB'}` }}>
    <div className="flex items-center gap-3">
      <span className="text-sm font-semibold" style={{ color: count > 0 ? RED : '#6B7280' }}>
        {count > 0 ? `${count} file${count !== 1 ? 's' : ''} selected` : 'No files selected'}
      </span>
      {total > 0 && (
        <div className="flex gap-2">
          <button onClick={onSelectAll} className="text-xs underline" style={{ color: RED }}>Select all ({total})</button>
          {count > 0 && <button onClick={onClear} className="text-xs underline" style={{ color: '#6B7280' }}>Clear</button>}
        </div>
      )}
    </div>
    <button
      onClick={onImport}
      disabled={count === 0 || importing}
      className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all"
      style={{
        background: count > 0 ? RED : '#E5E7EB',
        color: count > 0 ? '#fff' : '#9CA3AF',
        cursor: count > 0 && !importing ? 'pointer' : 'not-allowed',
      }}
    >
      {importing ? <Loader className="w-4 h-4 animate-spin" /> : <UploadIcon className="w-4 h-4" />}
      {importing ? 'Importing...' : `Import${count > 0 ? ` ${count}` : ''}`}
    </button>
  </div>
);

// ── Google Drive Tab ──────────────────────────────────────────────────────────
const SharedDriveTab = () => {
  const { driveToken, user } = useAuth();
  const [drives, setDrives] = useState([]);
  const [selectedDriveId, setSelectedDriveId] = useState('');
  const [crumbs, setCrumbs] = useState([{ id: 'root', name: 'My Drive' }]);
  const [folders, setFolders] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]); // [{id,name,mimeType}]
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const currentFolderId = crumbs[crumbs.length - 1]?.id || 'root';

  // Load drives on mount
  useEffect(() => {
    if (!driveToken) return;
    axios.get(`${API_BASE}/api/google-drive/shared-drives`, { params: { google_access_token: driveToken } })
      .then(r => setDrives(r.data.shared_drives || []))
      .catch(() => {});
  }, [driveToken]);

  const browse = useCallback(async (folderId, driveId) => {
    setLoading(true); setError(null);
    try {
      const res = await axios.get(`${API_BASE}/api/google-drive/browse`, {
        params: { google_access_token: driveToken, folder_id: folderId, ...(driveId ? { drive_id: driveId } : {}) }
      });
      setFolders(res.data.folders);
      setFiles(res.data.files);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load folder'); }
    finally { setLoading(false); }
  }, [driveToken]);

  // Browse root on drive change
  useEffect(() => {
    if (!driveToken) return;
    const rootName = selectedDriveId ? (drives.find(d => d.id === selectedDriveId)?.name || 'Shared Drive') : 'My Drive';
    const rootId = selectedDriveId || 'root';
    setCrumbs([{ id: rootId, name: rootName }]);
    setSelectedFiles([]);
    browse(rootId, selectedDriveId || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDriveId, driveToken]);

  const openFolder = (folder) => {
    setCrumbs(prev => [...prev, { id: folder.id, name: folder.name }]);
    setSelectedFiles([]);
    browse(folder.id, selectedDriveId || undefined);
  };

  const navigateTo = (index) => {
    const newCrumbs = crumbs.slice(0, index + 1);
    setCrumbs(newCrumbs);
    setSelectedFiles([]);
    browse(newCrumbs[newCrumbs.length - 1].id, selectedDriveId || undefined);
  };

  const toggleFile = (f) => setSelectedFiles(prev =>
    prev.find(x => x.id === f.id) ? prev.filter(x => x.id !== f.id) : [...prev, { id: f.id, name: f.name, mimeType: f.mimeType }]
  );
  const isSelected = (id) => !!selectedFiles.find(x => x.id === id);

  const handleImport = async () => {
    if (!selectedFiles.length) return;
    setImporting(true); setError(null); setResult(null);
    try {
      const res = await axios.post(`${API_BASE}/api/google-drive/import`, {
        files: selectedFiles,
        google_access_token: driveToken,
        user_id: user?.email || 'guest',
        ...(selectedDriveId ? { drive_id: selectedDriveId } : {}),
      });
      setResult(res.data); setSelectedFiles([]);
    } catch (e) { setError(e.response?.data?.detail || 'Import failed'); }
    finally { setImporting(false); }
  };

  if (!driveToken) return (
    <div className="dialog-card p-5" style={{ background: '#FEF9F9', borderColor: '#FEE2E2' }}>
      <div className="flex gap-3">
        <Info className="w-5 h-5 flex-shrink-0" style={{ color: RED }} />
        <div>
          <p className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Drive access not available</p>
          <p className="text-xs mt-1" style={{ color: '#6B7280' }}>Log out and sign in again — Drive access is granted automatically at login.</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Connected banner */}
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl" style={{ background: '#FFF5F5', border: `1px solid ${RED}` }}>
        <CheckCircle className="w-4 h-4" style={{ color: RED }} />
        <span className="text-sm font-semibold" style={{ color: RED }}>Google Drive connected</span>
        <span className="text-xs" style={{ color: '#6B7280' }}>— {user?.email}</span>
      </div>

      {/* Drive selector */}
      {drives.length > 0 && (
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wide mb-1.5" style={{ color: '#6B7280' }}>Drive</label>
          <select value={selectedDriveId} onChange={e => setSelectedDriveId(e.target.value)} className="dialog-input">
            <option value="">My Drive (personal)</option>
            {drives.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
      )}

      {/* File browser */}
      <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E8EAF0' }}>
        {/* Breadcrumb bar */}
        <div className="flex items-center justify-between px-2 border-b" style={{ borderColor: '#E8EAF0', background: '#FAFBFC' }}>
          <Breadcrumb crumbs={crumbs} onNavigate={navigateTo} />
          <button onClick={() => browse(currentFolderId, selectedDriveId || undefined)} disabled={loading}
            className="p-1.5 rounded transition-colors mr-2" style={{ color: '#9CA3AF' }}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Contents */}
        <div style={{ maxHeight: 320, overflowY: 'auto' }}>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader className="w-6 h-6 animate-spin" style={{ color: RED }} />
              <span className="ml-2 text-sm" style={{ color: '#9CA3AF' }}>Loading...</span>
            </div>
          ) : folders.length === 0 && files.length === 0 ? (
            <div className="flex flex-col items-center py-10" style={{ color: '#C4C9D4' }}>
              <FolderOpen className="w-8 h-8 mb-2 opacity-40" />
              <p className="text-sm">This folder is empty</p>
            </div>
          ) : (
            <>
              {folders.map(f => (
                <FileRow key={f.id} item={f} isFolder selected={false} onOpen={() => openFolder(f)} />
              ))}
              {files.map(f => (
                <FileRow key={f.id} item={f} isFolder={false} selected={isSelected(f.id)}
                  onSelect={() => toggleFile(f)} />
              ))}
            </>
          )}
        </div>
      </div>

      {/* Selection + import toolbar */}
      <SelectionBar
        count={selectedFiles.length}
        total={files.length}
        onSelectAll={() => setSelectedFiles(files.map(f => ({ id: f.id, name: f.name, mimeType: f.mimeType })))}
        onClear={() => setSelectedFiles([])}
        onImport={handleImport}
        importing={importing}
      />

      <ResultPanel result={result} error={error} onDismissError={() => setError(null)} />

      {/* KB Ingestion Status */}
      {result?.s3_key && <SyncStatusCard s3Key={result.s3_key} filename={result.filename || 'Imported files'} />}
    </div>
  );
};

// ── S3 / File Repository Tab ──────────────────────────────────────────────────
const S3ImportTab = () => {
  const { user } = useAuth();
  const [mode, setMode] = useState('browse'); // 'browse' | 'url'

  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      <div className="flex gap-2">
        <button onClick={() => setMode('browse')}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all"
          style={{ background: mode === 'browse' ? RED : 'transparent', color: mode === 'browse' ? '#fff' : '#6B7280', border: `1px solid ${mode === 'browse' ? RED : '#E5E7EB'}` }}>
          <Database className="w-4 h-4" /> Browse S3
        </button>
        <button onClick={() => setMode('url')}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all"
          style={{ background: mode === 'url' ? RED : 'transparent', color: mode === 'url' ? '#fff' : '#6B7280', border: `1px solid ${mode === 'url' ? RED : '#E5E7EB'}` }}>
          <Link2 className="w-4 h-4" /> Public URL
        </button>
      </div>

      {mode === 'browse' ? <S3BrowsePane user={user} /> : <PublicUrlPane user={user} />}
    </div>
  );
};

// ── S3 Browse sub-pane (existing browse + import logic) ───────────────────────
const S3BrowsePane = ({ user }) => {
  const [buckets, setBuckets] = useState([]);
  const [selectedBucket, setSelectedBucket] = useState('');
  const [customBucket, setCustomBucket] = useState('');
  const [crumbs, setCrumbs] = useState([{ prefix: '', name: 'Root' }]);
  const [folders, setFolders] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedKeys, setSelectedKeys] = useState([]); // full S3 keys
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const currentPrefix = crumbs[crumbs.length - 1]?.prefix ?? '';
  const activeBucket = selectedBucket || customBucket.trim();

  // Load pre-configured buckets on mount
  useEffect(() => {
    axios.get(`${API_BASE}/api/file-repo/buckets`)
      .then(r => {
        setBuckets(r.data.buckets || []);
        if (r.data.buckets?.length > 0) setSelectedBucket(r.data.buckets[0]);
      })
      .catch(() => {});
  }, []);

  const browse = useCallback(async (prefix, bucket) => {
    if (!bucket) return;
    setLoading(true); setError(null);
    try {
      const res = await axios.get(`${API_BASE}/api/file-repo/browse`, { params: { source_bucket: bucket, prefix } });
      setFolders(res.data.folders);
      setFiles(res.data.files);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to list folder'); }
    finally { setLoading(false); }
  }, []);

  // Browse root when bucket changes
  useEffect(() => {
    if (!activeBucket) return;
    setCrumbs([{ prefix: '', name: activeBucket }]);
    setSelectedKeys([]);
    browse('', activeBucket);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBucket, customBucket]);

  const openFolder = (folder) => {
    setCrumbs(prev => [...prev, { prefix: folder.prefix, name: folder.name }]);
    setSelectedKeys([]);
    browse(folder.prefix, activeBucket);
  };

  const navigateTo = (index) => {
    const newCrumbs = crumbs.slice(0, index + 1);
    setCrumbs(newCrumbs);
    setSelectedKeys([]);
    browse(newCrumbs[newCrumbs.length - 1].prefix, activeBucket);
  };

  const toggleKey = (key) => setSelectedKeys(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);

  const handleImport = async () => {
    if (!selectedKeys.length) return;
    setImporting(true); setError(null); setResult(null);
    const results = [];
    for (const key of selectedKeys) {
      try {
        const res = await axios.post(`${API_BASE}/api/file-repo/import-single`, {
          source_bucket: activeBucket, source_key: key,
          user_id: user?.email || 'guest',
        });
        results.push({ key, status: 'success', ...res.data });
      } catch (e) { results.push({ key, status: 'error', error: e.response?.data?.detail || e.message }); }
    }
    const ok = results.filter(r => r.status === 'success').length;
    setResult({ message: `Imported ${ok}/${selectedKeys.length} files to Knowledge Base`, results });
    setSelectedKeys([]);
    setImporting(false);
  };

  return (
    <div className="space-y-4">
      {/* Bucket selector */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wide mb-1.5" style={{ color: '#6B7280' }}>Source Bucket</label>
        {buckets.length > 0 ? (
          <div className="flex gap-2">
            <select value={selectedBucket} onChange={e => { setSelectedBucket(e.target.value); setCustomBucket(''); }}
              className="dialog-input flex-1">
              {buckets.map(b => <option key={b} value={b}>{b}</option>)}
              <option value="">— Enter manually —</option>
            </select>
            {selectedBucket === '' && (
              <input type="text" value={customBucket} onChange={e => setCustomBucket(e.target.value)}
                placeholder="bucket-name" className="dialog-input flex-1" />
            )}
          </div>
        ) : (
          <input type="text" value={customBucket} onChange={e => setCustomBucket(e.target.value)}
            placeholder="my-company-bucket" className="dialog-input" />
        )}
      </div>

      {/* File browser */}
      {activeBucket && (
        <div className="rounded-xl border overflow-hidden" style={{ borderColor: '#E8EAF0' }}>
          {/* Breadcrumb bar */}
          <div className="flex items-center justify-between px-2 border-b" style={{ borderColor: '#E8EAF0', background: '#FAFBFC' }}>
            <Breadcrumb crumbs={crumbs} onNavigate={navigateTo} />
            <button onClick={() => browse(currentPrefix, activeBucket)} disabled={loading}
              className="p-1.5 rounded mr-2" style={{ color: '#9CA3AF' }}>
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Contents */}
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="w-6 h-6 animate-spin" style={{ color: RED }} />
                <span className="ml-2 text-sm" style={{ color: '#9CA3AF' }}>Loading...</span>
              </div>
            ) : folders.length === 0 && files.length === 0 ? (
              <div className="flex flex-col items-center py-10" style={{ color: '#C4C9D4' }}>
                <FolderOpen className="w-8 h-8 mb-2 opacity-40" />
                <p className="text-sm">Empty folder</p>
              </div>
            ) : (
              <>
                {folders.map(f => (
                  <FileRow key={f.prefix} item={f} isFolder selected={false} onOpen={() => openFolder(f)} />
                ))}
                {files.map(f => (
                  <FileRow key={f.key} item={{ ...f, name: f.name }} isFolder={false}
                    selected={selectedKeys.includes(f.key)} onSelect={() => toggleKey(f.key)} />
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Selection + import toolbar */}
      {activeBucket && (
        <SelectionBar
          count={selectedKeys.length}
          total={files.length}
          onSelectAll={() => setSelectedKeys(files.map(f => f.key))}
          onClear={() => setSelectedKeys([])}
          onImport={handleImport}
          importing={importing}
        />
      )}

      <ResultPanel result={result} error={error} onDismissError={() => setError(null)} />

      {/* KB Ingestion Status */}
      {result?.s3_key && <SyncStatusCard s3Key={result.s3_key} filename={result.filename || 'Imported files'} />}
    </div>
  );
};

// ── Public URL sub-pane ───────────────────────────────────────────────────────
const PublicUrlPane = ({ user }) => {
  const [urls, setUrls] = useState(['']);
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const addRow    = () => setUrls(prev => [...prev, '']);
  const removeRow = (i) => setUrls(prev => prev.filter((_, idx) => idx !== i));
  const updateUrl = (i, val) => setUrls(prev => prev.map((u, idx) => idx === i ? val : u));

  const validUrls = urls.map(u => u.trim()).filter(u => u.startsWith('http'));

  const handleImport = async () => {
    if (!validUrls.length) return;
    setImporting(true); setError(null); setResults(null);
    try {
      const res = await axios.post(`${API_BASE}/api/upload/import-url`, {
        urls: validUrls,
        user_id: user?.email || 'guest',
      }, { timeout: 120000 });
      setResults(res.data);
      setUrls(['']);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Info */}
      <div className="flex gap-3 px-4 py-3 rounded-xl" style={{ background: '#EFF6FF', border: '1px solid #DBEAFE' }}>
        <Info className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: '#3B82F6' }} />
        <p className="text-xs" style={{ color: '#1E40AF' }}>
          Paste one or more public URLs (https://). The backend will fetch each file and store it in the Knowledge Base S3 bucket for ingestion.
        </p>
      </div>

      {/* URL rows */}
      <div className="space-y-2">
        {urls.map((url, i) => (
          <div key={i} className="flex gap-2 items-center">
            <div className="relative flex-1">
              <Link2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: '#C4C9D4' }} />
              <input
                type="url"
                value={url}
                onChange={e => updateUrl(i, e.target.value)}
                placeholder="https://example.com/document.pdf"
                className="dialog-input pl-9"
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addRow(); } }}
              />
            </div>
            {urls.length > 1 && (
              <button onClick={() => removeRow(i)} className="p-2 rounded-lg flex-shrink-0 transition-colors"
                style={{ color: '#9CA3AF', background: '#F9FAFB' }}
                onMouseEnter={e => { e.currentTarget.style.color = '#DC2626'; e.currentTarget.style.background = '#FEF2F2'; }}
                onMouseLeave={e => { e.currentTarget.style.color = '#9CA3AF'; e.currentTarget.style.background = '#F9FAFB'; }}>
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Add URL + count */}
      <div className="flex items-center justify-between">
        <button onClick={addRow} className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors"
          style={{ color: RED, background: '#FFF5F5' }}>
          <span className="text-lg leading-none">+</span> Add another URL
        </button>
        {validUrls.length > 0 && (
          <span className="text-xs" style={{ color: '#9CA3AF' }}>
            {validUrls.length} valid URL{validUrls.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Import button */}
      <button onClick={handleImport} disabled={!validUrls.length || importing}
        className="w-full py-3 text-base rounded-lg font-semibold text-white flex items-center justify-center gap-2 transition-all"
        style={{
          background: (!validUrls.length || importing) ? '#E5E7EB' : RED,
          cursor: (!validUrls.length || importing) ? 'not-allowed' : 'pointer'
        }}>
        {importing
          ? <><Loader className="w-5 h-5 animate-spin" />Fetching &amp; importing...</>
          : <><Link2 className="w-5 h-5" />Import from URL{validUrls.length > 1 ? 's' : ''}</>}
      </button>

      {/* Results */}
      {results && (
        <div className="dialog-card p-4" style={{ borderLeft: `4px solid ${RED}`, background: '#FFF5F5' }}>
          <p className="text-sm font-semibold mb-2" style={{ color: '#1A1A2E' }}>
            {results.imported} / {results.total} imported successfully
          </p>
          <div className="space-y-1.5">
            {results.results?.map((r, i) => (
              <div key={i} className="flex items-start gap-2">
                {r.status === 'success'
                  ? <CheckCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: RED }} />
                  : <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" style={{ color: '#DC2626' }} />}
                <div className="min-w-0">
                  <p className="text-xs font-mono truncate" style={{ color: '#6B7280' }}>{r.url}</p>
                  {r.status === 'success'
                    ? <p className="text-xs" style={{ color: RED }}>→ {r.s3_key}</p>
                    : <p className="text-xs" style={{ color: '#DC2626' }}>{r.error}</p>}
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs mt-3" style={{ color: '#9CA3AF' }}>Queryable in ~1-2 min after KB ingestion.</p>
        </div>
      )}

      {error && (
        <div className="dialog-card p-4" style={{ borderLeft: '4px solid #DC2626' }}>
          <div className="flex gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" style={{ color: '#DC2626' }} />
            <div className="flex-1">
              <p className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Error</p>
              <p className="text-xs mt-1" style={{ color: '#6B7280' }}>{error}</p>
              <button onClick={() => setError(null)} className="mt-2 text-xs underline" style={{ color: '#DC2626' }}>Dismiss</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Web Upload Tab ────────────────────────────────────────────────────────────
const WebUploadTab = () => {
  const { user } = useAuth();
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);

  const validateFile = (f) => {
    if (!f) return false;
    if (f.size > MAX_FILE_SIZE) { setError('File exceeds 500MB limit'); return false; }
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['pdf','doc','docx','txt','xlsx','xls','csv','png','jpg','jpeg','gif','webp','mp4','mp3','wav'].includes(ext)) {
      setError(`Unsupported type: .${ext}`); return false;
    }
    return true;
  };

  const pickFile = (f) => { setResult(null); setError(null); setProgress(0); if (validateFile(f)) setFile(f); };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setError(null); setResult(null); setProgress(0);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('user_id', user?.email || 'guest');
      const res = await axios.post(`${API_BASE}/api/upload/direct`, form, {
        headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000,
        onUploadProgress: (e) => setProgress(Math.round((e.loaded * 100) / e.total)),
      });
      setResult(res.data); setFile(null); setProgress(0);
    } catch (e) { setError(e.response?.data?.detail || e.message || 'Upload failed'); }
    finally { setUploading(false); }
  };

  const FileIcon = file ? getFileIcon(file.name) : UploadIcon;

  return (
    <div className="space-y-4">
      <div onDrop={(e) => { e.preventDefault(); setIsDragging(false); const f = e.dataTransfer.files[0]; if (f) pickFile(f); }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        className="rounded-xl p-10 text-center transition-all"
        style={{ border: `2px dashed ${error ? '#DC2626' : file ? '#059669' : isDragging ? RED : '#E8EAF0'}`, background: file ? '#ECFDF5' : isDragging ? '#FEF9F9' : '#FAFBFC' }}>
        {file ? (
          <div className="flex flex-col items-center">
            <FileIcon className="w-10 h-10 mb-3" style={{ color: RED }} />
            <p className="font-semibold mb-1" style={{ color: '#1A1A2E' }}>{file.name}</p>
            <p className="text-xs mb-4" style={{ color: '#9CA3AF' }}>{fmt(file.size)}</p>
            {progress > 0 && progress < 100 && (
              <div className="w-full max-w-xs mb-4">
                <div className="h-2 rounded-full" style={{ background: '#E5E7EB' }}>
                  <div className="h-full rounded-full" style={{ background: RED, width: `${progress}%`, transition: 'width 0.3s' }} />
                </div>
                <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>{progress}%</p>
              </div>
            )}
            <button onClick={() => setFile(null)} className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg" style={{ background: '#FEF2F2', color: RED }}>
              <X className="w-3 h-3" /> Remove
            </button>
          </div>
        ) : (
          <div>
            <div className="inline-flex p-5 rounded-full mb-4" style={{ background: 'rgba(228,0,43,0.08)' }}>
              <UploadIcon className="w-10 h-10" style={{ color: RED }} />
            </div>
            <p className="font-semibold text-base mb-2" style={{ color: '#1A1A2E' }}>Drag & drop your file here</p>
            <p className="text-sm mb-4" style={{ color: '#9CA3AF' }}>or browse from your computer</p>
            <label className="inline-block px-6 py-2.5 rounded-lg font-semibold text-white text-sm cursor-pointer" style={{ background: RED }}>
              Browse Files
              <input type="file" onChange={(e) => { if (e.target.files[0]) pickFile(e.target.files[0]); }} className="hidden"
                accept=".pdf,.doc,.docx,.txt,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.gif,.webp,.mp4,.mp3,.wav" />
            </label>
            <p className="text-xs mt-4" style={{ color: '#C4C9D4' }}>PDF, DOCX, XLSX, images, MP4, MP3 · Max 500MB</p>
          </div>
        )}
      </div>
      <button onClick={handleUpload} disabled={!file || uploading}
        className="w-full py-3 text-base rounded-lg font-semibold text-white flex items-center justify-center gap-2 transition-all"
        style={{
          background: (!file || uploading) ? '#E5E7EB' : RED,
          cursor: (!file || uploading) ? 'not-allowed' : 'pointer'
        }}>
        {uploading ? <><Loader className="w-5 h-5 animate-spin" />Uploading {progress}%</> : <><UploadIcon className="w-5 h-5" />Upload &amp; Ingest</>}
      </button>
      <ResultPanel result={result} error={error} onDismissError={() => setError(null)} />

      {/* KB Ingestion Status */}
      {result?.s3_key && <SyncStatusCard s3Key={result.s3_key} filename={result.filename || file?.name || 'Uploaded file'} />}
    </div>
  );
};

// ── Main Upload page ──────────────────────────────────────────────────────────
const Upload = () => {
  const [tab, setTab] = useState('web');

  return (
    <div className="min-h-screen pb-8">
      {/* Indeterminate progress bar CSS */}
      <style>{`
        @keyframes indeterminate {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(350%); }
        }
      `}</style>

      <PageHeader title="Upload Documents" subtitle="Web UI · Google Drive · S3 Repository" />
      <div className="p-6">
        <div className="max-w-3xl mx-auto">
          {/* Tabs */}
          <div className="flex flex-wrap gap-2 mb-5">
            <Tab active={tab === 'web'}   onClick={() => setTab('web')}   icon={UploadIcon} label="Web Upload" />
            <Tab active={tab === 'drive'} onClick={() => setTab('drive')} icon={HardDrive}  label="Google Drive" />
            <Tab active={tab === 's3'}    onClick={() => setTab('s3')}    icon={Database}   label="S3 Repository" />
          </div>

          <div className="dialog-card p-6">
            {tab === 'web'   && <WebUploadTab />}
            {tab === 'drive' && <SharedDriveTab />}
            {tab === 's3'    && <S3ImportTab />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
