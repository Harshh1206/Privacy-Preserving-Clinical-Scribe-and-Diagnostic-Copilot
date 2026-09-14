import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { Patient, Consultation } from '../models/types';
import { getPatient, getConsultations } from '../services/api';
import { calcAge, formatDate, formatDateTime, getStatusBadgeClass, getStatusLabel } from '../utils/format';

function IconBack() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6"/>
    </svg>
  );
}

function IconAllergy() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-slate-800 last:border-0">
      <span className="text-xs text-slate-500 w-32 shrink-0 pt-0.5">{label}</span>
      <span className="text-sm text-slate-200 flex-1">{value}</span>
    </div>
  );
}

export default function PatientProfile() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) return;
    Promise.all([getPatient(patientId), getConsultations(patientId)])
      .then(([pt, cons]) => {
        setPatient(pt);
        setConsultations(cons);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [patientId]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"/>
          <p className="text-sm text-slate-500">Loading patient…</p>
        </div>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="flex-1 flex items-center justify-center text-danger-400 text-sm">
        {error ?? 'Patient not found.'}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-5xl mx-auto px-6 py-5">
        {/* Breadcrumb */}
        <Link to="/patients" className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 mb-4 transition-colors">
          <IconBack /> Patients
        </Link>

        {/* Patient header */}
        <div className="flex items-start gap-4 mb-5">
          <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center text-lg font-semibold text-slate-200 shrink-0">
            {patient.firstName[0]}{patient.lastName[0]}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-semibold text-slate-100">{patient.firstName} {patient.lastName}</h1>
            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <span className="text-sm text-slate-400">{patient.mrn}</span>
              <span className="text-slate-700">·</span>
              <span className="text-sm text-slate-400">{calcAge(patient.dob)} y/o {patient.sex === 'M' ? 'Male' : patient.sex === 'F' ? 'Female' : 'Other'}</span>
              <span className="text-slate-700">·</span>
              <span className="text-sm text-slate-400">DOB: {formatDate(patient.dob)}</span>
              {patient.allergies.length > 0 && (
                <>
                  <span className="text-slate-700">·</span>
                  <span className="flex items-center gap-1 text-danger-400 text-sm font-medium">
                    <IconAllergy />
                    ALLERGY: {patient.allergies.map(a => a.split('—')[0].trim()).join(', ')}
                  </span>
                </>
              )}
            </div>
          </div>
          <div>
            <span className={`badge ${patient.privacyLevel === 'restricted' ? 'badge-danger' : patient.privacyLevel === 'sensitive' ? 'badge-warn' : 'badge-neutral'}`}>
              {patient.privacyLevel}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Patient details */}
          <div className="col-span-1 space-y-3">
            <div className="panel">
              <div className="panel-header"><span className="panel-title">Demographics</span></div>
              <div className="px-3 py-2">
                <InfoRow label="Date of birth" value={formatDate(patient.dob)} />
                <InfoRow label="Sex" value={patient.sex === 'M' ? 'Male' : patient.sex === 'F' ? 'Female' : 'Other'} />
                <InfoRow label="Phone" value={patient.phone ?? '—'} />
                <InfoRow label="Privacy level" value={patient.privacyLevel} />
              </div>
            </div>

            {patient.allergies.length > 0 && (
              <div className="panel border-danger-500/40">
                <div className="panel-header bg-danger-500/5">
                  <span className="panel-title text-danger-400 flex items-center gap-1.5">
                    <IconAllergy /> Allergies
                  </span>
                </div>
                <div className="px-3 py-2 space-y-1">
                  {patient.allergies.map((a, i) => (
                    <div key={i} className="text-sm text-danger-300 py-1 border-b border-slate-800 last:border-0">
                      {a}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="panel">
              <div className="panel-header"><span className="panel-title">Active Conditions</span></div>
              <div className="px-3 py-2 space-y-1">
                {patient.conditions.length === 0 ? (
                  <p className="text-sm text-slate-500">None on record.</p>
                ) : patient.conditions.map((c, i) => (
                  <div key={i} className="text-sm text-slate-300 py-1 border-b border-slate-800 last:border-0">{c}</div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header"><span className="panel-title">Current Medications</span></div>
              <div className="px-3 py-2 space-y-1">
                {patient.medications.length === 0 ? (
                  <p className="text-sm text-slate-500">None on record.</p>
                ) : patient.medications.map((m, i) => (
                  <div key={i} className="text-sm text-slate-300 py-1 border-b border-slate-800 last:border-0">{m}</div>
                ))}
              </div>
            </div>
          </div>

          {/* Consultation history */}
          <div className="col-span-2">
            <div className="panel">
              <div className="panel-header">
                <span className="panel-title">Consultation History ({consultations.length})</span>
              </div>
              {consultations.length === 0 ? (
                <div className="px-4 py-8 text-center text-slate-500 text-sm">No consultations on record.</div>
              ) : (
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Date & time</th>
                      <th>Chief complaint</th>
                      <th>Physician</th>
                      <th>Duration</th>
                      <th>Status</th>
                      <th/>
                    </tr>
                  </thead>
                  <tbody>
                    {consultations.map(con => (
                      <tr key={con.id}>
                        <td className="text-slate-400 text-xs">{formatDateTime(con.date)}</td>
                        <td className="text-slate-200 font-medium">{con.chiefComplaint}</td>
                        <td className="text-slate-400 text-xs">{con.physicianName}</td>
                        <td className="text-slate-400">{con.duration ?? '—'} min</td>
                        <td><span className={getStatusBadgeClass(con.status)}>{getStatusLabel(con.status)}</span></td>
                        <td>
                          <Link
                            to={`/consultation/${con.id}`}
                            className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
                          >
                            {con.status === 'finalized' ? 'View' : 'Review'} →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
