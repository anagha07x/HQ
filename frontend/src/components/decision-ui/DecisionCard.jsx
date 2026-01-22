import React, { useState } from 'react';
import { 
  CheckCircle, XCircle, Edit3, ChevronDown, ChevronUp,
  AlertTriangle, Target, Zap, MessageSquare, Link2
} from 'lucide-react';
import { ScoreIndicator, SeverityBadge, ConstraintBadge } from './Badges';

// ============================================================
// DECISION CARD
// ============================================================
export const DecisionCard = ({ 
  decision, 
  onApprove, 
  onReject, 
  onEdit,
  isExpanded = false,
  showActions = true 
}) => {
  const [expanded, setExpanded] = useState(isExpanded);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const handleApprove = async () => {
    setIsApproving(true);
    try {
      await onApprove?.(decision.id);
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await onReject?.(decision.id);
    } finally {
      setIsRejecting(false);
    }
  };

  const getDecisionTypeIcon = (type) => {
    switch (type) {
      case 'investigate': return AlertTriangle;
      case 'investigate_systemic': return AlertTriangle;
      case 'monitor': return Target;
      case 'escalate': return Zap;
      case 'resolve': return CheckCircle;
      case 'prioritize': return Target;
      case 'allocate': return Link2;
      case 'sequence': return Link2;
      case 'verify_targets': return Target;
      default: return MessageSquare;
    }
  };

  const getDecisionTypeColor = (type) => {
    switch (type) {
      case 'investigate':
      case 'investigate_systemic':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'escalate':
        return 'text-red-400 bg-red-500/10 border-red-500/20';
      case 'resolve':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'monitor':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      default:
        return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
    }
  };

  const Icon = getDecisionTypeIcon(decision.decision_type);
  const typeColor = getDecisionTypeColor(decision.decision_type);

  const isActedUpon = decision.ledger_status === 'approved' || decision.ledger_status === 'rejected';

  return (
    <div className={`bg-gradient-to-br from-slate-800 to-slate-800/50 rounded-xl border transition-all ${
      isActedUpon 
        ? decision.ledger_status === 'approved' 
          ? 'border-emerald-500/30' 
          : 'border-red-500/30'
        : 'border-slate-700/50 hover:border-slate-600'
    }`}>
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg border ${typeColor}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-medium uppercase px-2 py-0.5 rounded border ${typeColor}`}>
                  {decision.decision_type?.replace(/_/g, ' ')}
                </span>
                {isActedUpon && (
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    decision.ledger_status === 'approved'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-red-500/10 text-red-400 border border-red-500/20'
                  }`}>
                    {decision.ledger_status === 'approved' ? '✓ Approved' : '✗ Rejected'}
                  </span>
                )}
              </div>
              <h3 className="text-white font-medium leading-snug">{decision.summary}</h3>
            </div>
          </div>
          <button 
            onClick={() => setExpanded(!expanded)}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            {expanded ? (
              <ChevronUp className="w-5 h-5 text-slate-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-slate-400" />
            )}
          </button>
        </div>

        {/* Scores */}
        <div className="grid grid-cols-3 gap-4 mt-4">
          <ScoreIndicator label="Impact" value={decision.impact_score} color="red" />
          <ScoreIndicator label="Confidence" value={decision.confidence_score} color="blue" />
          <ScoreIndicator label="Urgency" value={decision.urgency_score} color="orange" />
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Reasoning */}
          <div>
            <h4 className="text-sm font-medium text-slate-300 mb-2">Root Cause Analysis</h4>
            <p className="text-sm text-slate-400 leading-relaxed bg-slate-800/50 rounded-lg p-3 border border-slate-700/30">
              {decision.reasoning}
            </p>
          </div>

          {/* Supporting Gaps */}
          {decision.supporting_gap_count > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2">
                Linked Gaps ({decision.supporting_gap_count})
              </h4>
              <div className="flex flex-wrap gap-2">
                {Array.from({ length: Math.min(decision.supporting_gap_count, 5) }).map((_, i) => (
                  <span key={i} className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-400 border border-slate-700">
                    Gap #{i + 1}
                  </span>
                ))}
                {decision.supporting_gap_count > 5 && (
                  <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-500 border border-slate-700">
                    +{decision.supporting_gap_count - 5} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Supporting Constraints */}
          {decision.supporting_constraint_count > 0 && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2">
                Related Constraints ({decision.supporting_constraint_count})
              </h4>
              <div className="flex flex-wrap gap-2">
                {Array.from({ length: Math.min(decision.supporting_constraint_count, 3) }).map((_, i) => (
                  <ConstraintBadge key={i} type="dependency" />
                ))}
                {decision.supporting_constraint_count > 3 && (
                  <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-500 border border-slate-700">
                    +{decision.supporting_constraint_count - 3} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Evidence */}
          {decision.evidence?.supporting_evidence && (
            <div>
              <h4 className="text-sm font-medium text-slate-300 mb-2">Evidence</h4>
              <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/30">
                <pre className="text-xs text-slate-400 overflow-x-auto">
                  {JSON.stringify(decision.evidence.supporting_evidence.slice(0, 2), null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Acted Info */}
          {isActedUpon && (
            <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
              <div className="flex items-center gap-2 text-sm">
                {decision.ledger_status === 'approved' ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
                <span className="text-slate-400">
                  {decision.ledger_status === 'approved' ? 'Approved' : 'Rejected'} by{' '}
                  <span className="text-white">{decision.acted_by || 'system'}</span>
                  {decision.acted_at && (
                    <span className="text-slate-500">
                      {' '}on {new Date(decision.acted_at).toLocaleDateString()}
                    </span>
                  )}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {showActions && !isActedUpon && (
        <div className="p-4 border-t border-slate-700/50 flex items-center justify-end gap-2">
          <button
            onClick={handleReject}
            disabled={isRejecting}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
            {isRejecting ? 'Rejecting...' : 'Reject'}
          </button>
          <button
            onClick={handleApprove}
            disabled={isApproving}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <CheckCircle className="w-4 h-4" />
            {isApproving ? 'Approving...' : 'Approve'}
          </button>
        </div>
      )}
    </div>
  );
};

export default DecisionCard;
