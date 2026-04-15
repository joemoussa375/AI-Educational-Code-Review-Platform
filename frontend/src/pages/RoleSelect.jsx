import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, Building, Eye, EyeOff, Terminal, LogIn } from 'lucide-react';
import './RoleSelect.css';

const STAFF_PASSCODE = 'mentor2026';

// Validate: 2 digit year prefix + 4 digit number
function validateStudentId(id) {
  return /^\d{6}$/.test(id);
}

export default function RoleSelect() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('student'); // 'student' | 'staff'

  // Student form
  const [studentId, setStudentId] = useState('');
  const [studentName, setStudentName] = useState('');
  const [studentError, setStudentError] = useState('');
  const [studentLoading, setStudentLoading] = useState(false);

  // Staff form
  const [passcode, setPasscode] = useState('');
  const [showPasscode, setShowPasscode] = useState(false);
  const [staffError, setStaffError] = useState('');

  async function handleStudentLogin(e) {
    e.preventDefault();
    setStudentError('');

    if (!validateStudentId(studentId)) {
      setStudentError('ID must be exactly 6 digits (e.g., 250001 for year 2025).');
      return;
    }
    if (!studentName.trim()) {
      setStudentError('Please enter your full name.');
      return;
    }

    setStudentLoading(true);

    try {
      // Register student with the API (if available)
      const apiUrl = sessionStorage.getItem('apiUrl') || '';
      if (apiUrl) {
        await fetch(`${apiUrl}/api/student/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
          body: JSON.stringify({ student_id: studentId, name: studentName.trim() }),
        }).catch(() => {}); // Silently fail if API not connected yet
      }
    } catch (_) {}

    sessionStorage.setItem('studentId', studentId);
    sessionStorage.setItem('studentName', studentName.trim());
    sessionStorage.setItem('role', 'student');
    setStudentLoading(false);
    navigate('/student');
  }

  function handleStaffLogin(e) {
    e.preventDefault();
    setStaffError('');
    if (passcode !== STAFF_PASSCODE) {
      setStaffError('Incorrect passcode. Please try again.');
      return;
    }
    sessionStorage.setItem('role', 'staff');
    navigate('/staff');
  }

  return (
    <div className="roleSelectPage">
      {/* Background decoration */}
      <div className="bgOrb bgOrb1" />
      <div className="bgOrb bgOrb2" />
      <div className="bgOrb bgOrb3" />

      <div className="roleContainer">
        {/* Header */}
        <div className="roleHeader">
          <div style={{color: 'var(--brand)', marginBottom: '16px', display: 'flex', justifyContent: 'center'}}>
            <Terminal size={48} />
          </div>
          <h1 className="roleTitle">AI Code Mentor</h1>
          <p className="roleSubtitle">RAG-Enhanced Code Review · Educational Platform</p>
        </div>

        {/* Tab switcher */}
        <div className="roleTabs">
          <button
            id="tab-student"
            className={`roleTab ${activeTab === 'student' ? 'active' : ''}`}
            onClick={() => { setActiveTab('student'); setStudentError(''); setStaffError(''); }}
          >
            <GraduationCap size={18} style={{ marginRight: '8px' }} /> Student
          </button>
          <button
            id="tab-staff"
            className={`roleTab ${activeTab === 'staff' ? 'active' : ''}`}
            onClick={() => { setActiveTab('staff'); setStudentError(''); setStaffError(''); }}
          >
            <Building size={18} style={{ marginRight: '8px' }} /> Teaching Staff
          </button>
        </div>

        {/* Card */}
        <div className="roleCard">
          {activeTab === 'student' ? (
            <form className="roleForm" onSubmit={handleStudentLogin} id="form-student">
              <div className="roleCardHeader">
                <div>
                  <h2>Student Access</h2>
                  <p>Submit your code for AI‑powered review and track your progress</p>
                </div>
              </div>

              <div className="formGroup">
                <label htmlFor="input-student-name">Full Name</label>
                <input
                  id="input-student-name"
                  type="text"
                  value={studentName}
                  onChange={e => setStudentName(e.target.value)}
                  autoComplete="off"
                />
              </div>

              <div className="formGroup">
                <label htmlFor="input-student-id">
                  Student ID
                </label>
                <input
                  id="input-student-id"
                  type="text"
                  placeholder="e.g., 250001"
                  value={studentId}
                  onChange={e => setStudentId(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  autoComplete="off"
                />
              </div>

              {studentError && <div className="formError" role="alert">{studentError}</div>}

              <button
                id="btn-student-login"
                type="submit"
                className="loginBtn student"
                disabled={studentLoading}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                <LogIn size={18} />
                {studentLoading ? 'Logging in...' : 'Enter Student Portal'}
              </button>
            </form>
          ) : (
            <form className="roleForm" onSubmit={handleStaffLogin} id="form-staff">
              <div className="roleCardHeader">
                <div>
                  <h2>Staff Access</h2>
                  <p>View class analytics, monitor students, and annotate reviews</p>
                </div>
              </div>

              <div className="formGroup">
                <label htmlFor="input-staff-passcode">Staff Passcode</label>
                <div className="passWrap">
                  <input
                    id="input-staff-passcode"
                    type={showPasscode ? 'text' : 'password'}
                    placeholder="Enter access code"
                    value={passcode}
                    onChange={e => setPasscode(e.target.value)}
                    autoComplete="off"
                  />
                  <button
                    type="button"
                    className="passToggle"
                    onClick={() => setShowPasscode(v => !v)}
                    tabIndex={-1}
                  >
                    {showPasscode ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {staffError && <div className="formError" role="alert">{staffError}</div>}

              <button id="btn-staff-login" type="submit" className="loginBtn staff" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <LogIn size={18} />
                Enter Staff Dashboard
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
