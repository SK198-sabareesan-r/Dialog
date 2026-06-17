import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertCircle, Activity, CheckCircle, XCircle, Clock, RefreshCw,
  TrendingUp, AlertTriangle, Info, Eye
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v1';
const PINK = '#E91E8C';
const REFRESH_INTERVAL = 15000; // 15 seconds

const PageHeader = ({ title, subtitle, onRefresh, isRefreshing, lastUpdated }) => (
  <div
    className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm"
    style={{ borderColor: '#E8EAF0' }}
  >
    <div className="flex-1">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold" style={{ color: '#1A1A2E' }}>{title}</h1>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs font-medium" style={{ color: '#059669' }}>Live</span>
        </div>
      </div>
      {subtitle && <p className="text-xs mt-0.5" style={{ color: '#9CA3AF' }}>{subtitle}</p>}
    </div>
    <div className="flex items-center gap-4">
      {lastUpdated && (
        <span className="text-xs" style={{ color: '#9CA3AF' }}>
          Updated: {lastUpdated.toLocaleTimeString()}
        </span>
      )}
      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all"
        style={{
          color: PINK,
          background: isRefreshing ? '#F3F4F6' : 'transparent',
          border: `1px solid ${isRefreshing ? '#E5E7EB' : PINK}`,
          cursor: isRefreshing ? 'not-allowed' : 'pointer',
          opacity: isRefreshing ? 0.6 : 1,
        }}
        onMouseEnter={(e) => {
          if (!isRefreshing) e.currentTarget.style.background = '#FDF0F7';
        }}
        onMouseLeave={(e) => {
          if (!isRefreshing) e.currentTarget.style.background = 'transparent';
        }}
        aria-label="Refresh metrics"
      >
        <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
        <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
      </button>
    </div>
  </div>
);

const MetricCard = ({ icon: Icon, title, value, accentColor, description, trend, trendValue }) => (
  <div
    className="dialog-card p-5 relative overflow-hidden"
    style={{ borderTop: `3px solid ${accentColor}` }}
  >
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: '#9CA3AF' }}>
          {title}
        </p>
        <h3 className="text-3xl font-bold mt-1.5" style={{ color: '#1A1A2E' }}>{value}</h3>
        <div className="flex items-center gap-2 mt-2">
          {description && (
            <p className="text-xs" style={{ color: '#9CA3AF' }}>{description}</p>
          )}
          {trend && trendValue !== undefined && (
            <span
              className="flex items-center gap-1 text-xs font-medium"
              style={{
                color: trend === 'up' ? '#059669' : trend === 'down' ? '#DC2626' : '#6B7280',
              }}
            >
              {trend === 'up' ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingUp className="w-3 h-3 rotate-180" />
              )}
              {trendValue}%
            </span>
          )}
        </div>
      </div>
      <div className="p-3 rounded-xl" style={{ background: `${accentColor}15` }}>
        <Icon className="w-6 h-6" style={{ color: accentColor }} />
      </div>
    </div>
  </div>
);

const StatusBadge = ({ status }) => {
  const map = {
    SUCCEEDED: { bg: '#ECFDF5', color: '#059669', icon: CheckCircle },
    FAILED: { bg: '#FEF2F2', color: '#DC2626', icon: XCircle },
    RUNNING: { bg: '#FFF7ED', color: '#D97706', icon: Activity },
    TIMED_OUT: { bg: '#FEFCE8', color: '#CA8A04', icon: Clock },
    ABORTED: { bg: '#F9FAFB', color: '#6B7280', icon: AlertTriangle },
  };
  const s = map[status] || map.ABORTED;
  const IconComponent = s.icon;

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{ background: s.bg, color: s.color }}
    >
      <IconComponent className="w-3 h-3" />
      {status}
    </span>
  );
};

const hourlyData = [
  { hour: '00:00', count: 5 },
  { hour: '04:00', count: 3 },
  { hour: '08:00', count: 12 },
  { hour: '12:00', count: 18 },
  { hour: '16:00', count: 15 },
  { hour: '20:00', count: 8 },
];

const Monitoring = () => {
  const [dlqStatus, setDlqStatus] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedExecution, setSelectedExecution] = useState(null);

  const fetchData = useCallback(async (isManualRefresh = false) => {
    try {
      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const [dlqRes, execRes] = await Promise.all([
        axios.get(`${API_BASE}/monitoring/dlq`, { timeout: 10000 })
          .catch(() => ({ data: { dlq_message_count: 0 } })),
        axios.get(`${API_BASE}/ingest/executions?max_results=100`, { timeout: 10000 })
          .catch(() => ({ data: { executions: [] } })),
      ]);

      setDlqStatus(dlqRes.data);
      setExecutions(execRes.data.executions || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Monitoring fetch error:', err);
      setError(err.message || 'Failed to load monitoring data');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    const interval = setInterval(() => {
      fetchData(true);
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchData]);

  const handleManualRefresh = () => {
    if (!isRefreshing) {
      fetchData(true);
    }
  };

  const counts = executions.reduce(
    (acc, e) => {
      acc[e.status] = (acc[e.status] || 0) + 1;
      return acc;
    },
    { SUCCEEDED: 0, FAILED: 0, RUNNING: 0, TIMED_OUT: 0, ABORTED: 0 }
  );

  const pieData = [
    { name: 'Succeeded', value: counts.SUCCEEDED, color: '#059669' },
    { name: 'Failed', value: counts.FAILED, color: '#DC2626' },
    { name: 'Running', value: counts.RUNNING, color: '#D97706' },
    { name: 'Timed Out', value: counts.TIMED_OUT, color: '#CA8A04' },
  ].filter((d) => d.value > 0);

  const tooltip = {
    background: '#FFFFFF',
    border: '1px solid #E8EAF0',
    borderRadius: 8,
    fontSize: 12,
    color: '#1A1A2E',
    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
  };

  if (loading && !isRefreshing) {
    return (
      <div className="min-h-screen">
        <PageHeader
          title="Monitoring"
          subtitle="Real-time pipeline metrics"
          onRefresh={handleManualRefresh}
          isRefreshing={false}
        />
        <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
          <div className="flex flex-col items-center gap-3">
            <Activity className="w-8 h-8 animate-spin" style={{ color: PINK }} />
            <p className="text-sm font-medium" style={{ color: '#1A1A2E' }}>Loading metrics</p>
            <p className="text-xs" style={{ color: '#9CA3AF' }}>Please wait...</p>
          </div>
        </div>
      </div>
    );
  }

  const successRate = executions.length > 0
    ? Math.round((counts.SUCCEEDED / executions.length) * 100)
    : 0;

  return (
    <div className="min-h-screen pb-8">
      <PageHeader
        title="Monitoring"
        subtitle="Real-time pipeline metrics and operational insights"
        onRefresh={handleManualRefresh}
        isRefreshing={isRefreshing}
        lastUpdated={lastUpdated}
      />

      <div className="p-6">
        {/* Auto-refresh info */}
        {lastUpdated && (
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs" style={{ color: '#9CA3AF' }}>
              Auto-refresh every 15 seconds
            </p>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="dialog-card p-4 mb-6" style={{ background: '#FEF2F2', borderColor: '#FEE2E2' }}>
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" style={{ color: '#DC2626' }} />
              <div className="flex-1">
                <h3 className="text-sm font-semibold" style={{ color: '#DC2626' }}>
                  Failed to load monitoring data
                </h3>
                <p className="text-xs mt-1" style={{ color: '#991B1B' }}>{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* DLQ Warning */}
        {dlqStatus?.threshold_exceeded && (
          <div className="dialog-card p-4 mb-6" style={{ background: '#FFF7ED', borderColor: '#FED7AA' }}>
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" style={{ color: '#D97706' }} />
              <div className="flex-1">
                <h3 className="text-sm font-semibold" style={{ color: '#D97706' }}>
                  Dead Letter Queue Threshold Exceeded
                </h3>
                <p className="text-xs mt-1" style={{ color: '#92400E' }}>
                  {dlqStatus.dlq_message_count} messages in DLQ. Investigate failed ingestions immediately.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Metric cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <MetricCard
            icon={CheckCircle}
            title="Succeeded"
            value={counts.SUCCEEDED}
            accentColor="#059669"
            description="Completed successfully"
            trend={successRate >= 90 ? 'up' : 'down'}
            trendValue={successRate}
          />
          <MetricCard
            icon={XCircle}
            title="Failed"
            value={counts.FAILED}
            accentColor="#DC2626"
            description={counts.FAILED > 5 ? 'Needs attention' : 'Normal'}
          />
          <MetricCard
            icon={Clock}
            title="Running"
            value={counts.RUNNING}
            accentColor="#D97706"
            description={counts.RUNNING > 0 ? 'In progress' : 'Idle'}
          />
          <MetricCard
            icon={AlertCircle}
            title="DLQ Messages"
            value={dlqStatus?.dlq_message_count || 0}
            accentColor={dlqStatus?.threshold_exceeded ? '#DC2626' : PINK}
            description={dlqStatus?.threshold_exceeded ? 'Above threshold!' : 'Normal'}
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
          {/* Pie Chart */}
          <div className="dialog-card p-6">
            <h2 className="text-sm font-semibold mb-4" style={{ color: '#1A1A2E' }}>
              Status Distribution
            </h2>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    dataKey="value"
                  >
                    {pieData.map((d, i) => (
                      <Cell key={i} fill={d.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltip} />
                  <Legend
                    wrapperStyle={{ fontSize: 12, paddingTop: 20 }}
                    iconType="circle"
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64" style={{ color: '#C4C9D4' }}>
                <div className="text-center">
                  <Activity className="w-12 h-12 mx-auto mb-3 opacity-20" />
                  <p className="text-sm">No execution data yet</p>
                </div>
              </div>
            )}
          </div>

          {/* Bar Chart */}
          <div className="dialog-card p-6">
            <h2 className="text-sm font-semibold mb-4" style={{ color: '#1A1A2E' }}>
              Hourly Activity
            </h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="hour" stroke="#D1D5DB" tick={{ fontSize: 11, fill: '#6B7280' }} />
                <YAxis stroke="#D1D5DB" tick={{ fontSize: 11, fill: '#6B7280' }} />
                <Tooltip contentStyle={tooltip} />
                <Bar dataKey="count" fill={PINK} radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Executions table */}
        <div className="dialog-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>
              Recent Executions
            </h2>
            <span className="text-xs" style={{ color: '#9CA3AF' }}>
              Showing {Math.min(executions.length, 20)} of {executions.length} executions
            </span>
          </div>
          {executions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="dialog-table">
                <thead>
                  <tr>
                    <th>Execution ID</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {executions.slice(0, 20).map((exec, i) => {
                    const start = new Date(exec.startDate);
                    const stop = exec.stopDate ? new Date(exec.stopDate) : null;
                    const duration = stop
                      ? `${((stop - start) / 1000).toFixed(0)}s`
                      : exec.status === 'RUNNING'
                      ? 'Running...'
                      : 'N/A';
                    return (
                      <tr key={exec.executionArn || i}>
                        <td className="font-medium" title={exec.executionArn}>
                          {exec.name || 'N/A'}
                        </td>
                        <td>
                          <StatusBadge status={exec.status} />
                        </td>
                        <td style={{ color: '#9CA3AF' }}>{start.toLocaleString()}</td>
                        <td style={{ color: '#6B7280', fontSize: '0.8rem' }}>{duration}</td>
                        <td>
                          <button
                            onClick={() => setSelectedExecution(exec)}
                            className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded transition-colors"
                            style={{ color: PINK }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = '#FDF0F7')}
                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                          >
                            <Eye className="w-3 h-3" />
                            View
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12" style={{ color: '#9CA3AF' }}>
              <Activity className="w-10 h-10 mx-auto mb-3 opacity-20" />
              <p className="text-sm font-medium">No executions found</p>
              <p className="text-xs mt-1">Executions will appear here once ingestion jobs start</p>
            </div>
          )}
        </div>

        {/* Execution Detail Modal */}
        {selectedExecution && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedExecution(null)}
          >
            <div
              className="dialog-card p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold" style={{ color: '#1A1A2E' }}>
                    Execution Details
                  </h3>
                  <p className="text-xs mt-1" style={{ color: '#9CA3AF' }}>
                    {selectedExecution.name}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedExecution(null)}
                  className="p-2 rounded-lg transition-colors"
                  style={{ color: '#6B7280' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#F3F4F6')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="font-semibold mb-1" style={{ color: '#6B7280' }}>Status</p>
                  <StatusBadge status={selectedExecution.status} />
                </div>
                <div>
                  <p className="font-semibold mb-1" style={{ color: '#6B7280' }}>Execution ARN</p>
                  <p className="font-mono text-xs break-all" style={{ color: '#1A1A2E' }}>
                    {selectedExecution.executionArn}
                  </p>
                </div>
                <div>
                  <p className="font-semibold mb-1" style={{ color: '#6B7280' }}>Started</p>
                  <p style={{ color: '#1A1A2E' }}>
                    {new Date(selectedExecution.startDate).toLocaleString()}
                  </p>
                </div>
                {selectedExecution.stopDate && (
                  <div>
                    <p className="font-semibold mb-1" style={{ color: '#6B7280' }}>Completed</p>
                    <p style={{ color: '#1A1A2E' }}>
                      {new Date(selectedExecution.stopDate).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Monitoring;
