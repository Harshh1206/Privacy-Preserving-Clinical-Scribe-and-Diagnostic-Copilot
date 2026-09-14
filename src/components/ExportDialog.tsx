import { useState } from 'react';
import type { ExportFormat, ExportResult } from '../models/types';
import { exportPDF, exportFHIR, sendToEHR } from '../services/api';

interface ExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  consultationId: string;
  patientName: string;
  isFinalized: boolean;
}

type Tab = 'pdf' | 'fhir' | 'ehr';

function IconDownload() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  );
}

function IconFHIR() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6"/>
      <polyline points="8 6 2 12 8 18"/>
    </svg>
  );
}

function IconSend() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function downloadBase64PDF(base64: string, filename: string) {
  try {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (err) {
    console.error('Download error:', err);
  }
}

function openPDFInNewTab(base64: string) {
  try {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (err) {
    console.error('Preview error:', err);
  }
}

function downloadTextFile(content: string, filename: string, mimeType: string) {
  try {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (err) {
    console.error('Download error:', err);
  }
}

export default function ExportDialog({ isOpen, onClose, consultationId, patientName, isFinalized }: ExportDialogProps) {
  const [activeTab, setActiveTab] = useState<Tab>('pdf');
  const [includeTranscript, setIncludeTranscript] = useState(false);
  const [includeValidation, setIncludeValidation] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [result, setResult] = useState<ExportResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [ehrResult, setEhrResult] = useState<{ success: boolean; confirmationId: string; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleExport() {
    setIsExporting(true);
    setResult(null);
    setEhrResult(null);
    setError(null);
    setCopied(false);

    try {
      const req = { consultationId, format: activeTab as ExportFormat, includeTranscript, includeValidation };
      if (activeTab === 'pdf') {
        const res = await exportPDF(req);
        setResult(res);
        // Automatically trigger browser download
        downloadBase64PDF(res.content, res.filename);
      } else if (activeTab === 'fhir') {
        const res = await exportFHIR(req);
        setResult(res);
        // Automatically trigger browser download
        downloadTextFile(res.content, res.filename, 'application/json');
      } else {
        const res = await sendToEHR(req);
        setEhrResult(res);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setIsExporting(false);
    }
  }

  function handleClose() {
    setResult(null);
    setEhrResult(null);
    setError(null);
    setCopied(false);
    onClose();
  }

  function handleCopyJSON() {
    if (result?.content) {
      navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const TABS: { key: Tab; label: string; icon: React.ReactNode; description: string }[] = [
    { key: 'pdf', label: 'PDF Export', icon: <IconDownload />, description: 'Download a fully formatted, printable PDF of the clinical encounter note.' },
    { key: 'fhir', label: 'FHIR Export', icon: <IconFHIR />, description: 'Export as a HL7 FHIR R4 Composition resource (JSON).' },
    { key: 'ehr', label: 'Send to EHR', icon: <IconSend />, description: 'Transmit this note directly to the connected EHR system.' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg w-full max-w-lg shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Export / Send Clinical Record</h2>
            <p className="text-xs text-slate-500">Patient: {patientName} · Encounter: {consultationId}</p>
          </div>
          <button onClick={handleClose} className="text-slate-500 hover:text-slate-300 transition-colors p-1">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Not finalized warning */}
        {!isFinalized && (
          <div className="px-4 py-2 bg-warn-500/10 border-b border-warn-500/20 text-warn-300 text-xs shrink-0 flex items-center gap-2">
            <span>⚠</span>
            <span>This note is still a draft. The exported document will carry a "DRAFT NOTE" indicator until finalized.</span>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-slate-800 shrink-0">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => { setActiveTab(tab.key); setResult(null); setEhrResult(null); setError(null); }}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm transition-colors ${
                activeTab === tab.key
                  ? 'text-brand-300 border-b-2 border-brand-500 -mb-px font-medium bg-slate-800/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="px-4 py-4 overflow-y-auto space-y-4">
          <p className="text-xs text-slate-400">{TABS.find(t => t.key === activeTab)?.description}</p>

          {/* Options (PDF & FHIR) */}
          {activeTab !== 'ehr' && (
            <div className="bg-slate-950/60 border border-slate-800 rounded-md p-3 space-y-2">
              <span className="text-2xs font-semibold text-slate-400 uppercase tracking-wider block">Document Contents</span>
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeValidation}
                  onChange={e => setIncludeValidation(e.target.checked)}
                  className="rounded border-slate-600 bg-slate-800 text-brand-500 focus:ring-brand-500"
                />
                <span className="text-xs text-slate-200">Include AI Grounding & Validation Report</span>
              </label>
              <label className="flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeTranscript}
                  onChange={e => setIncludeTranscript(e.target.checked)}
                  className="rounded border-slate-600 bg-slate-800 text-brand-500 focus:ring-brand-500"
                />
                <span className="text-xs text-slate-200">Include Ambient Audio Dialogue Transcript</span>
              </label>
            </div>
          )}

          {/* Result for PDF */}
          {result && activeTab === 'pdf' && (
            <div className="rounded-md border border-ok-500/30 bg-ok-500/10 p-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-ok-400 font-medium text-xs">
                  <IconCheck />
                  <span>PDF Generated and Download Triggered!</span>
                </div>
                <span className="text-2xs font-mono text-slate-400">
                  {Math.round((result.content.length * 0.75) / 1024)} KB
                </span>
              </div>

              <div className="bg-slate-900/90 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-2xs text-slate-300 break-all flex items-center justify-between">
                <span>📄 {result.filename}</span>
              </div>

              <p className="text-2xs text-slate-400">
                If your browser did not automatically download the file, click below:
              </p>

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => downloadBase64PDF(result.content, result.filename)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors shadow-sm"
                >
                  <IconDownload />
                  <span>Download PDF Again</span>
                </button>
                <button
                  onClick={() => openPDFInNewTab(result.content)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                    <polyline points="15 3 21 3 21 9"/>
                    <line x1="10" y1="14" x2="21" y2="3"/>
                  </svg>
                  <span>Preview in New Tab</span>
                </button>
              </div>
            </div>
          )}

          {/* Result for FHIR */}
          {result && activeTab === 'fhir' && (
            <div className="rounded-md border border-ok-500/30 bg-ok-500/10 p-3 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-ok-400 font-medium text-xs">
                  <IconCheck />
                  <span>FHIR R4 JSON Exported & Downloaded</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={handleCopyJSON}
                    className="text-2xs px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                  >
                    {copied ? '✓ Copied' : 'Copy JSON'}
                  </button>
                  <button
                    onClick={() => downloadTextFile(result.content, result.filename, 'application/json')}
                    className="text-2xs px-2 py-0.5 rounded bg-brand-600 hover:bg-brand-500 text-white transition-colors"
                  >
                    Download
                  </button>
                </div>
              </div>

              <div className="bg-slate-900/90 border border-slate-800 rounded px-2.5 py-1.5 font-mono text-2xs text-slate-300">
                📄 {result.filename}
              </div>

              <pre className="text-2xs text-slate-300 overflow-auto max-h-40 font-mono bg-slate-950 rounded p-2.5 border border-slate-800">
                {result.content}
              </pre>
            </div>
          )}

          {/* Result for EHR */}
          {ehrResult && (
            <div className="rounded-md border border-ok-500/30 bg-ok-500/10 p-3 space-y-2">
              <div className="flex items-center gap-1.5 text-ok-400 font-medium text-xs">
                <IconCheck />
                <span>Successfully Transmitted to EHR</span>
              </div>
              <p className="text-xs text-slate-300">{ehrResult.message}</p>
              <div className="p-2 bg-slate-950 rounded border border-slate-800 font-mono text-2xs text-brand-300">
                Confirmation ID: {ehrResult.confirmationId}
              </div>
              <p className="text-2xs text-slate-500 italic">
                Service boundary: Replace `sendToEHR()` with real HL7 FHIR / Epic SMART-on-FHIR endpoint.
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-md border border-danger-500/30 bg-danger-500/10 p-3 text-xs text-danger-300">
              Error: {error}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800 shrink-0 bg-slate-900/60">
          <span className="text-2xs text-slate-500">
            {activeTab === 'pdf' ? 'Real downloadable binary PDF' : activeTab === 'fhir' ? 'FHIR R4 Composition' : 'HL7 EHR integration'}
          </span>
          <div className="flex items-center gap-2">
            <button className="btn-ghost btn-sm" onClick={handleClose}>
              {result || ehrResult ? 'Done' : 'Cancel'}
            </button>
            <button
              className="btn-primary btn-sm flex items-center gap-1.5"
              onClick={handleExport}
              disabled={isExporting}
            >
              {isExporting ? (
                <>
                  <svg className="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  <span>Generating…</span>
                </>
              ) : activeTab === 'ehr' ? (
                <>
                  <IconSend />
                  <span>Send to EHR</span>
                </>
              ) : activeTab === 'fhir' ? (
                <>
                  <IconFHIR />
                  <span>Generate & Download FHIR</span>
                </>
              ) : (
                <>
                  <IconDownload />
                  <span>Generate & Download PDF</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
