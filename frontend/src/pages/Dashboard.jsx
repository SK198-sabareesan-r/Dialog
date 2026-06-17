import React, { useState, useEffect, useCallback } from 'react';
import {
  Upload, CheckCircle, AlertCircle, Activity, Database, RefreshCw,
  Clock, AlertTriangle
} from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v1';
const PINK = '#E91E8C';
const REFRESH_INTERVAL = 30000; // 30 seconds

/* ── Top header bar with refresh ── */
const PageHeader = ({ title, onRefresh, isRefreshing }) => (
  <div
    className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm"
    style={{ borderColor: '#E8EAF0' }}
  >
    <h1 className="text-lg font-semibold" style={{ color: '#1A1A2E' }}>{title}</h1>
    <button
      onClick={onRefresh}
      disabled={isRefreshing}
      className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all"
      style={{
        color: PINK,
        background: isRefreshing ? '#F3F4F6' : 'transparent',
        border: `1px solid ${isRefreshing ? '#E5E7EB' : PINK}`,
        cursor: isRefreshing ? 'not-allowed' : 'pointer',
        opacity: isRefreshing ? 0.6 : 1
      }}
      onMouseEnter={(e) => {
        if (!isRefreshing) e.currentTarget.style.background = '#FDF0F7';
      }}
      onMouseLeave={(e) => {
        if (!isRefreshing) e.currentTarget.style.background = 'transparent';
      }}
      aria-label="Refresh dashboard"
    >
      <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
      <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
    </button>
  </div>
);

/* ── Stat card ── */
const StatCard = ({ icon: Icon, title, value, accent, subtitle }) => (
  <div className="dialog-card p-5">
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <p className="text-xs font-medium uppercase tracking-wide" style={{ color: '#9CA3AF' }}>
          {title}
        </p>
        <h3 className="text-3xl font-bold mt-1.5" style={{ color: '#1A1A2E' }}>
          {value}
        </h3>
        {subtitle && (
          <p className="text-xs mt-2" style={{ color: '#9CA3AF' }}>{subtitle}</p>
        )}
      </div>
      <div
        className="p-3 rounded-xl"
        style={{ background: `${accent}12` }}
      >
        <Icon className="w-6 h-6" style={{ color: accent }} />
      </div>
    </div>
  </div>
);

/* ── Status badge ── */
const StatusBadge = ({ status }) => {
  const map = {
    SUCCEEDED: { bg: '#ECFDF5', color: '#059669', label: 'Succeeded', icon: CheckCircle },
    FAILED:    { bg: '#FEF2F2', color: '#DC2626', label: 'Failed', icon: AlertCircle },
    RUNNING:   { bg: '#FFF7ED', color: '#D97706', label: 'Running', icon: Activity },
    TIMED_OUT: { bg: '#FEFCE8', color: '#CA8A04', label: 'Timed Out', icon: Clock },
    ABORTED:   { bg: '#F9FAFB', color: '#6B7280', label: 'Aborted', icon: AlertTriangle },
  };
  const s = map[status] || map.ABORTED;
  const IconComponent = s.icon;

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{ background: s.bg, color: s.color }}
    >
      <IconComponent className="w-3 h-3" />
      {s.label}
    </span>
  );
};

/* ── Error Alert ── */
const ErrorAlert = ({ message, onRetry }) => (
  <div className="dialog-card p-4 mb-6" style={{ background: '#FEF2F2', borderColor: '#FEE2E2' }}>
    <div className="flex items-start gap-3">
      <AlertCircle className="w-5 h-5 flex-shrink-0" style={{ color: '#DC2626' }} />
      <div className="flex-1">
        <h3 className="text-sm font-semibold" style={{ color: '#DC2626' }}>Failed to load dashboard data</h3>
        <p className="text-xs mt-1" style={{ color: '#991B1B' }}>{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 text-xs font-medium underline"
            style={{ color: '#DC2626' }}
          >
            Try again
          </button>
        )}
      </div>
    </div>
  </div>
);

const Dashboard = () => {
  const [stats, setStats] = useState({ total: 0, successRate: 0, dlq: 0, active: 0 });
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadData = useCallback(async (isManualRefresh = false) => {
    try {
      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const [exRes, dlqRes] = await Promise.all([
        axios.get(`${API_BASE}/ingest/executions?max_results=50`, { timeout: 10000 })
          .catch(() => ({ data: { executions: [] } })),
        axios.get(`${API_BASE}/monitoring/dlq`, { timeout: 10000 })
          .catch(() => ({ data: { dlq_message_count: 0 } })),
      ]);

      const list = exRes.data.executions || [];
      const succeeded = list.filter(e => e.status === 'SUCCEEDED').length;

      setStats({
        total: list.length,
        successRate: list.length ? Math.round((succeeded / list.length) * 100) : 0,
        dlq: dlqRes.data.dlq_message_count || 0,
        active: list.filter(e => e.status === 'RUNNING').length,
      });
      setRecent(list.slice(0, 5));
    } catch (err) {
      console.error('Dashboard load error:', err);
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadData(true);
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [loadData]);

  const handleManualRefresh = () => {
    if (!isRefreshing) {
      loadData(true);
    }
  };

  if (loading && !isRefreshing) {
    return (
      <div className="min-h-screen">
        <PageHeader title="Dashboard" onRefresh={handleManualRefresh} isRefreshing={false} />
        <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
          <div className="flex flex-col items-center gap-3">
            <Activity className="w-8 h-8 animate-spin" style={{ color: PINK }} />
            <p className="text-sm font-medium" style={{ color: '#1A1A2E' }}>Loading dashboard</p>
            <p className="text-xs" style={{ color: '#9CA3AF' }}>Please wait...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-8">
      <PageHeader
        title="Dashboard"
        onRefresh={handleManualRefresh}
        isRefreshing={isRefreshing}
      />

      <div className="p-6">
        {/* Error alert */}
        {error && <ErrorAlert message={error} onRetry={() => loadData()} />}

        {/* DLQ Warning */}
        {stats.dlq > 10 && (
          <div className="dialog-card p-4 mb-6" style={{ background: '#FFF7ED', borderColor: '#FED7AA' }}>
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" style={{ color: '#D97706' }} />
              <div className="flex-1">
                <h3 className="text-sm font-semibold" style={{ color: '#92400E' }}>High DLQ Message Count</h3>
                <p className="text-xs mt-1" style={{ color: '#92400E' }}>
                  Dead Letter Queue has {stats.dlq} messages (threshold: 10). Please investigate failed ingestions.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <StatCard
            icon={Upload}
            title="Total Ingestions"
            value={stats.total}
            accent={PINK}
          />
          <StatCard
            icon={CheckCircle}
            title="Success Rate"
            value={`${stats.successRate}%`}
            accent={stats.successRate >= 90 ? '#059669' : stats.successRate >= 70 ? '#D97706' : '#DC2626'}
          />
          <StatCard
            icon={AlertCircle}
            title="DLQ Messages"
            value={stats.dlq}
            accent={stats.dlq > 10 ? '#DC2626' : '#059669'}
            subtitle={stats.dlq > 10 ? 'Above threshold' : 'Normal'}
          />
          <StatCard
            icon={Activity}
            title="Active Jobs"
            value={stats.active}
            accent={stats.active > 0 ? '#D97706' : '#6B7280'}
            subtitle={stats.active > 0 ? 'In progress' : 'Idle'}
          />
        </div>

        {/* Recent activity */}
        <div className="dialog-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold" style={{ color: '#1A1A2E' }}>Recent Activity</h2>
            {recent.length > 0 && (
              <span className="text-xs" style={{ color: '#9CA3AF' }}>
                Last {recent.length} executions
              </span>
            )}
          </div>
          {recent.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="dialog-table">
                <thead>
                  <tr>
                    <th>Execution ID</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((a, i) => (
                    <tr key={a.executionArn || i}>
                      <td className="font-medium" title={a.executionArn}>
                        {a.name || 'N/A'}
                      </td>
                      <td><StatusBadge status={a.status} /></td>
                      <td style={{ color: '#9CA3AF' }}>
                        {a.startDate ? new Date(a.startDate).toLocaleString() : 'N/A'}
                      </td>
                      <td style={{ color: '#6B7280', fontSize: '0.8rem' }}>
                        {a.stopDate && a.startDate
                          ? `${Math.round((new Date(a.stopDate) - new Date(a.startDate)) / 1000)}s`
                          : a.status === 'RUNNING' ? 'In progress' : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12" style={{ color: '#9CA3AF' }}>
              <Database className="w-10 h-10 mx-auto mb-3 opacity-20" />
              <p className="text-sm font-medium">No recent activity</p>
              <p className="text-xs mt-1">Ingestion jobs will appear here once started</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
