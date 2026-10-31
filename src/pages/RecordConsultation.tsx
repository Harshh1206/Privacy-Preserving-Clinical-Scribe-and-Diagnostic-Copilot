import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { Consultation, Patient, PatientSex, Transcript } from '../models/types';
import {
  createPatient,
  createConsultation,
  getPatients,
  getTeamATranscriptionStatus,
  uploadTeamAAudio,
} from '../services/api';

const MAX_AUDIO_BYTES = 25 * 1024 * 1024;

function extensionForMime(mimeType: string): string {
  if (mimeType.includes('mp4')) return 'm4a';
  if (mimeType.includes('mpeg')) return 'mpeg';
  if (mimeType.includes('ogg')) return 'ogg';
  if (mimeType.includes('wav')) return 'wav';
  if (mimeType.includes('webm')) return 'webm';
  return 'webm';
}

function preferredMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined;
  const candidates = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/webm'];
  return candidates.find(type => MediaRecorder.isTypeSupported(type));
}

function formatTimer(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

export default function RecordConsultation() {
  const { patientId: routePatientId } = useParams<{ patientId?: string }>();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState(routePatientId ?? '');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [starting, setStarting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patientMode, setPatientMode] = useState<'existing' | 'new'>(routePatientId ? 'existing' : 'existing');
  const [newPatient, setNewPatient] = useState({
    mrn: '',
    firstName: '',
    lastName: '',
    dob: '',
    sex: 'O' as PatientSex,
    phone: '',
  });
  const [creatingPatient, setCreatingPatient] = useState(false);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const cancelledRef = useRef(false);
  const retryFileRef = useRef<File | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    getPatients()
      .then(setPatients)
      .catch(e => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoadingPatients(false));
  }, []);

  useEffect(() => {
    if (!consultation || !transcript) return;
    if (transcript.processingStatus !== 'processing' && transcript.processingStatus !== 'pending') return;

    const poll = window.setInterval(async () => {
      try {
        const current = await getTeamATranscriptionStatus(consultation.id);
        if (!current) return;
        setTranscript(current);
        if (current.processingStatus === 'completed' || current.processingStatus === 'failed') {
          window.clearInterval(poll);
        }
      } catch (e) {
        window.clearInterval(poll);
        setError(e instanceof Error ? e.message : String(e));
      }
    }, 2000);

    return () => window.clearInterval(poll);
  }, [consultation, transcript?.processingStatus]);

  useEffect(() => () => {
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach(track => track.stop());
  }, []);

  function stopStream() {
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
  }

  function stopTimer() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  async function uploadRecordedFile(file: File, consultationId?: string) {
    const targetConsultationId = consultationId || consultation?.id;
    if (!targetConsultationId) return;
    if (file.size === 0) {
      setError('The recording is empty. Please record again.');
      return;
    }
    if (file.size > MAX_AUDIO_BYTES) {
      setError('Audio exceeds the 25 MB upload limit.');
      return;
    }
    retryFileRef.current = file;
    setUploading(true);
    setError(null);
    try {
      const status = await uploadTeamAAudio(targetConsultationId, file);
      setTranscript(status);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  }

  async function startRecording() {
    if (!patientId) {
      setError('Select a patient before starting the consultation.');
      return;
    }
    if (!chiefComplaint.trim()) {
      setError('Enter the chief complaint before starting the consultation.');
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone recording is not supported by this browser. Use a current Chrome, Edge, Firefox, or Safari browser.');
      return;
    }

    setStarting(true);
    setError(null);
    try {
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        const denied = e instanceof DOMException && (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError');
        throw new Error(denied
          ? 'Microphone permission was denied. Allow microphone access in browser settings, then retry.'
          : e instanceof Error ? `Unable to access the microphone: ${e.message}` : 'Unable to access the microphone.');
      }

      streamRef.current = stream;
      const created = await createConsultation({
        patientId,
        chiefComplaint: chiefComplaint.trim(),
        physicianId: 'dr-001',
        physicianName: 'Dr. Sarah Chen',
      });
      setConsultation(created);

      const mimeType = preferredMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      recorderRef.current = recorder;
      chunksRef.current = [];
      cancelledRef.current = false;
      recorder.ondataavailable = event => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        stopTimer();
        stopStream();
        setRecording(false);
        setError('The browser recording failed. Please try recording again.');
      };
      recorder.onstop = () => {
        stopTimer();
        stopStream();
        setRecording(false);
        if (cancelledRef.current) {
          chunksRef.current = [];
          setElapsed(0);
          return;
        }
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || 'audio/webm' });
        if (blob.size === 0) {
          setError('The recording produced no audio data. Please record again.');
          return;
        }
        const extension = extensionForMime(blob.type);
        const file = new File([blob], `consultation-${created.id}.${extension}`, { type: blob.type });
        void uploadRecordedFile(file, created.id);
      };
      recorder.start(1000);
      setRecording(true);
      setElapsed(0);
      timerRef.current = window.setInterval(() => setElapsed(value => value + 1), 1000);
    } catch (e) {
      stopStream();
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(false);
    }
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === 'inactive') return;
    cancelledRef.current = false;
    recorder.stop();
  }

  function cancelRecording() {
    const recorder = recorderRef.current;
    cancelledRef.current = true;
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    stopTimer();
    setRecording(false);
    setElapsed(0);
    chunksRef.current = [];
  }

  async function retryUpload() {
    if (retryFileRef.current) await uploadRecordedFile(retryFileRef.current);
  }

  async function handleCreatePatient() {
    if (!newPatient.mrn.trim() || !newPatient.firstName.trim() || !newPatient.lastName.trim() || !newPatient.dob) {
      setError('MRN, first name, last name, and date of birth are required.');
      return;
    }
    setCreatingPatient(true);
    setError(null);
    try {
      const created = await createPatient({
        mrn: newPatient.mrn.trim(),
        firstName: newPatient.firstName.trim(),
        lastName: newPatient.lastName.trim(),
        dob: newPatient.dob,
        sex: newPatient.sex,
        phone: newPatient.phone.trim() || undefined,
        allergies: [],
        conditions: [],
        medications: [],
        privacyLevel: 'standard',
      });
      setPatients(current => [created, ...current.filter(patient => patient.id !== created.id)]);
      setPatientId(created.id);
      setPatientMode('existing');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreatingPatient(false);
    }
  }

  const selectedPatient = patients.find(patient => patient.id === patientId);
  const status = transcript?.processingStatus;

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-5">
        <Link to={selectedPatient ? `/patients/${selectedPatient.id}` : '/patients'} className="text-xs text-slate-500 hover:text-slate-300">
          ← Back
        </Link>
        <div className="mt-3 mb-5">
          <h1 className="text-xl font-semibold text-slate-100">Record Consultation</h1>
          <p className="text-sm text-slate-500 mt-1">Synthetic or authorized clinical audio only. Audio is sent to the Groq transcription provider after upload.</p>
        </div>

        <div className="panel mb-4">
          <div className="panel-header"><span className="panel-title">Consultation Details</span></div>
          <div className="p-4 grid grid-cols-2 gap-4">
            {!consultation && (
              <div className="col-span-2">
                <div className="flex gap-2 mb-3">
                  <button
                    type="button"
                    className={patientMode === 'existing' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                    onClick={() => { setPatientMode('existing'); setError(null); }}
                  >
                    Select Existing Patient
                  </button>
                  <button
                    type="button"
                    className={patientMode === 'new' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                    onClick={() => { setPatientMode('new'); setError(null); }}
                  >
                    Add New Patient
                  </button>
                </div>

                {patientMode === 'existing' ? (
                  <label className="text-xs text-slate-400">
                    Patient
                    <select
                      className="input mt-1"
                      value={patientId}
                      onChange={event => setPatientId(event.target.value)}
                      disabled={recording || uploading || starting}
                    >
                      <option value="">Select patient…</option>
                      {loadingPatients && <option value="" disabled>Loading patients…</option>}
                      {!loadingPatients && patients.map(patient => (
                        <option key={patient.id} value={patient.id}>
                          {patient.lastName}, {patient.firstName} — {patient.mrn}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    <label className="text-xs text-slate-400">MRN
                      <input className="input mt-1" value={newPatient.mrn} onChange={e => setNewPatient(v => ({ ...v, mrn: e.target.value }))} />
                    </label>
                    <label className="text-xs text-slate-400">Date of birth
                      <input type="date" className="input mt-1" value={newPatient.dob} max={new Date().toISOString().slice(0, 10)} onChange={e => setNewPatient(v => ({ ...v, dob: e.target.value }))} />
                    </label>
                    <label className="text-xs text-slate-400">First name
                      <input className="input mt-1" value={newPatient.firstName} onChange={e => setNewPatient(v => ({ ...v, firstName: e.target.value }))} />
                    </label>
                    <label className="text-xs text-slate-400">Last name
                      <input className="input mt-1" value={newPatient.lastName} onChange={e => setNewPatient(v => ({ ...v, lastName: e.target.value }))} />
                    </label>
                    <label className="text-xs text-slate-400">Sex
                      <select className="input mt-1" value={newPatient.sex} onChange={e => setNewPatient(v => ({ ...v, sex: e.target.value as PatientSex }))}>
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                        <option value="O">Other</option>
                      </select>
                    </label>
                    <label className="text-xs text-slate-400">Phone
                      <input className="input mt-1" value={newPatient.phone} onChange={e => setNewPatient(v => ({ ...v, phone: e.target.value }))} />
                    </label>
                    <div className="col-span-2">
                      <button type="button" className="btn-secondary" onClick={handleCreatePatient} disabled={creatingPatient}>
                        {creatingPatient ? 'Creating patient…' : 'Create and Select Patient'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
            <label className="text-xs text-slate-400 col-span-2">
              Chief complaint
              <input
                className="input mt-1"
                value={chiefComplaint}
                onChange={event => setChiefComplaint(event.target.value)}
                disabled={recording || uploading || starting || !!consultation}
                placeholder="Describe the reason for the consultation"
              />
            </label>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {!consultation && (
          <button className="btn-primary w-full justify-center py-3" onClick={startRecording} disabled={starting || !patientId || !chiefComplaint.trim()}>
            {starting ? 'Preparing recording…' : 'Start Recording'}
          </button>
        )}

        {consultation && (
          <div className="panel mb-4">
            <div className="panel-header">
              <span className="panel-title">Microphone</span>
              {recording && <span className="flex items-center gap-2 text-xs text-red-400 font-semibold"><span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"/> Recording in progress</span>}
            </div>
            <div className="p-5 text-center">
              {recording ? (
                <>
                  <div className="text-3xl font-mono text-slate-100 mb-4">{formatTimer(elapsed)}</div>
                  <p className="text-sm font-semibold text-red-400 mb-4">Recording in progress</p>
                  <div className="flex justify-center gap-3">
                    <button className="btn-danger" onClick={stopRecording}>Stop Recording</button>
                    <button className="btn-ghost" onClick={cancelRecording}>Cancel</button>
                  </div>
                </>
              ) : uploading ? (
                <div className="text-sm text-brand-300">Uploading audio securely to the Team A transcription service…</div>
              ) : status === 'processing' || status === 'pending' ? (
                <div>
                  <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"/>
                  <p className="text-sm text-brand-300">Processing transcription…</p>
                  <p className="text-xs text-slate-500 mt-1">Consultation ID: {consultation.id}</p>
                </div>
              ) : status === 'completed' ? (
                <div>
                  <p className="text-sm text-ok-400 mb-2">Transcription completed</p>
                  <Link to={`/consultation/${consultation.id}`} className="btn-primary">Open Consultation Workspace</Link>
                </div>
              ) : status === 'failed' ? (
                <div>
                  <p className="text-sm text-red-400 mb-1">Transcription failed</p>
                  <p className="text-xs text-slate-500 mb-3">{transcript?.processingError || 'The provider could not process the recording.'}</p>
                  <button className="btn-secondary" onClick={retryUpload}>Retry Upload</button>
                </div>
              ) : error && retryFileRef.current ? (
                <div>
                  <p className="text-xs text-slate-500 mb-3">The recording is available for retry.</p>
                  <button className="btn-secondary" onClick={retryUpload}>Retry Upload</button>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Recording stopped. Upload is ready.</p>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
