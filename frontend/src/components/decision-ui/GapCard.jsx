import React from 'react';
import { SeverityBadge, ImpactBadge } from './Badges';
import { ChevronRight, AlertTriangle } from 'lucide-react';

// ============================================================
// GAP CARD
// ============================================================
export const GapCard = ({ gap, onClick, compact = false }) => {
  if (compact) {
    return (
      <div 
        onClick={onClick}
        className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg border border-slate-700/30 hover:border-slate-600 transition-all cursor-pointer group"
      >
        <div className="flex items-center gap-3 min-w-0">
          <SeverityBadge severity={gap.severity} />
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">{gap.metric_name}</p>
            <p className="text-xs text-slate-500 truncate">{gap.entity_id?.slice(0, 30)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <ImpactBadge value={gap.percentage_gap} type="percentage" />
          <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
        </div>
      </div>
    );
  }

  return (
    <div 
      onClick={onClick}
      className="bg-gradient-to-br from-slate-800 to-slate-800/50 rounded-xl border border-slate-700/50 hover:border-slate-600 transition-all cursor-pointer group overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <SeverityBadge severity={gap.severity} />
            <span className={`text-xs px-2 py-0.5 rounded ${
              gap.direction === 'under' 
                ? 'bg-red-500/10 text-red-400'
                : gap.direction === 'over'
                ? 'bg-emerald-500/10 text-emerald-400'
                : 'bg-slate-500/10 text-slate-400'
            }`}>
              {gap.direction === 'under' ? '↓ Under' : gap.direction === 'over' ? '↑ Over' : '→ Target'}
            </span>
          </div>
          <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-slate-400 transition-colors" />
        </div>
        
        <h3 className="text-white font-medium mt-3">{gap.metric_name}</h3>
        <p className="text-sm text-slate-400 mt-1 truncate">{gap.entity_id}</p>
      </div>

      {/* Body */}
      <div className="p-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-slate-500 uppercase mb-1">Plan</p>
            <p className="text-lg font-semibold text-emerald-400">
              {gap.plan_value?.toLocaleString() ?? 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase mb-1">Actual</p>
            <p className="text-lg font-semibold text-amber-400">
              {gap.actual_value?.toLocaleString() ?? 'N/A'}
            </p>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-700/50 flex items-center justify-between">
          <span className="text-xs text-slate-500">Impact</span>
          <ImpactBadge value={gap.absolute_gap} />
        </div>
      </div>
    </div>
  );
};

// ============================================================
// GAP TABLE ROW
// ============================================================
export const GapTableRow = ({ gap, onClick }) => {
  return (
    <tr 
      onClick={onClick}
      className="hover:bg-slate-800/50 cursor-pointer transition-colors border-b border-slate-700/30 last:border-0"
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className={`w-4 h-4 ${
            gap.severity === 'critical' ? 'text-red-400' :
            gap.severity === 'warning' ? 'text-amber-400' : 'text-slate-400'
          }`} />
          <span className="text-sm text-white truncate max-w-[200px]">{gap.entity_id}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <span className="text-sm text-slate-300">{gap.metric_name}</span>
      </td>
      <td className="px-4 py-3">
        <ImpactBadge value={gap.absolute_gap} />
      </td>
      <td className="px-4 py-3">
        <SeverityBadge severity={gap.severity} />
      </td>
      <td className="px-4 py-3">
        <span className={`text-sm ${
          gap.direction === 'under' ? 'text-red-400' :
          gap.direction === 'over' ? 'text-emerald-400' : 'text-slate-400'
        }`}>
          {gap.direction === 'under' ? 'Below target' :
           gap.direction === 'over' ? 'Above target' : 'On target'}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <ChevronRight className="w-4 h-4 text-slate-600 inline" />
      </td>
    </tr>
  );
};

export default GapCard;
