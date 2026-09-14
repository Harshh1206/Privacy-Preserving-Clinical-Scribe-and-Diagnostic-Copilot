import { useState, useEffect } from 'react';
import type { SOAPNote } from '../models/types';

interface SOAPEditorProps {
  note: SOAPNote;
  isStale?: boolean;
  onSave: (patch: Partial<Pick<SOAPNote, 'subjective' | 'objective' | 'assessment' | 'plan'>>) => Promise<void>;
  isSaving?: boolean;
}

type SectionKey = 'subjective' | 'objective' | 'assessment' | 'plan';

const SECTIONS: { key: SectionKey; label: string; abbr: string }[] = [
  { key: 'subjective',  label: 'Subjective',  abbr: 'S' },
  { key: 'objective',   label: 'Objective',   abbr: 'O' },
  { key: 'assessment',  label: 'Assessment',  abbr: 'A' },
  { key: 'plan',        label: 'Plan',        abbr: 'P' },
];

function IconEdit() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
  );
}

function IconLock() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}

function IconWarn() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

export default function SOAPEditor({ note, isStale, onSave, isSaving }: SOAPEditorProps) {
  const [draft, setDraft] = useState({
    subjective: note.subjective.text,
    objective: note.objective.text,
    assessment: note.assessment.text,
    plan: note.plan.text,
  });
  const [dirty, setDirty] = useState(false);
  const [activeSection, setActiveSection] = useState<SectionKey | null>(null);

  // Sync draft when note prop changes externally
  useEffect(() => {
    setDraft({
      subjective: note.subjective.text,
      objective: note.objective.text,
      assessment: note.assessment.text,
      plan: note.plan.text,
    });
    setDirty(false);
  }, [note.id, note.version]);

  function handleChange(key: SectionKey, value: string) {
    setDraft(prev => ({ ...prev, [key]: value }));
    setDirty(true);
  }

  async function handleSave() {
    await onSave({
      subjective: { ...note.subjective, text: draft.subjective },
      objective:  { ...note.objective,  text: draft.objective },
      assessment: { ...note.assessment, text: draft.assessment },
      plan:       { ...note.plan,       text: draft.plan },
    });
    setDirty(false);
  }

  const finalized = note.isFinalized;

  return (
    <div className="flex flex-col h-full">
      {/* Stale warning */}
      {isStale && !finalized && (
        <div className="flex items-center gap-2 px-3 py-2 bg-warn-500/10 border-b border-warn-500/30 text-warn-300 text-xs">
          <IconWarn />
          <span className="font-medium">Validation is stale.</span>
          <span className="text-slate-400">This note was edited after the last validation run. Revalidate to update grounding scores.</span>
        </div>
      )}

      {/* Finalized banner */}
      {finalized && (
        <div className="flex items-center gap-2 px-3 py-2 bg-ok-500/10 border-b border-ok-500/20 text-ok-300 text-xs">
          <IconLock />
          <span className="font-medium">Note finalized.</span>
          <span className="text-slate-400">Finalized by {note.finalizedBy} — read-only.</span>
        </div>
      )}

      {/* Dirty indicator */}
      {dirty && !finalized && (
        <div className="flex items-center justify-between px-3 py-1.5 bg-slate-800/80 border-b border-slate-700 text-xs">
          <span className="text-slate-400">Unsaved changes</span>
          <div className="flex gap-2">
            <button
              className="text-slate-500 hover:text-slate-300 transition-colors"
              onClick={() => {
                setDraft({
                  subjective: note.subjective.text,
                  objective: note.objective.text,
                  assessment: note.assessment.text,
                  plan: note.plan.text,
                });
                setDirty(false);
              }}
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {/* SOAP sections */}
      <div className="flex-1 overflow-auto divide-y divide-slate-800">
        {SECTIONS.map(({ key, label, abbr }) => (
          <div
            key={key}
            className={`transition-colors ${activeSection === key ? 'bg-slate-800/30' : ''}`}
          >
            <div className="flex items-center gap-2 px-3 pt-2.5 pb-1">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-brand-600/20 text-brand-300 text-xs font-bold shrink-0">
                {abbr}
              </span>
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">{label}</span>
              {!finalized && (
                <span className="ml-auto text-slate-600">
                  <IconEdit />
                </span>
              )}
            </div>
            {finalized ? (
              <div className="px-3 pb-3 text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                {note[key].text}
              </div>
            ) : (
              <textarea
                className="w-full bg-transparent border-0 focus:outline-none focus:ring-0 px-3 pb-3 pt-0 text-sm text-slate-200 leading-relaxed resize-none"
                rows={key === 'plan' ? 7 : key === 'subjective' ? 4 : 3}
                value={draft[key]}
                onChange={e => handleChange(key, e.target.value)}
                onFocus={() => setActiveSection(key)}
                onBlur={() => setActiveSection(null)}
                disabled={finalized}
                placeholder={`Enter ${label} notes…`}
              />
            )}
            {note[key].lastEditedAt && (
              <div className="px-3 pb-1.5 text-2xs text-slate-600">
                Last edited {new Date(note[key].lastEditedAt!).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                {note[key].lastEditedBy && ` by ${note[key].lastEditedBy}`}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Save footer */}
      {!finalized && (
        <div className="border-t border-slate-800 px-3 py-2 flex items-center justify-between">
          <span className="text-2xs text-slate-600">v{note.version}</span>
          <button
            className="btn-primary btn-sm"
            onClick={handleSave}
            disabled={!dirty || isSaving}
          >
            {isSaving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      )}
    </div>
  );
}
