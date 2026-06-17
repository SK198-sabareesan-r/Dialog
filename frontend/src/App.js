import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Retrieve from './pages/Retrieve';
import Monitoring from './pages/Monitoring';

function App() {
  return (
    <Router>
      <div className="flex min-h-screen" style={{ background: '#F5F6F8' }}>
        {/* Fixed sidebar */}
        <Sidebar />
        {/* Main content — offset by sidebar width */}
        <div className="flex-1 ml-0 md:ml-64 transition-all">
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/upload"     element={<Upload />} />
            <Route path="/retrieve"   element={<Retrieve />} />
            <Route path="/monitoring" element={<Monitoring />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
