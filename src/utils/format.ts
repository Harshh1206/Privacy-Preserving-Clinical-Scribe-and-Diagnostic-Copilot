import type { HallucinationRisk, ClaimStatus, ConsultationStatus, Severity } from '../models/types';

// ─── Date formatting ──────────────────────────────────────────────────────────

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function calcAge(dob: string): number {
  const birth = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today < new Date(today.getFullYear(), birth.getMonth(), birth.getDate())) age--;
  return age;
}

// ─── Grounding / Hallucination ────────────────────────────────────────────────

export function getHallucinationRisk(score: number): HallucinationRisk {
  if (score >= 90) return 'low';
  if (score >= 70) return 'moderate';
  return 'high';
}

export function getHallucinationRiskLabel(risk: HallucinationRisk): string {
  switch (risk) {
    case 'low': return 'Low Risk';
    case 'moderate': return 'Moderate Risk';
    case 'high': return 'High Risk';
  }
}

export function getRiskBadgeClass(risk: HallucinationRisk): string {
  switch (risk) {
    case 'low': return 'badge-ok';
    case 'moderate': return 'badge-warn';
    case 'high': return 'badge-danger';
  }
}

export function getGroundingColor(score: number): string {
  if (score >= 90) return 'text-ok-500';
  if (score >= 70) return 'text-warn-500';
  return 'text-danger-500';
}

export function getGroundingBgColor(score: number): string {
  if (score >= 90) return 'bg-ok-500';
  if (score >= 70) return 'bg-warn-500';
  return 'bg-danger-500';
}

// ─── Status labels ────────────────────────────────────────────────────────────

export function getStatusLabel(status: ConsultationStatus): string {
  switch (status) {
    case 'scheduled': return 'Scheduled';
    case 'in-progress': return 'In Progress';
    case 'pending-review': return 'Pending Review';
    case 'finalized': return 'Finalized';
    case 'cancelled': return 'Cancelled';
  }
}

export function getStatusBadgeClass(status: ConsultationStatus): string {
  switch (status) {
    case 'scheduled': return 'badge-neutral';
    case 'in-progress': return 'badge-brand';
    case 'pending-review': return 'badge-warn';
    case 'finalized': return 'badge-ok';
    case 'cancelled': return 'badge-neutral';
  }
}

export function getClaimStatusLabel(status: ClaimStatus): string {
  switch (status) {
    case 'supported': return 'Supported';
    case 'unsupported': return 'Unsupported';
    case 'conflict': return 'Conflict';
    case 'pending': return 'Pending';
  }
}

export function getClaimBadgeClass(status: ClaimStatus): string {
  switch (status) {
    case 'supported': return 'badge-ok';
    case 'unsupported': return 'badge-danger';
    case 'conflict': return 'badge-warn';
    case 'pending': return 'badge-neutral';
  }
}

export function getClaimRowClass(status: ClaimStatus): string {
  switch (status) {
    case 'supported': return 'claim-supported';
    case 'unsupported': return 'claim-unsupported';
    case 'conflict': return 'claim-conflict';
    default: return '';
  }
}

export function getSeverityBadgeClass(severity: Severity): string {
  switch (severity) {
    case 'low': return 'badge-neutral';
    case 'medium': return 'badge-brand';
    case 'high': return 'badge-danger';
    case 'critical': return 'badge-danger';
  }
}

export function getSectionLabel(section: string): string {
  switch (section) {
    case 'subjective': return 'S';
    case 'objective': return 'O';
    case 'assessment': return 'A';
    case 'plan': return 'P';
    default: return section.charAt(0).toUpperCase();
  }
}

export function getSpeakerBadgeClass(role: string): string {
  switch (role) {
    case 'doctor':
    case 'physician': return 'bg-brand-600/20 text-brand-300';
    case 'patient': return 'bg-slate-700 text-slate-300';
    case 'nurse': return 'bg-ok-600/20 text-ok-300';
    default: return 'bg-slate-700 text-slate-400';
  }
}
