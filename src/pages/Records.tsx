import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Consultation, Patient } from '../models/types';
import { getConsultations, getPatients } from '../services/api';
import { formatDateTime, getStatusBadgeClass, getStatusLabel, calcAge } from '../utils/format';

function IconSearch() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  );
}

export default function Records() {
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    Promise.all([getConsultations(), getPatients()])
      .then(([cons, pts]) => {
        setConsultations(cons);
        setPatients(pts);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const patientMap = Object.fromEntries(patients.map(p => [p.id, p]));

  const filtered = consultations.filter(con => {
    const pt = patientMap[con.patientId];
    const q = query.toLowerCase();
    const matchQ = !q || (
      (pt?.firstName.toLowerCase().includes(q)) ||
      (pt?.lastName.toLowerCase().includes(q)) ||
      (pt?.mrn.toLowerCase().includes(q)) ||
      con.chiefComplaint.toLowerCase().includes(q)
    );
    const matchS = statusFilter === 'all' || con.status === statusFilter;
    return matchQ && matchS;
  });

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"/>
          <p className="text-sm text-slate-500">Loading records…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return <div className="flex-1 flex items-center justify-center text-danger-400 text-sm">{error}</div>;
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-5xl mx-auto px-6 py-5">
        <div className="mb-4">
          <h1 className="text-lg font-semibold text-slate-100">Records</h1>
          <p className="text-sm text-slate-500 mt-0.5">All consultations across all patients</p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500"><IconSearch /></span>
            <input
              className="input pl-8"
              placeholder="Search by patient name, MRN, or complaint…"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
          </div>
          <select
            className="input w-44"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="pending-review">Pending review</option>
            <option value="finalized">Finalized</option>
            <option value="in-progress">In progress</option>
            <option value="scheduled">Scheduled</option>
          </select>
        </div>

        {/* Table */}
        <div className="panel">
          {filtered.length === 0 ? (
            <div className="px-4 py-10 text-center text-slate-500 text-sm">
              {query || statusFilter !== 'all' ? 'No records match the current filters.' : 'No records found.'}
            </div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Date & time</th>
                  <th>Chief complaint</th>
                  <th>Physician</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th/>
                </tr>
              </thead>
              <tbody>
                {filtered.map(con => {
                  const pt = patientMap[con.patientId];
                  return (
                    <tr key={con.id}>
                      <td>
                        <Link
                          to={`/patients/${con.patientId}`}
                          className="font-medium text-slate-100 hover:text-brand-300 transition-colors block"
                        >
                          {pt ? `${pt.lastName}, ${pt.firstName}` : con.patientId}
                        </Link>
                        {pt && (
                          <p className="text-2xs text-slate-500">
                            {pt.mrn} · {calcAge(pt.dob)} y/o {pt.sex}
                          </p>
                        )}
                      </td>
                      <td className="text-slate-400 text-xs">{formatDateTime(con.date)}</td>
                      <td className="text-slate-300">{con.chiefComplaint}</td>
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
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <p className="text-2xs text-slate-700 mt-3">
          Showing {filtered.length} of {consultations.length} records
        </p>
      </div>
    </div>
  );
}
