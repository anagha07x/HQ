import React from 'react';
import { X, FileSpreadsheet, AlertTriangle, Link2, ChevronRight } from 'lucide-react';
import { SeverityBadge, ImpactBadge } from './Badges';

// ============================================================
// EVIDENCE DRAWER
// ============================================================
export const EvidenceDrawer = ({ isOpen, onClose, gap, title = "Gap Evidence" }) => {
  if (!isOpen || !gap) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-lg bg-slate-900 border-l border-slate-700 z-50 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Summary */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="flex items-center gap-3 mb-3">
              <SeverityBadge severity={gap.severity} />
              <span className="text-slate-400 text-sm">
                {gap.direction === 'over' ? 'Overperformance' : gap.direction === 'under' ? 'Underperformance' : 'On Target'}
              </span>
            </div>
            
            <h3 className="text-white font-medium mb-2">{gap.metric_name}</h3>
            <p className="text-sm text-slate-400">Entity: {gap.entity_id}</p>
          </div>

          {/* Values */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <ChevronRight className="w-4 h-4" />
              Gap Analysis
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
                <p className="text-xs text-slate-500 uppercase mb-1">Plan Value</p>
                <p className="text-lg font-semibold text-emerald-400">
                  {gap.plan_value?.toLocaleString() ?? 'N/A'}
                </p>
              </div>
              <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
                <p className="text-xs text-slate-500 uppercase mb-1">Actual Value</p>
                <p className="text-lg font-semibold text-amber-400">
                  {gap.actual_value?.toLocaleString() ?? 'N/A'}
                </p>
              </div>
              <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
                <p className="text-xs text-slate-500 uppercase mb-1">Absolute Gap</p>
                <p className="text-lg font-semibold text-white">
                  {gap.absolute_gap?.toLocaleString() ?? 'N/A'}
                </p>
              </div>
              <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
                <p className="text-xs text-slate-500 uppercase mb-1">Percentage Gap</p>
                <ImpactBadge value={gap.percentage_gap} type="percentage" />
              </div>
            </div>
          </div>

          {/* Source Information */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4" />
              Source Information
            </h4>
            <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/30 space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-slate-400">Source Sheet</span>
                <span className="text-sm text-white">{gap.source_sheet || 'Multiple'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-slate-400">Gap ID</span>
                <span className="text-sm text-slate-500 font-mono">{gap.id?.slice(0, 8)}...</span>
              </div>
            </div>
          </div>

          {/* Explanation */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Analysis
            </h4>
            <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/30">
              <p className="text-sm text-slate-300 leading-relaxed">
                {gap.direction === 'under' 
                  ? `The actual value (${gap.actual_value?.toLocaleString()}) is ${Math.abs(gap.percentage_gap || 0).toFixed(1)}% below the planned target (${gap.plan_value?.toLocaleString()}). This represents a gap of ${Math.abs(gap.absolute_gap || 0).toLocaleString()} units.`
                  : gap.direction === 'over'
                  ? `The actual value (${gap.actual_value?.toLocaleString()}) exceeds the planned target (${gap.plan_value?.toLocaleString()}) by ${Math.abs(gap.percentage_gap || 0).toFixed(1)}%. Consider reviewing if targets need adjustment.`
                  : `The actual value is within acceptable range of the planned target.`
                }
              </p>
            </div>
          </div>

          {/* Related Entities */}
          {gap.related_entities && gap.related_entities.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                <Link2 className="w-4 h-4" />
                Related Entities
              </h4>
              <div className="flex flex-wrap gap-2">
                {gap.related_entities.map((entity, idx) => (
                  <span 
                    key={idx}
                    className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-400 border border-slate-700"
                  >
                    {entity}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default EvidenceDrawer;
