import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AreaChart, Area, PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { BarChart3, Users, FileText, RefreshCw, AlertCircle, AlertTriangle, CheckCircle, ChevronDown, ChevronUp, Clock, ShieldAlert, GraduationCap, ClipboardList, TrendingUp, Save, MessageSquare } from 'lucide-react';
import Header from '../components/Header';
import DashboardCard from '../components/DashboardCard';
import './StaffDashboard.css';

const STAFF_PASSCODE = 'mentor2026';

function riskBadge(level) {
  if (level === 'high')   return <span className="riskBadge riskHigh" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><ShieldAlert size={14} /> High</span>;
  if (level === 'medium') return <span className="riskBadge riskMid" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> Medium</span>;
  return                         <span className="riskBadge riskLow" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> Low</span>;
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
}

function formatFull(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) +
    ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

const PIE_COLORS = ['#ef4444', '#f59e0b', '#10b981'];
const GRADE_COLORS = ['#10b981', '#4361ee', '#f59e0b', '#f97316', '#ef4444'];

export default function StaffDashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('analytics');
  const [apiUrl, setApiUrl] = useState(sessionStorage.getItem('apiUrl') || '');

  // Guard
  useEffect(() => {
    if (sessionStorage.getItem('role') !== 'staff') navigate('/');
  }, [navigate]);

  // Analytics data
  const [analytics, setAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Students data
  const [students, setStudents] = useState([]);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [expandedStudent, setExpandedStudent] = useState(null);
  const [studentReviews, setStudentReviews] = useState({});
  const [sortBy, setSortBy] = useState('last_active');
  const [sortDir, setSortDir] = useState('desc');

  // Review feed
  const [reviews, setReviews] = useState([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [expandedReview, setExpandedReview] = useState(null);
  const [annotationInputs, setAnnotationInputs] = useState({});
  const [annotationLoading, setAnnotationLoading] = useState({});

  const fetchAnalytics = useCallback(async () => {
    if (!apiUrl) return;
    setAnalyticsLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/dashboard/analytics`, {
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });
      const data = await res.json();
      setAnalytics(data);
    } catch (_) {}
    finally { setAnalyticsLoading(false); }
  }, [apiUrl]);

  const fetchStudents = useCallback(async () => {
    if (!apiUrl) return;
    setStudentsLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/dashboard/students`, {
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });
      const data = await res.json();
      setStudents(data.students || []);
    } catch (_) {}
    finally { setStudentsLoading(false); }
  }, [apiUrl]);

  const fetchReviews = useCallback(async () => {
    if (!apiUrl) return;
    setReviewsLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/reviews?limit=30`, {
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });
      const data = await res.json();
      setReviews(data.reviews || []);
    } catch (_) {}
    finally { setReviewsLoading(false); }
  }, [apiUrl]);

  // Load data for active tab
  useEffect(() => {
    if (!apiUrl) return;
    if (activeTab === 'analytics') fetchAnalytics();
    if (activeTab === 'students') fetchStudents();
    if (activeTab === 'feed') fetchReviews();
  }, [activeTab, apiUrl, fetchAnalytics, fetchStudents, fetchReviews]);

  // Handle API connection
  function handleConnectionChange(connected, url) {
    if (connected) setApiUrl(url);
  }

  // Expand student row
  async function toggleStudent(studentId) {
    if (expandedStudent === studentId) { setExpandedStudent(null); return; }
    setExpandedStudent(studentId);
    if (!studentReviews[studentId] && apiUrl) {
      try {
        const res = await fetch(`${apiUrl}/api/reviews/${studentId}`, {
          headers: { 'ngrok-skip-browser-warning': 'true' },
        });
        const data = await res.json();
        setStudentReviews(prev => ({ ...prev, [studentId]: data.reviews || [] }));
      } catch (_) {}
    }
  }

  // Sort students
  function handleSort(col) {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('desc'); }
  }

  const sortedStudents = [...students].sort((a, b) => {
    let av = a[sortBy], bv = b[sortBy];
    if (typeof av === 'string') av = av.toLowerCase(), bv = (bv || '').toLowerCase();
    if (sortDir === 'asc') return av > bv ? 1 : -1;
    return av < bv ? 1 : -1;
  });

  // Annotation submit
  async function submitAnnotation(reviewId) {
    const comment = annotationInputs[reviewId]?.trim();
    if (!comment || !apiUrl) return;
    setAnnotationLoading(prev => ({ ...prev, [reviewId]: true }));
    try {
      await fetch(`${apiUrl}/api/review/${reviewId}/annotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        body: JSON.stringify({ comment, staff_id: 'Dr. Staff' }),
      });
      setAnnotationInputs(prev => ({ ...prev, [reviewId]: '' }));
      // Refresh reviews so annotation count updates
      fetchReviews();
    } catch (_) {}
    finally { setAnnotationLoading(prev => ({ ...prev, [reviewId]: false })); }
  }

  // Severity pie data
  const severityData = analytics ? [
    { name: 'Critical Issues', value: analytics.severity_distribution?.critical || 0 },
    { name: 'Style Issues', value: analytics.severity_distribution?.style || 0 },
    { name: 'Clean Submissions', value: analytics.severity_distribution?.clean || 0 },
  ] : [];

  return (
    <div className="staffApp">
      <Header
        onConnectionChange={handleConnectionChange}
        statusMessage={null}
        setStatusMessage={() => {}}
        role="staff"
      />

      <div className="dashboardLayout">
        {/* Sidebar nav */}
        <nav className="dashNav">
          <button
            id="tab-analytics"
            className={`dashNavBtn ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <BarChart3 size={18} /><span>Analytics</span>
          </button>
          <button
            id="tab-students"
            className={`dashNavBtn ${activeTab === 'students' ? 'active' : ''}`}
            onClick={() => setActiveTab('students')}
          >
            <Users size={18} /><span>Students</span>
          </button>
          <button
            id="tab-feed"
            className={`dashNavBtn ${activeTab === 'feed' ? 'active' : ''}`}
            onClick={() => setActiveTab('feed')}
          >
            <ClipboardList size={18} /><span>Review Feed</span>
          </button>
        </nav>

        {/* Main content */}
        <main className="dashMain">

          {/* ========== ANALYTICS TAB ========== */}
          {activeTab === 'analytics' && (
            <div className="dashContent" id="panel-analytics">
              <div className="dashContentHeader">
                <h2>Class Overview</h2>
                <button className="refreshBtn" onClick={fetchAnalytics} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><RefreshCw size={14} /> Refresh</button>
              </div>

              {analyticsLoading ? (
                <div className="dashLoading"><div className="spinner" /><span>Loading analytics...</span></div>
              ) : !analytics ? (
                <div className="dashEmpty">
                  <p>Connect to the API to load analytics.</p>
                  {!apiUrl && <p className="dashEmptyHint">Use the ⚙ settings in the header first.</p>}
                </div>
              ) : (
                <>
                  {/* Summary cards */}
                  <div className="cardGrid">
                    <DashboardCard
                      id="card-total-reviews"
                      icon={<FileText size={24} color="rgba(255,255,255,0.8)" />}
                      label="Total Reviews"
                      value={analytics.total_reviews}
                      sub="All time submissions"
                      gradient="var(--gradient-card-blue)"
                    />
                    <DashboardCard
                      id="card-active-students"
                      icon={<Users size={24} color="rgba(255,255,255,0.8)" />}
                      label="Active Students"
                      value={analytics.active_students}
                      sub="Unique submitters"
                      gradient="var(--gradient-card-green)"
                    />
                    <DashboardCard
                      id="card-critical-issues"
                      icon={<AlertCircle size={24} color="rgba(255,255,255,0.8)" />}
                      label="Critical Issues Flagged"
                      value={analytics.total_critical_issues}
                      sub="Security & logic bugs"
                      gradient="var(--gradient-card-red)"
                    />
                    <DashboardCard
                      id="card-avg-grade"
                      icon={<TrendingUp size={24} color="rgba(255,255,255,0.8)" />}
                      label="Class Average Grade"
                      value={analytics.avg_grade ? `${analytics.avg_grade}/100` : '—'}
                      sub="Auto-calculated score"
                      gradient="var(--gradient-card-orange)"
                    />
                  </div>

                  {/* Charts row */}
                  <div className="chartsGrid">
                    {/* Reviews per day */}
                    <div className="chartCard" id="chart-reviews-per-day">
                      <h3 className="chartTitle">Reviews per Day (Last 30 Days)</h3>
                      {analytics.reviews_per_day?.length > 0 ? (
                        <ResponsiveContainer width="100%" height={200}>
                          <AreaChart data={analytics.reviews_per_day}>
                            <defs>
                              <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#4361ee" stopOpacity={0.3}/>
                                <stop offset="95%" stopColor="#4361ee" stopOpacity={0}/>
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e6ef" />
                            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3b8' }} />
                            <YAxis tick={{ fontSize: 10, fill: '#9ca3b8' }} allowDecimals={false} />
                            <Tooltip contentStyle={{ fontSize: '0.8rem', borderRadius: '8px' }} />
                            <Area type="monotone" dataKey="count" stroke="#4361ee" strokeWidth={2} fill="url(#blueGrad)" name="Reviews" />
                          </AreaChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="chartEmpty">No data yet</div>
                      )}
                    </div>

                    {/* Severity distribution */}
                    <div className="chartCard" id="chart-severity">
                      <h3 className="chartTitle">Severity Distribution</h3>
                      {severityData.some(d => d.value > 0) ? (
                        <ResponsiveContainer width="100%" height={200}>
                          <PieChart>
                            <Pie data={severityData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                              {severityData.map((_, i) => (
                                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip contentStyle={{ fontSize: '0.8rem', borderRadius: '8px' }} />
                            <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: '0.78rem' }} />
                          </PieChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="chartEmpty">No data yet</div>
                      )}
                    </div>

                    {/* Grade distribution */}
                    <div className="chartCard chartCardWide" id="chart-grades">
                      <h3 className="chartTitle">Grade Distribution</h3>
                      {analytics.grade_distribution?.length > 0 ? (
                        <ResponsiveContainer width="100%" height={200}>
                          <BarChart data={analytics.grade_distribution} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e6ef" horizontal={false} />
                            <XAxis type="number" tick={{ fontSize: 10, fill: '#9ca3b8' }} allowDecimals={false} />
                            <YAxis type="category" dataKey="bracket" tick={{ fontSize: 10, fill: '#9ca3b8' }} width={80} />
                            <Tooltip contentStyle={{ fontSize: '0.8rem', borderRadius: '8px' }} />
                            <Bar dataKey="count" name="Students" radius={[0,4,4,0]}>
                              {analytics.grade_distribution.map((_, i) => (
                                <Cell key={i} fill={GRADE_COLORS[i % GRADE_COLORS.length]} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      ) : (
                        <div className="chartEmpty">No data yet</div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ========== STUDENTS TAB ========== */}
          {activeTab === 'students' && (
            <div className="dashContent" id="panel-students">
              <div className="dashContentHeader">
                <h2>Student Management</h2>
                <button className="refreshBtn" onClick={fetchStudents} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><RefreshCw size={14} /> Refresh</button>
              </div>

              {studentsLoading ? (
                <div className="dashLoading"><div className="spinner" /><span>Loading students...</span></div>
              ) : students.length === 0 ? (
                <div className="dashEmpty"><p>No student data yet. Students must connect and submit a review first.</p></div>
              ) : (
                <div className="tableWrap">
                  <table className="studentTable" id="table-students">
                    <thead>
                      <tr>
                        {[
                          { key: 'name', label: 'Name' },
                          { key: 'student_id', label: 'ID' },
                          { key: 'total_reviews', label: 'Reviews' },
                          { key: 'total_critical', label: 'Critical' },
                          { key: 'total_style', label: 'Style' },
                          { key: 'avg_grade', label: 'Avg Grade' },
                          { key: 'last_active', label: 'Last Active' },
                          { key: 'risk_level', label: 'Risk' },
                        ].map(col => (
                          <th key={col.key} onClick={() => handleSort(col.key)} className={sortBy === col.key ? 'sorted' : ''}>
                            {col.label} {sortBy === col.key ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {sortedStudents.map(s => (
                        <>
                          <tr
                            key={s.student_id}
                            className={`studentRow ${expandedStudent === s.student_id ? 'expanded' : ''}`}
                            onClick={() => toggleStudent(s.student_id)}
                            id={`student-row-${s.student_id}`}
                          >
                            <td className="tdName">{s.name}</td>
                            <td className="tdMono">{s.student_id}</td>
                            <td>{s.total_reviews}</td>
                            <td className={s.total_critical > 0 ? 'tdCritical' : ''}>{s.total_critical}</td>
                            <td className={s.total_style > 0 ? 'tdStyle' : ''}>{s.total_style}</td>
                            <td className="tdMono">{s.avg_grade}/100</td>
                            <td>{formatDate(s.last_active)}</td>
                            <td>{riskBadge(s.risk_level)}</td>
                          </tr>
                          {expandedStudent === s.student_id && (
                            <tr key={`${s.student_id}-expand`} className="expandRow">
                              <td colSpan={8}>
                                <div className="expandContent">
                                  <strong>Review History for {s.name}</strong>
                                  {!studentReviews[s.student_id] ? (
                                    <div className="miniLoading"><div className="miniSpinner" /> Loading...</div>
                                  ) : studentReviews[s.student_id].length === 0 ? (
                                    <p className="noReviews">No reviews found.</p>
                                  ) : (
                                    <div className="miniReviewList">
                                      {studentReviews[s.student_id].map(r => (
                                        <div key={r.id} className="miniReviewCard">
                                          <div className="miniReviewTop">
                                            <span className="miniDate">{formatFull(r.created_at)}</span>
                                            <span className="miniGrade">{r.grade}/100</span>
                                            <span>{r.line_count} lines</span>
                                            <span>{r.critical_count} critical</span>
                                            <span>{r.style_count} style</span>
                                          </div>
                                          <div className="miniCodePreview">{r.code_snippet.split('\n').slice(0,2).join('\n')}</div>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ========== REVIEW FEED TAB ========== */}
          {activeTab === 'feed' && (
            <div className="dashContent" id="panel-feed">
              <div className="dashContentHeader">
                <h2>Review Feed</h2>
                <button className="refreshBtn" onClick={fetchReviews} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><RefreshCw size={14} /> Refresh</button>
              </div>

              {reviewsLoading ? (
                <div className="dashLoading"><div className="spinner" /><span>Loading reviews...</span></div>
              ) : reviews.length === 0 ? (
                <div className="dashEmpty"><p>No reviews yet.</p></div>
              ) : (
                <div className="feedList" id="feed-list">
                  {reviews.map(r => (
                    <div key={r.id} className={`feedCard ${expandedReview === r.id ? 'feedExpanded' : ''}`} id={`feed-review-${r.id}`}>
                      {/* Card header */}
                      <div className="feedCardHeader" onClick={() => setExpandedReview(expandedReview === r.id ? null : r.id)}>
                        <div className="feedCardLeft">
                          <span className="feedStudentName">{r.student_name || r.student_id}</span>
                          <span className="feedStudentId">{r.student_id}</span>
                        </div>
                        <div className="feedCardMeta">
                          <span className={`feedGrade ${r.grade >= 80 ? 'grade-good' : r.grade >= 60 ? 'grade-mid' : 'grade-low'}`}>
                            {r.grade}/100
                          </span>
                          {r.critical_count > 0 && <span className="feedSev sevCrit"><AlertCircle size={14} className="mr-1"/>{r.critical_count} critical</span>}
                          {r.style_count > 0 && <span className="feedSev sevStyle"><AlertTriangle size={14} className="mr-1"/>{r.style_count} style</span>}
                          <span className="feedDate">{formatFull(r.created_at)}</span>
                          <span className="feedChevron">{expandedReview === r.id ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}</span>
                        </div>
                      </div>

                      {/* Code preview (always visible) */}
                      <div className="feedCodePreview">
                        {r.code_snippet.split('\n').slice(0, 2).join('\n')}
                      </div>

                      {/* Expanded view */}
                      {expandedReview === r.id && (
                        <div className="feedExpandBody">
                          {/* Full review */}
                          <div className="feedReviewText">{r.review_result}</div>

                          {/* Annotation input */}
                          <div className="annotationInput" id={`annotation-form-${r.id}`}>
                            <h4>Add Instructor Feedback</h4>
                            <textarea
                              id={`annotation-textarea-${r.id}`}
                              className="annotationTextarea"
                              placeholder="Write your feedback for this student here..."
                              value={annotationInputs[r.id] || ''}
                              onChange={e => setAnnotationInputs(prev => ({ ...prev, [r.id]: e.target.value }))}
                              rows={3}
                            />
                            <button
                              id={`btn-annotate-${r.id}`}
                              className="annotateSubmitBtn"
                              onClick={() => submitAnnotation(r.id)}
                              disabled={annotationLoading[r.id] || !annotationInputs[r.id]?.trim()}
                              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                            >
                              <Save size={16} />
                              {annotationLoading[r.id] ? 'Saving...' : 'Save Feedback'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
