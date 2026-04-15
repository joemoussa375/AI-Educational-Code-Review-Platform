import { Routes, Route, Navigate } from 'react-router-dom';
import RoleSelect from './pages/RoleSelect';
import StudentApp from './pages/StudentApp';
import StaffDashboard from './pages/StaffDashboard';
import './App.css';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RoleSelect />} />
      <Route path="/student" element={<StudentApp />} />
      <Route path="/staff" element={<StaffDashboard />} />
      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
