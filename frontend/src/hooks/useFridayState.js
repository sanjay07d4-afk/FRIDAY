import { useState, useEffect, useCallback, useRef } from 'react';
import { FridayApiClient } from '../services/fridayApi';
import { useVoiceAssistant } from './useVoiceAssistant';

// Task template mockups
export const TASK_TEMPLATES = [
  {
    type: 'weather',
    id: 'weather',
    temp: '21.5°C',
    condition: 'CLEAR',
    detail: 'HUM 58% · 1016 hPa',
    iconType: 'atmosphere'
  },
  {
    type: 'timer',
    id: 'timer',
    time: '04:18',
    target: 'T-MINUS 258s',
    progress: 0.65,
    iconType: 'temporal'
  },
  {
    type: 'status',
    id: 'status',
    metric: '98.4%',
    label: 'SUB-NET SYNC',
    latency: '8ms',
    segments: [true, true, true, false],
    iconType: 'diagnostic'
  },
  {
    type: 'comms',
    id: 'comms',
    freq: '432.0 MHz',
    carrier: 'LINK ACTIVE',
    bandwidth: '1.2 GB/s',
    bars: [0.6, 0.9, 0.4, 0.75, 0.5],
    iconType: 'signal'
  }
];

export const AI_STATES = ['idle', 'listening', 'processing', 'speaking'];

export function useFridayState() {
  const [aiState, setAiState] = useState('idle');
  const [tasks, setTasks] = useState([]);
  const [windowTransforms, setWindowTransforms] = useState({}); // { [instanceId]: { x, y, scale } }
  const [selectedWindowId, setSelectedWindowId] = useState(null);
  const [isDemoMenuOpen, setIsDemoMenuOpen] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);

  // Available slots for positioning around the central network
  // Slots: 0: Top-Left, 1: Mid-Left, 2: Bottom-Left, 3: Top-Right, 4: Mid-Right, 5: Bottom-Right
  const allocateSlot = useCallback((currentTasks) => {
    const occupiedSlots = new Set(currentTasks.map((t) => t.slot));
    const preferredOrder = [3, 0, 4, 1, 5, 2];
    for (const slot of preferredOrder) {
      if (!occupiedSlots.has(slot)) {
        return slot;
      }
    }
    return 3; // fallback
  }, []);

  // Spawn task pop-up
  const spawnTask = useCallback((type, dynamicProps = {}) => {
    setTasks((prev) => {
      if (prev.some((t) => t.type === type && !dynamicProps.forceNew && !dynamicProps.id)) {
        return prev;
      }
      const template = TASK_TEMPLATES.find((t) => t.type === type) || TASK_TEMPLATES[0];
      const slot = allocateSlot(prev);
      const newTask = {
        ...template,
        ...dynamicProps,
        instanceId: dynamicProps.id || `${type}-${Date.now()}`,
        slot,
        createdAt: Date.now()
      };
      return [...prev, newTask];
    });
  }, [allocateSlot]);

  // Maps backend task representation to visual HUD card
  const handleTaskEvent = useCallback((backendTask) => {
    if (!backendTask) return;
    const type = (backendTask.type || backendTask.task_type || '').toLowerCase();
    const taskId = backendTask.id || `task-${Date.now()}`;
    const title = backendTask.title || 'TASK';

    if (type.includes('weather') || title.toLowerCase().includes('weather')) {
      spawnTask('weather', {
        id: taskId,
        temp: backendTask.payload?.temperature_celsius ? `${backendTask.payload.temperature_celsius}°C` : '21.5°C',
        detail: backendTask.payload?.location ? `${backendTask.payload.condition || 'CLEAR'} · ${backendTask.payload.location}` : 'CLEAR · Tokyo Telemetry'
      });
    } else if (type.includes('timer') || type.includes('reminder') || title.toLowerCase().includes('remind')) {
      spawnTask('timer', {
        id: taskId,
        time: '04:18',
        target: title.slice(0, 18).toUpperCase(),
        progress: backendTask.progress || 0.65
      });
    } else if (type.includes('call') || type.includes('comms') || type.includes('message')) {
      spawnTask('comms', {
        id: taskId,
        carrier: title.slice(0, 18).toUpperCase(),
        freq: '432.0 MHz'
      });
    } else {
      spawnTask('status', {
        id: taskId,
        metric: `${Math.round((backendTask.progress || 0.98) * 100)}%`,
        label: title.slice(0, 16).toUpperCase()
      });
    }
  }, [spawnTask]);

  // Voice Assistant Hook
  const {
    isSupported: isVoiceSupported,
    micPermission,
    lastTranscript,
    voiceError,
    startListening,
    stopListening,
    speakResponse,
    executeCommand
  } = useVoiceAssistant({
    aiState,
    setAiState,
    onTaskSpawned: handleTaskEvent,
    onCommandProcessed: (res) => {
      // Additional command telemetry hook
    }
  });

  // Toggle specific task
  const toggleTask = useCallback((type) => {
    setTasks((prev) => {
      const exists = prev.some((t) => t.type === type);
      if (exists) {
        return prev.filter((t) => t.type !== type);
      } else {
        const template = TASK_TEMPLATES.find((t) => t.type === type) || TASK_TEMPLATES[0];
        const slot = allocateSlot(prev);
        return [...prev, { ...template, instanceId: `${type}-${Date.now()}`, slot, createdAt: Date.now() }];
      }
    });
  }, [allocateSlot]);

  // Dismiss specific task
  const dismissTask = useCallback((instanceId) => {
    setTasks((prev) => prev.filter((t) => t.instanceId !== instanceId));
    setWindowTransforms((prev) => {
      const copy = { ...prev };
      delete copy[instanceId];
      return copy;
    });
    setSelectedWindowId((prev) => (prev === instanceId ? null : prev));
  }, []);

  // Clear all tasks
  const clearAllTasks = useCallback(() => {
    setTasks([]);
    setWindowTransforms({});
    setSelectedWindowId(null);
  }, []);

  // Update window position from hand gesture drag (clamped within viewport)
  const updateWindowPosition = useCallback((instanceId, x, y) => {
    setWindowTransforms((prev) => {
      const current = prev[instanceId] || { x: 0, y: 0, scale: 1.0 };
      const clampedX = Math.max(10, Math.min((typeof window !== 'undefined' ? window.innerWidth : 1200) - 240, x));
      const clampedY = Math.max(10, Math.min((typeof window !== 'undefined' ? window.innerHeight : 800) - 80, y));

      return {
        ...prev,
        [instanceId]: {
          ...current,
          x: clampedX,
          y: clampedY
        }
      };
    });
  }, []);

  // Update window scale from two-hand gesture
  const updateWindowScale = useCallback((instanceId, scale) => {
    setWindowTransforms((prev) => {
      const current = prev[instanceId] || { x: 0, y: 0, scale: 1.0 };
      return {
        ...prev,
        [instanceId]: {
          ...current,
          scale: Math.max(0.75, Math.min(1.5, scale))
        }
      };
    });
  }, []);

  // Handle click on the central interactive globe
  const handleGlobeClick = useCallback(() => {
    if (aiState === 'listening') {
      stopListening();
    } else if (aiState === 'idle') {
      startListening();
    } else {
      // Cycle through states
      const currentIndex = AI_STATES.indexOf(aiState);
      const nextIndex = (currentIndex + 1) % AI_STATES.length;
      setAiState(AI_STATES[nextIndex]);
    }
  }, [aiState, startListening, stopListening]);

  // Preset demo scenario
  const runSimulatedScenario = useCallback(async () => {
    clearAllTasks();
    setAiState('listening');

    // Attempt real backend command if online, else fallback
    const backendResult = await FridayApiClient.submitCommand('Hey Friday, check atmospheric telemetry in Tokyo');

    if (backendResult && backendResult.tasks_spawned?.length) {
      setAiState('processing');
      setTimeout(() => {
        setAiState('speaking');
        spawnTask('weather', {
          temp: '21.5°C',
          detail: 'HUM 58% · Tokyo Telemetry'
        });
        speakResponse(backendResult.spoken_response || backendResult.response_text);
      }, 1200);

      setTimeout(() => {
        spawnTask('status', {
          metric: '100%',
          label: 'ORCHESTRATOR SYNC'
        });
      }, 2400);
      return;
    }

    // Local simulation fallback
    setTimeout(() => {
      setAiState('processing');
    }, 1200);

    setTimeout(() => {
      setAiState('speaking');
      spawnTask('weather');
      speakResponse('Atmospheric telemetry online. Temperature is 21.5 degrees Celsius with clear skies in Tokyo.');
    }, 2400);

    setTimeout(() => {
      spawnTask('timer');
    }, 3800);
  }, [clearAllTasks, spawnTask, speakResponse]);

  // Connect WebSocket to live backend task stream
  useEffect(() => {
    let wsHandle = null;

    wsHandle = FridayApiClient.connectTaskWebSocket(
      handleTaskEvent,
      (initialTasks) => {
        if (Array.isArray(initialTasks) && initialTasks.length > 0) {
          initialTasks.slice(0, 3).forEach(handleTaskEvent);
        }
      },
      (connected) => {
        setIsBackendConnected(connected);
      }
    );

    return () => {
      if (wsHandle) wsHandle.close();
    };
  }, [handleTaskEvent]);

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      const key = e.key.toLowerCase();
      if (key === ' ' || key === 'v') {
        e.preventDefault();
        if (aiState === 'listening') {
          stopListening();
        } else {
          startListening();
        }
      } else if (key === 'i') {
        stopListening();
        setAiState('idle');
      } else if (key === 'l') {
        startListening();
      } else if (key === 'p') {
        setAiState('processing');
      } else if (key === 's') {
        setAiState('speaking');
      } else if (key === '1') {
        toggleTask('weather');
      } else if (key === '2') {
        toggleTask('timer');
      } else if (key === '3') {
        toggleTask('status');
      } else if (key === '4') {
        toggleTask('comms');
      } else if (key === 'c') {
        clearAllTasks();
      } else if (key === 'a') {
        TASK_TEMPLATES.forEach((template, i) => {
          setTimeout(() => spawnTask(template.type), i * 150);
        });
      } else if (key === 'd') {
        runSimulatedScenario();
      } else if (key === 'h' || key === '?') {
        setIsDemoMenuOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [aiState, startListening, stopListening, toggleTask, clearAllTasks, spawnTask, runSimulatedScenario]);

  return {
    aiState,
    setAiState,
    handleGlobeClick,
    tasks,
    windowTransforms,
    selectedWindowId,
    setSelectedWindowId,
    updateWindowPosition,
    updateWindowScale,
    spawnTask,
    toggleTask,
    dismissTask,
    clearAllTasks,
    runSimulatedScenario,
    isDemoMenuOpen,
    setIsDemoMenuOpen,
    isBackendConnected,
    // Voice Assistant Controls
    isVoiceSupported,
    micPermission,
    lastTranscript,
    voiceError,
    startListening,
    stopListening
  };
}
