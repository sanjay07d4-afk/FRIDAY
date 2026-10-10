import React, { useState } from 'react';

export default function DemoHUDTrigger({
  aiState,
  setAiState,
  tasks,
  toggleTask,
  clearAllTasks,
  runSimulatedScenario,
  cameraState = 'idle',
  errorMessage = null,
  onToggleCamera,
  micPermission = 'prompt',
  onToggleVoice
}) {
  const [isOpen, setIsOpen] = useState(false);

  const getCameraLabel = () => {
    switch (cameraState) {
      case 'active':
        return 'DISABLE GESTURES';
      case 'requesting':
        return 'CONNECTING...';
      case 'denied':
        return 'CAM DENIED (RETRY)';
      case 'error':
        return 'CAM ERROR (RETRY)';
      default:
        return 'ENABLE GESTURES';
    }
  };

  return (
    <aside
      className={`demo-hud-controller ${isOpen ? 'expanded' : 'collapsed'}`}
      aria-label="Simulation Controls"
    >
      {/* Ultra-discrete toggle pill */}
      <button
        type="button"
        className="hud-pill-toggle"
        onClick={() => setIsOpen((prev) => !prev)}
        title="Toggle Simulation Control"
      >
        <span className={`hud-pill-indicator ${cameraState === 'active' ? 'cam-active' : ''}`} />
        <span className="hud-pill-label">
          {isOpen
            ? 'CLOSE SIM'
            : cameraState === 'active'
            ? `FRIDAY :: ${aiState.toUpperCase()} [GESTURES ON]`
            : `FRIDAY :: ${aiState.toUpperCase()}`}
        </span>
      </button>

      {/* Expanded minimal control panel */}
      {isOpen && (
        <div className="hud-panel-drawer">
          {/* Voice Input Section */}
          <div className="hud-control-group">
            <span className="hud-group-label">VOICE INTERACTION</span>
            <div className="hud-btn-row">
              <button
                className={`hud-action-chip ${aiState === 'listening' ? 'active highlight' : ''}`}
                onClick={onToggleVoice}
                title="Click or press SPACE to speak command to FRIDAY"
              >
                {aiState === 'listening' ? 'LISTENING... (STOP)' : 'VOICE INPUT [SPACE / V]'}
              </button>
              {micPermission === 'denied' && (
                <span className="hud-status-badge error">MIC DENIED</span>
              )}
            </div>
          </div>

          {/* Hand Gesture Camera Section */}
          <div className="hud-control-group">
            <span className="hud-group-label">GESTURE TRACKING</span>
            <div className="hud-btn-row">
              <button
                className={`hud-action-chip ${cameraState === 'active' ? 'active highlight' : ''}`}
                onClick={onToggleCamera}
                title="Pinch window to drag & move; use two hands to resize"
              >
                {getCameraLabel()}
              </button>
              {cameraState === 'active' && (
                <span className="hud-status-badge active">TRACKING ACTIVE</span>
              )}
              {cameraState === 'denied' && (
                <span className="hud-status-badge error">{errorMessage || 'DENIED'}</span>
              )}
            </div>
          </div>

          <div className="hud-control-group">
            <span className="hud-group-label">NEURAL STATE</span>
            <div className="hud-btn-row">
              {['idle', 'listening', 'processing', 'speaking'].map((st) => (
                <button
                  key={st}
                  className={`hud-action-chip ${aiState === st ? 'active' : ''}`}
                  onClick={() => setAiState(st)}
                >
                  {st.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="hud-control-group">
            <span className="hud-group-label">FLOATING TASKS</span>
            <div className="hud-btn-row">
              {[
                { type: 'weather', label: '+ WEATHER' },
                { type: 'timer', label: '+ TIMER' },
                { type: 'status', label: '+ STATUS' },
                { type: 'comms', label: '+ COMMS' }
              ].map(({ type, label }) => {
                const isActive = tasks.some((t) => t.type === type);
                return (
                  <button
                    key={type}
                    className={`hud-action-chip ${isActive ? 'active' : ''}`}
                    onClick={() => toggleTask(type)}
                  >
                    {isActive ? `DISMISS ${type.toUpperCase()}` : label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="hud-control-group">
            <span className="hud-group-label">SIMULATION</span>
            <div className="hud-btn-row">
              <button
                className="hud-action-chip highlight"
                onClick={runSimulatedScenario}
                title="Runs an automated sequence: Listen -> Process -> Speak -> Spawn Tasks -> Idle"
              >
                RUN SEQUENCE
              </button>
              <button
                className="hud-action-chip"
                onClick={clearAllTasks}
                title="Dismiss all active floating windows"
              >
                CLEAR ALL
              </button>
            </div>
          </div>

          <div className="hud-hotkeys-hint">
            <span>KEYBOARD: [SPACE/V] VOICE · [G] GESTURES · [1-4] TASKS · [D] DEMO · [C] CLEAR</span>
          </div>
        </div>
      )}
    </aside>
  );
}
