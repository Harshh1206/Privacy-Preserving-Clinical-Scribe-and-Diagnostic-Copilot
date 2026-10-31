import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Consultation, Patient } from '../models/types';
import { getConsultations, getPatients } from '../services/api';
import { formatDateTime, formatDate, getStatusLabel, getStatusBadgeClass, calcAge } from '../utils/format';

function IconAlert() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

function IconChevron() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  );
}

function IconClock() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  );
}

export default function Dashboard() {
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getConsultations(), getPatients()])
      .then(([cons, pts]) => {
        setConsultations(cons);
        setPatients(pts);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const today = formatDate(new Date().toISOString());
  const todayCons = consultations.filter(c => formatDate(c.date) === today);
  const pendingReview = consultations.filter(c => c.status === 'pending-review');
  const patientMap = Object.fromEntries(patients.map(p => [p.id, p]));

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"/>
          <p className="text-sm">Loading dashboard…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-danger-400">
          <p className="text-sm font-medium">Failed to load dashboard</p>
          <p className="text-xs text-slate-500 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-5xl mx-auto px-6 py-5">
        {/* Header */}
        <div className="mb-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-slate-100">Today's Overview</h1>
              <p className="text-sm text-slate-500 mt-0.5">{today} · Dr. Sarah Chen · Internal Medicine</p>
            </div>
            <Link to="/record" className="btn-primary">
              <span aria-hidden="true">●</span>
              Record Consultation
            </Link>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-4 gap-3 mb-5">
          {[
            { label: 'Today\'s consultations', value: todayCons.length, color: 'text-slate-100' },
            { label: 'Pending review', value: pendingReview.length, color: pendingReview.length > 0 ? 'text-warn-400' : 'text-slate-100' },
            { label: 'Finalized today', value: todayCons.filter(c => c.status === 'finalized').length, color: 'text-ok-400' },
            { label: 'Total patients', value: patients.length, color: 'text-slate-100' },
          ].map(stat => (
            <div key={stat.label} className="panel px-3 py-3">
              <p className="text-xs text-slate-500 mb-1">{stat.label}</p>
              <p className={`text-2xl font-semibold ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Pending review banner */}
        {pendingReview.length > 0 && (
          <div className="flex items-start gap-2 bg-warn-500/10 border border-warn-500/30 rounded px-3 py-2.5 mb-5 text-warn-300 text-sm">
            <IconAlert />
            <div>
              <span className="font-medium">{pendingReview.length} consultation{pendingReview.length > 1 ? 's' : ''} require review.</span>
              <span className="text-slate-400 ml-1">Review and finalize to complete the clinical record.</span>
            </div>
          </div>
        )}

        {/* Today's consultations */}
        <div className="panel mb-5">
          <div className="panel-header">
            <span className="panel-title">Today's Consultations</span>
            <Link to="/patients" className="text-2xs text-brand-400 hover:text-brand-300 transition-colors">
              View all patients →
            </Link>
          </div>
          {todayCons.length === 0 ? (
            <div className="px-4 py-8 text-center text-slate-500 text-sm">No consultations scheduled for today.</div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Time</th>
                  <th>Chief complaint</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th/>
                </tr>
              </thead>
              <tbody>
                {todayCons.map(con => {
                  const pt = patientMap[con.patientId];
                  return (
                    <tr key={con.id}>
                      <td>
                        <Link
                          to={`/patients/${con.patientId}`}
                          className="font-medium text-slate-100 hover:text-brand-300 transition-colors"
                        >
                          {pt ? `${pt.lastName}, ${pt.firstName}` : con.patientId}
                        </Link>
                        {pt && <p className="text-2xs text-slate-500">{pt.mrn} · {calcAge(pt.dob)} y/o {pt.sex}</p>}
                      </td>
                      <td>
                        <span className="flex items-center gap-1 text-slate-400">
                          <IconClock />
                          {formatDateTime(con.date).split(',')[1].trim()}
                        </span>
                      </td>
                      <td className="text-slate-300 max-w-xs truncate">{con.chiefComplaint}</td>
                      <td className="text-slate-400">{con.duration ?? '—'} min</td>
                      <td><span className={getStatusBadgeClass(con.status)}>{getStatusLabel(con.status)}</span></td>
                      <td>
                        <Link
                          to={`/consultation/${con.id}`}
                          className="flex items-center gap-0.5 text-brand-400 hover:text-brand-300 transition-colors text-xs"
                        >
                          Review <IconChevron />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Recent finalized */}
        {consultations.filter(c => c.status === 'finalized').length > 0 && (
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Recently Finalized</span>
            </div>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Date</th>
                  <th>Chief complaint</th>
                  <th>Finalized</th>
                  <th/>
                </tr>
              </thead>
              <tbody>
                {consultations.filter(c => c.status === 'finalized').slice(0, 5).map(con => {
                  const pt = patientMap[con.patientId];
                  return (
                    <tr key={con.id}>
                      <td className="font-medium text-slate-100">
                        {pt ? `${pt.lastName}, ${pt.firstName}` : con.patientId}
                      </td>
                      <td className="text-slate-400">{formatDate(con.date)}</td>
                      <td className="text-slate-300">{con.chiefComplaint}</td>
                      <td className="text-slate-400">{con.finalisedAt ? formatDateTime(con.finalisedAt) : '—'}</td>
                      <td>
                        <Link to={`/consultation/${con.id}`} className="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                          View
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
