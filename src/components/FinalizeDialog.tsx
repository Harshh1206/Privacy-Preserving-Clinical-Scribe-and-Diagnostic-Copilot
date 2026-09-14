import { useState } from 'react';
import type { ValidationResult } from '../models/types';
import { getGroundingColor, getHallucinationRiskLabel, getRiskBadgeClass } from '../utils/format';

interface FinalizeDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  validation: ValidationResult | null;
  consultationId: string;
  patientName: string;
}

function IconLock() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}

function IconWarn() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

export default function FinalizeDialog({ isOpen, onClose, onConfirm, validation, patientName }: FinalizeDialogProps) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  if (!isOpen) return null;

  const hasConflicts = (validation?.conflictCount ?? 0) > 0;
  const hasUnsupported = (validation?.unsupportedCount ?? 0) > 0;
  const isStale = validation?.isStale ?? false;

  async function handleConfirm() {
    setIsConfirming(true);
    try {
      await onConfirm();
      setConfirmed(true);
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="bg-slate-900 border border-slate-700 rounded-lg w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
          <span className="text-brand-400"><IconLock /></span>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Finalize Note</h2>
            <p className="text-xs text-slate-500">Patient: {patientName}</p>
          </div>
        </div>

        {confirmed ? (
          <div className="px-4 py-8 text-center">
            <div className="w-10 h-10 rounded-full bg-ok-500/20 flex items-center justify-center mx-auto mb-3">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-ok-400">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-100 mb-1">Note finalized successfully.</p>
            <p className="text-xs text-slate-500 mb-4">The note is now read-only and locked to the audit trail.</p>
            <button className="btn-primary" onClick={onClose}>Close</button>
          </div>
        ) : (
          <>
            {/* Validation summary */}
            {validation && (
              <div className="px-4 py-3 border-b border-slate-800">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Current validation state</p>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400">Grounding Score</span>
                  <span className={`text-sm font-semibold ${getGroundingColor(validation.groundingScore)}`}>
                    {validation.groundingScore}/100
                  </span>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400">Hallucination Risk</span>
                  <span className={getRiskBadgeClass(validation.hallucinationRisk)}>
                    {getHallucinationRiskLabel(validation.hallucinationRisk)}
                  </span>
                </div>
                {[
                  { label: 'Supported claims', value: validation.supportedCount, cls: 'text-ok-400' },
                  { label: 'Unsupported claims', value: validation.unsupportedCount, cls: 'text-danger-400' },
                  { label: 'Conflicts', value: validation.conflictCount, cls: 'text-warn-400' },
                ].map(({ label, value, cls }) => (
                  <div key={label} className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">{label}</span>
                    <span className={`text-xs font-medium ${cls}`}>{value}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Warnings */}
            <div className="px-4 py-3 space-y-2">
              {isStale && (
                <div className="flex items-start gap-2 text-warn-300 text-xs bg-warn-500/10 rounded px-2 py-2">
                  <IconWarn />
                  <span>Validation is stale. Consider revalidating before finalizing.</span>
                </div>
              )}
              {hasConflicts && (
                <div className="flex items-start gap-2 text-warn-300 text-xs bg-warn-500/10 rounded px-2 py-2">
                  <IconWarn />
                  <span><strong>{validation!.conflictCount} conflict{validation!.conflictCount > 1 ? 's' : ''}</strong> found in this note. Review conflicts before finalizing.</span>
                </div>
              )}
              {hasUnsupported && (
                <div className="flex items-start gap-2 text-danger-300 text-xs bg-danger-500/10 rounded px-2 py-2">
                  <IconWarn />
                  <span><strong>{validation!.unsupportedCount} claim{validation!.unsupportedCount > 1 ? 's' : ''}</strong> could not be grounded in the transcript.</span>
                </div>
              )}
              <p className="text-xs text-slate-500">
                Finalizing locks this note to the audit trail. The note will become read-only and cannot be edited after this action.
              </p>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-slate-800">
              <button className="btn-ghost btn-sm" onClick={onClose} disabled={isConfirming}>
                Cancel
              </button>
              <button
                className={hasConflicts || isStale ? 'btn-danger' : 'btn-primary'}
                onClick={handleConfirm}
                disabled={isConfirming}
              >
                {isConfirming ? 'Finalizing…' : 'Finalize Note'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
