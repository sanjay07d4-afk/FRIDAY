import { useState, useEffect, useRef, useCallback } from 'react';
import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision';

// Smoothing factor for exponential moving average (0 = no update, 1 = instant)
const LERP_FACTOR = 0.35;
// Minimum movement in pixels to consider as intentional (dead-zone)
const DEAD_ZONE_PX = 2.0;
// Distance threshold (normalized) between thumb tip and index tip for pinch
const PINCH_THRESHOLD = 0.07;
const PINCH_RELEASE_THRESHOLD = 0.095;

export function useHandGesture({ onWindowMove, onWindowScale, onWindowSelect }) {
  const [cameraState, setCameraState] = useState('idle'); // 'idle' | 'requesting' | 'active' | 'denied' | 'error'
  const [errorMessage, setErrorMessage] = useState(null);
  const [handPointers, setHandPointers] = useState([]); // Array of { x, y, isPinching, handIndex }
  const [activeGrabbedId, setActiveGrabbedId] = useState(null);

  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const landmarkerRef = useRef(null);
  const animFrameIdRef = useRef(null);

  // Mutable tracking references to avoid react re-render churn in animation loop
  const trackingRef = useRef({
    smoothedPositions: [
      { x: typeof window !== 'undefined' ? window.innerWidth / 2 : 400, y: typeof window !== 'undefined' ? window.innerHeight / 2 : 300, pinching: false },
      { x: typeof window !== 'undefined' ? window.innerWidth / 2 : 400, y: typeof window !== 'undefined' ? window.innerHeight / 2 : 300, pinching: false }
    ],
    lastPinchStates: [false, false],
    grabbedWindowId: null,
    grabOffset: { x: 0, y: 0 },
    initialTwoHandDist: null,
    initialWindowScale: 1.0,
    cooldownUntil: 0
  });

  // Calculate distance between two 3D landmarks
  const landmarkDistance = (p1, p2) => {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    const dz = (p1.z || 0) - (p2.z || 0);
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  };

  // Find task window element under screen coordinate (x, y)
  const hitTestWindow = (x, y) => {
    if (typeof document === 'undefined') return null;
    const elements = document.elementsFromPoint(x, y);
    for (const el of elements) {
      const hudEl = el.closest('.floating-task-hud');
      if (hudEl) {
        return {
          id: hudEl.getAttribute('data-task-id'),
          rect: hudEl.getBoundingClientRect()
        };
      }
    }
    return null;
  };

  // Start Camera & Hand Tracking
  const startTracking = useCallback(async () => {
    if (cameraState === 'active' || cameraState === 'requesting') return;
    setCameraState('requesting');
    setErrorMessage(null);

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access API is not supported in this browser context.');
      }

      // 1. Initialize MediaPipe HandLandmarker
      if (!landmarkerRef.current) {
        const vision = await FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/wasm'
        );

        try {
          landmarkerRef.current = await HandLandmarker.createFromOptions(vision, {
            baseOptions: {
              modelAssetPath:
                'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
              delegate: 'GPU'
            },
            runningMode: 'VIDEO',
            numHands: 2
          });
        } catch (gpuErr) {
          console.warn('[FRIDAY Gestures] GPU delegate failed, falling back to CPU', gpuErr);
          landmarkerRef.current = await HandLandmarker.createFromOptions(vision, {
            baseOptions: {
              modelAssetPath:
                'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
              delegate: 'CPU'
            },
            runningMode: 'VIDEO',
            numHands: 2
          });
        }
      }

      // 2. Request webcam video stream
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      streamRef.current = stream;

      // 3. Attach stream to hidden video element
      let video = videoRef.current;
      if (!video) {
        video = document.createElement('video');
        video.playsInline = true;
        video.muted = true;
        video.autoplay = true;
        video.style.position = 'fixed';
        video.style.top = '-9999px';
        video.style.left = '-9999px';
        video.style.width = '640px';
        video.style.height = '480px';
        video.style.opacity = '0';
        video.style.pointerEvents = 'none';
        document.body.appendChild(video);
        videoRef.current = video;
      }

      video.srcObject = stream;

      await new Promise((resolve) => {
        if (video.readyState >= 2) {
          video.play().then(resolve).catch(resolve);
        } else {
          video.onloadedmetadata = () => {
            video.play().then(resolve).catch(resolve);
          };
          setTimeout(resolve, 800);
        }
      });

      setCameraState('active');

      // 4. Start detection loop
      let lastVideoTime = -1;
      const processFrame = () => {
        if (!videoRef.current || !landmarkerRef.current || !streamRef.current) return;

        const now = performance.now();
        if (videoRef.current.currentTime !== lastVideoTime && videoRef.current.videoWidth > 0) {
          lastVideoTime = videoRef.current.currentTime;
          try {
            const detections = landmarkerRef.current.detectForVideo(videoRef.current, now);
            if (detections && detections.landmarks) {
              handleHandDetections(detections.landmarks);
            } else {
              setHandPointers([]);
            }
          } catch (detErr) {
            // Silently swallow frame drop
          }
        }

        animFrameIdRef.current = requestAnimationFrame(processFrame);
      };

      animFrameIdRef.current = requestAnimationFrame(processFrame);
    } catch (err) {
      console.error('[FRIDAY Gestures] Initialization error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraState('denied');
        setErrorMessage('Camera permission was denied in browser.');
      } else {
        setCameraState('error');
        setErrorMessage(err.message || 'Unable to access camera.');
      }
    }
  }, [cameraState]);

  // Stop Camera & Clean up resources
  const stopTracking = useCallback(() => {
    if (animFrameIdRef.current) {
      cancelAnimationFrame(animFrameIdRef.current);
      animFrameIdRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
      if (videoRef.current.parentNode) {
        videoRef.current.parentNode.removeChild(videoRef.current);
      }
      videoRef.current = null;
    }

    trackingRef.current.grabbedWindowId = null;
    setActiveGrabbedId(null);
    setHandPointers([]);
    setCameraState('idle');
  }, []);

  // Process detected hands, landmarks, pinches, and transformations
  const handleHandDetections = (handsList) => {
    const screenW = typeof window !== 'undefined' ? window.innerWidth : 1200;
    const screenH = typeof window !== 'undefined' ? window.innerHeight : 800;
    const pointers = [];
    const tState = trackingRef.current;
    const now = Date.now();

    // Track up to 2 hands
    for (let h = 0; h < Math.min(handsList.length, 2); h++) {
      const landmarks = handsList[h];
      const thumbTip = landmarks[4];
      const indexTip = landmarks[8];

      // Screen coordinate: mirror horizontally (user moving right -> pointer moves right)
      const rawScreenX = (1 - indexTip.x) * screenW;
      const rawScreenY = indexTip.y * screenH;

      // Exponential moving average smoothing & dead-zone
      const currentSmoothed = tState.smoothedPositions[h] || { x: rawScreenX, y: rawScreenY };
      const deltaX = rawScreenX - currentSmoothed.x;
      const deltaY = rawScreenY - currentSmoothed.y;

      let smoothX = currentSmoothed.x;
      let smoothY = currentSmoothed.y;

      if (Math.abs(deltaX) > DEAD_ZONE_PX) {
        smoothX += deltaX * LERP_FACTOR;
      }
      if (Math.abs(deltaY) > DEAD_ZONE_PX) {
        smoothY += deltaY * LERP_FACTOR;
      }

      // Clamp within screen boundaries
      smoothX = Math.max(10, Math.min(screenW - 10, smoothX));
      smoothY = Math.max(10, Math.min(screenH - 10, smoothY));

      // Calculate pinch distance
      const pinchDist = landmarkDistance(thumbTip, indexTip);
      const wasPinching = tState.lastPinchStates[h];
      const isPinching = wasPinching
        ? pinchDist < PINCH_RELEASE_THRESHOLD
        : pinchDist < PINCH_THRESHOLD;

      tState.smoothedPositions[h] = { x: smoothX, y: smoothY, pinching: isPinching };
      tState.lastPinchStates[h] = isPinching;

      pointers.push({
        x: smoothX,
        y: smoothY,
        isPinching,
        pinchDist,
        handIndex: h
      });
    }

    setHandPointers(pointers);

    // Primary hand for grabbing and moving (Hand 0)
    const primaryHand = pointers[0];

    // Two-Hand Zoom Gesture
    if (pointers.length >= 2) {
      const p1 = pointers[0];
      const p2 = pointers[1];
      const handDist = Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);

      if (tState.grabbedWindowId) {
        if (!tState.initialTwoHandDist) {
          tState.initialTwoHandDist = handDist;
        } else if (tState.initialTwoHandDist > 20) {
          const ratio = handDist / tState.initialTwoHandDist;
          // Apply scale change smoothly
          const targetScale = Math.max(0.75, Math.min(1.5, tState.initialWindowScale * ratio));
          if (onWindowScale) {
            onWindowScale(tState.grabbedWindowId, targetScale);
          }
        }
      }
    } else {
      tState.initialTwoHandDist = null;
    }

    // Single-Hand Grab & Move Gesture
    if (primaryHand) {
      const { x, y, isPinching } = primaryHand;

      // 1. Grab Initiation
      if (isPinching && !tState.grabbedWindowId && now > tState.cooldownUntil) {
        const hit = hitTestWindow(x, y);
        if (hit) {
          tState.grabbedWindowId = hit.id;
          tState.grabOffset = {
            x: x - hit.rect.left,
            y: y - hit.rect.top
          };
          tState.initialWindowScale = 1.0;
          setActiveGrabbedId(hit.id);
          if (onWindowSelect) onWindowSelect(hit.id);
        }
      }
      // 2. Continuous Drag while Pinched
      else if (isPinching && tState.grabbedWindowId) {
        const targetX = x - tState.grabOffset.x;
        const targetY = y - tState.grabOffset.y;

        if (onWindowMove) {
          onWindowMove(tState.grabbedWindowId, targetX, targetY);
        }
      }
      // 3. Release Window
      else if (!isPinching && tState.grabbedWindowId) {
        tState.grabbedWindowId = null;
        tState.cooldownUntil = now + 180; // 180ms cooldown to prevent accidental re-grab
        tState.initialTwoHandDist = null;
        setActiveGrabbedId(null);
      }
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTracking();
    };
  }, [stopTracking]);

  return {
    cameraState,
    errorMessage,
    handPointers,
    activeGrabbedId,
    startTracking,
    stopTracking
  };
}
