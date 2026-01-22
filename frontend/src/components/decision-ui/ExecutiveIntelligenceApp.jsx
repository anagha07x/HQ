import React, { useState, useEffect } from 'react';
import {
  Upload, FileSpreadsheet, BarChart3, AlertTriangle, Shield,
  Gavel, BookOpen, ChevronRight, Loader2, RefreshCw,
  Database, Layers, Link2, Target, X, Menu, Home,
  ChevronDown, ChevronUp, ExternalLink, TrendingUp, TrendingDown,
  Activity, Zap, Clock, CheckCircle, XCircle, Eye
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ============================================================
// UTILITY FUNCTIONS
// ============================================================
const formatNumber = (num, decimals = 0) => {
  if (num === null || num === undefined) return 'N/A';
  if (Math.abs(num) >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (Math.abs(num) >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toFixed(decimals);
};

const formatPercent = (num) => {
  if (num === null || num === undefined) return 'N/A';
  return `${Math.abs(num).toFixed(1)}%`;
};

// ============================================================
// MAIN APP
// ============================================================
const ExecutiveIntelligenceApp = () => {
  const [currentView, setCurrentView] = useState('overview');
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [intelligence, setIntelligence] = useState(null);
  const [ledger, setLedger] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [industry, setIndustry] = useState('generic');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [selectedTheme, setSelectedTheme] = useState(null);

  useEffect(() => {
    fetchDatasets();
  }, []);

  useEffect(() => {
    if (selectedDataset?.id) {
      fetchIntelligence(selectedDataset.id);
    }
  }, [selectedDataset, industry]);

  const fetchDatasets = async () => {
    try {
      const res = await fetch(`${API_URL}/api/datasets`);
      const data = await res.json();
      if (data.status === 'success') {
        setDatasets(data.datasets || []);
        if (data.datasets?.length > 0 && !selectedDataset) {
          setSelectedDataset(data.datasets[0]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch datasets:', err);
    }
  };

  const fetchIntelligence = async (datasetId) => {
    setLoading(true);
    try {
      const [intRes, ledgerRes] = await Promise.all([
        fetch(`${API_URL}/api/executive-intelligence`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataset_id: datasetId, industry })
        }),
        fetch(`${API_URL}/api/ledger?dataset_id=${datasetId}`)
      ]);

      const [intData, ledgerData] = await Promise.all([
        intRes.json(),
        ledgerRes.json()
      ]);

      if (intData.status === 'success') setIntelligence(intData);
      if (ledgerData.status === 'success') setLedger(ledgerData);
    } catch (err) {
      console.error('Failed to fetch intelligence:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadProgress('uploading');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      
      if (data.status === 'success') {
        setUploadProgress('analyzing');
        const analysisRes = await fetch(`${API_URL}/api/analyze-intelligence`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataset_id: data.dataset_id })
        });
        const analysisData = await analysisRes.json();
        
        if (analysisData.status === 'success') {
          await fetchDatasets();
          setSelectedDataset({ id: data.dataset_id, filename: file.name, has_analysis: true });
          setUploadProgress(null);
        }
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadProgress(null);
    }
  };

  const handleApprove = async (decisionId) => {
    try {
      await fetch(`${API_URL}/api/decisions/${decisionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'executive', notes: '' })
      });
      await fetchIntelligence(selectedDataset.id);
    } catch (err) {
      console.error('Approve failed:', err);
    }
  };

  const handleReject = async (decisionId) => {
    try {
      await fetch(`${API_URL}/api/decisions/${decisionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'executive', notes: '' })
      });
      await fetchIntelligence(selectedDataset.id);
    } catch (err) {
      console.error('Reject failed:', err);
    }
  };

  const navItems = [
    { id: 'overview', label: 'Executive Summary', icon: Home },
    { id: 'themes', label: 'Decision Themes', icon: Layers },
    { id: 'gaps', label: 'Variance Analysis', icon: AlertTriangle },
    { id: 'constraints', label: 'Constraints', icon: Shield },
    { id: 'decisions', label: 'Action Center', icon: Gavel },
    { id: 'ledger', label: 'Decision Ledger', icon: BookOpen }
  ];

  return (
    <div className="min-h-screen bg-[#0D0D0F] text-white flex font-['Inter',sans-serif]">
      {/* Sidebar */}
      <aside className={`${sidebarCollapsed ? 'w-16' : 'w-64'} bg-[#111113] border-r border-[#1E1E21] flex flex-col transition-all duration-300`}>
        {/* Logo */}
        <div className="h-16 border-b border-[#1E1E21] flex items-center justify-between px-4">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-[#C9A24D] to-[#8B7033] rounded flex items-center justify-center">
                <Gavel className="w-4 h-4 text-[#0D0D0F]" />
              </div>
              <span className="font-semibold tracking-tight text-[#E8E8E8]">ChanksHQ</span>
            </div>
          )}
          <button 
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-2 hover:bg-[#1A1A1D] rounded transition-colors"
          >
            <Menu className="w-4 h-4 text-[#6B6B70]" />
          </button>
        </div>

        {/* Dataset & Industry */}
        {!sidebarCollapsed && (
          <div className="p-4 border-b border-[#1E1E21] space-y-3">
            <div>
              <label className="text-[10px] text-[#6B6B70] uppercase tracking-widest">Dataset</label>
              <select
                value={selectedDataset?.id || ''}
                onChange={(e) => setSelectedDataset(datasets.find(d => d.id === e.target.value))}
                className="mt-1.5 w-full bg-[#0D0D0F] border border-[#2A2A2E] rounded px-3 py-2 text-sm text-[#E8E8E8] focus:ring-1 focus:ring-[#C9A24D] focus:border-[#C9A24D] outline-none"
              >
                {datasets.map(ds => (
                  <option key={ds.id} value={ds.id}>{ds.filename}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-[#6B6B70] uppercase tracking-widest">Industry Context</label>
              <select
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="mt-1.5 w-full bg-[#0D0D0F] border border-[#2A2A2E] rounded px-3 py-2 text-sm text-[#E8E8E8] focus:ring-1 focus:ring-[#C9A24D] focus:border-[#C9A24D] outline-none"
              >
                <option value="generic">Generic</option>
                <option value="pharma">Pharmaceutical</option>
                <option value="retail">Retail</option>
                <option value="saas">SaaS</option>
              </select>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-0.5">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded transition-colors ${
                currentView === item.id
                  ? 'bg-[#C9A24D]/10 text-[#C9A24D]'
                  : 'text-[#8B8B90] hover:bg-[#1A1A1D] hover:text-[#E8E8E8]'
              }`}
            >
              <item.icon className="w-4 h-4" />
              {!sidebarCollapsed && <span className="text-sm">{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Upload */}
        <div className="p-4 border-t border-[#1E1E21]">
          <label className={`flex items-center justify-center gap-2 px-4 py-2.5 bg-[#C9A24D] hover:bg-[#D4AF5A] rounded cursor-pointer transition-all ${uploadProgress ? 'opacity-50 pointer-events-none' : ''}`}>
            {uploadProgress ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-[#0D0D0F]" />
                {!sidebarCollapsed && <span className="text-sm font-medium text-[#0D0D0F]">
                  {uploadProgress === 'uploading' ? 'Uploading...' : 'Analyzing...'}
                </span>}
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 text-[#0D0D0F]" />
                {!sidebarCollapsed && <span className="text-sm font-medium text-[#0D0D0F]">Upload Dataset</span>}
              </>
            )}
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.json"
              onChange={handleFileUpload}
              className="hidden"
              disabled={!!uploadProgress}
            />
          </label>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin text-[#C9A24D] mx-auto mb-3" />
              <p className="text-sm text-[#6B6B70]">Loading intelligence...</p>
            </div>
          </div>
        ) : (
          <>
            {currentView === 'overview' && <ExecutiveSummaryPage data={intelligence} />}
            {currentView === 'themes' && (
              <ThemesPage 
                data={intelligence} 
                selectedTheme={selectedTheme}
                onSelectTheme={setSelectedTheme}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            )}
            {currentView === 'gaps' && <VarianceAnalysisPage data={intelligence} />}
            {currentView === 'constraints' && <ConstraintsPage data={intelligence} />}
            {currentView === 'decisions' && (
              <ActionCenterPage 
                data={intelligence} 
                onApprove={handleApprove}
                onReject={handleReject}
              />
            )}
            {currentView === 'ledger' && <LedgerPage data={ledger} />}
          </>
        )}
      </main>
    </div>
  );
};

// ============================================================
// EXECUTIVE SUMMARY PAGE
// ============================================================
const ExecutiveSummaryPage = ({ data }) => {
  if (!data || data.status !== 'success') {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-center">
          <FileSpreadsheet className="w-12 h-12 text-[#2A2A2E] mx-auto mb-4" />
          <h2 className="text-lg font-medium text-[#E8E8E8] mb-2">No Analysis Available</h2>
          <p className="text-sm text-[#6B6B70]">Upload a dataset to begin analysis.</p>
        </div>
      </div>
    );
  }

  const { executive_summary, sheets, entities, decision_themes, theme_summary } = data;
  const metrics = executive_summary?.key_metrics || {};

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className={`inline-flex items-center gap-2 px-3 py-1 rounded text-xs font-medium mb-4 ${
          executive_summary?.status === 'critical' ? 'bg-red-500/10 text-red-400' :
          executive_summary?.status === 'warning' ? 'bg-[#C9A24D]/10 text-[#C9A24D]' :
          'bg-emerald-500/10 text-emerald-400'
        }`}>
          <Activity className="w-3 h-3" />
          {executive_summary?.status_label || 'Analysis Complete'}
        </div>
        <h1 className="text-2xl font-semibold text-[#E8E8E8] tracking-tight mb-3">
          {executive_summary?.headline || 'Executive Intelligence Summary'}
        </h1>
        <p className="text-[#8B8B90] leading-relaxed max-w-3xl">
          {executive_summary?.narrative}
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard 
          label="Critical Variances"
          value={metrics.critical_variances || 0}
          variant="critical"
        />
        <MetricCard 
          label="Total Impact"
          value={formatNumber(metrics.critical_impact_value)}
          sublabel="Value at risk"
        />
        <MetricCard 
          label="Blocking Constraints"
          value={metrics.blocking_constraints || 0}
          variant={metrics.blocking_constraints > 0 ? 'warning' : 'default'}
        />
        <MetricCard 
          label="Decision Themes"
          value={theme_summary?.total_themes || 0}
          sublabel={`${theme_summary?.critical_themes || 0} critical`}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-2 gap-6">
        {/* Sheets */}
        <div className="bg-[#111113] rounded-lg border border-[#1E1E21] overflow-hidden">
          <div className="px-4 py-3 border-b border-[#1E1E21]">
            <h2 className="text-sm font-medium text-[#E8E8E8]">Data Sources</h2>
          </div>
          <div className="divide-y divide-[#1E1E21]">
            {sheets?.slice(0, 6).map((sheet, idx) => (
              <div key={idx} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileSpreadsheet className="w-4 h-4 text-[#6B6B70]" />
                  <span className="text-sm text-[#E8E8E8]">{sheet.name}</span>
                </div>
                <span className="text-xs px-2 py-1 bg-[#1A1A1D] rounded text-[#8B8B90]">
                  {sheet.translated_role}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Entities */}
        <div className="bg-[#111113] rounded-lg border border-[#1E1E21] overflow-hidden">
          <div className="px-4 py-3 border-b border-[#1E1E21]">
            <h2 className="text-sm font-medium text-[#E8E8E8]">Tracked Dimensions</h2>
          </div>
          <div className="divide-y divide-[#1E1E21]">
            {entities?.slice(0, 6).map((entity, idx) => (
              <div key={idx} className="px-4 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm text-[#E8E8E8]">{entity.executive_explanation?.name || entity.canonical_name}</p>
                  <p className="text-xs text-[#6B6B70] mt-0.5">{entity.executive_explanation?.significance?.slice(0, 50)}...</p>
                </div>
                <span className="text-lg font-semibold text-[#C9A24D]">
                  {entity.cardinality?.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Themes */}
      {decision_themes?.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-medium text-[#E8E8E8] mb-4">Priority Decision Themes</h2>
          <div className="grid grid-cols-2 gap-4">
            {decision_themes.slice(0, 4).map((theme, idx) => (
              <ThemeCard key={idx} theme={theme} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================
// THEMES PAGE
// ============================================================
const ThemesPage = ({ data, selectedTheme, onSelectTheme, onApprove, onReject }) => {
  if (!data || data.status !== 'success') {
    return <EmptyState icon={Layers} title="No Themes Available" />;
  }

  const { decision_themes, theme_summary } = data;

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[#E8E8E8] tracking-tight mb-2">Decision Themes</h1>
        <p className="text-sm text-[#6B6B70]">
          {theme_summary?.total_decisions || 0} decisions grouped into {theme_summary?.total_themes || 0} actionable themes
        </p>
      </div>

      {/* Theme Grid */}
      <div className="space-y-4">
        {decision_themes?.map((theme, idx) => (
          <ThemeCard 
            key={idx} 
            theme={theme} 
            expanded={selectedTheme === theme.id}
            onToggle={() => onSelectTheme(selectedTheme === theme.id ? null : theme.id)}
            onApprove={onApprove}
            onReject={onReject}
          />
        ))}
      </div>
    </div>
  );
};

// ============================================================
// VARIANCE ANALYSIS PAGE
// ============================================================
const VarianceAnalysisPage = ({ data }) => {
  const [severityFilter, setSeverityFilter] = useState('critical');

  if (!data || data.status !== 'success') {
    return <EmptyState icon={AlertTriangle} title="No Variance Data" />;
  }

  const gaps = data.critical_gaps || [];
  const filteredGaps = severityFilter === 'all' ? gaps : gaps.filter(g => g.severity === severityFilter);

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[#E8E8E8] tracking-tight mb-2">Variance Analysis</h1>
          <p className="text-sm text-[#6B6B70]">
            {gaps.length} critical variances identified for review
          </p>
        </div>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-[#111113] border border-[#2A2A2E] rounded px-3 py-2 text-sm text-[#E8E8E8]"
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical Only</option>
          <option value="warning">Warning Only</option>
        </select>
      </div>

      {/* Gap Cards */}
      <div className="space-y-3">
        {filteredGaps.map((gap, idx) => (
          <GapCard key={idx} gap={gap} />
        ))}
      </div>
    </div>
  );
};

// ============================================================
// CONSTRAINTS PAGE
// ============================================================
const ConstraintsPage = ({ data }) => {
  if (!data || data.status !== 'success') {
    return <EmptyState icon={Shield} title="No Constraints Identified" />;
  }

  const constraints = data.blocking_constraints || [];

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[#E8E8E8] tracking-tight mb-2">Execution Constraints</h1>
        <p className="text-sm text-[#6B6B70]">
          {constraints.length} blocking constraints requiring attention
        </p>
      </div>

      <div className="space-y-3">
        {constraints.map((constraint, idx) => (
          <ConstraintCard key={idx} constraint={constraint} />
        ))}
      </div>
    </div>
  );
};

// ============================================================
// ACTION CENTER PAGE
// ============================================================
const ActionCenterPage = ({ data, onApprove, onReject }) => {
  const [filter, setFilter] = useState('all');

  if (!data || data.status !== 'success') {
    return <EmptyState icon={Gavel} title="No Decisions Generated" />;
  }

  const decisions = data.top_decisions || [];

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[#E8E8E8] tracking-tight mb-2">Action Center</h1>
          <p className="text-sm text-[#6B6B70]">
            Review and act on AI-generated recommendations
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {decisions.map((decision, idx) => (
          <DecisionCard 
            key={idx} 
            decision={decision}
            onApprove={onApprove}
            onReject={onReject}
          />
        ))}
      </div>
    </div>
  );
};

// ============================================================
// LEDGER PAGE
// ============================================================
const LedgerPage = ({ data }) => {
  if (!data || data.status !== 'success' || !data.entries?.length) {
    return <EmptyState icon={BookOpen} title="Decision Ledger Empty" subtitle="Approved or rejected decisions will appear here." />;
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[#E8E8E8] tracking-tight mb-2">Decision Ledger</h1>
        <p className="text-sm text-[#6B6B70]">
          {data.summary?.total_entries || 0} decisions recorded
        </p>
      </div>

      <div className="bg-[#111113] rounded-lg border border-[#1E1E21] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-[#0D0D0F]">
              <th className="px-4 py-3 text-left text-[10px] font-medium text-[#6B6B70] uppercase tracking-wider">Decision</th>
              <th className="px-4 py-3 text-left text-[10px] font-medium text-[#6B6B70] uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-left text-[10px] font-medium text-[#6B6B70] uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-left text-[10px] font-medium text-[#6B6B70] uppercase tracking-wider">Acted By</th>
              <th className="px-4 py-3 text-left text-[10px] font-medium text-[#6B6B70] uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1E1E21]">
            {data.entries?.map((entry, idx) => (
              <tr key={idx} className="hover:bg-[#1A1A1D] transition-colors">
                <td className="px-4 py-3">
                  <p className="text-sm text-[#E8E8E8] truncate max-w-md">{entry.summary}</p>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-[#8B8B90] capitalize">{entry.decision_type?.replace(/_/g, ' ')}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded ${
                    entry.status === 'approved'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-red-500/10 text-red-400'
                  }`}>
                    {entry.status === 'approved' ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                    {entry.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-[#8B8B90]">{entry.acted_by}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-[#6B6B70]">
                    {entry.acted_at ? new Date(entry.acted_at).toLocaleDateString() : 'N/A'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================
// COMPONENTS
// ============================================================

const MetricCard = ({ label, value, sublabel, variant = 'default' }) => (
  <div className={`bg-[#111113] rounded-lg border p-4 ${
    variant === 'critical' ? 'border-red-500/20' :
    variant === 'warning' ? 'border-[#C9A24D]/20' :
    'border-[#1E1E21]'
  }`}>
    <p className="text-[10px] text-[#6B6B70] uppercase tracking-widest mb-2">{label}</p>
    <p className={`text-2xl font-semibold ${
      variant === 'critical' ? 'text-red-400' :
      variant === 'warning' ? 'text-[#C9A24D]' :
      'text-[#E8E8E8]'
    }`}>{value}</p>
    {sublabel && <p className="text-xs text-[#6B6B70] mt-1">{sublabel}</p>}
  </div>
);

const ThemeCard = ({ theme, expanded, onToggle, onApprove, onReject }) => {
  const [isExpanded, setIsExpanded] = useState(expanded || false);
  
  useEffect(() => {
    setIsExpanded(expanded);
  }, [expanded]);

  return (
    <div className="bg-[#111113] rounded-lg border border-[#1E1E21] overflow-hidden">
      <div 
        className="p-4 cursor-pointer hover:bg-[#1A1A1D] transition-colors"
        onClick={() => onToggle ? onToggle() : setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded ${
                theme.severity === 'critical' ? 'bg-red-500/10 text-red-400' :
                theme.severity === 'warning' ? 'bg-[#C9A24D]/10 text-[#C9A24D]' :
                'bg-[#2A2A2E] text-[#8B8B90]'
              }`}>
                {theme.theme_type?.replace(/_/g, ' ')}
              </span>
              <span className="text-xs text-[#6B6B70]">{theme.decision_count} decisions</span>
            </div>
            <h3 className="text-[#E8E8E8] font-medium">{theme.headline}</h3>
            <p className="text-sm text-[#6B6B70] mt-1">{theme.summary}</p>
          </div>
          <div className="flex items-center gap-4 ml-4">
            <div className="text-right">
              <p className="text-xs text-[#6B6B70]">Urgency</p>
              <p className="text-lg font-semibold text-[#C9A24D]">{Math.round((theme.max_urgency || 0) * 100)}%</p>
            </div>
            {isExpanded ? (
              <ChevronUp className="w-5 h-5 text-[#6B6B70]" />
            ) : (
              <ChevronDown className="w-5 h-5 text-[#6B6B70]" />
            )}
          </div>
        </div>
      </div>
      
      {isExpanded && theme.representative_decision && (
        <div className="border-t border-[#1E1E21] p-4 bg-[#0D0D0F]">
          <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-3">Representative Decision</p>
          <div className="bg-[#111113] rounded border border-[#1E1E21] p-4">
            <p className="text-sm text-[#E8E8E8] mb-2">{theme.representative_decision.summary}</p>
            <p className="text-xs text-[#6B6B70]">{theme.representative_decision.reasoning?.slice(0, 150)}...</p>
            {onApprove && (
              <div className="flex gap-2 mt-4">
                <button 
                  onClick={(e) => { e.stopPropagation(); onReject?.(theme.representative_decision.id); }}
                  className="px-3 py-1.5 bg-[#1A1A1D] hover:bg-[#2A2A2E] rounded text-sm text-[#8B8B90] transition-colors"
                >
                  Reject
                </button>
                <button 
                  onClick={(e) => { e.stopPropagation(); onApprove?.(theme.representative_decision.id); }}
                  className="px-3 py-1.5 bg-[#C9A24D] hover:bg-[#D4AF5A] rounded text-sm text-[#0D0D0F] font-medium transition-colors"
                >
                  Approve
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const GapCard = ({ gap }) => {
  const [expanded, setExpanded] = useState(false);
  const explanation = gap.executive_explanation || {};

  return (
    <div className="bg-[#111113] rounded-lg border border-[#1E1E21] overflow-hidden">
      <div 
        className="p-4 cursor-pointer hover:bg-[#1A1A1D] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded ${
                gap.severity === 'critical' ? 'bg-red-500/10 text-red-400' :
                gap.severity === 'warning' ? 'bg-[#C9A24D]/10 text-[#C9A24D]' :
                'bg-[#2A2A2E] text-[#8B8B90]'
              }`}>
                {gap.severity}
              </span>
              <span className={`text-xs ${gap.direction === 'under' ? 'text-red-400' : 'text-emerald-400'}`}>
                {gap.direction === 'under' ? 'Below Target' : 'Above Target'}
              </span>
            </div>
            <h3 className="text-[#E8E8E8] font-medium">{explanation.headline || gap.metric_name}</h3>
            <p className="text-sm text-[#6B6B70] mt-1 truncate">{gap.entity_id}</p>
          </div>
          <div className="flex items-center gap-6 ml-4">
            <div className="text-right">
              <p className="text-xs text-[#6B6B70]">Variance</p>
              <p className={`text-lg font-semibold ${gap.direction === 'under' ? 'text-red-400' : 'text-emerald-400'}`}>
                {formatPercent(gap.percentage_gap)}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-[#6B6B70]">Impact</p>
              <p className="text-lg font-semibold text-[#E8E8E8]">{formatNumber(Math.abs(gap.absolute_gap || 0))}</p>
            </div>
            {expanded ? <ChevronUp className="w-5 h-5 text-[#6B6B70]" /> : <ChevronDown className="w-5 h-5 text-[#6B6B70]" />}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-[#1E1E21] p-4 bg-[#0D0D0F] space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-1">Target</p>
              <p className="text-xl font-semibold text-[#C9A24D]">{formatNumber(gap.plan_value)}</p>
            </div>
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-1">Actual</p>
              <p className="text-xl font-semibold text-[#E8E8E8]">{formatNumber(gap.actual_value)}</p>
            </div>
          </div>
          
          {explanation.summary && (
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-2">Analysis</p>
              <p className="text-sm text-[#8B8B90] leading-relaxed">{explanation.summary}</p>
            </div>
          )}
          
          {explanation.recommended_action && (
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-2">Recommended Action</p>
              <p className="text-sm text-[#E8E8E8]">{explanation.recommended_action}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ConstraintCard = ({ constraint }) => {
  const explanation = constraint.executive_explanation || {};
  
  return (
    <div className="bg-[#111113] rounded-lg border border-[#1E1E21] p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className={`text-xs px-2 py-0.5 rounded ${
              constraint.constraint_type === 'blocking' ? 'bg-red-500/10 text-red-400' :
              constraint.constraint_type === 'deadline' ? 'bg-[#C9A24D]/10 text-[#C9A24D]' :
              'bg-[#2A2A2E] text-[#8B8B90]'
            }`}>
              {explanation.type || constraint.constraint_type}
            </span>
          </div>
          <h3 className="text-[#E8E8E8] font-medium">{explanation.headline || 'Constraint Identified'}</h3>
          <p className="text-sm text-[#6B6B70] mt-1">{explanation.summary || constraint.description}</p>
        </div>
      </div>
      
      {explanation.recommendation && (
        <div className="mt-4 pt-4 border-t border-[#1E1E21]">
          <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-1">Recommendation</p>
          <p className="text-sm text-[#8B8B90]">{explanation.recommendation}</p>
        </div>
      )}
    </div>
  );
};

const DecisionCard = ({ decision, onApprove, onReject }) => {
  const [expanded, setExpanded] = useState(false);
  const explanation = decision.executive_explanation || {};
  const isActed = decision.ledger_status === 'approved' || decision.ledger_status === 'rejected';

  return (
    <div className={`bg-[#111113] rounded-lg border overflow-hidden ${
      isActed 
        ? decision.ledger_status === 'approved' ? 'border-emerald-500/20' : 'border-red-500/20'
        : 'border-[#1E1E21]'
    }`}>
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded uppercase ${
                explanation.severity === 'critical' ? 'bg-red-500/10 text-red-400' :
                explanation.severity === 'warning' ? 'bg-[#C9A24D]/10 text-[#C9A24D]' :
                'bg-[#2A2A2E] text-[#8B8B90]'
              }`}>
                {decision.decision_type?.replace(/_/g, ' ')}
              </span>
              {isActed && (
                <span className={`text-xs px-2 py-0.5 rounded ${
                  decision.ledger_status === 'approved' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                }`}>
                  {decision.ledger_status}
                </span>
              )}
            </div>
            <h3 className="text-[#E8E8E8] font-medium">{explanation.headline || decision.summary}</h3>
            <p className="text-sm text-[#6B6B70] mt-1">{explanation.summary?.slice(0, 150)}...</p>
          </div>
          <button 
            onClick={() => setExpanded(!expanded)}
            className="p-2 hover:bg-[#1A1A1D] rounded transition-colors ml-4"
          >
            {expanded ? <ChevronUp className="w-5 h-5 text-[#6B6B70]" /> : <ChevronDown className="w-5 h-5 text-[#6B6B70]" />}
          </button>
        </div>

        {/* Scores */}
        <div className="grid grid-cols-3 gap-4 mt-4">
          <ScoreBar label="Impact" value={decision.impact_score} color="red" />
          <ScoreBar label="Confidence" value={decision.confidence_score} color="blue" />
          <ScoreBar label="Urgency" value={decision.urgency_score} color="gold" />
        </div>
      </div>

      {expanded && (
        <div className="border-t border-[#1E1E21] p-4 bg-[#0D0D0F] space-y-4">
          {explanation.business_impact && (
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-2">Business Impact</p>
              <p className="text-sm text-[#8B8B90] leading-relaxed">{explanation.business_impact}</p>
            </div>
          )}
          
          {explanation.root_cause && (
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-2">Root Cause</p>
              <p className="text-sm text-[#8B8B90] leading-relaxed">{explanation.root_cause}</p>
            </div>
          )}
          
          {explanation.recommended_action && (
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-2">Recommended Action</p>
              <p className="text-sm text-[#E8E8E8]">{explanation.recommended_action}</p>
            </div>
          )}
          
          {explanation.confidence_rationale && (
            <div>
              <p className="text-xs text-[#6B6B70] uppercase tracking-widest mb-2">Confidence Rationale</p>
              <p className="text-sm text-[#6B6B70]">{explanation.confidence_rationale}</p>
            </div>
          )}
        </div>
      )}

      {!isActed && (
        <div className="border-t border-[#1E1E21] p-4 flex justify-end gap-2">
          <button 
            onClick={() => onReject?.(decision.id)}
            className="px-4 py-2 bg-[#1A1A1D] hover:bg-[#2A2A2E] rounded text-sm text-[#8B8B90] transition-colors"
          >
            Reject
          </button>
          <button 
            onClick={() => onApprove?.(decision.id)}
            className="px-4 py-2 bg-[#C9A24D] hover:bg-[#D4AF5A] rounded text-sm text-[#0D0D0F] font-medium transition-colors"
          >
            Approve
          </button>
        </div>
      )}
    </div>
  );
};

const ScoreBar = ({ label, value, color }) => {
  const percent = Math.round((value || 0) * 100);
  const colors = {
    red: 'bg-red-500',
    blue: 'bg-blue-500',
    gold: 'bg-[#C9A24D]'
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-[#6B6B70]">{label}</span>
        <span className="text-xs text-[#8B8B90]">{percent}%</span>
      </div>
      <div className="h-1 bg-[#1A1A1D] rounded-full overflow-hidden">
        <div 
          className={`h-full ${colors[color]} transition-all`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};

const EmptyState = ({ icon: Icon, title, subtitle }) => (
  <div className="p-8 flex items-center justify-center h-full">
    <div className="text-center">
      <Icon className="w-12 h-12 text-[#2A2A2E] mx-auto mb-4" />
      <h2 className="text-lg font-medium text-[#E8E8E8] mb-2">{title}</h2>
      {subtitle && <p className="text-sm text-[#6B6B70]">{subtitle}</p>}
    </div>
  </div>
);

export default ExecutiveIntelligenceApp;
