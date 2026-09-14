import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Consultation, Patient, Transcript, SOAPNote, ValidationResult, Claim, Evidence, AuditEntry } from '../models/types';
import {
  getConsultation, getPatient, getTranscript, getSOAPNote,
  getValidation, updateSOAPNote, validateConsultation,
  finalizeConsultation, getAuditTrail
} from '../services/api';
import { formatDateTime, getStatusBadgeClass, getStatusLabel, calcAge } from '../utils/format';

import TranscriptPanel from '../components/TranscriptPanel';
import SOAPEditor from '../components/SOAPEditor';
import ValidationPanel from '../components/ValidationPanel';
import EvidencePanel from '../components/EvidencePanel';
import FinalizeDialog from '../components/FinalizeDialog';
import ExportDialog from '../components/ExportDialog';

function IconBack() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6"/>
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/>
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
    </svg>
  );
}

function IconExport() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  );
}

function IconLock() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}

function IconAudit() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
    </svg>
  );
}

function IconAllergy() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

// ─── Audit trail panel ────────────────────────────────────────────────────────

function AuditTrail({ entries }: { entries: AuditEntry[] }) {
  const ACTION_COLORS: Record<string, string> = {
    created: 'text-slate-400',
    edited: 'text-brand-400',
    validated: 'text-ok-400',
    revalidated: 'text-ok-400',
    finalized: 'text-ok-400 font-semibold',
    exported: 'text-slate-400',
    sent_to_ehr: 'text-brand-400',
  };

  return (
    <div className="divide-y divide-slate-800">
      {entries.map(entry => (
        <div key={entry.id} className="px-3 py-2">
          <div className="flex items-center justify-between mb-0.5">
            <span className={`text-xs capitalize ${ACTION_COLORS[entry.action] ?? 'text-slate-400'}`}>
              {entry.action.replace('_', ' ')}
            </span>
            <span className="text-2xs text-slate-600 font-mono">
              {new Date(entry.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <p className="text-2xs text-slate-500">{entry.detail}</p>
          <p className="text-2xs text-slate-700">{entry.actor}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Main workspace ───────────────────────────────────────────────────────────

export default function ConsultationWorkspace() {
  const { consultationId } = useParams<{ consultationId: string }>();

  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [soapNote, setSoapNote] = useState<SOAPNote | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);

  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence[]>([]);
  const [highlightedTranscriptId, setHighlightedTranscriptId] = useState<string | null>(null);

  const [showFinalize, setShowFinalize] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showAudit, setShowAudit] = useState(false);

  // Load all data
  useEffect(() => {
    if (!consultationId) return;
    setLoading(true);
    setError(null);

    getConsultation(consultationId)
      .then(async con => {
        if (!con) throw new Error('Consultation not found');
        setConsultation(con);

        const [pt, tx, soap, val, audit] = await Promise.all([
          getPatient(con.patientId),
          getTranscript(con.transcriptId),
          getSOAPNote(con.soapNoteId),
          con.validationId ? getValidation(con.validationId) : Promise.resolve(null),
          getAuditTrail(consultationId),
        ]);

        setPatient(pt);
        setTranscript(tx);
        setSoapNote(soap);
        setValidation(val);
        setAuditTrail(audit);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [consultationId]);

  // Save SOAP
  const handleSave = useCallback(async (
    patch: Partial<Pick<SOAPNote, 'subjective' | 'objective' | 'assessment' | 'plan'>>
  ) => {
    if (!soapNote) return;
    setIsSaving(true);
    try {
      const updated = await updateSOAPNote(soapNote.id, patch);
      setSoapNote(updated);
      setValidation(prev => prev ? { ...prev, isStale: true } : prev);
    } finally {
      setIsSaving(false);
    }
  }, [soapNote]);

  // Revalidate
  async function handleRevalidate() {
    if (!consultationId) return;
    setIsValidating(true);
    try {
      const val = await validateConsultation(consultationId);
      setValidation(val);
      const audit = await getAuditTrail(consultationId);
      setAuditTrail(audit);
    } finally {
      setIsValidating(false);
    }
  }

  // Finalize
  async function handleFinalize() {
    if (!consultationId) return;
    const { consultation: fc, soapNote: fn } = await finalizeConsultation(
      consultationId, 'dr-001', 'Dr. Sarah Chen'
    );
    setConsultation(fc);
    setSoapNote(fn);
    const audit = await getAuditTrail(consultationId);
    setAuditTrail(audit);
  }

  // Claim → evidence → transcript jump
  function handleClaimSelect(claim: Claim, evidence: Evidence[]) {
    setSelectedClaim(claim);
    setSelectedEvidence(evidence);
    setHighlightedTranscriptId(null);
  }

  function handleJumpToTranscript(entryId: string) {
    setHighlightedTranscriptId(entryId);
  }

  // ─── Loading / Error ──────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"/>
          <p className="text-sm text-slate-500">Loading consultation…</p>
        </div>
      </div>
    );
  }

  if (error || !consultation || !patient) {
    return (
      <div className="flex-1 flex items-center justify-center text-danger-400 text-sm">
        {error ?? 'Consultation not found.'}
      </div>
    );
  }

  const finalized = soapNote?.isFinalized ?? false;
  const isStale = validation?.isStale ?? false;

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-w-0">
      {/* Top bar */}
      <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center gap-3 shrink-0">
        <Link
          to={`/patients/${patient.id}`}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors shrink-0"
        >
          <IconBack /> {patient.lastName}, {patient.firstName}
        </Link>
        <span className="text-slate-700">›</span>
        <span className="text-xs text-slate-400 truncate">{consultation.chiefComplaint}</span>
        <span className="text-xs text-slate-600">{formatDateTime(consultation.date)}</span>

        {/* Allergy alert */}
        {patient.allergies.length > 0 && (
          <span className="flex items-center gap-1 text-danger-400 text-xs font-medium bg-danger-500/10 px-2 py-0.5 rounded">
            <IconAllergy />
            ALLERGY: {patient.allergies.map(a => a.split('—')[0].trim()).join(', ')}
          </span>
        )}

        <span className={`${getStatusBadgeClass(consultation.status)} ml-1`}>
          {getStatusLabel(consultation.status)}
        </span>

        {isStale && !finalized && (
          <span className="badge badge-warn">Validation stale</span>
        )}

        {/* Actions */}
        <div className="ml-auto flex items-center gap-2">
          <button
            className="btn-ghost btn-sm flex items-center gap-1.5"
            onClick={() => setShowAudit(s => !s)}
          >
            <IconAudit />
            <span className="hidden lg:inline">Audit</span>
          </button>

          <button
            className="btn-ghost btn-sm flex items-center gap-1.5"
            onClick={() => setShowExport(true)}
          >
            <IconExport />
            <span className="hidden lg:inline">Export / Send</span>
          </button>

          {!finalized && (
            <>
              <button
                className={`btn-secondary btn-sm flex items-center gap-1.5 ${isValidating ? 'opacity-60' : ''}`}
                onClick={handleRevalidate}
                disabled={isValidating}
              >
                <IconRefresh />
                {isValidating ? 'Validating…' : 'Revalidate'}
              </button>

              <button
                className="btn-primary btn-sm flex items-center gap-1.5"
                onClick={() => setShowFinalize(true)}
              >
                <IconLock />
                Finalize Note
              </button>
            </>
          )}

          {finalized && (
            <span className="flex items-center gap-1 text-xs text-ok-400 font-medium">
              <IconLock /> Finalized
            </span>
          )}
        </div>
      </div>

      {/* Patient meta bar */}
      <div className="bg-slate-950 border-b border-slate-800 px-4 py-1.5 flex items-center gap-4 text-xs text-slate-500 shrink-0">
        <span className="font-medium text-slate-300">{patient.firstName} {patient.lastName}</span>
        <span>{patient.mrn}</span>
        <span>{calcAge(patient.dob)} y/o {patient.sex}</span>
        <span>{consultation.physicianName}</span>
        {consultation.duration && <span>{consultation.duration} min</span>}
      </div>

      {/* Main 3-column layout */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Column 1: Transcript */}
        <div className="w-[30%] min-w-[280px] flex flex-col border-r border-slate-800 overflow-hidden">
          <div className="panel-header shrink-0">
            <span className="panel-title">Transcript</span>
            <span className="text-2xs text-slate-600">
              {transcript?.entries.length ?? 0} entries · Team A
            </span>
          </div>
          <div className="flex-1 overflow-auto">
            <TranscriptPanel
              entries={transcript?.entries ?? []}
              highlightedEntryId={highlightedTranscriptId}
              loading={!transcript}
            />
          </div>
        </div>

        {/* Column 2: SOAP Note */}
        <div className="w-[35%] min-w-[300px] flex flex-col border-r border-slate-800 overflow-hidden">
          <div className="panel-header shrink-0">
            <span className="panel-title">SOAP Note</span>
            {soapNote && (
              <span className="text-2xs text-slate-600">v{soapNote.version}{finalized ? ' · finalized' : ''}</span>
            )}
          </div>
          <div className="flex-1 overflow-hidden">
            {soapNote ? (
              <SOAPEditor
                note={soapNote}
                isStale={isStale}
                onSave={handleSave}
                isSaving={isSaving}
              />
            ) : (
              <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
                No SOAP note found.
              </div>
            )}
          </div>
        </div>

        {/* Column 3: Validation + Evidence */}
        <div className="flex-1 min-w-[280px] flex flex-col overflow-hidden">
          {/* Validation sub-panel */}
          <div className="flex flex-col" style={{ height: selectedClaim ? '55%' : '100%' }}>
            <div className="panel-header shrink-0">
              <span className="panel-title">Validation</span>
              {validation && (
                <span className="text-2xs text-slate-600">
                  {validation.groundingScore}/100 grounding
                </span>
              )}
            </div>
            <div className="flex-1 overflow-hidden">
              {validation ? (
                <ValidationPanel
                  validation={validation}
                  onClaimSelect={handleClaimSelect}
                  selectedClaimId={selectedClaim?.id}
                  loading={isValidating}
                />
              ) : (
                <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
                  No validation data. Run Revalidate.
                </div>
              )}
            </div>
          </div>

          {/* Evidence sub-panel */}
          {selectedClaim && (
            <div className="border-t border-slate-800 flex flex-col" style={{ height: '45%' }}>
              <div className="panel-header shrink-0">
                <span className="panel-title">Evidence</span>
                <button
                  onClick={() => { setSelectedClaim(null); setSelectedEvidence([]); }}
                  className="text-slate-500 hover:text-slate-300 text-xs transition-colors"
                >
                  ✕ Close
                </button>
              </div>
              <div className="flex-1 overflow-auto">
                <EvidencePanel
                  claim={selectedClaim}
                  evidenceList={selectedEvidence}
                  onJumpToTranscript={handleJumpToTranscript}
                />
              </div>
            </div>
          )}
        </div>

        {/* Audit trail drawer */}
        {showAudit && (
          <div className="w-64 border-l border-slate-800 flex flex-col overflow-hidden bg-slate-900">
            <div className="panel-header shrink-0">
              <span className="panel-title">Audit Trail</span>
              <button onClick={() => setShowAudit(false)} className="text-slate-500 hover:text-slate-300 text-xs">✕</button>
            </div>
            <div className="flex-1 overflow-auto">
              {auditTrail.length === 0 ? (
                <p className="px-3 py-4 text-xs text-slate-600">No audit entries yet.</p>
              ) : (
                <AuditTrail entries={[...auditTrail].reverse()} />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Dialogs */}
      <FinalizeDialog
        isOpen={showFinalize}
        onClose={() => setShowFinalize(false)}
        onConfirm={handleFinalize}
        validation={validation}
        consultationId={consultation.id}
        patientName={`${patient.firstName} ${patient.lastName}`}
      />

      <ExportDialog
        isOpen={showExport}
        onClose={() => setShowExport(false)}
        consultationId={consultation.id}
        patientName={`${patient.firstName} ${patient.lastName}`}
        isFinalized={finalized}
      />
    </div>
  );
}
