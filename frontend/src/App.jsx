import React, { useEffect } from 'react';
import CentralNetworkCanvas from './components/CentralNetworkCanvas';
import FloatingTaskWindow from './components/FloatingTaskWindow';
import DemoHUDTrigger from './components/DemoHUDTrigger';
import HandCursorOverlay from './components/HandCursorOverlay';
import { useFridayState } from './hooks/useFridayState';
import { useHandGesture } from './hooks/useHandGesture';
import './App.css';

function App() {
  const {
    aiState,
    setAiState,
    handleGlobeClick,
    tasks,
    windowTransforms,
    selectedWindowId,
    setSelectedWindowId,
    updateWindowPosition,
    updateWindowScale,
    toggleTask,
    dismissTask,
    clearAllTasks,
    runSimulatedScenario,
    isVoiceSupported,
    micPermission,
    voiceError,
    startListening,
    stopListening
  } = useFridayState();

  const {
    cameraState,
    errorMessage: cameraErrorMessage,
    handPointers,
    activeGrabbedId,
    startTracking,
    stopTracking
  } = useHandGesture({
    onWindowMove: updateWindowPosition,
    onWindowScale: updateWindowScale,
    onWindowSelect: setSelectedWindowId
  });

  const handleToggleCamera = () => {
    if (cameraState === 'active' || cameraState === 'requesting') {
      stopTracking();
    } else {
      startTracking();
    }
  };

  // Keyboard shortcut 'g' to toggle gestures
  useEffect(() => {
    const handleKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key.toLowerCase() === 'g') {
        handleToggleCamera();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [cameraState]);

  return (
    <main className="friday-root-viewport">
      {/* Subtle vignette layer for holographic depth */}
      <div className="hologram-vignette" />

      {/* Central 3D Interconnected Wire Globe */}
      <CentralNetworkCanvas
        aiState={aiState}
        onGlobeClick={handleGlobeClick}
      />

      {/* Floating Independent Task Pop-ups */}
      {tasks.map((task) => (
        <FloatingTaskWindow
          key={task.instanceId}
          task={task}
          transform={windowTransforms[task.instanceId]}
          isGrabbed={activeGrabbedId === task.instanceId}
          isSelected={selectedWindowId === task.instanceId}
          onDismiss={dismissTask}
        />
      ))}

      {/* Holographic Hand Cursor Reticle Overlay */}
      <HandCursorOverlay
        handPointers={handPointers}
        isResizing={handPointers.length >= 2 && !!activeGrabbedId}
      />

      {/* Discrete Simulation Control Pill */}
      <DemoHUDTrigger
        aiState={aiState}
        setAiState={setAiState}
        tasks={tasks}
        toggleTask={toggleTask}
        clearAllTasks={clearAllTasks}
        runSimulatedScenario={runSimulatedScenario}
        cameraState={cameraState}
        errorMessage={cameraErrorMessage || voiceError}
        onToggleCamera={handleToggleCamera}
        micPermission={micPermission}
        onToggleVoice={startListening}
      />
    </main>
  );
}

export default App;
