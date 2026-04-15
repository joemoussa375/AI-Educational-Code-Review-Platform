import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import CodeEditor from '../components/CodeEditor';
import AnalysisReport from '../components/AnalysisReport';
import ReviewHistory from '../components/ReviewHistory';
import '../App.css';
import './StudentApp.css';

export default function StudentApp() {
  const navigate = useNavigate();

  // Read session identity
  const studentId = sessionStorage.getItem('studentId') || 'anonymous';
  const studentName = sessionStorage.getItem('studentName') || 'Student';
  const apiUrlStored = sessionStorage.getItem('apiUrl') || 'https://krysten-chromous-gaylord.ngrok-free.dev';

  // Guard: redirect if no role
  useEffect(() => {
    if (!sessionStorage.getItem('role')) navigate('/');
  }, [navigate]);

  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [apiUrl, setApiUrl] = useState(apiUrlStored);
  const [statusMessage, setStatusMessage] = useState(null);

  // Editor state
  const [code, setCode] = useState('');

  // Review state (live review)
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewResult, setReviewResult] = useState(null);
  const [reviewError, setReviewError] = useState(null);
  const [reviewTime, setReviewTime] = useState(null);
  const [reviewLines, setReviewLines] = useState(null);
  const [grade, setGrade] = useState(null);
  const [criticalCount, setCriticalCount] = useState(null);
  const [styleCount, setStyleCount] = useState(null);

  // History state
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeHistoryId, setActiveHistoryId] = useState(null);
  const [historyAnnotations, setHistoryAnnotations] = useState(null);
  const [isHistoryView, setIsHistoryView] = useState(false);

  // Abort controller for cancelling reviews
  const controllerRef = useRef(null);

  // Fetch review history
  const fetchHistory = useCallback(async () => {
    if (!apiUrl || !isConnected) return;
    setHistoryLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/reviews/${studentId}`, {
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });
      const data = await res.json();
      setHistory(data.reviews || []);
    } catch (_) {}
    finally { setHistoryLoading(false); }
  }, [apiUrl, isConnected, studentId]);

  // Register student and load history when connected
  useEffect(() => {
    if (!isConnected || !apiUrl) return;

    // Auto-register
    fetch(`${apiUrl}/api/student/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
      body: JSON.stringify({ student_id: studentId, name: studentName }),
    }).catch(() => {});

    fetchHistory();
  }, [isConnected, apiUrl, studentId, studentName, fetchHistory]);

  function handleConnectionChange(connected, url) {
    setIsConnected(connected);
    setApiUrl(url);
  }

  async function runReview() {
    const trimmed = code.trim();
    if (!trimmed || !isConnected) return;

    // Reset to live review mode
    setReviewResult(null);
    setReviewError(null);
    setReviewTime(null);
    setReviewLines(null);
    setGrade(null);
    setCriticalCount(null);
    setStyleCount(null);
    setStatusMessage(null);
    setIsReviewing(true);
    setIsHistoryView(false);
    setActiveHistoryId(null);
    setHistoryAnnotations(null);

    try {
      controllerRef.current = new AbortController();
      const timeout = setTimeout(() => controllerRef.current.abort(), 600000);

      const res = await fetch(`${apiUrl}/api/review`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
        },
        body: JSON.stringify({ code: trimmed, student_id: studentId }),
        signal: controllerRef.current.signal,
      });
      clearTimeout(timeout);

      const data = await res.json();

      if (data.error) {
        setReviewError(data.error);
      } else {
        setReviewResult(data.review);
        setReviewTime(data.time);
        setReviewLines(data.lines);
        setGrade(data.grade);
        setCriticalCount(data.critical_count);
        setStyleCount(data.style_count);
        // Refresh history after new review
        fetchHistory();
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setReviewError('Review stopped by user.');
      } else {
        setReviewError(`Network error: ${err.message}. Is the API still running?`);
      }
    } finally {
      controllerRef.current = null;
      setIsReviewing(false);
    }
  }

  function stopReview() {
    if (controllerRef.current) controllerRef.current.abort();
  }

  async function handleSelectHistoryReview(r) {
    setActiveHistoryId(r.id);
    setIsHistoryView(true);
    setIsReviewing(false);
    setReviewError(null);
    setReviewResult(r.review_result);
    setReviewTime(r.review_time_sec);
    setReviewLines(r.line_count);
    setGrade(r.grade);
    setCriticalCount(r.critical_count);
    setStyleCount(r.style_count);
    setCode(r.code_snippet);

    // Fetch annotations for this review
    try {
      const res = await fetch(`${apiUrl}/api/review/${r.id}/annotations`, {
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });
      const data = await res.json();
      setHistoryAnnotations(data.annotations || []);
    } catch (_) {
      setHistoryAnnotations([]);
    }
  }

  function handleNewReview() {
    setIsHistoryView(false);
    setActiveHistoryId(null);
    setReviewResult(null);
    setReviewError(null);
    setReviewTime(null);
    setReviewLines(null);
    setGrade(null);
    setCriticalCount(null);
    setStyleCount(null);
    setHistoryAnnotations(null);
    setCode('');
  }

  return (
    <div className="studentApp">
      <Header
        onConnectionChange={handleConnectionChange}
        statusMessage={statusMessage}
        setStatusMessage={setStatusMessage}
        role="student"
        userName={studentName}
      />
      <div className="studentWorkspace">
        <ReviewHistory
          reviews={history}
          activeReviewId={activeHistoryId}
          onSelectReview={handleSelectHistoryReview}
          onNewReview={handleNewReview}
          loading={historyLoading}
        />
        <main className="workspace">
          <CodeEditor
            code={code}
            setCode={setCode}
            isConnected={isConnected}
            isReviewing={isReviewing}
            onRunReview={runReview}
            onStopReview={stopReview}
            isHistoryView={isHistoryView}
          />
          <AnalysisReport
            isReviewing={isReviewing}
            reviewResult={reviewResult}
            reviewError={reviewError}
            reviewTime={reviewTime}
            reviewLines={reviewLines}
            statusMessage={statusMessage}
            grade={grade}
            criticalCount={criticalCount}
            styleCount={styleCount}
            annotations={historyAnnotations}
            isHistoryView={isHistoryView}
          />
        </main>
      </div>
    </div>
  );
}
