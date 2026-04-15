import { useState, useEffect } from 'react';
import { ChevronDown, Copy, Check, Loader2, XCircle, Search, Clock, AlignLeft, Bot, MessageSquare, AlertCircle, AlertTriangle, CheckCircle, Terminal } from 'lucide-react';
import './AnalysisReport.css';

// Helper: strip common leading whitespace
function dedentCode(code) {
  code = code.replace(/^\s*\n/g, '').replace(/\n\s*$/g, '');
  const lines = code.split('\n');
  const indents = lines
    .filter((l) => l.trim().length > 0)
    .map((l) => {
      const match = l.match(/^([\s\t]*)/);
      return match ? match[1].length : 0;
    });
  const min = indents.length > 0 ? Math.min(...indents) : 0;
  if (min === 0) return code;
  return lines.map((l) => l.slice(min)).join('\n');
}

// Helper: escape HTML
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Classify section title for color
function classifySection(title) {
  const lower = title.toLowerCase();
  if (lower.includes('critical') || lower.includes('issue') || lower.includes('bug')) return 'critical';
  if (lower.includes('style') || lower.includes('pep') || lower.includes('naming')) return 'style';
  if (lower.includes('refactor') || lower.includes('solution') || lower.includes('improved')) return 'refactored';
  return '';
}

// Removed sectionIcon as emojis are no longer used

// Grade ring color
function gradeClass(grade) {
  if (grade >= 80) return 'grade-good';
  if (grade >= 60) return 'grade-mid';
  return 'grade-low';
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) +
    ' at ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function CollapsibleSection({ title, content, cssClass }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="resultSection">
      <div className={`sectionHeader ${cssClass}`} onClick={() => setOpen(!open)}>
        <span>{title}</span>
        <span className={`chevron ${open ? 'open' : ''}`}><ChevronDown size={14} /></span>
      </div>
      {open && (
        <div className="sectionBody" dangerouslySetInnerHTML={{ __html: escapeHtml(content) }} />
      )}
    </div>
  );
}

function CodeBlockDisplay({ code }) {
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(true);

  function handleCopy(e) {
    e.stopPropagation();
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="resultSection">
      <div className="sectionHeader refactored" onClick={() => setOpen(!open)}>
        <span>Refactored Solution</span>
        <span className={`chevron ${open ? 'open' : ''}`}><ChevronDown size={14} /></span>
      </div>
      {open && (
        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
          <div className="codeBlock">
            <button className="copyBtn" onClick={handleCopy} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              {copied ? <><Check size={14} /> Copied!</> : <><Copy size={14} /> Copy</>}
            </button>
            {code}
          </div>
        </div>
      )}
    </div>
  );
}

function AnnotationsSection({ annotations }) {
  const [open, setOpen] = useState(true);
  if (!annotations || annotations.length === 0) return null;
  return (
    <div className="resultSection annotationsSection">
      <div className="sectionHeader annotation" onClick={() => setOpen(!open)}>
        <span>Instructor Feedback</span>
        <span className="annotationCount">{annotations.length}</span>
        <span className={`chevron ${open ? 'open' : ''}`}><ChevronDown size={14} /></span>
      </div>
      {open && (
        <div className="annotationsBody">
          {annotations.map((a, i) => (
            <div key={i} className="annotationItem">
              <div className="annotationMeta">
                <span className="annotationStaff">{a.staff_id}</span>
                <span className="annotationDate">{formatDate(a.created_at)}</span>
              </div>
              <p className="annotationComment">{a.comment}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AnalysisReport({
  isReviewing,
  reviewResult,
  reviewError,
  reviewTime,
  reviewLines,
  statusMessage,
  grade,
  criticalCount,
  styleCount,
  annotations,
  isHistoryView,
}) {
  // Loading step animation
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (!isReviewing) {
      setActiveStep(0);
      return;
    }
    setActiveStep(1);
    const t1 = setTimeout(() => setActiveStep(2), 3000);
    const t2 = setTimeout(() => setActiveStep(3), 8000);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [isReviewing]);

  // Parse the review text into sections
  function parseResult(text) {
    const codeMatch = text.match(/```(?:python)?\s*([\s\S]*?)```/);
    let mainText = text;
    let refactoredCode = null;

    if (codeMatch) {
      refactoredCode = dedentCode(codeMatch[1]);
      mainText = text.replace(codeMatch[0], '').trim();
    }

    const sectionPatterns = [
      /\*\*(\d+\.\s*[^*]+)\*\*/g,
      /^(\d+\.\s*(?:Critical Issues|Style Analysis|Refactored Solution)[^\n]*):?\s*$/gm,
      /^(Critical Issues|Style Analysis|Refactored Solution)[:\s]*$/gm,
    ];

    let sections = null;
    for (const pattern of sectionPatterns) {
      const parts = mainText.split(pattern);
      if (parts.length > 1) {
        sections = parts;
        break;
      }
    }

    const parsed = [];
    if (sections && sections.length > 1) {
      for (let i = 1; i < sections.length; i += 2) {
        const title = sections[i].trim().replace(/[:*]/g, '').trim();
        const content = (sections[i + 1] || '').trim();
        if (!content && !title) continue;
        parsed.push({ title, content, cssClass: classifySection(title) });
      }
    } else {
      parsed.push({ title: 'Analysis', content: mainText, cssClass: '' });
    }

    return { parsed, refactoredCode };
  }

  // Grade badge
  const gradeBadge = grade != null && (
    <div className={`gradeBadgeHeader ${gradeClass(grade)}`} title="Auto-calculated code quality score">
      <span className="gradeValue">{grade}</span>
      <span className="gradeLabel">/100</span>
    </div>
  );

  // --- Render States ---

  // Loading state
  if (isReviewing) {
    const steps = [
      '1. Running Static Analysis (Pylint)',
      '2. Retrieving Style Guidelines (RAG)',
      '3. Generating AI Review (Qwen2.5-Coder)',
    ];
    return (
      <div className="reportPanel">
        <div className="panelHeader">
          <h2 className="panelTitle">
            <Terminal size={20} /> Analysis Report
          </h2>
        </div>
        <div className="panelBody">
          <div className="loadingWrap">
            <div className="spinner" />
            <div className="loadingSteps">
              {steps.map((step, i) => {
                const idx = i + 1;
                let cls = '';
                if (idx < activeStep) cls = 'done';
                else if (idx === activeStep) cls = 'active';
                let icon = <Loader2 size={16} />;
                if (idx < activeStep) icon = <CheckCircle size={16} />;
                else if (idx === activeStep) icon = <Loader2 size={16} />;
                return (
                  <div key={i} className={`loadingStep ${cls}`}>
                    <span className="stepIcon">{icon}</span>
                    <span>{step}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (reviewError) {
    return (
      <div className="reportPanel">
        <div className="panelHeader">
          <h2 className="panelTitle">
            <Terminal size={20} /> Analysis Report
          </h2>
        </div>
        <div className="panelBody">
          <div className="resultContent">
            <div className="errorMsg">
              <XCircle size={20} />
              <span>{reviewError}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Result state
  if (reviewResult) {
    const { parsed, refactoredCode } = parseResult(reviewResult);
    return (
      <div className="reportPanel">
        <div className="panelHeader">
          <h2 className="panelTitle">
            <Terminal size={20} /> {isHistoryView ? ' Past Review' : ' Analysis Report'}
          </h2>
          <div className="panelHeaderRight">
            {reviewTime && <span className="badge badgeBlue" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Clock size={12} /> {reviewTime}s</span>}
            {gradeBadge}
          </div>
        </div>
        <div className="panelBody">
          <div className="resultContent">
            {/* TA Annotations first (most important) */}
            <AnnotationsSection annotations={annotations} />

            {parsed.map((s, i) => (
              <CollapsibleSection key={i} title={s.title} content={s.content} cssClass={s.cssClass} />
            ))}
            {refactoredCode && <CodeBlockDisplay code={refactoredCode} />}
            <div className="reviewMeta">
              <span className="metaBadge" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Clock size={14} /> {reviewTime}s</span>
              <span className="metaBadge" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><AlignLeft size={14} /> {reviewLines} lines</span>
              {criticalCount != null && <span className="metaBadge" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><AlertCircle size={14} /> {criticalCount} critical</span>}
              {styleCount != null && <span className="metaBadge" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><AlertTriangle size={14} /> {styleCount} style</span>}
              <span className="metaBadge" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Bot size={14} /> Qwen2.5-Coder-7B (4-bit)</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Placeholder state (default)
  return (
    <div className="reportPanel">
      <div className="panelHeader">
        <h2 className="panelTitle">
          Analysis Report
        </h2>
      </div>
      <div className="panelBody">
        <div className="placeholder">
          <Search size={48} className="placeholderIcon" style={{ marginBottom: '16px', color: 'var(--text-muted)', opacity: 0.5 }} />
          {statusMessage ? (
            <p className={`statusMsg ${statusMessage.type}`}>{statusMessage.text}</p>
          ) : (
            <p className="placeholderText">
              Connect to the API and submit your code
              <br />
              to see the AI review here.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
