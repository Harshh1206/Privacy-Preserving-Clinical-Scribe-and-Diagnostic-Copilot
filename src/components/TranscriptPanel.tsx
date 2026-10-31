import { useRef, useEffect } from 'react';
import type { TranscriptEntry } from '../models/types';
import { getSpeakerBadgeClass } from '../utils/format';

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
  highlightedEntryId?: string | null;
  onEntryClick?: (entry: TranscriptEntry) => void;
  loading?: boolean;
  diarizationStatus?: 'disabled' | 'processing' | 'completed' | 'failed';
  diarizationError?: string | null;
  onSpeakerMap?: (
    speakerId: string,
    speakerRole: 'doctor' | 'patient' | 'unknown',
    speakerDisplayName: string,
  ) => Promise<void>;
}

function IconLinked() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>
  );
}

export default function TranscriptPanel({ entries, highlightedEntryId, onEntryClick, loading, onSpeakerMap, diarizationStatus, diarizationError }: TranscriptPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to highlighted entry
  useEffect(() => {
    if (highlightedEntryId && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightedEntryId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="text-center">
          <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-1.5"/>
          <p className="text-xs text-slate-500">Loading transcript…</p>
        </div>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
        No transcript entries.
      </div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-0 divide-y divide-slate-800/60">
      {(diarizationStatus === 'failed' || diarizationStatus === 'disabled') && (
        <div className="px-3 py-2 text-2xs text-amber-400 bg-amber-950/20 border-b border-slate-800">
          {diarizationError || (diarizationStatus === 'disabled'
            ? 'Speaker diarization is unavailable because it is disabled.'
            : 'Speaker diarization is unavailable. Transcription text is still shown.')}
        </div>
      )}
      {entries.map(entry => {
        const isHighlighted = entry.id === highlightedEntryId;
        const hasLinkedClaims = (entry.linkedClaimIds?.length ?? 0) > 0;
        const utteranceClass =
          entry.speakerRole === 'doctor' || entry.speakerRole === 'physician'
            ? 'ml-0 mr-8 border-l-2 border-brand-500 bg-brand-950/20'
            : entry.speakerRole === 'patient'
              ? 'ml-8 mr-0 border-l-2 border-slate-500 bg-slate-800/30'
              : 'ml-4 mr-4 border-l-2 border-slate-700 bg-slate-900/30';

        return (
          <div
            key={entry.id}
            ref={isHighlighted ? highlightRef : undefined}
            onClick={() => onEntryClick?.(entry)}
            className={`px-3 py-2.5 transition-colors cursor-default ${utteranceClass} ${
              isHighlighted
                ? 'bg-brand-600/15 border-l-2 border-brand-500'
                : 'hover:bg-slate-800/40'
            } ${onEntryClick ? 'cursor-pointer' : ''}`}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className={`text-2xs font-semibold px-1.5 py-0.5 rounded ${getSpeakerBadgeClass(entry.speakerRole)}`}>
                  {entry.speakerDisplayName || entry.speaker}
                </span>
                <span className="text-2xs text-slate-500 font-mono">{entry.timestamp}</span>
                {entry.endTimeMs !== undefined && entry.startTimeMs !== undefined && (
                  <span className="text-2xs text-slate-600 font-mono">
                    {entry.startTimeMs}–{entry.endTimeMs} ms
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                {hasLinkedClaims && (
                  <span className="flex items-center gap-0.5 text-brand-400" title="This entry supports one or more SOAP claims">
                    <IconLinked />
                  </span>
                )}
                {entry.confidence !== undefined && entry.confidence !== null && Number.isFinite(entry.confidence) ? (
                  <span className="text-2xs text-slate-400" title={`ASR confidence: ${Math.round(entry.confidence * 100)}%`}>
                    {Math.round(entry.confidence * 100)}%
                  </span>
                ) : (
                  <span className="text-2xs text-slate-600" title="No genuine ASR confidence score was provided">N/A</span>
                )}
              </div>
            </div>
            <p className={`text-sm leading-relaxed ${
              isHighlighted ? 'text-slate-100' : 'text-slate-300'
            }`}>
              {entry.text}
            </p>
            {entry.speakerId && entry.speakerRole === 'unknown' && onSpeakerMap && (
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <span className="text-2xs text-slate-500">Identify this speaker:</span>
                <button
                  type="button"
                  className="text-2xs px-2 py-1 rounded bg-brand-600/20 text-brand-300"
                  onClick={(event) => {
                    event.stopPropagation();
                    void onSpeakerMap(entry.speakerId!, 'doctor', 'Doctor');
                  }}
                >
                  Doctor
                </button>
                <button
                  type="button"
                  className="text-2xs px-2 py-1 rounded bg-slate-700 text-slate-200"
                  onClick={(event) => {
                    event.stopPropagation();
                    void onSpeakerMap(entry.speakerId!, 'patient', 'Patient');
                  }}
                >
                  Patient
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
