import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw, Info, Zap, Shield, Database, GitBranch } from 'lucide-react';
import PipelineFlow3DEnhanced from '../components/PipelineFlow3DEnhanced';

const PINK = '#E91E8C';

const stages = [
  { id: 'sources', name: 'Data Sources', dot: '#6B7280', description: 'Web UI, Shared Drives, File Repos' },
  { id: 'raw', name: 'S3 Raw Zone', dot: '#1565C0', description: 'Centralized storage for uploaded files' },
  { id: 'orchestration', name: 'Step Functions', dot: '#6B7280', description: 'Orchestrates the ingestion workflow' },
  { id: 'bda', name: 'Parser', dot: '#D97706', description: 'Parses and processes documents' },
  { id: 'processed', name: 'S3 Processed', dot: '#1565C0', description: 'Stores parsed and chunked content' },
  { id: 'dlq', name: 'Dead Letter Queue', dot: '#DC2626', description: 'Handles failed ingestions' },
  { id: 'kb', name: 'Knowledge Base', dot: PINK, description: 'AWS Bedrock Knowledge Base' },
  { id: 'opensearch', name: 'OpenSearch', dot: '#059669', description: 'Vector database for semantic search' },
  { id: 'retrieval', name: 'Retrieval + IAM', dot: '#7C3AED', description: 'Secure document retrieval' },
];

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

const Pipeline3D = () => {
  const [activeStage, setActiveStage] = useState(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const [animationSpeed, setAnimationSpeed] = useState(1500);
  const [currentStageInfo, setCurrentStageInfo] = useState(null);

  useEffect(() => {
    if (activeStage) {
      const stage = stages.find((s) => s.id === activeStage);
      setCurrentStageInfo(stage);
    } else {
      setCurrentStageInfo(null);
    }
  }, [activeStage]);

  const animatePipeline = () => {
    if (isAnimating) {
      setIsAnimating(false);
      setActiveStage(null);
      return;
    }

    setIsAnimating(true);
    let i = 0;
    const intervalId = setInterval(() => {
      if (i >= stages.length) {
        clearInterval(intervalId);
        setIsAnimating(false);
        setActiveStage(null);
        return;
      }
      setActiveStage(stages[i].id);
      i++;
    }, animationSpeed);
  };

  const reset = () => {
    setActiveStage(null);
    setIsAnimating(false);
    setCurrentStageInfo(null);
  };

  return (
    <div className="min-h-screen pb-8">
      <PageHeader
        title="3D Pipeline Visualization"
        subtitle="Interactive visualization of the ingestion pipeline"
      />

      <div className="p-6">
        {/* Info Banner */}
        <div className="dialog-card p-4 mb-6" style={{ background: '#EFF6FF', borderColor: '#DBEAFE' }}>
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: '#3B82F6' }} />
            <div className="flex-1">
              <p className="text-xs leading-relaxed" style={{ color: '#1E40AF' }}>
                This 3D visualization shows the complete data ingestion pipeline. Use the controls below to
                animate the flow or click individual stages to highlight them. Rotate, zoom, and pan the
                canvas for different viewing angles.
              </p>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="dialog-card p-5 mb-5">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-3 flex-wrap">
              <button
                onClick={animatePipeline}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold text-sm text-white transition-all shadow-sm"
                style={{
                  background: isAnimating
                    ? 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)'
                    : `linear-gradient(135deg, ${PINK} 0%, #C91578 100%)`,
                }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.9')}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                aria-label={isAnimating ? 'Stop animation' : 'Start animation'}
              >
                {isAnimating ? (
                  <>
                    <Pause className="w-4 h-4" /> Stop Animation
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" /> Animate Flow
                  </>
                )}
              </button>

              <button
                onClick={reset}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg font-semibold text-sm transition-all"
                style={{
                  background: '#F9FAFB',
                  color: '#6B7280',
                  border: '1px solid #E8EAF0',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#FDF0F7';
                  e.currentTarget.style.color = PINK;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#F9FAFB';
                  e.currentTarget.style.color = '#6B7280';
                }}
                aria-label="Reset visualization"
              >
                <RotateCcw className="w-4 h-4" /> Reset
              </button>

              <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg" style={{ background: '#F9FAFB' }}>
                <label className="text-xs font-semibold" style={{ color: '#6B7280' }}>
                  Speed:
                </label>
                <select
                  value={animationSpeed}
                  onChange={(e) => setAnimationSpeed(Number(e.target.value))}
                  className="text-xs font-medium px-2 py-1 rounded border-none outline-none"
                  style={{ background: '#FFFFFF', color: '#1A1A2E' }}
                  disabled={isAnimating}
                >
                  <option value={3000}>Slow</option>
                  <option value={1500}>Normal</option>
                  <option value={800}>Fast</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs" style={{ color: '#9CA3AF' }}>
              <span className="hidden md:inline">Controls:</span>
              <span className="px-2 py-1 rounded" style={{ background: '#F9FAFB' }}>
                Mouse: Rotate
              </span>
              <span className="px-2 py-1 rounded" style={{ background: '#F9FAFB' }}>
                Scroll: Zoom
              </span>
              <span className="px-2 py-1 rounded" style={{ background: '#F9FAFB' }}>
                Drag: Pan
              </span>
            </div>
          </div>
        </div>

        {/* Current Stage Info */}
        {currentStageInfo && (
          <div
            className="dialog-card p-5 mb-5 animate-in"
            style={{ borderLeft: `4px solid ${currentStageInfo.dot}` }}
          >
            <div className="flex items-start gap-3">
              <div
                className="p-2.5 rounded-lg flex-shrink-0"
                style={{ background: `${currentStageInfo.dot}15` }}
              >
                <div className="w-3 h-3 rounded-full" style={{ background: currentStageInfo.dot }} />
              </div>
              <div>
                <h3 className="text-base font-semibold mb-1" style={{ color: '#1A1A2E' }}>
                  {currentStageInfo.name}
                </h3>
                <p className="text-sm" style={{ color: '#6B7280' }}>
                  {currentStageInfo.description}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 3D Canvas */}
        <div className="dialog-card overflow-hidden mb-6" style={{ height: 600 }}>
          <PipelineFlow3DEnhanced activeStage={activeStage} />
        </div>

        {/* Stage Legend */}
        <div className="dialog-card p-6 mb-6">
          <h2 className="text-sm font-semibold mb-4" style={{ color: '#1A1A2E' }}>
            Pipeline Stages
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {stages.map((s) => (
              <button
                key={s.id}
                onClick={() => setActiveStage(s.id === activeStage ? null : s.id)}
                className="flex items-start gap-3 px-4 py-3 rounded-lg text-sm transition-all text-left group"
                style={{
                  background: activeStage === s.id ? `${PINK}10` : '#F9FAFB',
                  border: `1px solid ${activeStage === s.id ? PINK : '#E8EAF0'}`,
                }}
                onMouseEnter={(e) => {
                  if (activeStage !== s.id) {
                    e.currentTarget.style.background = '#FDF0F7';
                  }
                }}
                onMouseLeave={(e) => {
                  if (activeStage !== s.id) {
                    e.currentTarget.style.background = '#F9FAFB';
                  }
                }}
              >
                <span
                  className="w-3 h-3 rounded-full flex-shrink-0 mt-0.5"
                  style={{ background: s.dot }}
                />
                <div className="flex-1">
                  <p
                    className="font-semibold mb-1"
                    style={{ color: activeStage === s.id ? PINK : '#1A1A2E' }}
                  >
                    {s.name}
                  </p>
                  <p className="text-xs leading-relaxed" style={{ color: '#6B7280' }}>
                    {s.description}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="dialog-card p-5" style={{ borderTop: `3px solid ${PINK}` }}>
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-lg" style={{ background: `${PINK}15` }}>
                <GitBranch className="w-5 h-5" style={{ color: PINK }} />
              </div>
              <h3 className="font-semibold text-sm" style={{ color: '#1A1A2E' }}>
                Ingestion Path
              </h3>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: '#6B7280' }}>
              Data flows from multiple sources → Raw S3 → Parser → Processed S3 → Knowledge Base →
              OpenSearch for semantic retrieval.
            </p>
          </div>

          <div className="dialog-card p-5" style={{ borderTop: '3px solid #DC2626' }}>
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-lg" style={{ background: '#FEE2E2' }}>
                <Zap className="w-5 h-5" style={{ color: '#DC2626' }} />
              </div>
              <h3 className="font-semibold text-sm" style={{ color: '#1A1A2E' }}>
                Error Handling
              </h3>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: '#6B7280' }}>
              Failed jobs retry with exponential backoff. After 3 attempts, they're sent to the DLQ with
              CloudWatch alerts.
            </p>
          </div>

          <div className="dialog-card p-5" style={{ borderTop: '3px solid #7C3AED' }}>
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-lg" style={{ background: '#EDE9FE' }}>
                <Shield className="w-5 h-5" style={{ color: '#7C3AED' }} />
              </div>
              <h3 className="font-semibold text-sm" style={{ color: '#1A1A2E' }}>
                Access Control
              </h3>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: '#6B7280' }}>
              Retrieval enforces IAM + metadata filtering to ensure users only access authorized documents
              based on User/Team IDs.
            </p>
          </div>

          <div className="dialog-card p-5" style={{ borderTop: '3px solid #059669' }}>
            <div className="flex items-start gap-3 mb-3">
              <div className="p-2 rounded-lg" style={{ background: '#DCFCE7' }}>
                <Database className="w-5 h-5" style={{ color: '#059669' }} />
              </div>
              <h3 className="font-semibold text-sm" style={{ color: '#1A1A2E' }}>
                Vector Search
              </h3>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: '#6B7280' }}>
              OpenSearch Serverless stores embeddings generated by Amazon Titan for fast semantic similarity
              search across documents.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Pipeline3D;
