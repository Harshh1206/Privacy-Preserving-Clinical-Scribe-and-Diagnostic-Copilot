// ─── Core typed models for Team C ───────────────────────────────────────────

export type PatientSex = 'M' | 'F' | 'O';
export type ConsultationStatus = 'scheduled' | 'in-progress' | 'pending-review' | 'finalized' | 'cancelled';
export type ClaimStatus = 'supported' | 'unsupported' | 'conflict' | 'pending';
export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type HallucinationRisk = 'low' | 'moderate' | 'high';
export type ExportFormat = 'pdf' | 'fhir' | 'ehr';

// ─── Patient ─────────────────────────────────────────────────────────────────

export interface Patient {
  id: string;
  mrn: string;           // Medical Record Number
  firstName: string;
  lastName: string;
  dob: string;           // ISO date
  sex: PatientSex;
  phone?: string;
  allergies: string[];   // Known allergies (critical for conflict detection)
  conditions: string[];  // Active conditions
  medications: string[]; // Current medications
  lastVisit?: string;    // ISO date
  consultationCount: number;
  privacyLevel: 'standard' | 'sensitive' | 'restricted';
}

// ─── Consultation ─────────────────────────────────────────────────────────────

export interface Consultation {
  id: string;
  patientId: string;
  date: string;          // ISO datetime
  chiefComplaint: string;
  status: ConsultationStatus;
  physicianId: string;
  physicianName: string;
  duration?: number;     // minutes
  transcriptId: string;
  soapNoteId: string;
  validationId?: string;
  finalisedAt?: string;  // ISO datetime
  createdAt: string;
  updatedAt: string;
}

// ─── Transcript ───────────────────────────────────────────────────────────────

export type SpeakerRole = 'physician' | 'patient' | 'nurse' | 'system';

export interface TranscriptEntry {
  id: string;
  consultationId: string;
  timestamp: string;     // "00:01:23" or ISO offset
  offsetMs: number;      // milliseconds from start
  speaker: string;       // Display name
  speakerRole: SpeakerRole;
  text: string;
  linkedClaimIds?: string[]; // Claims that reference this entry
  confidence?: number;   // 0-1 ASR confidence (Team A)
}

export interface Transcript {
  id: string;
  consultationId: string;
  entries: TranscriptEntry[];
  recordedAt: string;
  durationMs: number;
  language: string;
}

// ─── SOAP Note ────────────────────────────────────────────────────────────────

export interface SOAPSection {
  text: string;
  lastEditedAt?: string;
  lastEditedBy?: string;
}

export interface SOAPNote {
  id: string;
  consultationId: string;
  subjective: SOAPSection;
  objective: SOAPSection;
  assessment: SOAPSection;
  plan: SOAPSection;
  createdAt: string;
  updatedAt: string;
  isFinalized: boolean;
  finalizedAt?: string;
  finalizedBy?: string;
  version: number;
}

// ─── Medical Entity ───────────────────────────────────────────────────────────

export interface MedicalEntity {
  id: string;
  text: string;
  type: 'symptom' | 'diagnosis' | 'medication' | 'procedure' | 'lab' | 'allergy' | 'vital';
  normalizedTerm?: string;
  icdCode?: string;
  rxNormCode?: string;
}

// ─── Evidence ─────────────────────────────────────────────────────────────────

export interface Evidence {
  id: string;
  transcriptEntryId: string;
  transcriptText: string;        // Exact quote from transcript
  speaker: string;
  timestamp: string;
  relevanceScore: number;        // 0-1
  matchType: 'exact' | 'semantic' | 'inferred';
}

// ─── Claim ────────────────────────────────────────────────────────────────────

export interface Claim {
  id: string;
  soapSection: 'subjective' | 'objective' | 'assessment' | 'plan';
  text: string;                  // The specific claim from SOAP
  status: ClaimStatus;
  severity: Severity;
  evidenceIds: string[];
  conflictDescription?: string;  // For conflict claims
  conflictingEntities?: string[];
  suggestedCorrection?: string;
}

// ─── Validation Result ────────────────────────────────────────────────────────

export interface ValidationResult {
  id: string;
  consultationId: string;
  soapNoteVersion: number;
  claims: Claim[];
  evidence: Evidence[];
  groundingScore: number;         // 0-100, = supported/total * 100
  hallucinationRisk: HallucinationRisk;
  supportedCount: number;
  unsupportedCount: number;
  conflictCount: number;
  totalClaimCount: number;
  isStale: boolean;               // true when SOAP edited after validation
  validatedAt: string;
  validationNotes?: string;
}

export interface GroundingResult {
  score: number;                 // 0-100
  hallucinationRisk: HallucinationRisk;
  label: string;                 // "95 / 100"
  interpretation: string;        // "High evidence grounding…"
}

// ─── Audit Trail ─────────────────────────────────────────────────────────────

export interface AuditEntry {
  id: string;
  consultationId: string;
  timestamp: string;
  action: 'created' | 'edited' | 'validated' | 'revalidated' | 'finalized' | 'exported' | 'sent_to_ehr';
  actor: string;
  detail: string;
  soapVersion?: number;
}

// ─── Export ───────────────────────────────────────────────────────────────────

export interface ExportRequest {
  consultationId: string;
  format: ExportFormat;
  includeTranscript: boolean;
  includeValidation: boolean;
}

export interface ExportResult {
  format: ExportFormat;
  filename: string;
  content: string;    // Base64 for PDF, JSON string for FHIR/EHR
  generatedAt: string;
}

// ─── UI State helpers ─────────────────────────────────────────────────────────

export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
