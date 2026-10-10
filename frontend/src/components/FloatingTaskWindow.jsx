import React from 'react';

export default function FloatingTaskWindow({
  task,
  transform,
  isGrabbed = false,
  isSelected = false,
  onDismiss
}) {
  const { type, slot, instanceId } = task;

  const customStyle = transform
    ? {
        position: 'fixed',
        left: `${transform.x}px`,
        top: `${transform.y}px`,
        right: 'auto',
        bottom: 'auto',
        transform: `scale(${transform.scale || 1.0})`,
        transformOrigin: 'center center',
        zIndex: isGrabbed ? 100 : 25
      }
    : {};

  return (
    <div
      className={`floating-task-hud slot-${slot} ${isGrabbed ? 'grabbed' : ''} ${isSelected ? 'selected' : ''}`}
      style={customStyle}
      data-task-id={instanceId}
      data-task-type={type}
    >
      {/* Corner holographic tick accents */}
      <div className="hud-corner top-left" />
      <div className="hud-corner bottom-right" />

      {/* Dismiss trigger */}
      <button
        className="hud-dismiss-btn"
        onClick={(e) => {
          e.stopPropagation();
          onDismiss(instanceId);
        }}
        aria-label="Dismiss task"
        title="Dismiss"
      >
        <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
          <path d="M1 1L7 7M7 1L1 7" stroke="rgba(216, 75, 16, 0.7)" strokeWidth="1.2" strokeLinecap="round"/>
        </svg>
      </button>

      {/* Content depending on task type - Minimal essential output only */}
      <div className="hud-content">
        {type === 'weather' && (
          <div className="task-weather-visual">
            <div className="weather-glyph">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="4.5" stroke="rgba(216, 75, 16, 0.95)" strokeWidth="1.2" />
                <path d="M12 3V5M12 19V21M3 12H5M19 12H21" stroke="rgba(216, 75, 16, 0.5)" strokeWidth="1" strokeLinecap="round" />
                <path d="M5.6 5.6L7 7M17 17L18.4 18.4M5.6 18.4L7 17M17 7L18.4 5.6" stroke="rgba(216, 75, 16, 0.35)" strokeWidth="1" strokeLinecap="round" />
              </svg>
            </div>
            <div className="weather-data">
              <span className="primary-metric">{task.temp}</span>
              <span className="secondary-metric">{task.detail}</span>
            </div>
          </div>
        )}

        {type === 'timer' && (
          <div className="task-timer-visual">
            <div className="timer-ring-container">
              <svg width="30" height="30" viewBox="0 0 32 32" className="timer-svg">
                <circle cx="16" cy="16" r="12" stroke="rgba(216, 75, 16, 0.18)" strokeWidth="1.8" fill="none" />
                <circle
                  cx="16"
                  cy="16"
                  r="12"
                  stroke="rgba(216, 75, 16, 0.9)"
                  strokeWidth="1.8"
                  fill="none"
                  strokeDasharray="75.4"
                  strokeDashoffset={75.4 * (1 - (task.progress || 0.65))}
                  strokeLinecap="round"
                  transform="rotate(-90 16 16)"
                />
              </svg>
            </div>
            <div className="timer-data">
              <span className="primary-metric">{task.time}</span>
              <span className="secondary-metric">{task.target}</span>
            </div>
          </div>
        )}

        {type === 'status' && (
          <div className="task-status-visual">
            <div className="status-bars-container">
              <div className="status-meter-segments">
                {[0, 1, 2, 3].map((idx) => (
                  <div
                    key={idx}
                    className={`meter-bar ${idx < 3 ? 'active' : ''}`}
                  />
                ))}
              </div>
              <span className="status-dot-pulse" />
            </div>
            <div className="status-data">
              <span className="primary-metric">{task.metric}</span>
              <span className="secondary-metric">{task.latency} · {task.label}</span>
            </div>
          </div>
        )}

        {type === 'comms' && (
          <div className="task-comms-visual">
            <div className="comms-spectrum-bars">
              {[0.4, 0.85, 0.55, 0.95, 0.6].map((heightFrac, idx) => (
                <div
                  key={idx}
                  className="spectrum-bar"
                  style={{
                    height: `${Math.round(heightFrac * 16)}px`,
                    animationDelay: `${idx * 0.12}s`
                  }}
                />
              ))}
            </div>
            <div className="comms-data">
              <span className="primary-metric">{task.freq}</span>
              <span className="secondary-metric">{task.bandwidth} · {task.carrier}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
