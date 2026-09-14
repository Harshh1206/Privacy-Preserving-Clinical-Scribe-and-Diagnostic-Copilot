import type { Claim, Evidence } from '../models/types';
import { getClaimBadgeClass, getClaimStatusLabel, getSeverityBadgeClass, getSectionLabel } from '../utils/format';

interface EvidencePanelProps {
  claim: Claim | null;
  evidenceList: Evidence[];
  onJumpToTranscript?: (entryId: string) => void;
}

function IconQuote() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/>
      <path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/>
    </svg>
  );
}

function IconJump() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      <polyline points="15 3 21 3 21 9"/>
      <line x1="10" y1="14" x2="21" y2="3"/>
    </svg>
  );
}

function IconNoEvidence() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-slate-700">
      <circle cx="12" cy="12" r="10"/>
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
    </svg>
  );
}

export default function EvidencePanel({ claim, evidenceList, onJumpToTranscript }: EvidencePanelProps) {
  if (!claim) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4 py-8">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-slate-700 mb-2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        <p className="text-xs text-slate-500">Select a claim from the Validation panel to view its transcript evidence.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Claim detail */}
      <div className="px-3 py-2.5 border-b border-slate-800">
        <div className="flex items-start gap-2 mb-2">
          <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-slate-700 text-2xs font-bold text-slate-300 shrink-0 mt-0.5">
            {getSectionLabel(claim.soapSection)}
          </span>
          <p className="text-sm text-slate-200 leading-snug flex-1">{claim.text}</p>
        </div>
        <div className="flex items-center gap-2 ml-7">
          <span className={getClaimBadgeClass(claim.status)}>{getClaimStatusLabel(claim.status)}</span>
          <span className={getSeverityBadgeClass(claim.severity)}>{claim.severity}</span>
        </div>
      </div>

      {/* Conflict description */}
      {claim.conflictDescription && (
        <div className="px-3 py-2.5 bg-warn-500/10 border-b border-warn-500/20">
          <p className="text-xs font-semibold text-warn-400 mb-1">⚠ Conflict detected</p>
          <p className="text-xs text-warn-300 leading-relaxed">{claim.conflictDescription}</p>
        </div>
      )}

      {/* Suggested correction */}
      {claim.suggestedCorrection && (
        <div className="px-3 py-2 bg-brand-500/5 border-b border-brand-500/20">
          <p className="text-xs font-semibold text-brand-400 mb-1">Suggested correction</p>
          <p className="text-xs text-brand-300 leading-relaxed">{claim.suggestedCorrection}</p>
        </div>
      )}

      {/* Evidence list */}
      <div className="flex-1 overflow-auto">
        {evidenceList.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 py-6">
            <IconNoEvidence />
            <p className="text-xs text-slate-500 mt-2">
              {claim.status === 'unsupported'
                ? 'No supporting evidence found in the transcript.'
                : 'No evidence linked to this claim.'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            <div className="px-3 py-1.5 text-2xs text-slate-500 uppercase tracking-wider font-semibold">
              {evidenceList.length} transcript excerpt{evidenceList.length > 1 ? 's' : ''}
            </div>
            {evidenceList.map(ev => (
              <div key={ev.id} className="px-3 py-3">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-2xs font-mono text-slate-500">{ev.timestamp}</span>
                    <span className="text-2xs text-slate-400">{ev.speaker}</span>
                    <span className="badge badge-neutral text-2xs">{ev.matchType}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-2xs text-slate-500">{Math.round(ev.relevanceScore * 100)}% match</span>
                    {onJumpToTranscript && (
                      <button
                        onClick={() => onJumpToTranscript(ev.transcriptEntryId)}
                        className="flex items-center gap-1 text-2xs text-brand-400 hover:text-brand-300 transition-colors"
                        title="Jump to transcript entry"
                      >
                        <IconJump /> Jump
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <span className="text-slate-600 mt-0.5 shrink-0"><IconQuote /></span>
                  <p className="text-sm text-slate-300 leading-relaxed italic">
                    "{ev.transcriptText}"
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
