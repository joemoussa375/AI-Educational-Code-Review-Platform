import { useState } from 'react';
import { History, AlertCircle, AlertTriangle, CheckCircle, ChevronLeft, Plus } from 'lucide-react';
import './ReviewHistory.css';

function gradeColor(grade) {
  if (grade >= 80) return 'grade-good';
  if (grade >= 60) return 'grade-mid';
  return 'grade-low';
}

function severityBadge(critical, style) {
  if (critical > 0)  return { cls: 'sev-critical', icon: <AlertCircle size={14} />, label: 'Critical' };
  if (style > 0)     return { cls: 'sev-style',    icon: <AlertTriangle size={14} />, label: 'Style' };
  return               { cls: 'sev-clean',         icon: <CheckCircle size={14} />, label: 'Clean'  };
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) +
    ' · ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

export default function ReviewHistory({ reviews, activeReviewId, onSelectReview, onNewReview, loading }) {
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState('');

  const filtered = search
    ? reviews.filter(r =>
        formatDate(r.created_at).toLowerCase().includes(search.toLowerCase()) ||
        String(r.grade).includes(search)
      )
    : reviews;

  if (collapsed) {
    return (
      <aside className="historyPanel collapsed">
        <button
          id="btn-history-expand"
          className="collapseBtn"
          onClick={() => setCollapsed(false)}
          title="Show Review History"
        >
          <History size={18} />
          <span className="collapseCount">{reviews.length}</span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="historyPanel" id="history-panel">
      <div className="historyHeader">
        <div className="historyTitle">
          <History size={18} />
          <span>Review History</span>
          <span className="historyCount">{reviews.length}</span>
        </div>
        <button
          id="btn-history-collapse"
          className="collapseBtn inline"
          onClick={() => setCollapsed(true)}
          title="Collapse"
        >
          <ChevronLeft size={16} />
        </button>
      </div>

      <div className="historyActions">
        <button id="btn-new-review" className="newReviewBtn" onClick={onNewReview} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
          <Plus size={16} /> New Review
        </button>
        <input
          id="input-history-search"
          className="historySearch"
          type="text"
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="historyList">
        {loading && (
          <div className="historyLoading">
            <div className="miniSpinner" />
            <span>Loading history...</span>
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="historyEmpty">
            {reviews.length === 0
              ? 'No reviews yet.\nSubmit your first code!'
              : 'No results for your search.'}
          </div>
        )}

        {!loading && filtered.map(r => {
          const sev = severityBadge(r.critical_count, r.style_count);
          const isActive = r.id === activeReviewId;
          return (
            <button
              key={r.id}
              id={`history-item-${r.id}`}
              className={`historyItem ${isActive ? 'active' : ''}`}
              onClick={() => onSelectReview(r)}
            >
              <div className="historyItemTop">
                <span className={`sevBadge ${sev.cls}`} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {sev.icon} {sev.label}
                </span>
                <span className={`gradeBadge ${gradeColor(r.grade)}`}>{r.grade}/100</span>
              </div>
              <div className="historyItemMeta">
                <span>{r.line_count} lines</span>
                <span>{r.review_time_sec}s</span>
              </div>
              <div className="historyItemDate">{formatDate(r.created_at)}</div>
              <div className="historyCodePreview">
                {r.code_snippet.split('\n').slice(0, 2).join('\n')}
              </div>
              {r.annotations && r.annotations.length > 0 && (
                <div className="annotationBadge">
                  {r.annotations.length} instructor note{r.annotations.length > 1 ? 's' : ''}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
