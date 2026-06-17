import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Upload from './pages/Upload';
import Retrieve from './pages/Retrieve';

function App() {
  return (
    <Router>
      <div className="flex min-h-screen" style={{ background: '#F5F6F8' }}>
        {/* Fixed sidebar */}
        <Sidebar />
        {/* Main content — offset by sidebar width */}
        <div className="flex-1 ml-0 md:ml-64 transition-all">
          <Routes>
            <Route path="/"         element={<Navigate to="/upload" replace />} />
            <Route path="/upload"   element={<Upload />} />
            <Route path="/retrieve" element={<Retrieve />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
