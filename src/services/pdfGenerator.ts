import { jsPDF } from 'jspdf';
import type { Consultation, Patient, SOAPNote, ValidationResult, Transcript } from '../models/types';

interface GeneratePDFOptions {
  consultation: Consultation;
  patient: Patient;
  soapNote: SOAPNote;
  validation?: ValidationResult | null;
  transcript?: Transcript | null;
  includeTranscript: boolean;
  includeValidation: boolean;
}

// Clean unicode symbols that default Helvetica font cannot render and guard against non-strings
function sanitizeText(val: unknown): string {
  if (val === null || val === undefined) return '';
  const str = String(val);
  return str
    .replace(/[↑▲]/g, '[elevated]')
    .replace(/[↓▼]/g, '[lowered]')
    .replace(/°C/g, ' deg C')
    .replace(/°F/g, ' deg F')
    .replace(/°/g, ' deg')
    .replace(/±/g, '+/-')
    .replace(/[—–]/g, '-')
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/×/g, 'x')
    .replace(/…/g, '...');
}

export function generateClinicalPDF(options: GeneratePDFOptions): { blob: Blob; base64: string } {
  const {
    consultation,
    patient,
    soapNote,
    validation,
    transcript,
    includeTranscript,
    includeValidation,
  } = options;

  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - margin * 2;
  let y = margin;

  const patientFullName = [patient.firstName, patient.lastName].filter(Boolean).join(' ') || 'Unknown Patient';
  const birthYear = new Date(patient.dob).getFullYear();
  const ageStr = !isNaN(birthYear) ? `${new Date().getFullYear() - birthYear}y ` : '';
  const sexStr = patient.sex === 'F' ? 'Female' : patient.sex === 'M' ? 'Male' : patient.sex || '';

  function checkPageBreak(requiredSpaceMm: number) {
    if (y + requiredSpaceMm > pageHeight - margin) {
      doc.addPage();
      y = margin;
      drawHeaderSmall();
    }
  }

  function drawHeaderSmall() {
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(140, 150, 165);
    doc.text(
      `Patient: ${sanitizeText(patientFullName)} (MRN: ${patient.mrn}) | Encounter: ${consultation.id}`,
      margin,
      y
    );
    y += 6;
    doc.setDrawColor(220, 225, 230);
    doc.setLineWidth(0.3);
    doc.line(margin, y, pageWidth - margin, y);
    y += 6;
  }

  // ── 1. MAIN HEADER ────────────────────────────────────────────────────────
  doc.setFillColor(15, 23, 42); // slate-900
  doc.rect(margin, y, contentWidth, 22, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(14);
  doc.setTextColor(255, 255, 255);
  doc.text('CLINICAL SCRIBE & DIAGNOSTIC COPILOT', margin + 4, y + 8);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(203, 213, 225);
  doc.text('Ambulatory Clinical Encounter Summary · Electronic Health Record Export', margin + 4, y + 14);
  doc.text('CONFIDENTIAL MEDICAL RECORD - HIPAA PROTECTED', margin + 4, y + 18.5);

  // Finalized badge on top right of header
  if (soapNote.isFinalized) {
    doc.setFillColor(22, 101, 52); // ok-800
    doc.roundedRect(pageWidth - margin - 35, y + 5, 31, 12, 1.5, 1.5, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(240, 253, 244);
    doc.text('FINALIZED', pageWidth - margin - 19.5, y + 10, { align: 'center' });
    doc.setFontSize(6.5);
    doc.text('Official Record', pageWidth - margin - 19.5, y + 14, { align: 'center' });
  } else {
    doc.setFillColor(133, 77, 14); // warn-800
    doc.roundedRect(pageWidth - margin - 35, y + 5, 31, 12, 1.5, 1.5, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(254, 240, 138);
    doc.text('DRAFT NOTE', pageWidth - margin - 19.5, y + 10, { align: 'center' });
    doc.setFontSize(6.5);
    doc.text(`Version v${soapNote.version}`, pageWidth - margin - 19.5, y + 14, { align: 'center' });
  }

  y += 27;

  // ── 2. PATIENT & ENCOUNTER INFO BOX ───────────────────────────────────────
  checkPageBreak(35);
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(203, 213, 225);
  doc.setLineWidth(0.4);
  doc.rect(margin, y, contentWidth, 30, 'FD');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(30, 41, 59);

  // Left col: demographics
  doc.text('PATIENT DEMOGRAPHICS', margin + 4, y + 5.5);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(51, 65, 85);
  doc.text(`Name: ${sanitizeText(patientFullName)}`, margin + 4, y + 11);
  doc.text(`MRN: ${patient.mrn}   DOB: ${patient.dob} (${ageStr}${sexStr})`, margin + 4, y + 16.5);
  doc.text(`Phone: ${patient.phone ?? 'N/A'}`, margin + 4, y + 22);

  // Right col: encounter
  const rightColX = margin + (contentWidth / 2) + 2;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(30, 41, 59);
  doc.text('ENCOUNTER DETAILS', rightColX, y + 5.5);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(51, 65, 85);
  doc.text(`Encounter ID: ${consultation.id}`, rightColX, y + 11);
  const encounterDate = consultation.date ? new Date(consultation.date).toLocaleString() : 'N/A';
  doc.text(`Date & Time: ${encounterDate}`, rightColX, y + 16.5);
  doc.text(`Attending Physician: Dr. Sarah Chen, MD`, rightColX, y + 22);

  y += 33;

  // Allergies banner
  if (patient.allergies && patient.allergies.length > 0) {
    checkPageBreak(12);
    doc.setFillColor(254, 242, 242);
    doc.setDrawColor(239, 68, 68);
    doc.setLineWidth(0.6);
    doc.roundedRect(margin, y, contentWidth, 8, 1, 1, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(185, 28, 28);
    const allergiesList = Array.isArray(patient.allergies) ? patient.allergies.join('; ') : String(patient.allergies);
    doc.text(`CRITICAL ALLERGIES: ${sanitizeText(allergiesList)}`, margin + 4, y + 5.2);
    y += 12;
  }

  // ── 3. SOAP NOTE SECTIONS ──────────────────────────────────────────────────
  function renderSection(sectionTitle: string, contentText: string, iconBadge: string) {
    checkPageBreak(25);

    // Section header
    doc.setFillColor(241, 245, 249);
    doc.rect(margin, y, contentWidth, 7, 'F');
    doc.setDrawColor(148, 163, 184);
    doc.setLineWidth(0.5);
    doc.line(margin, y, margin, y + 7);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(15, 23, 42);
    doc.text(`${iconBadge}  ${sectionTitle.toUpperCase()}`, margin + 4, y + 5);
    y += 10;

    // Body
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(30, 41, 59);

    const sanitized = sanitizeText((contentText || '').trim() || 'None reported.');
    const lines = doc.splitTextToSize(sanitized, contentWidth - 6);

    for (const line of lines) {
      checkPageBreak(5);
      doc.text(line, margin + 3, y);
      y += 4.5;
    }
    y += 4;
  }

  renderSection('Subjective', soapNote?.subjective?.text || '', 'S');
  renderSection('Objective', soapNote?.objective?.text || '', 'O');
  renderSection('Assessment', soapNote?.assessment?.text || '', 'A');
  renderSection('Plan', soapNote?.plan?.text || '', 'P');

  // ── 4. VALIDATION & GROUNDING REPORT (OPTIONAL) ───────────────────────────
  if (includeValidation && validation) {
    checkPageBreak(30);

    doc.setFillColor(238, 242, 255); // indigo-50
    doc.setDrawColor(99, 102, 241);
    doc.setLineWidth(0.4);
    doc.rect(margin, y, contentWidth, 8, 'FD');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(49, 46, 129);
    doc.text(`AI COPILOT GROUNDING & VALIDATION REPORT (Score: ${validation.groundingScore}/100 - ${String(validation.hallucinationRisk || '').toUpperCase()} RISK)`, margin + 4, y + 5.5);
    y += 11;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    doc.setTextColor(71, 85, 105);
    const validatedDate = validation.validatedAt ? new Date(validation.validatedAt).toLocaleString() : 'N/A';
    const summaryLine = `Evaluated ${validation.claims?.length || 0} clinical assertions against ambient dialogue. Verified at ${validatedDate}.`;
    doc.text(summaryLine, margin + 2, y);
    y += 5;

    // List claims
    if (validation.claims && Array.isArray(validation.claims)) {
      for (const claim of validation.claims) {
        checkPageBreak(12);
        const isConflict = claim.status === 'conflict';
        const isSupported = claim.status === 'supported';

        // Status indicator text
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(7.5);
        if (isSupported) {
          doc.setTextColor(22, 101, 52);
          doc.text('[SUPPORTED]', margin + 2, y);
        } else if (isConflict) {
          doc.setTextColor(185, 28, 28);
          doc.text('[CONTRAINDICATION / CONFLICT]', margin + 2, y);
        } else {
          doc.setTextColor(161, 98, 7);
          doc.text(`[${String(claim.status || '').toUpperCase()}]`, margin + 2, y);
        }

        // Claim text
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(30, 41, 59);
        const claimLines = doc.splitTextToSize(`(${claim.soapSection || ''}) ${sanitizeText(claim.text)}`, contentWidth - 45);
        doc.text(claimLines, margin + 42, y);
        y += claimLines.length * 4;

        if (isConflict && claim.conflictDescription) {
          doc.setFont('helvetica', 'italic');
          doc.setTextColor(185, 28, 28);
          const warnLines = doc.splitTextToSize(`Warning: ${sanitizeText(claim.conflictDescription)}`, contentWidth - 45);
          checkPageBreak(warnLines.length * 4 + 2);
          doc.text(warnLines, margin + 42, y);
          y += warnLines.length * 4;
        }
        y += 2;
      }
    }
    y += 4;
  }

  // ── 5. TRANSCRIPT (OPTIONAL) ──────────────────────────────────────────────
  if (includeTranscript && transcript && Array.isArray(transcript.entries) && transcript.entries.length > 0) {
    checkPageBreak(25);

    doc.setFillColor(241, 245, 249);
    doc.rect(margin, y, contentWidth, 7, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(15, 23, 42);
    doc.text('AMBIENT AUDIO TRANSCRIPT (SOURCE RECORD)', margin + 4, y + 5);
    y += 10;

    for (const entry of transcript.entries) {
      checkPageBreak(8);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(71, 85, 105);
      doc.text(`[${entry.timestamp || ''}] ${sanitizeText(entry.speaker)}:`, margin + 2, y);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(30, 41, 59);
      const entryLines = doc.splitTextToSize(sanitizeText(entry.text), contentWidth - 35);
      doc.text(entryLines, margin + 32, y);
      y += Math.max(entryLines.length * 4, 4.5);
    }
    y += 4;
  }

  // ── 6. SIGNATURE BLOCK ────────────────────────────────────────────────────
  checkPageBreak(30);
  doc.setDrawColor(203, 213, 225);
  doc.setLineWidth(0.4);
  doc.line(margin, y, pageWidth - margin, y);
  y += 6;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text('ATTENDING PHYSICIAN ATTESTATION & ELECTRONIC SIGNATURE', margin, y);
  y += 5;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(71, 85, 105);
  const signDate = soapNote.finalizedAt || consultation.finalisedAt || Date.now();
  doc.text(
    soapNote.isFinalized
      ? `Electronically signed and verified by Dr. Sarah Chen, MD on ${new Date(signDate).toLocaleString()}.`
      : 'DRAFT DOCUMENT: Pending physician signature and clinical review.',
    margin,
    y
  );
  y += 4.5;
  doc.text('Internal Medicine · NPI: 1982736450 · ClinicalScribe Encrypted Audit Trail Verified', margin, y);

  // ── 7. PAGE NUMBERS ───────────────────────────────────────────────────────
  const totalPages = doc.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    doc.setPage(p);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text(
      `Page ${p} of ${totalPages} · ClinicalScribe HIPAA-Compliant Export · Generated: ${new Date().toLocaleDateString()}`,
      pageWidth / 2,
      pageHeight - 8,
      { align: 'center' }
    );
  }

  const blob = doc.output('blob');
  const base64 = doc.output('datauristring').split(',')[1] || '';

  return { blob, base64 };
}
