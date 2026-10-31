import type {
  Patient, Consultation, Transcript, SOAPNote,
  ValidationResult, AuditEntry, TranscriptEntry, Claim, Evidence
} from '../models/types';

// ─── Patients ─────────────────────────────────────────────────────────────────

export const MOCK_PATIENTS: Patient[] = [
  {
    id: 'pt-001',
    mrn: 'MRN-20240001',
    firstName: 'Eleanor',
    lastName: 'Hartman',
    dob: '1958-03-14',
    sex: 'F',
    phone: '(617) 555-0182',
    allergies: [],
    conditions: ['Essential hypertension', 'Hyperlipidaemia'],
    medications: ['Lisinopril 10 mg daily', 'Atorvastatin 40 mg nightly'],
    lastVisit: '2026-09-14T09:00:00Z',
    consultationCount: 7,
    privacyLevel: 'standard',
  },
  {
    id: 'pt-002',
    mrn: 'MRN-20240002',
    firstName: 'Marcus',
    lastName: 'Okafor',
    dob: '1974-11-29',
    sex: 'M',
    phone: '(617) 555-0247',
    allergies: [],
    conditions: ['Type 2 diabetes mellitus', 'Obesity'],
    medications: ['Metformin 1000 mg BID', 'Empagliflozin 10 mg daily'],
    lastVisit: '2026-09-14T10:15:00Z',
    consultationCount: 4,
    privacyLevel: 'standard',
  },
  {
    id: 'pt-003',
    mrn: 'MRN-20240003',
    firstName: 'Priya',
    lastName: 'Nair',
    dob: '1989-07-07',
    sex: 'F',
    phone: '(617) 555-0318',
    allergies: ['Penicillin — anaphylaxis (documented 2019)'],
    conditions: ['Upper respiratory infection'],
    medications: [],
    lastVisit: '2026-09-14T11:30:00Z',
    consultationCount: 2,
    privacyLevel: 'standard',
  },
];

// ─── Consultations ────────────────────────────────────────────────────────────

export const MOCK_CONSULTATIONS: Consultation[] = [
  {
    id: 'con-001',
    patientId: 'pt-001',
    date: '2026-09-14T09:00:00Z',
    chiefComplaint: 'Hypertension follow-up',
    status: 'pending-review',
    physicianId: 'dr-001',
    physicianName: 'Dr. Sarah Chen',
    duration: 20,
    transcriptId: 'tx-001',
    soapNoteId: 'soap-001',
    validationId: 'val-001',
    createdAt: '2026-09-14T09:00:00Z',
    updatedAt: '2026-09-14T09:25:00Z',
     safetyStatus: 'CLEAR',
     },
  {
    id: 'con-002',
    patientId: 'pt-002',
    date: '2026-09-14T10:15:00Z',
    chiefComplaint: 'Type 2 DM management review',
    status: 'pending-review',
    physicianId: 'dr-001',
    physicianName: 'Dr. Sarah Chen',
    duration: 25,
    transcriptId: 'tx-002',
    soapNoteId: 'soap-002',
    validationId: 'val-002',
    createdAt: '2026-09-14T10:15:00Z',
    updatedAt: '2026-09-14T10:45:00Z',
    safetyStatus: 'CLEAR',
    },
  {
    id: 'con-003',
    patientId: 'pt-003',
    date: '2026-09-14T11:30:00Z',
    chiefComplaint: 'URI — sore throat, fever',
    status: 'pending-review',
    physicianId: 'dr-001',
    physicianName: 'Dr. Sarah Chen',
    duration: 15,
    transcriptId: 'tx-003',
    soapNoteId: 'soap-003',
    validationId: 'val-003',
    createdAt: '2026-09-14T11:30:00Z',
    updatedAt: '2026-09-14T11:50:00Z',
    safetyStatus: 'CLEAR',
    },
  {
    id: 'con-004',
    patientId: 'pt-001',
    date: '2026-07-10T09:00:00Z',
    chiefComplaint: 'Hypertension 3-month check',
    status: 'finalized',
    physicianId: 'dr-001',
    physicianName: 'Dr. Sarah Chen',
    duration: 18,
    transcriptId: 'tx-004',
    soapNoteId: 'soap-004',
    validationId: 'val-004',
    finalisedAt: '2026-07-10T09:40:00Z',
    createdAt: '2026-07-10T09:00:00Z',
    updatedAt: '2026-07-10T09:40:00Z',
    safetyStatus: 'CLEAR',
    },
];

// ─── Scenario A: Eleanor Hartman — Hypertension follow-up (HIGH GROUNDING) ──

const TX_ENTRIES_001: TranscriptEntry[] = [
  { id: 'te-001-1', consultationId: 'con-001', timestamp: '00:00:08', offsetMs: 8000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Good morning Eleanor, how have you been since our last visit?', confidence: 0.99 },
  { id: 'te-001-2', consultationId: 'con-001', timestamp: '00:00:15', offsetMs: 15000, speaker: 'Eleanor Hartman', speakerRole: 'patient', text: 'I\'ve been feeling pretty good overall, but I have noticed some occasional headaches, mostly in the mornings.', confidence: 0.97 },
  { id: 'te-001-3', consultationId: 'con-001', timestamp: '00:00:35', offsetMs: 35000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Morning headaches can sometimes be related to blood pressure. Are you still taking the Lisinopril every day?', confidence: 0.99 },
  { id: 'te-001-4', consultationId: 'con-001', timestamp: '00:00:50', offsetMs: 50000, speaker: 'Eleanor Hartman', speakerRole: 'patient', text: 'Yes, every morning without fail. And the Atorvastatin at night too.', confidence: 0.98 },
  { id: 'te-001-5', consultationId: 'con-001', timestamp: '00:01:05', offsetMs: 65000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Good. Let me check your blood pressure today. It\'s reading 148 over 92. That\'s a bit elevated compared to last time.', confidence: 0.99, linkedClaimIds: ['cl-001-3'] },
  { id: 'te-001-6', consultationId: 'con-001', timestamp: '00:01:30', offsetMs: 90000, speaker: 'Eleanor Hartman', speakerRole: 'patient', text: 'I\'ve been a bit stressed with work. Could that be causing it?', confidence: 0.97 },
  { id: 'te-001-7', consultationId: 'con-001', timestamp: '00:01:45', offsetMs: 105000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Stress definitely plays a role. I also want to check your weight today — you\'re at 68 kilograms, which is stable.', confidence: 0.99, linkedClaimIds: ['cl-001-4'] },
  { id: 'te-001-8', consultationId: 'con-001', timestamp: '00:02:10', offsetMs: 130000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'I\'m going to increase the Lisinopril to 20 milligrams daily to get better blood pressure control.', confidence: 0.99, linkedClaimIds: ['cl-001-5'] },
  { id: 'te-001-9', consultationId: 'con-001', timestamp: '00:02:30', offsetMs: 150000, speaker: 'Eleanor Hartman', speakerRole: 'patient', text: 'Will the higher dose have side effects?', confidence: 0.96 },
  { id: 'te-001-10', consultationId: 'con-001', timestamp: '00:02:40', offsetMs: 160000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Watch for a dry cough — that\'s the most common one. If it becomes bothersome we can switch. Also I\'d like you to get a basic metabolic panel before your next visit.', confidence: 0.99, linkedClaimIds: ['cl-001-6'] },
  { id: 'te-001-11', consultationId: 'con-001', timestamp: '00:03:15', offsetMs: 195000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'We\'ll schedule a follow-up in 6 weeks. In the meantime, please monitor your blood pressure at home daily.', confidence: 0.99, linkedClaimIds: ['cl-001-7'] },
  { id: 'te-001-12', consultationId: 'con-001', timestamp: '00:03:35', offsetMs: 215000, speaker: 'Eleanor Hartman', speakerRole: 'patient', text: 'I understand. Thank you, Doctor.', confidence: 0.99 },
];

export const MOCK_TRANSCRIPT_001: Transcript = {
  id: 'tx-001',
  consultationId: 'con-001',
  entries: TX_ENTRIES_001,
  recordedAt: '2026-09-14T09:00:08Z',
  durationMs: 225000,
  language: 'en-US',
};

export const MOCK_SOAP_001: SOAPNote = {
  id: 'soap-001',
  consultationId: 'con-001',
  subjective: {
    text: 'Patient reports occasional morning headaches since last visit. She denies dizziness, chest pain, or shortness of breath. Medication adherence confirmed — Lisinopril 10 mg daily and Atorvastatin 40 mg nightly. Patient attributes symptoms to increased work-related stress.',
    lastEditedAt: '2026-09-14T09:22:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  objective: {
    text: 'BP: 148/92 mmHg (elevated). Weight: 68 kg (stable). HR: 74 bpm, regular. Respiratory rate: 14/min. No peripheral oedema. Auscultation: clear lung fields bilaterally.',
    lastEditedAt: '2026-09-14T09:22:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  assessment: {
    text: 'Essential hypertension — suboptimally controlled. Likely exacerbated by psychosocial stressors. Hyperlipidaemia — stable on current therapy.',
    lastEditedAt: '2026-09-14T09:22:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  plan: {
    text: '1. Increase Lisinopril to 20 mg daily for improved BP control.\n2. Monitor for ACE inhibitor-related dry cough; switch to ARB if symptomatic.\n3. Order basic metabolic panel (BMP) — check renal function and electrolytes prior to next visit.\n4. Home BP monitoring daily — log and bring to follow-up.\n5. Follow-up appointment in 6 weeks.\n6. Counsel patient on stress management and lifestyle modification.',
    lastEditedAt: '2026-09-14T09:22:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  createdAt: '2026-09-14T09:22:00Z',
  updatedAt: '2026-09-14T09:22:00Z',
  isFinalized: false,
  version: 1,
};

const EVIDENCE_001: Evidence[] = [
  { id: 'ev-001-1', transcriptEntryId: 'te-001-2', transcriptText: 'I\'ve been feeling pretty good overall, but I have noticed some occasional headaches, mostly in the mornings.', speaker: 'Eleanor Hartman', timestamp: '00:00:15', relevanceScore: 0.98, matchType: 'exact' },
  { id: 'ev-001-2', transcriptEntryId: 'te-001-4', transcriptText: 'Yes, every morning without fail. And the Atorvastatin at night too.', speaker: 'Eleanor Hartman', timestamp: '00:00:50', relevanceScore: 0.97, matchType: 'exact' },
  { id: 'ev-001-3', transcriptEntryId: 'te-001-5', transcriptText: 'It\'s reading 148 over 92. That\'s a bit elevated compared to last time.', speaker: 'Dr. Chen', timestamp: '00:01:05', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-001-4', transcriptEntryId: 'te-001-7', transcriptText: 'you\'re at 68 kilograms, which is stable', speaker: 'Dr. Chen', timestamp: '00:01:45', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-001-5', transcriptEntryId: 'te-001-8', transcriptText: 'I\'m going to increase the Lisinopril to 20 milligrams daily to get better blood pressure control.', speaker: 'Dr. Chen', timestamp: '00:02:10', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-001-6', transcriptEntryId: 'te-001-10', transcriptText: 'Watch for a dry cough — that\'s the most common one. Also I\'d like you to get a basic metabolic panel before your next visit.', speaker: 'Dr. Chen', timestamp: '00:02:40', relevanceScore: 0.99, matchType: 'exact' },
  { id: 'ev-001-7', transcriptEntryId: 'te-001-11', transcriptText: 'We\'ll schedule a follow-up in 6 weeks. In the meantime, please monitor your blood pressure at home daily.', speaker: 'Dr. Chen', timestamp: '00:03:15', relevanceScore: 1.0, matchType: 'exact' },
];

const CLAIMS_001: Claim[] = [
  { id: 'cl-001-1', soapSection: 'subjective', text: 'Patient reports occasional morning headaches since last visit.', status: 'supported', severity: 'low', evidenceIds: ['ev-001-1'] },
  { id: 'cl-001-2', soapSection: 'subjective', text: 'Medication adherence confirmed — Lisinopril 10 mg daily and Atorvastatin 40 mg nightly.', status: 'supported', severity: 'low', evidenceIds: ['ev-001-2'] },
  { id: 'cl-001-3', soapSection: 'objective', text: 'BP: 148/92 mmHg (elevated).', status: 'supported', severity: 'medium', evidenceIds: ['ev-001-3'] },
  { id: 'cl-001-4', soapSection: 'objective', text: 'Weight: 68 kg (stable).', status: 'supported', severity: 'low', evidenceIds: ['ev-001-4'] },
  { id: 'cl-001-5', soapSection: 'plan', text: 'Increase Lisinopril to 20 mg daily for improved BP control.', status: 'supported', severity: 'medium', evidenceIds: ['ev-001-5'] },
  { id: 'cl-001-6', soapSection: 'plan', text: 'Order basic metabolic panel (BMP).', status: 'supported', severity: 'low', evidenceIds: ['ev-001-6'] },
  { id: 'cl-001-7', soapSection: 'plan', text: 'Follow-up appointment in 6 weeks.', status: 'supported', severity: 'low', evidenceIds: ['ev-001-7'] },
];

export const MOCK_VALIDATION_001: ValidationResult = {
  id: 'val-001',
  consultationId: 'con-001',
  soapNoteVersion: 1,
  claims: CLAIMS_001,
  evidence: EVIDENCE_001,
  groundingScore: 100,
  hallucinationRisk: 'low',
  supportedCount: 7,
  unsupportedCount: 0,
  conflictCount: 0,
  totalClaimCount: 7,
  isStale: false,
  validatedAt: '2026-09-14T09:23:00Z',
};

// ─── Scenario B: Marcus Okafor — DM review (UNSUPPORTED CLAIM) ─────────────

const TX_ENTRIES_002: TranscriptEntry[] = [
  { id: 'te-002-1', consultationId: 'con-002', timestamp: '00:00:10', offsetMs: 10000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Morning Marcus. Let\'s review your diabetes management today. How has your blood sugar been at home?', confidence: 0.99 },
  { id: 'te-002-2', consultationId: 'con-002', timestamp: '00:00:22', offsetMs: 22000, speaker: 'Marcus Okafor', speakerRole: 'patient', text: 'Honestly not great. My fasting levels have been around 180 to 200 most days. I\'ve been eating better but it\'s been stressful.', confidence: 0.96 },
  { id: 'te-002-3', consultationId: 'con-002', timestamp: '00:00:50', offsetMs: 50000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Those numbers are higher than we\'d like. Are you taking the Metformin and Empagliflozin as prescribed?', confidence: 0.99 },
  { id: 'te-002-4', consultationId: 'con-002', timestamp: '00:01:02', offsetMs: 62000, speaker: 'Marcus Okafor', speakerRole: 'patient', text: 'Yes, I take both pills. Metformin twice a day and the other one in the morning.', confidence: 0.97 },
  { id: 'te-002-5', consultationId: 'con-002', timestamp: '00:01:20', offsetMs: 80000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Good. Your weight today is 104 kilograms. That\'s up 2 kilos from last time. Have you been getting regular exercise?', confidence: 0.99, linkedClaimIds: ['cl-002-3'] },
  { id: 'te-002-6', consultationId: 'con-002', timestamp: '00:01:38', offsetMs: 98000, speaker: 'Marcus Okafor', speakerRole: 'patient', text: 'I walk about 20 minutes a day, maybe 4 or 5 times a week.', confidence: 0.97 },
  { id: 'te-002-7', consultationId: 'con-002', timestamp: '00:02:00', offsetMs: 120000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'That\'s a good start. I\'d like to increase that to 30 minutes daily if possible. I\'m going to refer you to the diabetes educator as well.', confidence: 0.99, linkedClaimIds: ['cl-002-5'] },
  { id: 'te-002-8', consultationId: 'con-002', timestamp: '00:02:25', offsetMs: 145000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'We need labs — fasting glucose and a repeat HbA1c. I\'d like to see you back in 8 weeks to review the results.', confidence: 0.99, linkedClaimIds: ['cl-002-6'] },
  { id: 'te-002-9', consultationId: 'con-002', timestamp: '00:02:50', offsetMs: 170000, speaker: 'Marcus Okafor', speakerRole: 'patient', text: 'Okay, I\'ll try to get the blood work done this week.', confidence: 0.97 },
  { id: 'te-002-10', consultationId: 'con-002', timestamp: '00:03:05', offsetMs: 185000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Perfect. Continue current medications for now.', confidence: 0.99 },
];

export const MOCK_TRANSCRIPT_002: Transcript = {
  id: 'tx-002',
  consultationId: 'con-002',
  entries: TX_ENTRIES_002,
  recordedAt: '2026-09-14T10:15:10Z',
  durationMs: 195000,
  language: 'en-US',
};

export const MOCK_SOAP_002: SOAPNote = {
  id: 'soap-002',
  consultationId: 'con-002',
  subjective: {
    text: 'Patient reports fasting blood glucose readings of 180–200 mg/dL at home. Increased work-related stress identified as contributor. Medication adherence confirmed — Metformin 1000 mg BID and Empagliflozin 10 mg daily. Patient exercising approximately 20 minutes, 4–5 days/week.',
    lastEditedAt: '2026-09-14T10:42:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  objective: {
    text: 'Weight: 104 kg (↑2 kg from last visit). BP: 122/78 mmHg. HR: 80 bpm. BMI: 33.2 kg/m². Last HbA1c result: 9.2% (three months ago — indicates poor glycaemic control).',
    lastEditedAt: '2026-09-14T10:42:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  assessment: {
    text: 'Type 2 diabetes mellitus — suboptimally controlled (HbA1c 9.2%). Obesity — BMI 33.2, weight trending up. Poor glycaemic control likely multifactorial: dietary, psychosocial, and activity-related.',
    lastEditedAt: '2026-09-14T10:42:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  plan: {
    text: '1. Continue Metformin 1000 mg BID and Empagliflozin 10 mg daily.\n2. Increase physical activity to 30 minutes daily aerobic exercise.\n3. Refer to certified diabetes educator for nutrition and lifestyle counselling.\n4. Order fasting glucose and repeat HbA1c labs.\n5. Follow-up in 8 weeks to review lab results and reassess glycaemic control.',
    lastEditedAt: '2026-09-14T10:42:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  createdAt: '2026-09-14T10:42:00Z',
  updatedAt: '2026-09-14T10:42:00Z',
  isFinalized: false,
  version: 1,
};

const EVIDENCE_002: Evidence[] = [
  { id: 'ev-002-1', transcriptEntryId: 'te-002-2', transcriptText: 'My fasting levels have been around 180 to 200 most days.', speaker: 'Marcus Okafor', timestamp: '00:00:22', relevanceScore: 0.99, matchType: 'exact' },
  { id: 'ev-002-2', transcriptEntryId: 'te-002-4', transcriptText: 'Yes, I take both pills. Metformin twice a day and the other one in the morning.', speaker: 'Marcus Okafor', timestamp: '00:01:02', relevanceScore: 0.97, matchType: 'semantic' },
  { id: 'ev-002-3', transcriptEntryId: 'te-002-5', transcriptText: 'Your weight today is 104 kilograms. That\'s up 2 kilos from last time.', speaker: 'Dr. Chen', timestamp: '00:01:20', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-002-4', transcriptEntryId: 'te-002-6', transcriptText: 'I walk about 20 minutes a day, maybe 4 or 5 times a week.', speaker: 'Marcus Okafor', timestamp: '00:01:38', relevanceScore: 0.98, matchType: 'exact' },
  { id: 'ev-002-5', transcriptEntryId: 'te-002-7', transcriptText: 'I\'d like to increase that to 30 minutes daily if possible. I\'m going to refer you to the diabetes educator as well.', speaker: 'Dr. Chen', timestamp: '00:02:00', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-002-6', transcriptEntryId: 'te-002-8', transcriptText: 'We need labs — fasting glucose and a repeat HbA1c. I\'d like to see you back in 8 weeks to review the results.', speaker: 'Dr. Chen', timestamp: '00:02:25', relevanceScore: 1.0, matchType: 'exact' },
];

const CLAIMS_002: Claim[] = [
  { id: 'cl-002-1', soapSection: 'subjective', text: 'Patient reports fasting blood glucose readings of 180–200 mg/dL at home.', status: 'supported', severity: 'low', evidenceIds: ['ev-002-1'] },
  { id: 'cl-002-2', soapSection: 'subjective', text: 'Medication adherence confirmed — Metformin 1000 mg BID and Empagliflozin 10 mg daily.', status: 'supported', severity: 'low', evidenceIds: ['ev-002-2'] },
  { id: 'cl-002-3', soapSection: 'objective', text: 'Weight: 104 kg (↑2 kg from last visit).', status: 'supported', severity: 'low', evidenceIds: ['ev-002-3'] },
  {
    id: 'cl-002-4',
    soapSection: 'objective',
    text: 'Last HbA1c result: 9.2% (three months ago — indicates poor glycaemic control).',
    status: 'unsupported',
    severity: 'high',
    evidenceIds: [],
    suggestedCorrection: 'HbA1c value of 9.2% was not mentioned in the consultation transcript. This value may come from prior records — cite source explicitly or remove if uncertain.',
  },
  { id: 'cl-002-5', soapSection: 'plan', text: 'Increase physical activity to 30 minutes daily aerobic exercise.', status: 'supported', severity: 'low', evidenceIds: ['ev-002-5'] },
  { id: 'cl-002-6', soapSection: 'plan', text: 'Order fasting glucose and repeat HbA1c labs; follow-up in 8 weeks.', status: 'supported', severity: 'low', evidenceIds: ['ev-002-6'] },
  { id: 'cl-002-7', soapSection: 'plan', text: 'Refer to certified diabetes educator for nutrition and lifestyle counselling.', status: 'supported', severity: 'low', evidenceIds: ['ev-002-5'] },
];

export const MOCK_VALIDATION_002: ValidationResult = {
  id: 'val-002',
  consultationId: 'con-002',
  soapNoteVersion: 1,
  claims: CLAIMS_002,
  evidence: EVIDENCE_002,
  groundingScore: Math.round((6 / 7) * 100),
  hallucinationRisk: 'moderate',
  supportedCount: 6,
  unsupportedCount: 1,
  conflictCount: 0,
  totalClaimCount: 7,
  isStale: false,
  validatedAt: '2026-09-14T10:43:00Z',
};

// ─── Scenario C: Priya Nair — URI + Penicillin/Amoxicillin conflict ────────

const TX_ENTRIES_003: TranscriptEntry[] = [
  { id: 'te-003-1', consultationId: 'con-003', timestamp: '00:00:08', offsetMs: 8000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Hi Priya. What brings you in today?', confidence: 0.99 },
  { id: 'te-003-2', consultationId: 'con-003', timestamp: '00:00:14', offsetMs: 14000, speaker: 'Priya Nair', speakerRole: 'patient', text: 'I\'ve had a really bad sore throat and a fever for the past three days. I feel exhausted and my neck glands are swollen.', confidence: 0.97 },
  { id: 'te-003-3', consultationId: 'con-003', timestamp: '00:00:35', offsetMs: 35000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Any cough or runny nose? Headache?', confidence: 0.99 },
  { id: 'te-003-4', consultationId: 'con-003', timestamp: '00:00:42', offsetMs: 42000, speaker: 'Priya Nair', speakerRole: 'patient', text: 'A little bit of a headache, but no cough. Some nasal congestion yesterday.', confidence: 0.96 },
  { id: 'te-003-5', consultationId: 'con-003', timestamp: '00:01:00', offsetMs: 60000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Let me have a look at your throat. Your temperature is 38.6 degrees Celsius. Your throat looks quite inflamed — I can see tonsillar exudate. Lymph nodes are palpably enlarged bilaterally.', confidence: 0.99, linkedClaimIds: ['cl-003-2'] },
  { id: 'te-003-6', consultationId: 'con-003', timestamp: '00:01:40', offsetMs: 100000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'I\'m going to do a rapid strep test right now.', confidence: 0.99 },
  { id: 'te-003-7', consultationId: 'con-003', timestamp: '00:03:15', offsetMs: 195000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'The strep test is positive. This looks like streptococcal pharyngitis — strep throat.', confidence: 0.99, linkedClaimIds: ['cl-003-4'] },
  { id: 'te-003-8', consultationId: 'con-003', timestamp: '00:03:35', offsetMs: 215000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'I\'ll prescribe amoxicillin 500 milligrams three times a day for 10 days.', confidence: 0.99, linkedClaimIds: ['cl-003-5'] },
  { id: 'te-003-9', consultationId: 'con-003', timestamp: '00:03:52', offsetMs: 232000, speaker: 'Priya Nair', speakerRole: 'patient', text: 'Is that okay? I feel like I had a reaction to a similar antibiotic once.', confidence: 0.93 },
  { id: 'te-003-10', consultationId: 'con-003', timestamp: '00:04:05', offsetMs: 245000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'That\'s important to note. Can you remember which antibiotic it was?', confidence: 0.99 },
  { id: 'te-003-11', consultationId: 'con-003', timestamp: '00:04:15', offsetMs: 255000, speaker: 'Priya Nair', speakerRole: 'patient', text: 'I think it started with a P... penicillin maybe? I had trouble breathing. It was documented somewhere.', confidence: 0.92 },
  { id: 'te-003-12', consultationId: 'con-003', timestamp: '00:04:30', offsetMs: 270000, speaker: 'Dr. Chen', speakerRole: 'physician', text: 'Rest, fluids, ibuprofen or paracetamol for fever. Return if symptoms worsen.', confidence: 0.99, linkedClaimIds: ['cl-003-6'] },
];

export const MOCK_TRANSCRIPT_003: Transcript = {
  id: 'tx-003',
  consultationId: 'con-003',
  entries: TX_ENTRIES_003,
  recordedAt: '2026-09-14T11:30:08Z',
  durationMs: 285000,
  language: 'en-US',
};

export const MOCK_SOAP_003: SOAPNote = {
  id: 'soap-003',
  consultationId: 'con-003',
  subjective: {
    text: 'Patient presents with 3-day history of severe sore throat, fever, fatigue, and bilateral cervical lymphadenopathy. Reports mild headache and nasal congestion. No significant cough.',
    lastEditedAt: '2026-09-14T11:48:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  objective: {
    text: 'Temperature: 38.6°C. Throat: markedly erythematous with tonsillar exudate bilaterally. Lymph nodes: bilateral cervical lymphadenopathy palpable. Rapid strep antigen test: POSITIVE.',
    lastEditedAt: '2026-09-14T11:48:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  assessment: {
    text: 'Streptococcal pharyngitis (Group A Streptococcus). Acute bacterial tonsillitis.',
    lastEditedAt: '2026-09-14T11:48:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  plan: {
    text: '1. Prescribe Amoxicillin 500 mg TID × 10 days.\n2. Rest and adequate hydration.\n3. Ibuprofen 400 mg PRN or Paracetamol 500 mg PRN for fever and pain.\n4. Return if symptoms worsen or fail to improve within 48–72 hours.',
    lastEditedAt: '2026-09-14T11:48:00Z',
    lastEditedBy: 'Dr. Sarah Chen',
  },
  createdAt: '2026-09-14T11:48:00Z',
  updatedAt: '2026-09-14T11:48:00Z',
  isFinalized: false,
  version: 1,
};

const EVIDENCE_003: Evidence[] = [
  { id: 'ev-003-1', transcriptEntryId: 'te-003-2', transcriptText: 'I\'ve had a really bad sore throat and a fever for the past three days. I feel exhausted and my neck glands are swollen.', speaker: 'Priya Nair', timestamp: '00:00:14', relevanceScore: 0.99, matchType: 'exact' },
  { id: 'ev-003-2', transcriptEntryId: 'te-003-5', transcriptText: 'Your temperature is 38.6 degrees Celsius. Your throat looks quite inflamed — I can see tonsillar exudate. Lymph nodes are palpably enlarged bilaterally.', speaker: 'Dr. Chen', timestamp: '00:01:00', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-003-3', transcriptEntryId: 'te-003-7', transcriptText: 'The strep test is positive. This looks like streptococcal pharyngitis — strep throat.', speaker: 'Dr. Chen', timestamp: '00:03:15', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-003-4', transcriptEntryId: 'te-003-8', transcriptText: 'I\'ll prescribe amoxicillin 500 milligrams three times a day for 10 days.', speaker: 'Dr. Chen', timestamp: '00:03:35', relevanceScore: 1.0, matchType: 'exact' },
  { id: 'ev-003-5', transcriptEntryId: 'te-003-12', transcriptText: 'Rest, fluids, ibuprofen or paracetamol for fever. Return if symptoms worsen.', speaker: 'Dr. Chen', timestamp: '00:04:30', relevanceScore: 0.99, matchType: 'exact' },
];

const CLAIMS_003: Claim[] = [
  { id: 'cl-003-1', soapSection: 'subjective', text: 'Patient presents with 3-day history of severe sore throat, fever, fatigue, and bilateral cervical lymphadenopathy.', status: 'supported', severity: 'low', evidenceIds: ['ev-003-1'] },
  { id: 'cl-003-2', soapSection: 'objective', text: 'Temperature: 38.6°C. Throat: markedly erythematous with tonsillar exudate bilaterally.', status: 'supported', severity: 'low', evidenceIds: ['ev-003-2'] },
  { id: 'cl-003-3', soapSection: 'objective', text: 'Bilateral cervical lymphadenopathy palpable.', status: 'supported', severity: 'low', evidenceIds: ['ev-003-2'] },
  { id: 'cl-003-4', soapSection: 'objective', text: 'Rapid strep antigen test: POSITIVE.', status: 'supported', severity: 'medium', evidenceIds: ['ev-003-3'] },
  {
    id: 'cl-003-5',
    soapSection: 'plan',
    text: 'Prescribe Amoxicillin 500 mg TID × 10 days.',
    status: 'conflict',
    severity: 'critical',
    evidenceIds: ['ev-003-4'],
    conflictDescription: 'Patient record documents PENICILLIN ALLERGY (anaphylaxis, 2019). Amoxicillin is a penicillin-class antibiotic and is CONTRAINDICATED. Patient also mentioned a possible penicillin reaction during the consultation (00:04:15).',
    conflictingEntities: ['Penicillin allergy', 'Amoxicillin'],
    suggestedCorrection: 'Consider azithromycin 500 mg day 1 then 250 mg days 2–5 (macrolide) or clindamycin as alternatives for penicillin-allergic patients with strep pharyngitis.',
  },
  { id: 'cl-003-6', soapSection: 'plan', text: 'Rest, adequate hydration, Ibuprofen PRN or Paracetamol PRN for fever and pain.', status: 'supported', severity: 'low', evidenceIds: ['ev-003-5'] },
];

export const MOCK_VALIDATION_003: ValidationResult = {
  id: 'val-003',
  consultationId: 'con-003',
  soapNoteVersion: 1,
  claims: CLAIMS_003,
  evidence: EVIDENCE_003,
  groundingScore: Math.round((5 / 6) * 100),
  hallucinationRisk: 'moderate',
  supportedCount: 5,
  unsupportedCount: 0,
  conflictCount: 1,
  totalClaimCount: 6,
  isStale: false,
  validatedAt: '2026-09-14T11:49:00Z',
};

// ─── Audit Trails ─────────────────────────────────────────────────────────────

export const MOCK_AUDITS: AuditEntry[] = [
  { id: 'au-001', consultationId: 'con-001', timestamp: '2026-09-14T09:22:00Z', action: 'created', actor: 'System (AI Scribe)', detail: 'SOAP note v1 generated from transcript tx-001.', soapVersion: 1 },
  { id: 'au-002', consultationId: 'con-001', timestamp: '2026-09-14T09:23:00Z', action: 'validated', actor: 'System', detail: 'Initial validation complete. Grounding Score: 100/100. Risk: Low.', soapVersion: 1 },
  { id: 'au-003', consultationId: 'con-002', timestamp: '2026-09-14T10:42:00Z', action: 'created', actor: 'System (AI Scribe)', detail: 'SOAP note v1 generated from transcript tx-002.', soapVersion: 1 },
  { id: 'au-004', consultationId: 'con-002', timestamp: '2026-09-14T10:43:00Z', action: 'validated', actor: 'System', detail: 'Initial validation complete. Grounding Score: 86/100. 1 unsupported claim detected. Risk: Moderate.', soapVersion: 1 },
  { id: 'au-005', consultationId: 'con-003', timestamp: '2026-09-14T11:48:00Z', action: 'created', actor: 'System (AI Scribe)', detail: 'SOAP note v1 generated from transcript tx-003.', soapVersion: 1 },
  { id: 'au-006', consultationId: 'con-003', timestamp: '2026-09-14T11:49:00Z', action: 'validated', actor: 'System', detail: 'Initial validation complete. Grounding Score: 83/100. 1 CRITICAL conflict detected: Penicillin allergy + Amoxicillin. Risk: Moderate.', soapVersion: 1 },
];

// ─── Finalized consultation (history) ────────────────────────────────────────

export const MOCK_SOAP_004: SOAPNote = {
  id: 'soap-004',
  consultationId: 'con-004',
  subjective: { text: 'Patient reports good blood pressure control at home with home monitor readings averaging 130/80. Tolerating Lisinopril well. No side effects.', lastEditedBy: 'Dr. Sarah Chen', lastEditedAt: '2026-07-10T09:35:00Z' },
  objective: { text: 'BP: 132/84 mmHg. Weight: 67 kg. HR: 72 bpm.', lastEditedBy: 'Dr. Sarah Chen', lastEditedAt: '2026-07-10T09:35:00Z' },
  assessment: { text: 'Essential hypertension — well controlled on current regimen.', lastEditedBy: 'Dr. Sarah Chen', lastEditedAt: '2026-07-10T09:35:00Z' },
  plan: { text: '1. Continue Lisinopril 10 mg daily.\n2. Follow-up in 3 months.\n3. Repeat lipid panel in 6 months.', lastEditedBy: 'Dr. Sarah Chen', lastEditedAt: '2026-07-10T09:35:00Z' },
  createdAt: '2026-07-10T09:35:00Z',
  updatedAt: '2026-07-10T09:40:00Z',
  isFinalized: true,
  finalizedAt: '2026-07-10T09:40:00Z',
  finalizedBy: 'Dr. Sarah Chen',
  version: 1,
};

export const MOCK_VALIDATION_004: ValidationResult = {
  id: 'val-004',
  consultationId: 'con-004',
  soapNoteVersion: 1,
  claims: [],
  evidence: [],
  groundingScore: 100,
  hallucinationRisk: 'low',
  supportedCount: 4,
  unsupportedCount: 0,
  conflictCount: 0,
  totalClaimCount: 4,
  isStale: false,
  validatedAt: '2026-07-10T09:38:00Z',
};

// ─── Lookup maps ──────────────────────────────────────────────────────────────

export const TRANSCRIPTS: Record<string, Transcript> = {
  'tx-001': MOCK_TRANSCRIPT_001,
  'tx-002': MOCK_TRANSCRIPT_002,
  'tx-003': MOCK_TRANSCRIPT_003,
};

export const SOAP_NOTES: Record<string, SOAPNote> = {
  'soap-001': MOCK_SOAP_001,
  'soap-002': MOCK_SOAP_002,
  'soap-003': MOCK_SOAP_003,
  'soap-004': MOCK_SOAP_004,
};

export const VALIDATIONS: Record<string, ValidationResult> = {
  'val-001': MOCK_VALIDATION_001,
  'val-002': MOCK_VALIDATION_002,
  'val-003': MOCK_VALIDATION_003,
  'val-004': MOCK_VALIDATION_004,
};

export const MOCK_TEAM_B_RESPONSE = {
  patient_info: { demographics: {}, allergies: ['Penicillin'], medications: [] },
  soap_note: {
    subjective: 'Sore throat and fever for 3 days.',
    objective: 'Temperature: 101.2°F. Throat inflammation.',
    assessment: 'Likely streptococcal pharyngitis.',
    plan: 'Prescription requires safety review.',
  },
  conflicts: [{
    type: 'MEDICATION_ALLERGY',
    allergy: 'Penicillin',
    medication: 'Amoxicillin',
    severity: 'HIGH',
    status: 'BLOCKED',
    message: 'Medication conflicts with documented allergy.',
  }],
  safety_status: 'CONFLICT_DETECTED',
} as const;
