import React, { useState, useEffect, useCallback } from 'react';
import {
  Upload, FileSpreadsheet, BarChart3, AlertTriangle, Shield,
  Gavel, BookOpen, ChevronRight, Loader2, RefreshCw,
  Database, Layers, Link2, Target, X, Menu, Home
} from 'lucide-react';

// Import components
import { 
  StatCard, SeverityBadge, ImpactBadge, ConstraintBadge, 
  SheetRoleBadge, ConfidenceMeter 
} from './Badges';
import { GapCard, GapTableRow } from './GapCard';
import { DecisionCard } from './DecisionCard';
import { EvidenceDrawer } from './EvidenceDrawer';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ============================================================
// MAIN APP
// ============================================================
const DecisionIntelligenceApp = () => {
  // State
  const [currentView, setCurrentView] = useState('overview');
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [summary, setSummary] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [constraints, setConstraints] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [ledger, setLedger] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedGap, setSelectedGap] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(null);

  // Fetch datasets on mount
  useEffect(() => {
    fetchDatasets();
  }, []);

  // Fetch data when dataset changes
  useEffect(() => {
    if (selectedDataset) {
      fetchAllData(selectedDataset.id);
    }
  }, [selectedDataset]);

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

  const fetchAllData = async (datasetId) => {
    setLoading(true);
    try {
      const [summaryRes, gapsRes, constraintsRes, decisionsRes, ledgerRes] = await Promise.all([
        fetch(`${API_URL}/api/intelligence/${datasetId}/summary`),
        fetch(`${API_URL}/api/intelligence/${datasetId}/gaps`),
        fetch(`${API_URL}/api/intelligence/${datasetId}/constraints`),
        fetch(`${API_URL}/api/intelligence/${datasetId}/decisions`),
        fetch(`${API_URL}/api/ledger?dataset_id=${datasetId}`)
      ]);

      const [summaryData, gapsData, constraintsData, decisionsData, ledgerData] = await Promise.all([
        summaryRes.json(),
        gapsRes.json(),
        constraintsRes.json(),
        decisionsRes.json(),
        ledgerRes.json()
      ]);

      if (summaryData.status === 'success') setSummary(summaryData);
      if (gapsData.status === 'success') setGaps(gapsData);
      if (constraintsData.status === 'success') setConstraints(constraintsData);
      if (decisionsData.status === 'success') setDecisions(decisionsData);
      if (ledgerData.status === 'success') setLedger(ledgerData);
    } catch (err) {
      console.error('Failed to fetch data:', err);
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
        // Run analysis
        const analysisRes = await fetch(`${API_URL}/api/analyze-intelligence`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataset_id: data.dataset_id })
        });
        const analysisData = await analysisRes.json();
        
        if (analysisData.status === 'success') {
          await fetchDatasets();
          const newDataset = { id: data.dataset_id, filename: file.name, has_analysis: true };
          setSelectedDataset(newDataset);
          setUploadProgress(null);
        }
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setUploadProgress(null);
    }
  };

  const handleRunAnalysis = async () => {
    if (!selectedDataset) return;
    setAnalyzing(true);
    try {
      const res = await fetch(`${API_URL}/api/analyze-intelligence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: selectedDataset.id })
      });
      const data = await res.json();
      if (data.status === 'success') {
        await fetchAllData(selectedDataset.id);
      }
    } catch (err) {
      console.error('Analysis failed:', err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleApproveDecision = async (decisionId) => {
    try {
      const res = await fetch(`${API_URL}/api/decisions/${decisionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'user', notes: '' })
      });
      const data = await res.json();
      if (data.status === 'success') {
        await fetchAllData(selectedDataset.id);
      }
    } catch (err) {
      console.error('Approve failed:', err);
    }
  };

  const handleRejectDecision = async (decisionId) => {
    try {
      const res = await fetch(`${API_URL}/api/decisions/${decisionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'user', notes: '' })
      });
      const data = await res.json();
      if (data.status === 'success') {
        await fetchAllData(selectedDataset.id);
      }
    } catch (err) {
      console.error('Reject failed:', err);
    }
  };

  const openGapDrawer = (gap) => {
    setSelectedGap(gap);
    setDrawerOpen(true);
  };

  // Navigation items
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Home },
    { id: 'gaps', label: 'Gaps & Risks', icon: AlertTriangle },
    { id: 'constraints', label: 'Constraints', icon: Shield },
    { id: 'decisions', label: 'Decision Center', icon: Gavel },
    { id: 'ledger', label: 'Decision Ledger', icon: BookOpen }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white flex">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-slate-900 border-r border-slate-800 flex flex-col transition-all duration-300`}>
        {/* Logo */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Gavel className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-lg">ChanksHQ</span>
            </div>
          )}
          <button 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <Menu className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Dataset Selector */}
        {sidebarOpen && (
          <div className="p-4 border-b border-slate-800">
            <label className="text-xs text-slate-500 uppercase tracking-wide">Dataset</label>
            <select
              value={selectedDataset?.id || ''}
              onChange={(e) => {
                const ds = datasets.find(d => d.id === e.target.value);
                setSelectedDataset(ds);
              }}
              className="mt-2 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            >
              {datasets.map(ds => (
                <option key={ds.id} value={ds.id}>{ds.filename}</option>
              ))}
            </select>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-2">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors mb-1 ${
                currentView === item.id
                  ? 'bg-cyan-500/10 text-cyan-400'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <item.icon className="w-5 h-5" />
              {sidebarOpen && <span className="text-sm font-medium">{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Upload */}
        <div className="p-4 border-t border-slate-800">
          <label className={`flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 rounded-lg cursor-pointer transition-all ${uploadProgress ? 'opacity-50 pointer-events-none' : ''}`}>
            {uploadProgress ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {sidebarOpen && <span className="text-sm font-medium">
                  {uploadProgress === 'uploading' ? 'Uploading...' : 'Analyzing...'}
                </span>}
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                {sidebarOpen && <span className="text-sm font-medium">Upload Dataset</span>}
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
            <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
          </div>
        ) : (
          <>
            {currentView === 'overview' && (
              <OverviewPage 
                summary={summary} 
                onRunAnalysis={handleRunAnalysis}
                analyzing={analyzing}
              />
            )}
            {currentView === 'gaps' && (
              <GapsPage 
                gaps={gaps} 
                onGapClick={openGapDrawer}
              />
            )}
            {currentView === 'constraints' && (
              <ConstraintsPage constraints={constraints} />
            )}
            {currentView === 'decisions' && (
              <DecisionsPage 
                decisions={decisions}
                onApprove={handleApproveDecision}
                onReject={handleRejectDecision}
              />
            )}
            {currentView === 'ledger' && (
              <LedgerPage ledger={ledger} />
            )}
          </>
        )}
      </main>

      {/* Evidence Drawer */}
      <EvidenceDrawer 
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        gap={selectedGap}
      />
    </div>
  );
};

// ============================================================
// OVERVIEW PAGE
// ============================================================
const OverviewPage = ({ summary, onRunAnalysis, analyzing }) => {
  if (!summary || summary.status !== 'success') {
    return (
      <div className="p-8">
        <div className="max-w-2xl mx-auto text-center py-20">
          <FileSpreadsheet className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">No Analysis Available</h2>
          <p className="text-slate-400 mb-6">Upload a dataset or run analysis on an existing one.</p>
          <button
            onClick={onRunAnalysis}
            disabled={analyzing}
            className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-white font-medium transition-colors disabled:opacity-50 flex items-center gap-2 mx-auto"
          >
            {analyzing ? <Loader2 className="w-5 h-5 animate-spin" /> : <BarChart3 className="w-5 h-5" />}
            {analyzing ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </div>
      </div>
    );
  }

  const { dataset, analysis, sheets, entities } = summary;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <FileSpreadsheet className="w-8 h-8 text-cyan-500" />
          <h1 className="text-2xl font-bold text-white">{dataset?.filename}</h1>
        </div>
        <p className="text-slate-400">
          Uploaded {dataset?.uploaded_at ? new Date(dataset.uploaded_at).toLocaleDateString() : 'N/A'} • 
          Analyzed {analysis?.analyzed_at ? new Date(analysis.analyzed_at).toLocaleString() : 'N/A'}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard 
          title="Sheets" 
          value={analysis?.sheet_count || 0}
          icon={Layers}
        />
        <StatCard 
          title="Entities" 
          value={analysis?.entity_count || 0}
          icon={Database}
        />
        <StatCard 
          title="Critical Gaps" 
          value={analysis?.critical_gaps || 0}
          variant="critical"
          icon={AlertTriangle}
        />
        <StatCard 
          title="Decisions" 
          value={analysis?.decision_count || 0}
          icon={Gavel}
        />
      </div>

      {/* Sheets Section */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-cyan-500" />
          Detected Sheets
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {sheets?.map((sheet, idx) => (
            <div 
              key={idx}
              className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50 flex items-center justify-between"
            >
              <div>
                <h3 className="text-white font-medium">{sheet.name}</h3>
                <p className="text-sm text-slate-500">
                  {sheet.profile?.row_count?.toLocaleString() || 0} rows • 
                  {sheet.profile?.col_count || 0} columns
                </p>
              </div>
              <SheetRoleBadge role={sheet.role} />
            </div>
          ))}
        </div>
      </div>

      {/* Entities Section */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-cyan-500" />
          Detected Entities
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {entities?.slice(0, 9).map((entity, idx) => (
            <div 
              key={idx}
              className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50"
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-white font-medium truncate">{entity.canonical_name}</h3>
                {entity.is_primary && (
                  <span className="text-xs bg-cyan-500/10 text-cyan-400 px-2 py-0.5 rounded border border-cyan-500/20">
                    Primary
                  </span>
                )}
              </div>
              <p className="text-2xl font-bold text-slate-300">{entity.cardinality?.toLocaleString()}</p>
              <p className="text-xs text-slate-500 mt-1">
                Found in {entity.source_sheets?.length || 0} sheet(s)
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Top Decision Summary */}
      {summary.top_decision_summary && (
        <div className="bg-gradient-to-br from-amber-900/20 to-slate-800/50 rounded-xl p-6 border border-amber-500/20">
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Target className="w-5 h-5 text-amber-500" />
            Key Finding
          </h2>
          <p className="text-slate-300 leading-relaxed">{summary.top_decision_summary}</p>
        </div>
      )}
    </div>
  );
};

// ============================================================
// GAPS PAGE
// ============================================================
const GapsPage = ({ gaps, onGapClick }) => {
  const [viewMode, setViewMode] = useState('table');
  const [severityFilter, setSeverityFilter] = useState('all');

  if (!gaps || gaps.status !== 'success') {
    return (
      <div className="p-8 text-center py-20">
        <AlertTriangle className="w-16 h-16 text-slate-600 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">No Gap Analysis Available</h2>
        <p className="text-slate-400">Run analysis on a dataset to see gaps.</p>
      </div>
    );
  }

  const filteredGaps = severityFilter === 'all' 
    ? gaps.gaps 
    : gaps.gaps.filter(g => g.severity === severityFilter);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <AlertTriangle className="w-7 h-7 text-amber-500" />
            Gaps & Risks
          </h1>
          <p className="text-slate-400 mt-1">Plan vs Actual analysis with severity scoring</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="normal">Normal</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard 
          title="Total Gaps" 
          value={gaps.summary?.total_gaps || 0}
          icon={BarChart3}
        />
        <StatCard 
          title="Critical" 
          value={gaps.summary?.critical_count || 0}
          variant="critical"
          icon={AlertTriangle}
        />
        <StatCard 
          title="Warning" 
          value={gaps.summary?.warning_count || 0}
          variant="warning"
          icon={AlertTriangle}
        />
        <StatCard 
          title="Total Impact" 
          value={`${((gaps.summary?.total_impact || 0) / 1000).toFixed(0)}K`}
          subtitle="Absolute value at risk"
          icon={Target}
        />
      </div>

      {/* Gap Table */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-800">
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wide">Entity</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wide">Metric</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wide">Impact</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wide">Severity</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wide">Direction</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {filteredGaps.slice(0, 50).map((gap, idx) => (
              <GapTableRow key={idx} gap={gap} onClick={() => onGapClick(gap)} />
            ))}
          </tbody>
        </table>
        {filteredGaps.length > 50 && (
          <div className="p-4 text-center text-sm text-slate-500 border-t border-slate-700/50">
            Showing 50 of {filteredGaps.length} gaps
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================
// CONSTRAINTS PAGE
// ============================================================
const ConstraintsPage = ({ constraints }) => {
  if (!constraints || constraints.status !== 'success') {
    return (
      <div className="p-8 text-center py-20">
        <Shield className="w-16 h-16 text-slate-600 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">No Constraints Found</h2>
        <p className="text-slate-400">Run analysis to extract constraints from data.</p>
      </div>
    );
  }

  const { constraints_by_type, summary } = constraints;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Shield className="w-7 h-7 text-purple-500" />
          Constraints
        </h1>
        <p className="text-slate-400 mt-1">Blocking factors and limitations extracted from data</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard 
          title="Total Constraints" 
          value={summary?.total_constraints || 0}
          icon={Shield}
        />
        <StatCard 
          title="Blocking" 
          value={summary?.blocking_count || 0}
          variant="critical"
          icon={AlertTriangle}
        />
        <StatCard 
          title="Types" 
          value={Object.keys(summary?.type_breakdown || {}).length}
          icon={Layers}
        />
      </div>

      {/* Constraints by Type */}
      <div className="space-y-6">
        {Object.entries(constraints_by_type || {}).map(([type, items]) => (
          <div key={type} className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
            <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ConstraintBadge type={type} />
                <span className="text-white font-medium">{items.length} constraint(s)</span>
              </div>
            </div>
            <div className="divide-y divide-slate-700/30">
              {items.slice(0, 10).map((c, idx) => (
                <div key={idx} className="p-4">
                  <p className="text-white text-sm">{c.description}</p>
                  <div className="flex items-center gap-4 mt-2">
                    {c.entity_id && (
                      <span className="text-xs text-slate-500">Entity: {c.entity_id?.slice(0, 30)}</span>
                    )}
                    <span className="text-xs text-slate-500">Source: {c.source_text?.slice(0, 50)}...</span>
                  </div>
                </div>
              ))}
              {items.length > 10 && (
                <div className="p-4 text-center text-sm text-slate-500">
                  +{items.length - 10} more constraints
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================
// DECISIONS PAGE
// ============================================================
const DecisionsPage = ({ decisions, onApprove, onReject }) => {
  const [statusFilter, setStatusFilter] = useState('pending');

  if (!decisions || decisions.status !== 'success') {
    return (
      <div className="p-8 text-center py-20">
        <Gavel className="w-16 h-16 text-slate-600 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">No Decisions Generated</h2>
        <p className="text-slate-400">Run analysis to generate decision candidates.</p>
      </div>
    );
  }

  const { decisions_by_status, summary } = decisions;
  const filteredDecisions = decisions_by_status?.[statusFilter] || [];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Gavel className="w-7 h-7 text-cyan-500" />
            Decision Center
          </h1>
          <p className="text-slate-400 mt-1">Review and act on AI-generated decision candidates</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard 
          title="Total Decisions" 
          value={summary?.total_decisions || 0}
          icon={Gavel}
        />
        <StatCard 
          title="Pending" 
          value={summary?.pending_count || 0}
          variant="warning"
          icon={AlertTriangle}
        />
        <StatCard 
          title="Approved" 
          value={summary?.approved_count || 0}
          variant="success"
          icon={Target}
        />
        <StatCard 
          title="Rejected" 
          value={summary?.rejected_count || 0}
          icon={X}
        />
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6">
        {['pending', 'approved', 'rejected'].map(status => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === status
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700 border border-slate-700'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
            <span className="ml-2 px-1.5 py-0.5 bg-slate-700 rounded text-xs">
              {decisions_by_status?.[status]?.length || 0}
            </span>
          </button>
        ))}
      </div>

      {/* Decision Cards */}
      <div className="space-y-4">
        {filteredDecisions.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            No {statusFilter} decisions
          </div>
        ) : (
          filteredDecisions.map((decision, idx) => (
            <DecisionCard
              key={idx}
              decision={decision}
              onApprove={onApprove}
              onReject={onReject}
              showActions={statusFilter === 'pending'}
            />
          ))
        )}
      </div>
    </div>
  );
};

// ============================================================
// LEDGER PAGE
// ============================================================
const LedgerPage = ({ ledger }) => {
  if (!ledger || ledger.status !== 'success') {
    return (
      <div className="p-8 text-center py-20">
        <BookOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Decision Ledger Empty</h2>
        <p className="text-slate-400">Approve or reject decisions to record them here.</p>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <BookOpen className="w-7 h-7 text-indigo-500" />
          Decision Ledger
        </h1>
        <p className="text-slate-400 mt-1">Immutable record of all decision actions</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard 
          title="Total Entries" 
          value={ledger.summary?.total_entries || 0}
          icon={BookOpen}
        />
        <StatCard 
          title="Approved" 
          value={ledger.summary?.approved_count || 0}
          variant="success"
          icon={Target}
        />
        <StatCard 
          title="Rejected" 
          value={ledger.summary?.rejected_count || 0}
          icon={X}
        />
      </div>

      {/* Ledger Table */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-800">
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Decision</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Type</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Acted By</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/30">
            {ledger.entries?.map((entry, idx) => (
              <tr key={idx} className="hover:bg-slate-800/50">
                <td className="px-4 py-3">
                  <p className="text-sm text-white truncate max-w-md">{entry.summary}</p>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-slate-400 capitalize">{entry.decision_type?.replace(/_/g, ' ')}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-1 rounded ${
                    entry.status === 'approved'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-red-500/10 text-red-400'
                  }`}>
                    {entry.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-slate-300">{entry.acted_by}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-sm text-slate-500">
                    {entry.acted_at ? new Date(entry.acted_at).toLocaleDateString() : 'N/A'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!ledger.entries || ledger.entries.length === 0) && (
          <div className="p-8 text-center text-slate-500">
            No ledger entries yet
          </div>
        )}
      </div>
    </div>
  );
};

export default DecisionIntelligenceApp;
