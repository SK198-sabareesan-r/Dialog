/**
 * GoogleDriveBrowser - Folder navigation UI for Google Drive import
 *
 * Features:
 * - Browse My Drive and Shared Drives
 * - Breadcrumb navigation
 * - Folder/file selection
 * - Bulk import to S3 + Bedrock KB
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Folder, File, ChevronRight, Home, Loader,
  CheckCircle, AlertTriangle, HardDrive
} from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';

function GoogleDriveBrowser() {
  const { driveToken, user } = useAuth();

  const [sharedDrives, setSharedDrives] = useState([]);
  const [selectedDrive, setSelectedDrive] = useState(null); // null = My Drive
  const [breadcrumb, setBreadcrumb] = useState([{ id: 'root', name: 'My Drive' }]);
  const [folders, setFolders] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState(null);
  const [error, setError] = useState(null);

  // Load shared drives on mount
  useEffect(() => {
    loadSharedDrives();
  }, [driveToken]);

  // Load folder contents when drive or folder changes
  useEffect(() => {
    if (driveToken) {
      browseFolder(breadcrumb[breadcrumb.length - 1].id);
    }
  }, [selectedDrive, driveToken]);

  const loadSharedDrives = async () => {
    if (!driveToken) return;

    try {
      const response = await axios.get(`${API_BASE}/api/google-drive/shared-drives`, {
        params: { google_access_token: driveToken }
      });
      setSharedDrives(response.data.shared_drives || []);
    } catch (err) {
      console.error('Failed to load shared drives:', err);
    }
  };

  const browseFolder = async (folderId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE}/api/google-drive/browse`, {
        params: {
          google_access_token: driveToken,
          folder_id: folderId,
          drive_id: selectedDrive
        }
      });

      setFolders(response.data.folders || []);
      setFiles(response.data.files || []);
      setSelectedFiles(new Set()); // Clear selection on navigate
    } catch (err) {
      console.error('Failed to browse folder:', err);
      setError('Failed to load folder contents');
    } finally {
      setLoading(false);
    }
  };

  const handleDriveChange = (driveId) => {
    setSelectedDrive(driveId);
    if (driveId) {
      const drive = sharedDrives.find(d => d.id === driveId);
      setBreadcrumb([{ id: 'root', name: drive?.name || 'Shared Drive' }]);
    } else {
      setBreadcrumb([{ id: 'root', name: 'My Drive' }]);
    }
  };

  const handleFolderClick = (folder) => {
    setBreadcrumb([...breadcrumb, { id: folder.id, name: folder.name }]);
    browseFolder(folder.id);
  };

  const handleBreadcrumbClick = (index) => {
    const newBreadcrumb = breadcrumb.slice(0, index + 1);
    setBreadcrumb(newBreadcrumb);
    browseFolder(newBreadcrumb[newBreadcrumb.length - 1].id);
  };

  const handleFileSelect = (fileId) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelectedFiles(newSelected);
  };

  const handleImport = async () => {
    if (selectedFiles.size === 0) return;

    setImporting(true);
    setImportStatus(null);
    setError(null);

    try {
      const filesToImport = files.filter(f => selectedFiles.has(f.id));

      const response = await axios.post(`${API_BASE}/api/google-drive/import`, {
        files: filesToImport,
        google_access_token: driveToken,
        user_id: user.email,
        drive_id: selectedDrive
      });

      setImportStatus({
        success: true,
        count: response.data.count,
        message: response.data.message
      });
      setSelectedFiles(new Set());
    } catch (err) {
      console.error('Import failed:', err);
      setImportStatus({
        success: false,
        message: err.response?.data?.detail || 'Import failed'
      });
    } finally {
      setImporting(false);
    }
  };

  if (!driveToken) {
    return (
      <div className="p-6 text-center">
        <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
        <p className="text-gray-600">Google Drive access not available. Please log out and sign in again.</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Drive Selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Drive
        </label>
        <select
          value={selectedDrive || ''}
          onChange={(e) => handleDriveChange(e.target.value || null)}
          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
          style={{ borderColor: '#E8EAF0' }}
        >
          <option value="">My Drive</option>
          {sharedDrives.map(drive => (
            <option key={drive.id} value={drive.id}>{drive.name}</option>
          ))}
        </select>
      </div>

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4 text-sm">
        <Home className="w-4 h-4 text-gray-400" />
        {breadcrumb.map((crumb, index) => (
          <React.Fragment key={crumb.id}>
            <button
              onClick={() => handleBreadcrumbClick(index)}
              className="text-pink-600 hover:text-pink-700 font-medium"
              disabled={index === breadcrumb.length - 1}
            >
              {crumb.name}
            </button>
            {index < breadcrumb.length - 1 && (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Status Messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {importStatus && (
        <div className={`mb-4 p-4 rounded-lg flex items-start gap-3 ${
          importStatus.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          {importStatus.success ? (
            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          )}
          <p className={`text-sm ${importStatus.success ? 'text-green-700' : 'text-red-700'}`}>
            {importStatus.message}
          </p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="w-8 h-8 animate-spin text-pink-500" />
        </div>
      )}

      {/* Folders and Files */}
      {!loading && (
        <>
          {/* Folders */}
          {folders.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Folders</h3>
              <div className="space-y-2">
                {folders.map(folder => (
                  <button
                    key={folder.id}
                    onClick={() => handleFolderClick(folder)}
                    className="w-full flex items-center gap-3 p-3 rounded-lg border hover:bg-pink-50 hover:border-pink-300 transition-all"
                    style={{ borderColor: '#E8EAF0' }}
                  >
                    <Folder className="w-5 h-5 text-yellow-500 flex-shrink-0" />
                    <span className="text-sm font-medium text-gray-700">{folder.name}</span>
                    <ChevronRight className="w-4 h-4 text-gray-400 ml-auto" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Files */}
          {files.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Files</h3>
              <div className="space-y-2">
                {files.map(file => (
                  <label
                    key={file.id}
                    className="flex items-center gap-3 p-3 rounded-lg border hover:bg-gray-50 cursor-pointer"
                    style={{ borderColor: '#E8EAF0' }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(file.id)}
                      onChange={() => handleFileSelect(file.id)}
                      className="w-4 h-4 text-pink-600 rounded focus:ring-pink-500"
                    />
                    <File className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
                      <p className="text-xs text-gray-500">
                        {file.size ? `${(file.size / 1024).toFixed(1)} KB` : 'Unknown size'}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {folders.length === 0 && files.length === 0 && (
            <div className="text-center py-12">
              <HardDrive className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p className="text-gray-500">This folder is empty</p>
            </div>
          )}
        </>
      )}

      {/* Import Button */}
      {selectedFiles.size > 0 && (
        <div className="mt-6 p-4 bg-pink-50 border border-pink-200 rounded-lg">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-700">
              <span className="font-semibold">{selectedFiles.size}</span> file(s) selected
            </p>
            <button
              onClick={handleImport}
              disabled={importing}
              className="px-6 py-2 rounded-lg text-white font-medium transition-all flex items-center gap-2"
              style={{ background: importing ? '#CBD5E0' : '#E91E8C' }}
            >
              {importing ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Importing...
                </>
              ) : (
                'Import Selected Files'
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default GoogleDriveBrowser;
