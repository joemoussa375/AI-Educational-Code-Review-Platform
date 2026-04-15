import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Terminal, Settings, LogOut, GraduationCap, ShieldCheck, Eye, EyeOff, X } from 'lucide-react';
import './Header.css';

export default function Header({ onConnectionChange, statusMessage, setStatusMessage, role, userName }) {
  const navigate = useNavigate();
  const [url, setUrl] = useState(sessionStorage.getItem('apiUrl') || 'https://krysten-chromous-gaylord.ngrok-free.dev');
  const [showUrl, setShowUrl] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // Initial connection check on mount
  useEffect(() => {
    checkConnection(url);
  }, []);

  async function checkConnection(targetUrl) {
    const cleanUrl = (targetUrl || url).trim().replace(/\/$/, '');
    if (!cleanUrl) {
      if (setStatusMessage) setStatusMessage({ text: 'Please enter an API URL', type: 'error' });
      return;
    }

    setIsConnecting(true);
    if (setStatusMessage) setStatusMessage({ text: 'Connecting to API...', type: 'loading' });

    try {
      const res = await fetch(`${cleanUrl}/api/health`, {
        method: 'GET',
        headers: {
          'ngrok-skip-browser-warning': 'true',
          Accept: 'application/json',
        },
      });

      const contentType = res.headers.get('content-type') || '';
      let data;

      if (!contentType.includes('application/json')) {
        const retry = await fetch(`${cleanUrl}/api/health`, {
          method: 'GET',
          headers: {
            'ngrok-skip-browser-warning': 'true',
            Accept: 'application/json',
          },
        });
        data = await retry.json();
      } else {
        data = await res.json();
      }

      if (data.status) {
        setConnected(true);
        sessionStorage.setItem('apiUrl', cleanUrl);
        onConnectionChange(true, cleanUrl);
        const engineStatus = data.status === 'online' ? `Engine Ready (${data.gpu || 'GPU'})` : 'Loading Model...';
        if (setStatusMessage) setStatusMessage({ text: `Connected — ${engineStatus}`, type: 'success' });

        if (data.status === 'model_not_loaded') {
          handleModelLoad(cleanUrl);
        }
      }
    } catch (err) {
      setConnected(false);
      onConnectionChange(false, '');
      if (setStatusMessage) setStatusMessage({ text: `Connection failed: ${err.message}`, type: 'error' });
    } finally {
      setIsConnecting(false);
    }
  }

  async function handleModelLoad(cleanUrl) {
    try {
      await fetch(`${cleanUrl}/api/load`, {
        method: 'POST',
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });

      const poll = setInterval(async () => {
        try {
          const hRes = await fetch(`${cleanUrl}/api/health`, {
            headers: { 'ngrok-skip-browser-warning': 'true', Accept: 'application/json' },
          });
          const hData = await hRes.json();
          if (hData.status === 'online') {
            clearInterval(poll);
            if (setStatusMessage) setStatusMessage({ text: `Connected — Engine Ready`, type: 'success' });
          }
        } catch (e) {
          /* ignore */
        }
      }, 5000);
    } catch (e) {
      /* ignore */
    }
  }

  function handleLogout() {
    sessionStorage.removeItem('role');
    sessionStorage.removeItem('studentId');
    sessionStorage.removeItem('studentName');
    navigate('/');
  }

  return (
    <header className="header">
      <div className="headerLeft">
        <div style={{ display: 'flex', alignItems: 'center', marginRight: '12px', color: 'var(--brand)' }}>
          <Terminal size={32} />
        </div>
        <div>
          <h1 className="brandTitle">AI Code Mentor</h1>
          <p className="brandSub">Automated Code Review · RAG + Static Analysis + LLM</p>
        </div>
      </div>

      <div className="headerRight">
        {/* Role badge */}
        {role === 'student' && userName && (
          <div className="userBadge studentBadge" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <GraduationCap size={16} />
            <span>{userName}</span>
          </div>
        )}
        {role === 'staff' && (
          <div className="userBadge staffBadge" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={16} />
            <span>Staff Mode</span>
          </div>
        )}

        {/* Connection status */}
        <div className="statusIndicator">
          <span className={`dot ${connected ? 'connected' : ''}`} title={connected ? 'Connected' : 'Disconnected'} />
          <span>{connected ? 'Connected' : 'Offline'}</span>
        </div>
        <button className="settingsBtn" onClick={() => setShowModal(true)} title="Connection Settings">
          <Settings size={18} />
        </button>

        {/* Logout */}
        <button className="logoutBtn" onClick={handleLogout} id="btn-logout" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <LogOut size={16} /> Logout
        </button>
      </div>

      {/* Settings Modal */}
      {showModal && (
        <div className="modalOverlay" onClick={() => setShowModal(false)}>
          <div className="modalContent" onClick={(e) => e.stopPropagation()}>
            <div className="modalHeader">
              <h3>Connection Settings</h3>
              <button className="closeBtn" onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modalBody">
              <div className="inputGroup">
                <label>API Endpoint (ngrok URL)</label>
                <div className="urlInputWrap">
                  <input
                    type={showUrl ? 'text' : 'password'}
                    value={url}
                    className={connected ? 'connected' : ''}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://..."
                    spellCheck="false"
                  />
                  <button className="toggleBtn" onClick={() => setShowUrl(!showUrl)}>
                    {showUrl ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              <p className="brandSub" style={{ marginTop: '-10px' }}>
                Paste the ngrok URL provided by your backend environment.
              </p>
            </div>
            <div className="modalFooter">
              <button
                className="modalConnectBtn"
                onClick={() => checkConnection(url)}
                disabled={isConnecting}
              >
                {isConnecting ? 'Connecting...' : 'Test Connection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
