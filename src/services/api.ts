/**
 * Clinical Scribe — Service Layer (Team C)
 *
 * This module defines the API/service interface that Team B's real implementation
 * will replace. All method signatures, parameter shapes, and return types are
 * intentionally stable. Replace the mock implementations below with real HTTP
 * calls by swapping out this file (or a sub-module it imports).
 *
 * MOCK STATUS: All methods return typed mock data with a simulated network delay.
 */

import type {
  Patient, Consultation, Transcript, SOAPNote,
  ValidationResult, AuditEntry, ExportRequest, ExportResult,
} from '../models/types';

import {
  MOCK_PATIENTS, MOCK_CONSULTATIONS, MOCK_AUDITS,
  TRANSCRIPTS, SOAP_NOTES, VALIDATIONS,
  MOCK_VALIDATION_001, MOCK_VALIDATION_002, MOCK_VALIDATION_003,
} from '../data/mockData';
import { generateClinicalPDF } from './pdfGenerator';

// In-memory mutable state so edits persist within the session
const _patients = [...MOCK_PATIENTS];
const _consultations = [...MOCK_CONSULTATIONS];
const _soapNotes: Record<string, SOAPNote> = { ...SOAP_NOTES };
const _validations: Record<string, ValidationResult> = { ...VALIDATIONS };
const _audits: AuditEntry[] = [...MOCK_AUDITS];

function delay<T>(value: T, ms = 300): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(value), ms));
}

function now(): string {
  return new Date().toISOString();
}

// ─── Patients ─────────────────────────────────────────────────────────────────

export async function getPatients(): Promise<Patient[]> {
  return delay(_patients);
}

export async function getPatient(patientId: string): Promise<Patient | null> {
  return delay(_patients.find(p => p.id === patientId) ?? null);
}

// ─── Consultations ────────────────────────────────────────────────────────────

export async function getConsultations(patientId?: string): Promise<Consultation[]> {
  const list = patientId
    ? _consultations.filter(c => c.patientId === patientId)
    : _consultations;
  return delay([...list].sort((a, b) => b.date.localeCompare(a.date)));
}

export async function getConsultation(consultationId: string): Promise<Consultation | null> {
  return delay(_consultations.find(c => c.id === consultationId) ?? null);
}

// ─── Transcript (Team A output) ───────────────────────────────────────────────

export async function getTranscript(transcriptId: string): Promise<Transcript | null> {
  return delay(TRANSCRIPTS[transcriptId] ?? null, 200);
}

// ─── SOAP Note (Team B output — currently mocked) ────────────────────────────

export async function getSOAPNote(soapNoteId: string): Promise<SOAPNote | null> {
  return delay(_soapNotes[soapNoteId] ?? null, 200);
}

export async function updateSOAPNote(
  soapNoteId: string,
  patch: Partial<Pick<SOAPNote, 'subjective' | 'objective' | 'assessment' | 'plan'>>
): Promise<SOAPNote> {
  const note = _soapNotes[soapNoteId];
  if (!note) throw new Error(`SOAP note ${soapNoteId} not found`);
  if (note.isFinalized) throw new Error('Cannot edit a finalized SOAP note');

  const updated: SOAPNote = {
    ...note,
    ...patch,
    version: note.version + 1,
    updatedAt: now(),
  };
  _soapNotes[soapNoteId] = updated;

  // Mark associated validation as stale
  const con = _consultations.find(c => c.soapNoteId === soapNoteId);
  if (con?.validationId && _validations[con.validationId]) {
    _validations[con.validationId] = { ..._validations[con.validationId], isStale: true };
  }

  // Audit
  _audits.push({
    id: `au-${Date.now()}`,
    consultationId: con?.id ?? 'unknown',
    timestamp: now(),
    action: 'edited',
    actor: 'Dr. Sarah Chen',
    detail: `SOAP note edited. Version bumped to v${updated.version}.`,
    soapVersion: updated.version,
  });

  return delay(updated, 200);
}

// ─── Validation (Team B output — currently mocked) ───────────────────────────

export async function validateConsultation(consultationId: string): Promise<ValidationResult> {
  const con = _consultations.find(c => c.id === consultationId);
  if (!con) throw new Error(`Consultation ${consultationId} not found`);

  // Simulate revalidation with current SOAP version
  const note = _soapNotes[con.soapNoteId];
  let freshValidation: ValidationResult;

  if (consultationId === 'con-001') {
    freshValidation = { ...MOCK_VALIDATION_001, soapNoteVersion: note?.version ?? 1, isStale: false, validatedAt: now() };
  } else if (consultationId === 'con-002') {
    freshValidation = { ...MOCK_VALIDATION_002, soapNoteVersion: note?.version ?? 1, isStale: false, validatedAt: now() };
  } else if (consultationId === 'con-003') {
    freshValidation = { ...MOCK_VALIDATION_003, soapNoteVersion: note?.version ?? 1, isStale: false, validatedAt: now() };
  } else {
    freshValidation = { ..._validations[con.validationId ?? ''], isStale: false, validatedAt: now() };
  }

  if (con.validationId) {
    _validations[con.validationId] = freshValidation;
  }

  _audits.push({
    id: `au-${Date.now()}`,
    consultationId,
    timestamp: now(),
    action: 'revalidated',
    actor: 'System',
    detail: `Revalidation complete. Grounding Score: ${freshValidation.groundingScore}/100. Risk: ${freshValidation.hallucinationRisk}.`,
    soapVersion: freshValidation.soapNoteVersion,
  });

  return delay(freshValidation, 800);
}

export async function getValidation(validationId: string): Promise<ValidationResult | null> {
  return delay(_validations[validationId] ?? null, 200);
}

// ─── Finalization ─────────────────────────────────────────────────────────────

export async function finalizeConsultation(
  consultationId: string,
  physicianId: string,
  physicianName: string
): Promise<{ consultation: Consultation; soapNote: SOAPNote }> {
  const con = _consultations.find(c => c.id === consultationId);
  if (!con) throw new Error(`Consultation ${consultationId} not found`);

  const note = _soapNotes[con.soapNoteId];
  if (!note) throw new Error('SOAP note not found');

  const finalNote: SOAPNote = {
    ...note,
    isFinalized: true,
    finalizedAt: now(),
    finalizedBy: physicianName,
    updatedAt: now(),
  };
  _soapNotes[con.soapNoteId] = finalNote;

  const idx = _consultations.findIndex(c => c.id === consultationId);
  const finalCon: Consultation = {
    ...con,
    status: 'finalized',
    finalisedAt: now(),
    updatedAt: now(),
  };
  _consultations[idx] = finalCon;

  _audits.push({
    id: `au-${Date.now()}`,
    consultationId,
    timestamp: now(),
    action: 'finalized',
    actor: physicianName,
    detail: `Consultation finalized by ${physicianName}. SOAP note v${finalNote.version} locked.`,
    soapVersion: finalNote.version,
  });

  return delay({ consultation: finalCon, soapNote: finalNote }, 400);
}

// ─── Audit ────────────────────────────────────────────────────────────────────

export async function getAuditTrail(consultationId: string): Promise<AuditEntry[]> {
  return delay(_audits.filter(a => a.consultationId === consultationId).sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
}

// ─── Export / EHR ─────────────────────────────────────────────────────────────

/**
 * exportPDF — Generates a real clinical encounter PDF using client-side jsPDF
 * and records the export action in the audit trail.
 */
export async function exportPDF(req: ExportRequest): Promise<ExportResult> {
  const con = _consultations.find(c => c.id === req.consultationId);
  if (!con) throw new Error(`Consultation ${req.consultationId} not found`);

  const patient = _patients.find(p => p.id === con.patientId);
  if (!patient) throw new Error(`Patient ${con.patientId} not found`);

  const soapNote = _soapNotes[con.soapNoteId];
  if (!soapNote) throw new Error(`SOAP note ${con.soapNoteId} not found`);

  const validation = con.validationId ? _validations[con.validationId] : null;
  const transcript = con.transcriptId ? TRANSCRIPTS[con.transcriptId] : null;

  const { base64 } = generateClinicalPDF({
    consultation: con,
    patient,
    soapNote,
    validation,
    transcript,
    includeTranscript: req.includeTranscript,
    includeValidation: req.includeValidation,
  });

  await delay(null, 300);

  const filename = `ClinicalNote_${patient.lastName}_${req.consultationId}_${Date.now()}.pdf`;

  _audits.push({
    id: `au-${Date.now()}`,
    consultationId: req.consultationId,
    timestamp: now(),
    action: 'exported',
    actor: 'Dr. Sarah Chen',
    detail: `Exported PDF: ${filename} (transcript: ${req.includeTranscript}, validation: ${req.includeValidation}).`,
    soapVersion: soapNote.version,
  });

  return {
    format: 'pdf',
    filename,
    content: base64,
    generatedAt: now(),
  };
}

/**
 * exportFHIR — SERVICE BOUNDARY
 * Replace with real FHIR R4 resource builder endpoint.
 * Returns a mock FHIR Composition resource JSON.
 */
export async function exportFHIR(req: ExportRequest): Promise<ExportResult> {
  const con = _consultations.find(c => c.id === req.consultationId);
  const note = con ? _soapNotes[con.soapNoteId] : null;

  const fhirResource = {
    resourceType: 'Composition',
    id: `comp-${req.consultationId}`,
    status: 'final',
    type: {
      coding: [{ system: 'http://loinc.org', code: '11488-4', display: 'Consult note' }],
    },
    date: now(),
    title: 'Clinical Encounter Note',
    section: [
      { title: 'Subjective', text: { status: 'generated', div: `<div>${note?.subjective.text ?? ''}</div>` } },
      { title: 'Objective', text: { status: 'generated', div: `<div>${note?.objective.text ?? ''}</div>` } },
      { title: 'Assessment', text: { status: 'generated', div: `<div>${note?.assessment.text ?? ''}</div>` } },
      { title: 'Plan', text: { status: 'generated', div: `<div>${note?.plan.text ?? ''}</div>` } },
    ],
    // MOCK: Real impl resolves Patient/Practitioner/Organization references
    _mock: true,
  };

  await delay(null, 400);

  return {
    format: 'fhir',
    filename: `FHIR_${req.consultationId}_${Date.now()}.json`,
    content: JSON.stringify(fhirResource, null, 2),
    generatedAt: now(),
  };
}

/**
 * sendToEHR — SERVICE BOUNDARY
 * Replace with real EHR integration (HL7 FHIR API, Epic SMART, Cerner, etc.).
 * Currently simulates a POST and returns a mock confirmation.
 */
export async function sendToEHR(req: ExportRequest): Promise<{ success: boolean; confirmationId: string; message: string }> {
  await delay(null, 1200);

  const con = _consultations.find(c => c.id === req.consultationId);

  _audits.push({
    id: `au-${Date.now()}`,
    consultationId: req.consultationId,
    timestamp: now(),
    action: 'sent_to_ehr',
    actor: 'Dr. Sarah Chen',
    detail: `MOCK: Note sent to EHR system. Confirmation ID: EHR-MOCK-${Date.now()}.`,
  });

  return {
    success: true,
    confirmationId: `EHR-MOCK-${Date.now()}`,
    message: `Note for consultation ${req.consultationId} successfully transmitted to Mock EHR. Patient: ${con?.patientId ?? 'unknown'}.`,
  };
}
