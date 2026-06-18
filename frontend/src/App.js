import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ChatSessionProvider } from './context/ChatSessionContext';
import { ToastProvider } from './context/ToastContext';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Upload from './pages/UploadNew';
import Retrieve from './pages/Retrieve';

// Protected Route wrapper
function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <svg className="animate-spin h-12 w-12 text-pink-500 mx-auto mb-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

// Main App Layout with Sidebar
function AppLayout({ children }) {
  return (
    <div className="flex min-h-screen" style={{ background: '#F5F6F8' }}>
      <Sidebar />
      <div className="flex-1 ml-0 md:ml-64 transition-all">
        {children}
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
        <ChatSessionProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/auth-callback" element={<AuthCallback />} />

          {/* Protected routes with sidebar */}
          <Route path="/" element={
            <ProtectedRoute>
              <AppLayout>
                <Navigate to="/upload" replace />
              </AppLayout>
            </ProtectedRoute>
          } />

          <Route path="/upload" element={
            <ProtectedRoute>
              <AppLayout>
                <Upload />
              </AppLayout>
            </ProtectedRoute>
          } />

          <Route path="/retrieve" element={
            <ProtectedRoute>
              <AppLayout>
                <Retrieve />
              </AppLayout>
            </ProtectedRoute>
          } />
        </Routes>
        </ChatSessionProvider>
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
