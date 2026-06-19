# BDA Pipeline Frontend - 3D Visualization

Modern React frontend with 3D visualization for the BDA Knowledge Base Ingestion Pipeline.

## Features

- **Real-time Dashboard**: Monitor ingestion metrics and activity
- **File Upload**: Drag-and-drop interface for document ingestion
- **Document Retrieval**: Search knowledge base with access control
- **Monitoring**: View execution status, metrics, and DLQ alerts
- **Responsive Design**: Works on desktop and tablet devices
- **Modern UI**: Clean, professional interface with intuitive navigation

## Tech Stack

- React 18
- React Router (navigation)
- Tailwind CSS (styling)
- Axios (API calls)
- Lucide React (icons)

## Installation

```bash
cd frontend
npm install
```

## Configuration

The frontend connects to the backend API at `http://localhost:8001` by default.

To change the API endpoint, update the `API_BASE` constant in the page components.

## Running the App

```bash
npm start
```

The app will open at `http://localhost:3000`

## Available Pages

1. **Dashboard** (`/`)
   - Overview metrics (Total Ingestions, Success Rate, DLQ Messages, Active Jobs)
   - Recent executions with status
   - Real-time data refresh

2. **Upload** (`/upload`)
   - Drag-and-drop file upload
   - Source type selection
   - User/Team ID configuration
   - Automatic metadata extraction

3. **Retrieve** (`/retrieve`)
   - Search knowledge base
   - Access control filters
   - Results with metadata and relevance scores

4. **Monitoring** (`/monitoring`)
   - Real-time execution status
   - DLQ monitoring
   - Execution history and filtering

## Building for Production

```bash
npm run build
```

The optimized production build will be in the `build/` directory.

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   └── Sidebar.jsx
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   ├── Upload.jsx
│   │   ├── Retrieve.jsx
│   │   └── Monitoring.jsx
│   ├── App.js
│   ├── index.js
│   └── index.css
├── package.json
└── tailwind.config.js
```

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge
