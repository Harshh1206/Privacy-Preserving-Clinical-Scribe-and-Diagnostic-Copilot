import type { ClinicalRecord, Patient } from '../models/types';
import type { ReactNode } from 'react';

interface PatientClinicalSummaryProps {
  patient: Patient;
  consultationId: string;
}

interface SummaryItem {
  id: string;
  name: string;
  details: string[];
  source: string;
}

interface LegacyClinicalLabel {
  name: string;
  status?: string;
  verification?: string;
  reaction?: string;
}

const EMPTY_VALUE = 'Not documented';

function IconAllergy() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3 2.8 19a1.4 1.4 0 0 0 1.2 2.1h16a1.4 1.4 0 0 0 1.2-2.1L12 3Z"/>
      <path d="M12 9v4"/>
      <path d="M12 17h.01"/>
    </svg>
  );
}

function IconCondition() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v18M3 12h18"/>
      <circle cx="12" cy="12" r="9"/>
    </svg>
  );
}

function IconMedication() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m10.5 3.5 10 10a4.24 4.24 0 0 1-6 6l-10-10a4.24 4.24 0 0 1 6-6Z"/>
      <path d="m8 16 8-8"/>
    </svg>
  );
}

function patientRecords(patient: Patient, category: ClinicalRecord['category']): ClinicalRecord[] {
  return (patient.clinicalRecords ?? []).filter(
    record => record.patientId === patient.id && record.category === category,
  );
}

function normalizedName(value: string): string {
  return value.trim().toLowerCase();
}

function parseLegacyStatusLabel(value: string): LegacyClinicalLabel {
  const match = value.match(/^(.*?)\s+—\s+([^,]+),\s*(confirmed|reported|awaiting[_ ]review)\s*$/i);
  if (!match) return { name: value.trim() };
  return {
    name: match[1].trim(),
    status: match[2].trim(),
    verification: match[3].replace(/_/g, ' ').trim(),
  };
}

function parseLegacyAllergyLabel(value: string): LegacyClinicalLabel {
  const match = value.match(/^(.*?)\s+—\s+(.*?)\s*$/);
  if (!match) return { name: value.trim() };
  const verificationMatch = match[2].match(/^(.*?)\s+\((confirmed|reported|awaiting[_ ]review)\)\s*$/i);
  return {
    name: match[1].trim(),
    reaction: (verificationMatch?.[1] ?? match[2]).trim(),
    verification: verificationMatch?.[2].replace(/_/g, ' ').trim(),
  };
}

function allergyName(value: string): string {
  return value.replace(/^(?:drug|medication|food)(?: allergy)?\s*:\s*/i, '').trim();
}

function isNoKnownAllergyStatement(value: string): boolean {
  return /^(?:no known allergies|no known drug allergies|no known food allergies|nka|nkda)[.!]?$/i.test(value.trim());
}

function isExplicitAllergyRejection(value: string): boolean {
  return /^(?:no known drug allergies|no known food allergies|nkda)[.!]?$/i.test(value.trim());
}

function allergyNegativeStatuses(allergies: string[], items: SummaryItem[]): string[] {
  const statements = allergies.map(value => value.trim().toLowerCase().replace(/[.!]$/, ''));
  const allAllergiesNegative = statements.some(value => value === 'no known allergies' || value === 'nka');
  if (allAllergiesNegative && items.length === 0) return ['No known allergies reported'];

  const drugNegative = statements.some(value => value === 'no known drug allergies' || value === 'nkda');
  const foodNegative = statements.some(value => value === 'no known food allergies');
  const hasDrugAllergy = items.some(item => item.details.includes('Type: Drug'));
  const hasFoodAllergy = items.some(item => item.details.includes('Type: Food'));
  const statuses: string[] = [];
  if (drugNegative && !hasDrugAllergy) statuses.push('No known drug allergies reported');
  if (foodNegative && !hasFoodAllergy) statuses.push('No known food allergies reported');
  if (drugNegative && !foodNegative && !hasFoodAllergy) statuses.push('Food allergies: Not documented');
  if (foodNegative && !drugNegative && !hasDrugAllergy) statuses.push('Drug allergies: Not documented');
  return statuses;
}

function allergyType(value: string, status?: string): string {
  const normalizedStatus = (status ?? '').trim().toLowerCase();
  if (['drug', 'medication'].includes(normalizedStatus)) return 'Type: Drug';
  if (normalizedStatus === 'food') return 'Type: Food';
  if (normalizedStatus === 'environmental') return 'Type: Environmental';
  if (/^(?:drug|medication)(?: allergy)?\s*:/i.test(value) || /\b(?:drug|medication) allergy\b/i.test(value)) {
    return 'Type: Drug';
  }
  if (/^food(?: allergy)?\s*:/i.test(value) || /\bfood allergy\b/i.test(value)) {
    return 'Type: Food';
  }
  return 'Type: Not documented';
}

function recordSource(record: ClinicalRecord, consultationId: string): string {
  if (record.consultationId === consultationId) {
    return record.verification === 'reported' ? 'Encounter-reported' : `Current encounter · ${record.verification.replace('_', ' ')}`;
  }
  return `Patient record · ${record.verification.replace('_', ' ')}`;
}

function formatStatus(status?: string): string | null {
  if (!status?.trim()) return null;
  return status.replace(/[_-]/g, ' ');
}

function allergyItems(patient: Patient, consultationId: string): {
  items: SummaryItem[];
  statusMessages: string[];
} {
  const legacyAllergies = Array.isArray(patient.allergies) ? patient.allergies : [];
  const records = patientRecords(patient, 'allergy').filter(
    record => !/\b(?:resolved|inactive|discontinued|deleted)\b/i.test(record.status ?? ''),
  );
  const items: SummaryItem[] = records.map(record => {
    const typeLabel = allergyType(record.name, record.status);
    const reaction = record.reaction ? `Reaction: ${record.reaction}` : '';
    const statusText = record.status && /(?:documented|explicitly|no known|not documented)/i.test(record.status)
      ? `Allergy status: ${record.status.replace(/_/g, ' ')}`
      : formatStatus(record.status) ? `Status: ${formatStatus(record.status)}` : '';
    return {
      id: record.id,
      name: allergyName(record.name),
      details: [
        typeLabel,
        reaction,
        statusText,
        record.value ? `Details: ${record.value}` : '',
      ].filter(Boolean),
      source: recordSource(record, consultationId),
    };
  });
  const knownNames = new Set(items.map(item => normalizedName(item.name)));

  for (const [index, allergy] of legacyAllergies.entries()) {
    const parsed = parseLegacyAllergyLabel(allergy);
    const name = allergyName(parsed.name);
    if (isNoKnownAllergyStatement(allergy) || isExplicitAllergyRejection(allergy) || knownNames.has(normalizedName(name))) continue;
    items.push({
      id: `allergy-${patient.id}-${index}`,
      name,
      details: [
        allergyType(parsed.name),
        parsed.reaction ? `Reaction: ${parsed.reaction}` : '',
      ].filter(Boolean),
      source: parsed.verification
        ? `Patient record · ${parsed.verification}`
        : 'Patient record · verification not documented',
    });
    knownNames.add(normalizedName(name));
  }

  return { items, statusMessages: allergyNegativeStatuses(legacyAllergies, items) };
}

function conditionItems(patient: Patient, consultationId: string): SummaryItem[] {
  const allRecords = patientRecords(patient, 'condition');
  const records = allRecords.filter(
    record => !/\b(?:resolved|inactive|discontinued)\b/i.test(record.status ?? ''),
  );
  const items: SummaryItem[] = records.map(record => {
    const duration = record.value?.match(/Duration:\s*([^;]+)/i)?.[1]?.trim();
    const classification = record.value?.match(/Classification:\s*([^;]+)/i)?.[1]?.trim();
    return {
      id: record.id,
      name: record.name,
      details: [
        formatStatus(record.status) ? `Status: ${formatStatus(record.status)}` : '',
        duration ? `Duration: ${duration}` : '',
        classification ? `Classification: ${classification}` : 'Classification: Not documented',
      ].filter(Boolean),
      source: recordSource(record, consultationId),
    };
  });
  const knownNames = new Set(allRecords.map(record => normalizedName(record.name)));

  for (const [index, condition] of (Array.isArray(patient.conditions) ? patient.conditions : []).entries()) {
    const parsed = parseLegacyStatusLabel(condition);
    if (knownNames.has(normalizedName(parsed.name))) continue;
    items.push({
      id: `condition-${patient.id}-${index}`,
      name: parsed.name,
      details: [
        parsed.status ? `Status: ${parsed.status}` : 'Status: Not documented',
        'Classification: Not documented',
      ],
      source: parsed.verification
        ? `Patient record · ${parsed.verification}`
        : 'Patient record · verification not documented',
    });
    knownNames.add(normalizedName(parsed.name));
  }
  return items;
}

function medicationItems(patient: Patient, consultationId: string): SummaryItem[] {
  const allRecords = patientRecords(patient, 'medication');
  const records = allRecords.filter(record => {
    if (record.consultationId === consultationId) {
      return !/\b(?:discontinued|inactive|resolved)\b/i.test(record.status ?? '');
    }
    return /^(?:current|active|reported[_ -]?current)$/i.test(record.status?.trim() ?? '');
  });
  const items: SummaryItem[] = records.map(record => {
    const valueText = record.value ? record.value.trim() : '';
    const details = [
      valueText ? `Details: ${valueText}` : '',
      formatStatus(record.status) ? `Status: ${formatStatus(record.status)}` : 'Status: Not documented',
    ].filter(Boolean);
    return {
      id: record.id,
      name: record.name,
      details,
      source: recordSource(record, consultationId),
    };
  });
  const knownNames = new Set(allRecords.map(record => normalizedName(record.name)));

  for (const [index, medication] of (Array.isArray(patient.medications) ? patient.medications : []).entries()) {
    const parsed = parseLegacyStatusLabel(medication);
    if (knownNames.has(normalizedName(parsed.name))) continue;
    if (parsed.status && !/^(?:current|active|reported[_ -]?current)$/i.test(parsed.status)) continue;
    items.push({
      id: `medication-${patient.id}-${index}`,
      name: parsed.name,
      details: [parsed.status ? `Status: ${parsed.status}` : 'Status: Current patient medication list'],
      source: parsed.verification
        ? `Patient record · ${parsed.verification}`
        : 'Patient record · details not separately documented',
    });
    knownNames.add(normalizedName(parsed.name));
  }
  return items;
}

function SummaryCard({
  title,
  icon,
  items,
  emptyMessage,
  statusMessages = [],
}: {
  title: string;
  icon: ReactNode;
  items: SummaryItem[];
  emptyMessage: string;
  statusMessages?: string[];
}) {
  return (
    <section className="min-w-0 rounded-lg bg-slate-900/80 px-3 py-2.5">
      <h3 className="flex items-center gap-2 text-xs font-semibold text-slate-300">
        <span className="text-slate-500">{icon}</span>
        {title}
      </h3>
      {items.length === 0 && statusMessages.length === 0 ? (
        <p className="mt-2 text-xs text-slate-500">{emptyMessage}</p>
      ) : (
        <div className="mt-2 max-h-28 space-y-2 overflow-y-auto pr-1">
          {statusMessages.map(message => (
            <p key={message} className={`text-xs ${message.includes('Not documented') ? 'text-slate-500' : 'text-ok-300'}`}>
              {message}
            </p>
          ))}
          {items.length > 0 && (
            <ul className="space-y-2">
              {items.map(item => (
                <li key={item.id} className="border-t border-slate-800/80 pt-1.5 first:border-0 first:pt-0">
                  <p className="break-words text-xs leading-snug text-slate-200">{item.name}</p>
                  {item.details.map(detail => (
                    <p key={detail} className="mt-0.5 break-words text-2xs capitalize text-slate-400">{detail}</p>
                  ))}
                  <p className="mt-0.5 text-2xs text-slate-600">{item.source}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

export default function PatientClinicalSummary({ patient, consultationId }: PatientClinicalSummaryProps) {
  const allergies = allergyItems(patient, consultationId);
  const conditions = conditionItems(patient, consultationId);
  const medications = medicationItems(patient, consultationId);

  return (
    <section aria-label="Patient clinical summary" className="border-t border-slate-800 px-3 py-3">
      <h2 className="mb-2 text-2xs font-semibold uppercase tracking-wider text-slate-500">Patient clinical summary</h2>
      <div className="grid grid-cols-1 gap-2 xl:grid-cols-3">
        <SummaryCard
          title="Allergies"
          icon={<IconAllergy />}
          items={allergies.items}
          emptyMessage={EMPTY_VALUE}
          statusMessages={allergies.statusMessages}
        />
        <SummaryCard
          title="Medical conditions"
          icon={<IconCondition />}
          items={conditions}
          emptyMessage={EMPTY_VALUE}
        />
        <SummaryCard
          title="Current medications"
          icon={<IconMedication />}
          items={medications}
          emptyMessage={EMPTY_VALUE}
        />
      </div>
    </section>
  );
}
