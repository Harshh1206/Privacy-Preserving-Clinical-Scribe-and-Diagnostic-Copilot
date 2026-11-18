import { useState } from 'react';
import type { ValidationResult, Claim, Evidence } from '../models/types';
import {
  getFindingStatus, getFindingStatusPresentation, getGroundingColor, getGroundingBgColor,
  getHallucinationRiskLabel, getRiskBadgeClass,
} from '../utils/format';
import type { FindingStatus } from '../utils/format';
import type { Patient } from '../models/types';
import PatientClinicalSummary from './PatientClinicalSummary';

interface ValidationPanelProps {
  validation: ValidationResult;
  patient: Patient;
  consultationId: string;
  onClaimSelect: (claim: Claim, evidence: Evidence[]) => void;
  onJumpToTranscript?: (entryId: string) => void;
  selectedClaimId?: string | null;
  loading?: boolean;
}

type FindingGroupId = FindingStatus;

interface FindingGroup {
  id: FindingGroupId;
  title: string;
  claims: Claim[];
}

const SECTION_NAMES: Record<Claim['soapSection'], string> = {
  subjective: 'Subjective',
  objective: 'Objective',
  assessment: 'Assessment',
  plan: 'Plan',
};

const GROUPS: Array<Pick<FindingGroup, 'id' | 'title'>> = [
  { id: 'unsupported', title: 'Unsupported claims' },
  { id: 'conflict', title: 'Conflicting claims' },
  { id: 'needs-review', title: 'Needs clinician review' },
  { id: 'not-assessed', title: 'Not assessed / missing information' },
  { id: 'supported', title: 'Supported claims' },
];

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

function IconChevron({ className = '' }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  );
}

function getFindingGuidance(
  claim: Claim,
  groupId: FindingGroupId,
): { explanation: string; action?: string } {
  if (groupId === 'conflict') {
    return {
      explanation: claim.conflictDescription ?? 'The validation result marks this claim as conflicting with the encounter record.',
      action: /\b(?:patient|medical|health) record\b/i.test(claim.conflictDescription ?? '')
        ? 'Reconcile the claim against the patient record with the clinician before finalizing.'
        : 'Review the source value against the transcript before finalizing.',
    };
  }

  if (groupId === 'not-assessed') {
    const isFamilyHistory = /\bfamily history\b/i.test(claim.text);
    const isExamination = /\b(?:exam|examination)\b/i.test(claim.text);
    return {
      explanation: 'This information is not documented or discussed; that is not the same as a negative finding.',
      action: isFamilyHistory
        ? 'Keep it as not documented; do not infer a negative family history.'
        : isExamination
          ? 'Keep the examination as not documented; do not infer a normal examination.'
          : 'Leave it as not documented, and confirm with the clinician if needed.',
    };
  }

  if (groupId === 'needs-review') {
    return {
      explanation: claim.status === 'pending'
        ? 'The validation result does not establish a clear evidence relationship for this claim.'
        : 'The linked transcript match is inferred and may need confirmation in context.',
      action: 'Review the transcript evidence and confirm the claim with the clinician.',
    };
  }

  if (groupId === 'unsupported') {
    if (/\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|several|few|couple(?:\s+of)?)\s*[- ]?\s*(?:days?|weeks?|months?|years?)\b|\b(?:duration|for the past)\b/i.test(claim.text)) {
      return {
        explanation: 'The transcript does not establish this duration.',
        action: 'Remove it or confirm it with the clinician.',
      };
    }

    if (claim.soapSection === 'assessment') {
      return {
        explanation: 'No supporting evidence for this assessment was found in the encounter transcript.',
        action: 'Verify against the patient record before retaining.',
      };
    }

    if (claim.soapSection === 'objective' && /\d/.test(claim.text)) {
      return {
        explanation: 'The transcript does not confirm this documented value.',
        action: 'Review the source value before finalizing.',
      };
    }

    return {
      explanation: 'No supporting evidence for this assertion was found in the encounter transcript.',
      action: 'Confirm it with the clinician or source record before retaining.',
    };
  }

  return { explanation: 'Linked transcript evidence supports this claim.' };
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

// ─── Claim finding ────────────────────────────────────────────────────────────

function ClaimFinding({
  claim,
  groupId,
  evidenceList,
  isSelected,
  onClaimSelect,
  onJumpToTranscript,
}: {
  claim: Claim;
  groupId: FindingGroupId;
  evidenceList: Evidence[];
  isSelected: boolean;
  onClaimSelect: (claim: Claim, evidence: Evidence[]) => void;
  onJumpToTranscript?: (entryId: string) => void;
}) {
  const status = getFindingStatusPresentation(groupId);
  const guidance = getFindingGuidance(claim, groupId);

  return (
    <details className={`finding-disclosure border-b border-slate-800/80 last:border-0 ${isSelected ? 'bg-brand-500/[0.04]' : ''}`}>
      <summary
        className="flex cursor-pointer items-start gap-2.5 px-3 py-2.5 transition-colors hover:bg-slate-800/40 focus-visible:outline focus-visible:outline-1 focus-visible:outline-brand-500"
        onClick={() => onClaimSelect(claim, evidenceList)}
      >
        <IconChevron className="finding-chevron mt-0.5 shrink-0 text-slate-500 transition-transform" />
        <div className="min-w-0 flex-1">
          <p className="text-sm leading-snug text-slate-200">{claim.text}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-2xs text-slate-500">{SECTION_NAMES[claim.soapSection]}</span>
            <span className={`rounded px-1.5 py-0.5 text-2xs font-medium ${status.className}`}>{status.label}</span>
            {evidenceList.length > 0 && (
              <span className="text-2xs text-slate-500">
                {evidenceList.length} transcript excerpt{evidenceList.length === 1 ? '' : 's'}
              </span>
            )}
          </div>
        </div>
      </summary>

      <div className="px-3 pb-3 pl-9">
        <div className="rounded-md bg-slate-950/70 px-3 py-2.5">
          <p className="text-xs leading-relaxed text-slate-300">{guidance.explanation}</p>
          {guidance.action && (
            <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
              <span className="font-medium text-slate-300">Recommended action: </span>{guidance.action}
            </p>
          )}
        </div>

        <div className="mt-3">
          <p className="mb-1.5 text-2xs font-semibold uppercase tracking-wider text-slate-500">Transcript evidence</p>
          <div className="mb-2 rounded-md border-l-2 border-slate-700 bg-slate-950/60 px-3 py-2">
            <p className="text-2xs font-medium uppercase tracking-wide text-slate-500">Claim evaluated · {SECTION_NAMES[claim.soapSection]}</p>
            <p className="mt-1 text-xs leading-relaxed text-slate-300">{claim.text}</p>
          </div>
          {evidenceList.length === 0 ? (
            <p className="text-xs text-slate-500">No transcript quotation is linked to this claim.</p>
          ) : (
            <div className="space-y-2">
              {evidenceList.map(evidence => (
                <blockquote key={evidence.id} className="rounded-md border-l-2 border-brand-500/50 bg-slate-950/60 px-3 py-2">
                  <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2 text-2xs text-slate-500">
                    <span>{evidence.speaker} · {evidence.timestamp}</span>
                    <div className="flex items-center gap-2">
                      <span className="capitalize">{evidence.matchType} match</span>
                      {onJumpToTranscript && (
                        <button
                          type="button"
                          className="text-brand-400 transition-colors hover:text-brand-300"
                          onClick={event => {
                            event.stopPropagation();
                            onClaimSelect(claim, evidenceList);
                            onJumpToTranscript(evidence.transcriptEntryId);
                          }}
                        >
                          Jump to transcript
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-sm leading-relaxed text-slate-300">“{evidence.transcriptText}”</p>
                </blockquote>
              ))}
            </div>
          )}
          <button
            type="button"
            className="mt-2 text-2xs text-slate-400 transition-colors hover:text-brand-300"
            onClick={event => {
              event.stopPropagation();
              onClaimSelect(claim, evidenceList);
            }}
          >
            View in evidence panel
          </button>
        </div>
      </div>
    </details>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ValidationPanel({
  validation,
  patient,
  consultationId,
  onClaimSelect,
  onJumpToTranscript,
  selectedClaimId,
  loading,
}: ValidationPanelProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<FindingGroupId>>(
    () => new Set(['unsupported', 'conflict', 'needs-review', 'not-assessed']),
  );
  const evidenceMap = Object.fromEntries(validation.evidence.map(e => [e.id, e]));
  const findings = GROUPS.map(group => ({
    ...group,
    claims: validation.claims.filter(claim => {
      const evidenceList = claim.evidenceIds.map(id => evidenceMap[id]).filter((evidence): evidence is Evidence => Boolean(evidence));
      return getFindingStatus(claim, evidenceList) === group.id;
    }),
  })).filter(group => group.claims.length > 0);

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

      {validation.validationNotes && (
        <div className="px-3 py-2 bg-slate-950 border-b border-slate-800 text-xs text-slate-400">
          {validation.validationNotes}
        </div>
      )}

      {/* Claims list */}
      <div className="flex-1 overflow-auto">
        <div className="px-3 py-2 border-b border-slate-800">
          <p className="text-2xs text-slate-500 uppercase tracking-wider font-semibold">
            Claims ({validation.totalClaimCount}) · select a claim to view evidence
          </p>
        </div>

        {findings.map(group => {
          const isExpanded = expandedGroups.has(group.id);
          return (
            <section key={group.id} className="border-b border-slate-800">
              <button
                type="button"
                aria-expanded={isExpanded}
                onClick={() => setExpandedGroups(current => {
                  const next = new Set(current);
                  if (next.has(group.id)) next.delete(group.id);
                  else next.add(group.id);
                  return next;
                })}
                className="flex w-full items-center gap-2 bg-slate-950/80 px-3 py-2.5 text-left transition-colors hover:bg-slate-800/60 focus-visible:outline focus-visible:outline-1 focus-visible:outline-brand-500"
              >
                <IconChevron className={`shrink-0 text-slate-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                <span className="flex-1 text-xs font-semibold text-slate-300">{group.title}</span>
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-2xs font-medium text-slate-400">{group.claims.length}</span>
              </button>
              {isExpanded && (
                <div>
                  {group.claims.map(claim => {
                    const evidenceList = claim.evidenceIds
                      .map(id => evidenceMap[id])
                      .filter((evidence): evidence is Evidence => Boolean(evidence));
                    return (
                      <ClaimFinding
                        key={claim.id}
                        claim={claim}
                        groupId={group.id}
                        evidenceList={evidenceList}
                        isSelected={claim.id === selectedClaimId}
                        onClaimSelect={onClaimSelect}
                        onJumpToTranscript={onJumpToTranscript}
                      />
                    );
                  })}
                </div>
              )}
            </section>
          );
        })}

        <PatientClinicalSummary patient={patient} consultationId={consultationId} />
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-slate-800 text-2xs text-slate-600">
        Validated: {new Date(validation.validatedAt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} · v{validation.soapNoteVersion}
      </div>
    </div>
  );
}
