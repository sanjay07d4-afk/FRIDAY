import { useState, useEffect, useRef, useCallback } from 'react';
import { FridayApiClient } from '../services/fridayApi';

export function useVoiceAssistant({
  aiState,
  setAiState,
  onTaskSpawned,
  onCommandProcessed
}) {
  const [isSupported, setIsSupported] = useState(true);
  const [micPermission, setMicPermission] = useState('prompt'); // 'prompt' | 'granted' | 'denied' | 'unsupported'
  const [lastTranscript, setLastTranscript] = useState('');
  const [voiceError, setVoiceError] = useState(null);
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);

  const recognitionRef = useRef(null);
  const isListeningRef = useRef(false);
  const isProcessingRef = useRef(false);
  const isSpeakingRef = useRef(false);
  const isVoiceModeActiveRef = useRef(false);
  const currentUtteranceRef = useRef(null);
  const resumeTimerRef = useRef(null);
  const ttsWatchdogRef = useRef(null);
  const hasDispatchedCurrentUtteranceRef = useRef(false);

  // Sync ref with state
  useEffect(() => {
    isVoiceModeActiveRef.current = isVoiceModeActive;
  }, [isVoiceModeActive]);

  // Cleanly abort / pause speech recognition without triggering error cascade
  const safePauseRecognition = useCallback(() => {
    isListeningRef.current = false;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {}
    }
  }, []);

  // Safe restart of speech recognition during active continuous session
  const safeResumeListening = useCallback(() => {
    if (resumeTimerRef.current) {
      clearTimeout(resumeTimerRef.current);
      resumeTimerRef.current = null;
    }

    if (!isVoiceModeActiveRef.current || isSpeakingRef.current || isProcessingRef.current) {
      return;
    }

    resumeTimerRef.current = setTimeout(() => {
      if (!isVoiceModeActiveRef.current || isSpeakingRef.current || isProcessingRef.current) {
        return;
      }

      if (!recognitionRef.current) return;

      try {
        hasDispatchedCurrentUtteranceRef.current = false;
        recognitionRef.current.start();
        isListeningRef.current = true;
        setAiState('listening');
      } catch (err) {
        // If already started, mark listening state
        if (err.name === 'InvalidStateError') {
          isListeningRef.current = true;
          setAiState('listening');
        } else {
          console.warn('[FRIDAY Voice] Safe resume recognition notice:', err.message);
        }
      }
    }, 280); // 280ms acoustic buffer to prevent microphone from hearing residual speaker reverberation
  }, [setAiState]);

  // Audible speech synthesis with safety watchdog
  const speakResponse = useCallback(
    (textToSpeak, onComplete) => {
      if (typeof window === 'undefined' || !window.speechSynthesis || !textToSpeak) {
        isSpeakingRef.current = false;
        if (isVoiceModeActiveRef.current) {
          safeResumeListening();
        } else {
          setAiState('idle');
        }
        if (onComplete) onComplete();
        return;
      }

      // 1. Immediately pause microphone recognition so FRIDAY never hears its own voice
      safePauseRecognition();
      isSpeakingRef.current = true;
      setAiState('speaking');

      try {
        window.speechSynthesis.cancel(); // Clear any previous speech queue

        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        currentUtteranceRef.current = utterance;
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Select suitable English voice
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice =
          voices.find(
            (v) =>
              v.lang.startsWith('en') &&
              (v.name.includes('Natural') ||
                v.name.includes('Google') ||
                v.name.includes('Samantha') ||
                v.name.includes('Female'))
          ) || voices.find((v) => v.lang.startsWith('en'));

        if (preferredVoice) {
          utterance.voice = preferredVoice;
        }

        const cleanupTTS = () => {
          if (ttsWatchdogRef.current) {
            clearTimeout(ttsWatchdogRef.current);
            ttsWatchdogRef.current = null;
          }
          currentUtteranceRef.current = null;
          isSpeakingRef.current = false;
        };

        const handleSpeechFinished = () => {
          cleanupTTS();
          if (onComplete) onComplete();

          // AUTOMATIC RETURN TO LISTENING in continuous voice session
          if (isVoiceModeActiveRef.current) {
            setAiState('listening');
            safeResumeListening();
          } else {
            setAiState('idle');
          }
        };

        utterance.onend = handleSpeechFinished;

        utterance.onerror = (e) => {
          console.warn('[FRIDAY Voice] Speech synthesis event notice:', e.error);
          handleSpeechFinished();
        };

        // Safety Watchdog: If browser background-throttles speech onend, auto-recover
        const estimatedDurationMs = Math.max(2500, textToSpeak.length * 90 + 2000);
        ttsWatchdogRef.current = setTimeout(() => {
          if (isSpeakingRef.current) {
            console.warn('[FRIDAY Voice] TTS watchdog triggered fallback to listening');
            window.speechSynthesis.cancel();
            handleSpeechFinished();
          }
        }, estimatedDurationMs);

        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.error('[FRIDAY Voice] Speech synthesis error:', err);
        isSpeakingRef.current = false;
        if (isVoiceModeActiveRef.current) {
          safeResumeListening();
        } else {
          setAiState('idle');
        }
        if (onComplete) onComplete();
      }
    },
    [safePauseRecognition, safeResumeListening, setAiState]
  );

  // Full command execution pipeline: Transcript -> Backend API -> Task HUD -> Spoken Response -> Resume Listening
  const handleFinalVoiceCommand = useCallback(
    async (commandText) => {
      const cleanText = commandText.trim();
      if (!cleanText || cleanText.length < 2) return;

      if (hasDispatchedCurrentUtteranceRef.current) return;
      hasDispatchedCurrentUtteranceRef.current = true;

      // 1. Transition to processing
      isProcessingRef.current = true;
      safePauseRecognition();
      setAiState('processing');

      try {
        // 2. Dispatch command to backend
        const result = await FridayApiClient.submitCommand(cleanText);

        if (result && result.response_text) {
          // Spawn any tasks generated by AI Orchestrator in floating HUD
          if (Array.isArray(result.tasks_spawned) && result.tasks_spawned.length > 0) {
            result.tasks_spawned.forEach((task) => {
              if (onTaskSpawned) {
                onTaskSpawned(task);
              }
            });
          }

          if (onCommandProcessed) {
            onCommandProcessed(result);
          }

          // 3. Audibly speak the verified response
          const spokenText = result.spoken_response || result.response_text;
          speakResponse(spokenText, () => {
            isProcessingRef.current = false;
            hasDispatchedCurrentUtteranceRef.current = false;
          });
        } else {
          // Fallback if backend temporarily unavailable
          const fallbackText = `Instruction received: "${cleanText}". System operational.`;
          speakResponse(fallbackText, () => {
            isProcessingRef.current = false;
            hasDispatchedCurrentUtteranceRef.current = false;
          });
        }
      } catch (err) {
        console.error('[FRIDAY Voice] Command processing error:', err);
        speakResponse('I encountered an error synchronizing with the neural engine.', () => {
          isProcessingRef.current = false;
          hasDispatchedCurrentUtteranceRef.current = false;
        });
      }
    },
    [safePauseRecognition, speakResponse, onTaskSpawned, onCommandProcessed, setAiState]
  );

  // Initialize SpeechRecognition instance
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('[FRIDAY Voice] Web Speech API is not supported in this browser.');
      setIsSupported(false);
      setMicPermission('unsupported');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false; // Discrete captures with automatic lifecycle chaining
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        isListeningRef.current = true;
        setMicPermission('granted');
        setVoiceError(null);
        setAiState('listening');
      };

      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTranscript += result[0].transcript;
          } else {
            interimTranscript += result[0].transcript;
          }
        }

        const currentText = (finalTranscript || interimTranscript).trim();
        if (currentText) {
          setLastTranscript(currentText);
        }

        if (finalTranscript.trim() && !isProcessingRef.current && !isSpeakingRef.current) {
          handleFinalVoiceCommand(finalTranscript.trim());
        }
      };

      recognition.onerror = (event) => {
        isListeningRef.current = false;

        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          console.warn('[FRIDAY Voice] Microphone permission denied');
          setMicPermission('denied');
          setIsVoiceModeActive(false);
          isVoiceModeActiveRef.current = false;
          setVoiceError('Microphone permission denied. Please allow microphone in browser.');
          setAiState('idle');
        } else if (event.error === 'no-speech') {
          // Silence timeout: auto-restart if voice mode is still active
          if (isVoiceModeActiveRef.current && !isSpeakingRef.current && !isProcessingRef.current) {
            safeResumeListening();
          } else if (!isVoiceModeActiveRef.current) {
            setAiState('idle');
          }
        } else if (event.error === 'aborted') {
          // Intentional abort (e.g. during TTS speech), ignore
        } else if (event.error === 'network') {
          console.warn('[FRIDAY Voice] Speech network error');
          setVoiceError('Speech network connection interrupted.');
          if (isVoiceModeActiveRef.current) {
            safeResumeListening();
          } else {
            setAiState('idle');
          }
        } else {
          if (isVoiceModeActiveRef.current && !isSpeakingRef.current && !isProcessingRef.current) {
            safeResumeListening();
          } else {
            setAiState('idle');
          }
        }
      };

      recognition.onend = () => {
        isListeningRef.current = false;

        // In continuous voice mode: if not speaking and not processing, resume listening automatically!
        if (isVoiceModeActiveRef.current && !isSpeakingRef.current && !isProcessingRef.current) {
          safeResumeListening();
        } else if (!isVoiceModeActiveRef.current && !isSpeakingRef.current && !isProcessingRef.current) {
          setAiState('idle');
        }
      };

      recognitionRef.current = recognition;
    } catch (e) {
      console.error('[FRIDAY Voice] Failed to initialize SpeechRecognition:', e);
      setIsSupported(false);
    }

    return () => {
      if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
      if (ttsWatchdogRef.current) clearTimeout(ttsWatchdogRef.current);
      safePauseRecognition();
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [handleFinalVoiceCommand, safePauseRecognition, safeResumeListening, setAiState]);

  // Start continuous voice session
  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      setVoiceError('Speech recognition is not supported in this browser.');
      return;
    }

    // Barge-in: if currently speaking, stop TTS immediately
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    isSpeakingRef.current = false;
    isProcessingRef.current = false;
    hasDispatchedCurrentUtteranceRef.current = false;

    setIsVoiceModeActive(true);
    isVoiceModeActiveRef.current = true;
    setVoiceError(null);

    try {
      recognitionRef.current.start();
      isListeningRef.current = true;
      setAiState('listening');
    } catch (err) {
      if (err.name === 'InvalidStateError') {
        isListeningRef.current = true;
        setAiState('listening');
      } else {
        console.warn('[FRIDAY Voice] recognition.start() notice:', err.message);
      }
    }
  }, [setAiState]);

  // Stop continuous voice session
  const stopListening = useCallback(() => {
    setIsVoiceModeActive(false);
    isVoiceModeActiveRef.current = false;
    if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current);
    if (ttsWatchdogRef.current) clearTimeout(ttsWatchdogRef.current);

    safePauseRecognition();

    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    isSpeakingRef.current = false;
    isProcessingRef.current = false;
    hasDispatchedCurrentUtteranceRef.current = false;
    setAiState('idle');
  }, [safePauseRecognition, setAiState]);

  // Toggle voice session
  const toggleListening = useCallback(() => {
    if (isVoiceModeActiveRef.current || isListeningRef.current || aiState === 'listening') {
      stopListening();
    } else {
      startListening();
    }
  }, [aiState, startListening, stopListening]);

  return {
    isSupported,
    micPermission,
    lastTranscript,
    voiceError,
    isVoiceModeActive,
    startListening,
    stopListening,
    toggleListening,
    speakResponse,
    executeCommand: handleFinalVoiceCommand
  };
}
