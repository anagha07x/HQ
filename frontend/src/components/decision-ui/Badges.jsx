import React from 'react';
import { AlertTriangle, AlertCircle, Info, TrendingUp, TrendingDown } from 'lucide-react';

// ============================================================
// IMPACT BADGE
// ============================================================
export const ImpactBadge = ({ value, type = 'currency' }) => {
  if (value === null || value === undefined) return null;
  
  const isPositive = value >= 0;
  const absValue = Math.abs(value);
  
  const formatValue = () => {
    if (type === 'percentage') {
      return `${absValue.toFixed(1)}%`;
    }
    if (absValue >= 1000000) {
      return `${(absValue / 1000000).toFixed(1)}M`;
    }
    if (absValue >= 1000) {
      return `${(absValue / 1000).toFixed(1)}K`;
    }
    return absValue.toFixed(0);
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
      isPositive 
        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
        : 'bg-red-500/10 text-red-400 border border-red-500/20'
    }`}>
      {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      {formatValue()}
    </span>
  );
};

// ============================================================
// SEVERITY BADGE
// ============================================================
export const SeverityBadge = ({ severity }) => {
  const config = {
    critical: {
      bg: 'bg-red-500/10',
      text: 'text-red-400',
      border: 'border-red-500/20',
      icon: AlertTriangle,
      label: 'Critical'
    },
    warning: {
      bg: 'bg-amber-500/10',
      text: 'text-amber-400',
      border: 'border-amber-500/20',
      icon: AlertCircle,
      label: 'Warning'
    },
    normal: {
      bg: 'bg-slate-500/10',
      text: 'text-slate-400',
      border: 'border-slate-500/20',
      icon: Info,
      label: 'Normal'
    }
  };

  const cfg = config[severity] || config.normal;
  const Icon = cfg.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
};

// ============================================================
// CONSTRAINT BADGE
// ============================================================
export const ConstraintBadge = ({ type }) => {
  const config = {
    blocking: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
    deadline: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/20' },
    dependency: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20' },
    capacity: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
    resource: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20' },
    exception: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20' },
    in_progress: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' }
  };

  const cfg = config[type] || config.exception;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
      {type?.replace(/_/g, ' ')}
    </span>
  );
};

// ============================================================
// SHEET ROLE BADGE
// ============================================================
export const SheetRoleBadge = ({ role }) => {
  const config = {
    master: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20', icon: '📋' },
    transactional: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20', icon: '📊' },
    plan: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', icon: '🎯' },
    actual: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', icon: '📈' },
    summary: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20', icon: '📑' },
    comparison: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20', icon: '⚖️' },
    unknown: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20', icon: '❓' }
  };

  const cfg = config[role] || config.unknown;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium capitalize ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
      <span>{cfg.icon}</span>
      {role}
    </span>
  );
};

// ============================================================
// CONFIDENCE METER
// ============================================================
export const ConfidenceMeter = ({ value, showLabel = true }) => {
  const percentage = Math.round((value || 0) * 100);
  const getColor = () => {
    if (percentage >= 80) return 'bg-emerald-500';
    if (percentage >= 60) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${getColor()} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-slate-400 w-10">{percentage}%</span>
      )}
    </div>
  );
};

// ============================================================
// SCORE INDICATOR
// ============================================================
export const ScoreIndicator = ({ label, value, color = 'blue' }) => {
  const colors = {
    blue: 'from-blue-500 to-cyan-500',
    green: 'from-emerald-500 to-teal-500',
    orange: 'from-orange-500 to-amber-500',
    red: 'from-red-500 to-rose-500'
  };

  const percentage = Math.round((value || 0) * 100);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between items-center">
        <span className="text-xs text-slate-400">{label}</span>
        <span className="text-xs font-medium text-slate-300">{percentage}%</span>
      </div>
      <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full bg-gradient-to-r ${colors[color]} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

// ============================================================
// STAT CARD
// ============================================================
export const StatCard = ({ title, value, subtitle, icon: Icon, variant = 'default' }) => {
  const variants = {
    default: 'from-slate-800 to-slate-800/50 border-slate-700/50',
    critical: 'from-red-900/20 to-slate-800/50 border-red-500/20',
    warning: 'from-amber-900/20 to-slate-800/50 border-amber-500/20',
    success: 'from-emerald-900/20 to-slate-800/50 border-emerald-500/20'
  };

  return (
    <div className={`bg-gradient-to-br ${variants[variant]} border rounded-xl p-4`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className="p-2 bg-slate-700/50 rounded-lg">
            <Icon className="w-5 h-5 text-slate-400" />
          </div>
        )}
      </div>
    </div>
  );
};

export default {
  ImpactBadge,
  SeverityBadge,
  ConstraintBadge,
  SheetRoleBadge,
  ConfidenceMeter,
  ScoreIndicator,
  StatCard
};
