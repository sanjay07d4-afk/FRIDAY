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

  const recognitionRef = useRef(null);
  const isListeningRef = useRef(false);
  const isProcessingRef = useRef(false);
  const synthRef = useRef(typeof window !== 'undefined' ? window.speechSynthesis : null);
  const currentUtteranceRef = useRef(null);
  const restartTimerRef = useRef(null);

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
      recognition.continuous = false; // Capture discrete voice commands
      recognition.interimResults = true; // Show fast live feedback
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

        if (finalTranscript.trim() && !isProcessingRef.current) {
          handleFinalVoiceCommand(finalTranscript.trim());
        }
      };

      recognition.onerror = (event) => {
        console.warn('[FRIDAY Voice] Speech recognition event error:', event.error);
        isListeningRef.current = false;

        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setMicPermission('denied');
          setVoiceError('Microphone access denied. Please allow microphone permissions in browser.');
          setAiState('idle');
        } else if (event.error === 'no-speech') {
          // Timeout without speech, gracefully return to idle
          setAiState('idle');
        } else if (event.error === 'network') {
          setVoiceError('Speech recognition network error.');
          setAiState('idle');
        } else {
          setAiState('idle');
        }
      };

      recognition.onend = () => {
        isListeningRef.current = false;
        // If not processing and not speaking, return to idle
        if (!isProcessingRef.current && aiState === 'listening') {
          setAiState('idle');
        }
      };

      recognitionRef.current = recognition;
    } catch (e) {
      console.error('[FRIDAY Voice] Failed to initialize SpeechRecognition:', e);
      setIsSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }
      if (synthRef.current) {
        synthRef.current.cancel();
      }
    };
  }, []);

  // Speak assistant response audibly using Web Speech Synthesis
  const speakResponse = useCallback((textToSpeak, onComplete) => {
    if (!synthRef.current || !textToSpeak) {
      setAiState('idle');
      if (onComplete) onComplete();
      return;
    }

    try {
      synthRef.current.cancel(); // Cancel any existing speaking audio

      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      currentUtteranceRef.current = utterance;
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      // Select natural English voice if available
      const voices = synthRef.current.getVoices();
      const preferredVoice =
        voices.find((v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Female'))) ||
        voices.find((v) => v.lang.startsWith('en'));

      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onstart = () => {
        setAiState('speaking');
      };

      utterance.onend = () => {
        currentUtteranceRef.current = null;
        setAiState('idle');
        if (onComplete) onComplete();
      };

      utterance.onerror = (e) => {
        console.warn('[FRIDAY Voice] Speech synthesis error:', e);
        currentUtteranceRef.current = null;
        setAiState('idle');
        if (onComplete) onComplete();
      };

      synthRef.current.speak(utterance);
    } catch (err) {
      console.error('[FRIDAY Voice] Speech synthesis exception:', err);
      setAiState('idle');
      if (onComplete) onComplete();
    }
  }, [setAiState]);

  // Execute full NLP command cycle
  const handleFinalVoiceCommand = useCallback(
    async (commandText) => {
      isProcessingRef.current = true;
      setAiState('processing');

      try {
        if (recognitionRef.current) {
          try {
            recognitionRef.current.stop();
          } catch {}
        }

        // 1. Submit command to backend
        const result = await FridayApiClient.submitCommand(commandText);

        if (result && result.response_text) {
          // Spawn any tasks created by AI Orchestrator
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

          // 2. Speak the response
          const spokenText = result.spoken_response || result.response_text;
          speakResponse(spokenText, () => {
            isProcessingRef.current = false;
          });
        } else {
          // Fallback if backend unavailable
          const fallbackText = `Acknowledged. Processed instruction: "${commandText}".`;
          speakResponse(fallbackText, () => {
            isProcessingRef.current = false;
          });
        }
      } catch (err) {
        console.error('[FRIDAY Voice] Error processing command:', err);
        speakResponse('I encountered a synchronization error while processing your instruction.', () => {
          isProcessingRef.current = false;
        });
      }
    },
    [onTaskSpawned, onCommandProcessed, setAiState, speakResponse]
  );

  // Trigger voice listening
  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      // Fallback message if speech recognition not supported
      setVoiceError('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (synthRef.current) {
      synthRef.current.cancel(); // Stop talking if user interrupts
    }

    if (isListeningRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      isListeningRef.current = false;
      setAiState('idle');
      return;
    }

    try {
      setVoiceError(null);
      isProcessingRef.current = false;
      recognitionRef.current.start();
    } catch (e) {
      console.warn('[FRIDAY Voice] recognition.start() error:', e);
      // If already started, stop and reset
      try {
        recognitionRef.current.stop();
      } catch {}
    }
  }, [setAiState]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListeningRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    if (synthRef.current) {
      synthRef.current.cancel();
    }
    isListeningRef.current = false;
    isProcessingRef.current = false;
    setAiState('idle');
  }, [setAiState]);

  return {
    isSupported,
    micPermission,
    lastTranscript,
    voiceError,
    startListening,
    stopListening,
    speakResponse,
    executeCommand: handleFinalVoiceCommand
  };
}
