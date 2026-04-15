import { useRef } from 'react';
import './CodeEditor.css';

export default function CodeEditor({
  code,
  setCode,
  isConnected,
  isReviewing,
  onRunReview,
  onStopReview,
}) {
  const textareaRef = useRef(null);
  const gutterRef = useRef(null);

  const linesArray = code ? code.split('\n') : [''];
  const linesCount = linesArray.length;
  const chars = code ? code.length : 0;

  const overLimit = linesCount > 150;
  const nearLimit = linesCount > 120;

  function handleScroll() {
    if (gutterRef.current && textareaRef.current) {
      gutterRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  }

  function handleTab(e) {
    if (e.key === 'Tab') {
      e.preventDefault();
      const ta = textareaRef.current;
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const newVal = code.substring(0, start) + '    ' + code.substring(end);
      setCode(newVal);
      requestAnimationFrame(() => {
        ta.selectionStart = ta.selectionEnd = start + 4;
      });
    }
  }

  return (
    <div className="editorPanel">
      {/* Panel Header */}
      <div className="panelHeader">
        <h2 className="panelTitle">
          <span className="icon">✏️</span> Code Input
        </h2>
        <span className="badge badgeMuted">{linesCount} {linesCount === 1 ? 'line' : 'lines'}</span>
      </div>

      {/* Textarea Area with Gutter */}
      <div className="panelBody">
        <div className="gutter" ref={gutterRef}>
          {linesArray.map((_, i) => (
            <div key={i} className="lineNumber">{i + 1}</div>
          ))}
        </div>
        <textarea
          ref={textareaRef}
          className="codeTextarea"
          placeholder={`Paste your Python code here...\n\nExample:\ndef ProcessData(InputList):\n    import os\n    for item in InputList:\n        if item % 2 == 0:\n            InputList.remove(item)\n    return InputList`}
          spellCheck="false"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={handleTab}
          onScroll={handleScroll}
        />
      </div>

      {/* Action Bar */}
      <div className="actionBar">
        <div className="actionMeta">
          <span>{chars} chars</span>
          <span>·</span>
          <span className={overLimit ? 'limitWarning' : nearLimit ? 'limitCaution' : ''}>
            {overLimit ? `⚠️ Over limit (${lines}/150)` : `Max 150 lines`}
          </span>
        </div>
        <div className="actionButtons">
          {isReviewing && (
            <button className="stopBtn" onClick={onStopReview}>
              ⏹ Stop
            </button>
          )}
          <button
            className="reviewBtn"
            disabled={!isConnected || isReviewing || !code.trim()}
            onClick={onRunReview}
          >
            {isReviewing ? '⏳ Reviewing...' : '🚀 Run Review'}
          </button>
        </div>
      </div>
    </div>
  );
}
