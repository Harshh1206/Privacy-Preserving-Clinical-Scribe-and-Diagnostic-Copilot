/**
 * Clinical Scribe — Service Layer (Team C)
 *
 * HTTP client for the Team C FastAPI backend. Method signatures match the UI.
 */

import type {
  Patient, Consultation, Transcript, SOAPNote,
  ValidationResult, AuditEntry, ExportRequest, ExportResult,
  TeamBApiResponse,
} from '../models/types';

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') || 'http://localhost:8000';

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map(item => (typeof item === 'object' && item && 'msg' in item ? String((item as { msg: unknown }).msg) : JSON.stringify(item)))
        .join('; ');
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(detailMessage(body, res.statusText || `HTTP ${res.status}`));
  }
  return body as T;
}

async function getOrNull<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_BASE}${path}`);
  if (res.status === 404) return null;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(detailMessage(body, res.statusText || `HTTP ${res.status}`));
  }
  return body as T;
}

export async function getPatients(): Promise<Patient[]> {
  return request<Patient[]>('/api/patients');
}

export async function getPatient(patientId: string): Promise<Patient | null> {
  return getOrNull<Patient>(`/api/patients/${patientId}`);
}

export async function getConsultations(patientId?: string): Promise<Consultation[]> {
  const q = patientId ? `?patientId=${encodeURIComponent(patientId)}` : '';
  return request<Consultation[]>(`/api/consultations${q}`);
}

export async function getConsultation(consultationId: string): Promise<Consultation | null> {
  return getOrNull<Consultation>(`/api/consultations/${consultationId}`);
}

export async function getTranscript(transcriptId: string): Promise<Transcript | null> {
  return getOrNull<Transcript>(`/api/transcripts/${transcriptId}`);
}

export async function getSOAPNote(soapNoteId: string): Promise<SOAPNote | null> {
  return getOrNull<SOAPNote>(`/api/soap-notes/${soapNoteId}`);
}

export async function updateSOAPNote(
  soapNoteId: string,
  patch: Partial<Pick<SOAPNote, 'subjective' | 'objective' | 'assessment' | 'plan'>>
): Promise<SOAPNote> {
  return request<SOAPNote>(`/api/soap-notes/${soapNoteId}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

export async function validateConsultation(consultationId: string): Promise<ValidationResult> {
  return request<ValidationResult>(`/api/consultations/${consultationId}/validate`, { method: 'POST' });
}

export async function getValidation(validationId: string): Promise<ValidationResult | null> {
  return getOrNull<ValidationResult>(`/api/validations/${validationId}`);
}

export async function finalizeConsultation(
  consultationId: string,
  physicianId: string,
  physicianName: string
): Promise<{ consultation: Consultation; soapNote: SOAPNote }> {
  return request<{ consultation: Consultation; soapNote: SOAPNote }>(
    `/api/consultations/${consultationId}/finalize`,
    {
      method: 'POST',
      body: JSON.stringify({ physicianId, physicianName }),
    }
  );
}

export async function getAuditTrail(consultationId: string): Promise<AuditEntry[]> {
  return request<AuditEntry[]>(`/api/consultations/${consultationId}/audit`);
}

export async function ingestTeamB(consultationId: string, payload: TeamBApiResponse): Promise<{
  consultation: Consultation;
  soapNote: SOAPNote;
  validation: ValidationResult;
}> {
  return request(`/api/team-b/ingest/${encodeURIComponent(consultationId)}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function exportPDF(req: ExportRequest): Promise<ExportResult> {
  return request<ExportResult>('/api/exports/pdf', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function exportFHIR(req: ExportRequest): Promise<ExportResult> {
  return request<ExportResult>('/api/exports/fhir', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function sendToEHR(req: ExportRequest): Promise<{ success: boolean; confirmationId: string; message: string }> {
  return request<{ success: boolean; confirmationId: string; message: string }>('/api/exports/ehr', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}
