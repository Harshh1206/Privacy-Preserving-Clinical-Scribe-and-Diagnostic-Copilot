import type { ValidationResult, Claim, Evidence } from '../models/types';
import {
  getGroundingColor, getGroundingBgColor, getHallucinationRiskLabel, getRiskBadgeClass,
  getClaimStatusLabel, getClaimBadgeClass, getClaimRowClass, getSectionLabel, getSeverityBadgeClass,
} from '../utils/format';

interface ValidationPanelProps {
  validation: ValidationResult;
  onClaimSelect: (claim: Claim, evidence: Evidence[]) => void;
  selectedClaimId?: string | null;
  loading?: boolean;
}

function IconRefresh() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/>
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
    </svg>
  );
}

function IconInfo() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="16" x2="12" y2="12"/>
      <line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>
  );
}

// ─── Grounding Score widget ───────────────────────────────────────────────────

function GroundingScore({ score, risk }: { score: number; risk: ValidationResult['hallucinationRisk'] }) {
  const color = getGroundingColor(score);
  const bgColor = getGroundingBgColor(score);
  const riskBadge = getRiskBadgeClass(risk);
  const riskLabel = getHallucinationRiskLabel(risk);

  return (
    <div className="px-3 py-3 border-b border-slate-800">
      <div className="flex items-center justify-between mb-1.5">
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Grounding Score</p>
          <p className="text-2xs text-slate-600 mt-0.5">Evidence-based claim coverage · not clinical correctness</p>
        </div>
        <div className="text-right">
          <span className={`text-2xl font-bold ${color}`}>{score}</span>
          <span className="text-sm text-slate-500">/100</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full rounded-full transition-all ${bgColor}`}
          style={{ width: `${score}%` }}
        />
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <IconInfo />
          <span>Hallucination Risk:</span>
          <span className={riskBadge}>{riskLabel}</span>
        </div>
        <div className="text-2xs text-slate-600">
          {Math.round(score)}% of claims grounded in transcript
        </div>
      </div>
    </div>
  );
}

// ─── Claim row ────────────────────────────────────────────────────────────────

function ClaimRow({
  claim,
  evidenceList,
  isSelected,
  onClick,
}: {
  claim: Claim;
  evidenceList: Evidence[];
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`px-3 py-2.5 cursor-pointer transition-colors border-b border-slate-800 last:border-0 ${
        getClaimRowClass(claim.status)
      } ${isSelected ? 'ring-1 ring-inset ring-brand-500/50' : 'hover:bg-slate-800/40'}`}
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 inline-flex items-center justify-center w-4 h-4 rounded bg-slate-700 text-2xs font-bold text-slate-300 shrink-0">
          {getSectionLabel(claim.soapSection)}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-200 leading-snug">{claim.text}</p>
          {claim.conflictDescription && (
            <p className="mt-1 text-xs text-warn-300 leading-snug">{claim.conflictDescription}</p>
          )}
          {claim.suggestedCorrection && (
            <p className="mt-1 text-xs text-brand-300 leading-snug">
              <span className="font-medium">Suggestion: </span>{claim.suggestedCorrection}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1.5">
            <span className={getClaimBadgeClass(claim.status)}>{getClaimStatusLabel(claim.status)}</span>
            <span className={getSeverityBadgeClass(claim.severity)}>{claim.severity}</span>
            {claim.status !== 'unsupported' && evidenceList.length > 0 && (
              <span className="text-2xs text-slate-500">{evidenceList.length} evidence item{evidenceList.length > 1 ? 's' : ''}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ValidationPanel({ validation, onClaimSelect, selectedClaimId, loading }: ValidationPanelProps) {
  const evidenceMap = Object.fromEntries(validation.evidence.map(e => [e.id, e]));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="text-center">
          <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-1.5"/>
          <p className="text-xs text-slate-500">Validating…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Grounding Score */}
      <GroundingScore score={validation.groundingScore} risk={validation.hallucinationRisk} />

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-px bg-slate-800 border-b border-slate-800">
        {[
          { label: 'Supported', value: validation.supportedCount, cls: 'text-ok-400' },
          { label: 'Unsupported', value: validation.unsupportedCount, cls: 'text-danger-400' },
          { label: 'Conflicts', value: validation.conflictCount, cls: 'text-warn-400' },
        ].map(({ label, value, cls }) => (
          <div key={label} className="bg-slate-900 px-3 py-2 text-center">
            <p className={`text-lg font-semibold ${cls}`}>{value}</p>
            <p className="text-2xs text-slate-500 uppercase tracking-wider">{label}</p>
          </div>
        ))}
      </div>

      {/* Stale indicator */}
      {validation.isStale && (
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-warn-500/10 border-b border-warn-500/30 text-warn-400 text-xs">
          <IconRefresh />
          <span>Results are stale — SOAP was edited after this validation run.</span>
        </div>
      )}

      {/* Claims list */}
      <div className="flex-1 overflow-auto">
        <div className="px-3 py-2 border-b border-slate-800">
          <p className="text-2xs text-slate-500 uppercase tracking-wider font-semibold">
            Claims ({validation.totalClaimCount}) · click to view evidence
          </p>
        </div>

        {/* Critical conflicts first */}
        {validation.claims.filter(c => c.status === 'conflict').map(claim => (
          <ClaimRow
            key={claim.id}
            claim={claim}
            evidenceList={claim.evidenceIds.map(eid => evidenceMap[eid]).filter(Boolean)}
            isSelected={claim.id === selectedClaimId}
            onClick={() => onClaimSelect(claim, claim.evidenceIds.map(eid => evidenceMap[eid]).filter(Boolean))}
          />
        ))}

        {/* Unsupported */}
        {validation.claims.filter(c => c.status === 'unsupported').map(claim => (
          <ClaimRow
            key={claim.id}
            claim={claim}
            evidenceList={[]}
            isSelected={claim.id === selectedClaimId}
            onClick={() => onClaimSelect(claim, [])}
          />
        ))}

        {/* Supported */}
        {validation.claims.filter(c => c.status === 'supported').map(claim => (
          <ClaimRow
            key={claim.id}
            claim={claim}
            evidenceList={claim.evidenceIds.map(eid => evidenceMap[eid]).filter(Boolean)}
            isSelected={claim.id === selectedClaimId}
            onClick={() => onClaimSelect(claim, claim.evidenceIds.map(eid => evidenceMap[eid]).filter(Boolean))}
          />
        ))}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-slate-800 text-2xs text-slate-600">
        Validated: {new Date(validation.validatedAt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} · v{validation.soapNoteVersion}
      </div>
    </div>
  );
}
