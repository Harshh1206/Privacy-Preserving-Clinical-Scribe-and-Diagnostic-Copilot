import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Patients from './pages/Patients';
import PatientProfile from './pages/PatientProfile';
import ConsultationWorkspace from './pages/ConsultationWorkspace';
import Records from './pages/Records';
import RecordConsultation from './pages/RecordConsultation';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-slate-950">
        <Sidebar />
        <main className="flex-1 flex overflow-hidden min-w-0">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/patients" element={<Patients />} />
            <Route path="/patients/:patientId" element={<PatientProfile />} />
            <Route path="/consultation/:consultationId" element={<ConsultationWorkspace />} />
            <Route path="/record" element={<RecordConsultation />} />
            <Route path="/record/:patientId" element={<RecordConsultation />} />
            <Route path="/records" element={<Records />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
