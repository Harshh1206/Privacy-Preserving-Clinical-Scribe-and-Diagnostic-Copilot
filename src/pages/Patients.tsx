import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Patient } from '../models/types';
import { getPatients } from '../services/api';
import { calcAge, formatDate } from '../utils/format';

function IconSearch() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  );
}

function IconAllergy() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const filtered = patients.filter(p => {
    const q = query.toLowerCase();
    return (
      p.firstName.toLowerCase().includes(q) ||
      p.lastName.toLowerCase().includes(q) ||
      p.mrn.toLowerCase().includes(q) ||
      p.conditions.some(c => c.toLowerCase().includes(q))
    );
  });

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"/>
          <p className="text-sm text-slate-500">Loading patients…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center text-danger-400 text-sm">
        Failed to load patients: {error}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-5xl mx-auto px-6 py-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Patients</h1>
            <p className="text-sm text-slate-500 mt-0.5">{patients.length} patients on record</p>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500">
            <IconSearch />
          </span>
          <input
            className="input pl-8"
            placeholder="Search by name, MRN, or condition…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>

        {/* Table */}
        <div className="panel">
          {filtered.length === 0 ? (
            <div className="px-4 py-10 text-center text-slate-500 text-sm">
              {query ? `No patients matching "${query}".` : 'No patients found.'}
            </div>
          ) : (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>MRN</th>
                  <th>DOB / Age</th>
                  <th>Active conditions</th>
                  <th>Allergies</th>
                  <th>Visits</th>
                  <th>Last visit</th>
                  <th/>
                </tr>
              </thead>
              <tbody>
                {filtered.map(pt => (
                  <tr key={pt.id}>
                    <td>
                      <Link
                        to={`/patients/${pt.id}`}
                        className="font-medium text-slate-100 hover:text-brand-300 transition-colors"
                      >
                        {pt.lastName}, {pt.firstName}
                      </Link>
                      <p className="text-2xs text-slate-500">{pt.sex === 'M' ? 'Male' : pt.sex === 'F' ? 'Female' : 'Other'}</p>
                    </td>
                    <td className="font-mono text-xs text-slate-400">{pt.mrn}</td>
                    <td className="text-slate-400">
                      {formatDate(pt.dob)}
                      <span className="ml-1 text-slate-500">({calcAge(pt.dob)}y)</span>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {pt.conditions.slice(0, 2).map(c => (
                          <span key={c} className="badge badge-neutral text-2xs">{c}</span>
                        ))}
                        {pt.conditions.length > 2 && (
                          <span className="text-2xs text-slate-500">+{pt.conditions.length - 2}</span>
                        )}
                      </div>
                    </td>
                    <td>
                      {pt.allergies.length > 0 ? (
                        <span className="flex items-center gap-1 text-danger-400 text-xs font-medium">
                          <IconAllergy />
                          {pt.allergies.length} allerg{pt.allergies.length > 1 ? 'ies' : 'y'}
                        </span>
                      ) : (
                        <span className="text-slate-600 text-xs">NKDA</span>
                      )}
                    </td>
                    <td className="text-slate-400">{pt.consultationCount}</td>
                    <td className="text-slate-400 text-xs">{pt.lastVisit ? formatDate(pt.lastVisit) : '—'}</td>
                    <td>
                      <Link
                        to={`/patients/${pt.id}`}
                        className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
                      >
                        View →
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
  );
}
