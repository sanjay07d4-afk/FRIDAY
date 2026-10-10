import React, { useRef, useEffect, useCallback } from 'react';

// Generates N points on a 3D sphere surface using Fibonacci spiral
function generateFibonacciSphere(samples, radius) {
  const points = [];
  const phi = Math.PI * (Math.sqrt(5) - 1); // golden ratio angle ~ 2.39996323

  for (let i = 0; i < samples; i++) {
    // y goes from 1 to -1
    const y = 1 - (i / (samples - 1)) * 2;
    const radiusAtY = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = phi * i;

    const x = Math.cos(theta) * radiusAtY;
    const z = Math.sin(theta) * radiusAtY;

    // Slight irregular deviation to give authentic network feel
    const jitter = 0.94 + Math.random() * 0.12;

    points.push({
      baseX: x * radius * jitter,
      baseY: y * radius * jitter,
      baseZ: z * radius * jitter,
      x: x * radius * jitter,
      y: y * radius * jitter,
      z: z * radius * jitter,
      phase: Math.random() * Math.PI * 2,
      speed: 0.8 + Math.random() * 0.8,
      pulse: Math.random(),
      connections: []
    });
  }

  // Precompute connections based on proximity threshold
  const connectionDistance = radius * 0.44;
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      const dx = points[i].baseX - points[j].baseX;
      const dy = points[i].baseY - points[j].baseY;
      const dz = points[i].baseZ - points[j].baseZ;
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (dist < connectionDistance) {
        points[i].connections.push({ target: j, dist });
      }
    }
  }

  return points;
}

export default function CentralNetworkCanvas({ aiState = 'idle', onGlobeClick }) {
  const canvasRef = useRef(null);
  const stateRef = useRef({
    aiState,
    rotationX: 0.2,
    rotationY: 0,
    rotationZ: 0,
    targetRotationX: 0.2,
    targetRotationY: 0,
    mouseOffsetX: 0,
    mouseOffsetY: 0,
    time: 0,
    rippleRadius: 0,
    rippleAlpha: 0
  });

  // Keep stateRef up to date with prop
  useEffect(() => {
    stateRef.current.aiState = aiState;
  }, [aiState]);

  // Handle canvas click feedback
  const handleClick = useCallback((e) => {
    stateRef.current.rippleRadius = 10;
    stateRef.current.rippleAlpha = 0.8;
    if (onGlobeClick) {
      onGlobeClick();
    }
  }, [onGlobeClick]);

  // Handle subtle mouse parallax
  const handleMouseMove = useCallback((e) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const normX = (e.clientX - rect.left) / rect.width - 0.5;
    const normY = (e.clientY - rect.top) / rect.height - 0.5;
    stateRef.current.mouseOffsetX = normX * 0.3;
    stateRef.current.mouseOffsetY = normY * 0.3;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId;
    let width = 0;
    let height = 0;
    let globeRadius = 180;
    let nodes = [];
    const NUM_NODES = 150;

    // Synaptic pulses traveling along connections
    const pulses = Array.from({ length: 14 }, () => ({
      fromIdx: Math.floor(Math.random() * NUM_NODES),
      toIdx: 0,
      progress: Math.random(),
      speed: 0.015 + Math.random() * 0.02
    }));

    const updateDimensions = () => {
      const dpr = window.devicePixelRatio || 1;
      const displayWidth = canvas.clientWidth || window.innerWidth;
      const displayHeight = canvas.clientHeight || window.innerHeight;

      width = displayWidth;
      height = displayHeight;
      canvas.width = Math.floor(displayWidth * dpr);
      canvas.height = Math.floor(displayHeight * dpr);
      ctx.scale(dpr, dpr);

      // Adapt radius dynamically for mobile vs desktop
      const minDim = Math.min(displayWidth, displayHeight);
      globeRadius = minDim < 600 ? minDim * 0.28 : Math.min(220, minDim * 0.24);

      nodes = generateFibonacciSphere(NUM_NODES, globeRadius);

      // Initialize pulse targets
      pulses.forEach((p) => {
        if (nodes[p.fromIdx]?.connections.length > 0) {
          const randConn = nodes[p.fromIdx].connections[
            Math.floor(Math.random() * nodes[p.fromIdx].connections.length)
          ];
          p.toIdx = randConn.target;
        }
      });
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);

    // Render loop
    const render = () => {
      stateRef.current.time += 0.016;
      const t = stateRef.current.time;
      const currentAiState = stateRef.current.aiState;

      // Adjust rotation speed and dynamics based on AI state
      let speedY = 0.0035;
      let speedX = 0.0015;
      let waveAmp = 0.04;
      let waveFreq = 1.8;

      if (currentAiState === 'listening') {
        speedY = 0.002;
        speedX = 0.001;
        waveAmp = 0.06;
        waveFreq = 3.2;
      } else if (currentAiState === 'processing') {
        speedY = 0.011;
        speedX = 0.005;
        waveAmp = 0.08;
        waveFreq = 5.0;
      } else if (currentAiState === 'speaking') {
        speedY = 0.005;
        speedX = 0.002;
        // Harmonic vocal pulsation envelope
        const vocalEnvelope = 0.5 + 0.5 * Math.sin(t * 8) * Math.cos(t * 4.5);
        waveAmp = 0.05 + 0.06 * vocalEnvelope;
        waveFreq = 4.0;
      }

      stateRef.current.rotationY += speedY;
      stateRef.current.rotationX += speedX;

      // Subtle parallax blend
      const rotY = stateRef.current.rotationY + stateRef.current.mouseOffsetX;
      const rotX = stateRef.current.rotationX + stateRef.current.mouseOffsetY;

      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);

      const cx = width / 2;
      const cy = height / 2;
      const fov = 480;

      // Clear canvas with pure black
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, width, height);

      // Animate organic node displacement and project to 3D
      const projected = [];
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];

        // Complex organic wave motion across sphere surface
        const wave =
          Math.sin(t * waveFreq * n.speed + n.phase) *
          Math.cos(t * 1.2 + (n.baseY / globeRadius) * 3);
        const radiusFactor = 1 + wave * waveAmp;

        const curX = n.baseX * radiusFactor;
        const curY = n.baseY * radiusFactor;
        const curZ = n.baseZ * radiusFactor;

        // 3D Rotation (Y-axis then X-axis)
        // Y rotation
        const x1 = curX * cosY + curZ * sinY;
        const z1 = -curX * sinY + curZ * cosY;
        // X rotation
        const y2 = curY * cosX - z1 * sinX;
        const z2 = curY * sinX + z1 * cosX;

        // Perspective projection
        const scale = fov / (fov + z2);
        const projX = cx + x1 * scale;
        const projY = cy + y2 * scale;

        projected.push({
          x: projX,
          y: projY,
          z: z2,
          scale,
          origIndex: i
        });
      }

      // 1. Draw subtle background depth arcs / latitude rings for futuristic holographic wireframe
      ctx.save();
      ctx.lineWidth = 0.75;
      const ringAlpha = currentAiState === 'processing' ? 0.22 : 0.12;
      ctx.strokeStyle = `rgba(216, 75, 16, ${ringAlpha})`;

      // Draw 2 inclined orbital guide circles
      for (let ring = 0; ring < 2; ring++) {
        const ringAngle = t * (ring === 0 ? 0.003 : -0.002) + ring * Math.PI * 0.5;
        const tiltX = Math.cos(ringAngle) * 0.4;
        const tiltY = Math.sin(ringAngle) * 0.4;

        ctx.beginPath();
        for (let a = 0; a <= Math.PI * 2; a += 0.12) {
          const rx = Math.cos(a) * globeRadius * 1.02;
          const ry = Math.sin(a) * globeRadius * 1.02 * (0.35 + ring * 0.25);
          // rotate in 2D around center
          const cosR = Math.cos(tiltX);
          const sinR = Math.sin(tiltX);
          const px = cx + (rx * cosR - ry * sinR);
          const py = cy + (rx * sinR + ry * cosR);
          if (a === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.stroke();
      }
      ctx.restore();

      // 2. Draw Interconnected Network Chords (Wires)
      const maxDist2D = globeRadius * 0.75;
      for (let i = 0; i < nodes.length; i++) {
        const p1 = projected[i];
        const conns = nodes[i].connections;

        for (let c = 0; c < conns.length; c++) {
          const targetIdx = conns[c].target;
          if (targetIdx <= i) continue; // avoid duplicate lines
          const p2 = projected[targetIdx];

          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist2D = Math.sqrt(dx * dx + dy * dy);

          if (dist2D < maxDist2D) {
            // Depth modulation: front wires are brighter, back wires are faint
            const avgZ = (p1.z + p2.z) / 2;
            const depthRatio = (avgZ + globeRadius) / (2 * globeRadius); // 0 (back) to 1 (front)
            const clampedDepth = Math.max(0.1, Math.min(1.0, depthRatio));

            // State specific alpha adjustments
            let baseAlpha = 0.22;
            if (currentAiState === 'listening') baseAlpha = 0.28;
            if (currentAiState === 'processing') baseAlpha = 0.35;
            if (currentAiState === 'speaking') baseAlpha = 0.30;

            const lineAlpha = (1 - dist2D / maxDist2D) * clampedDepth * baseAlpha;

            if (lineAlpha > 0.02) {
              ctx.beginPath();
              ctx.moveTo(p1.x, p1.y);
              ctx.lineTo(p2.x, p2.y);
              ctx.lineWidth = clampedDepth > 0.6 ? 1.0 : 0.65;
              ctx.strokeStyle = `rgba(216, 75, 16, ${lineAlpha.toFixed(3)})`;
              ctx.stroke();
            }
          }
        }
      }

      // 3. Draw Synaptic Data Pulses (Traveling Packets)
      const pulseSpeedMultiplier = currentAiState === 'processing' ? 2.8 : currentAiState === 'speaking' ? 1.6 : 1.0;
      for (let p = 0; p < pulses.length; p++) {
        const pulse = pulses[p];
        pulse.progress += pulse.speed * pulseSpeedMultiplier;

        if (pulse.progress >= 1) {
          pulse.progress = 0;
          pulse.fromIdx = pulse.toIdx;
          const conns = nodes[pulse.fromIdx]?.connections;
          if (conns && conns.length > 0) {
            pulse.toIdx = conns[Math.floor(Math.random() * conns.length)].target;
          } else {
            pulse.fromIdx = Math.floor(Math.random() * NUM_NODES);
            pulse.toIdx = (pulse.fromIdx + 1) % NUM_NODES;
          }
        }

        const p1 = projected[pulse.fromIdx];
        const p2 = projected[pulse.toIdx];
        if (p1 && p2) {
          const px = p1.x + (p2.x - p1.x) * pulse.progress;
          const py = p1.y + (p2.y - p1.y) * pulse.progress;
          const pz = p1.z + (p2.z - p1.z) * pulse.progress;

          // Only draw if facing front or mid
          if (pz > -globeRadius * 0.4) {
            const pulseAlpha = Math.min(0.85, 0.4 + (pz + globeRadius) / (2 * globeRadius));
            ctx.beginPath();
            ctx.arc(px, py, 1.8, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(240, 110, 35, ${pulseAlpha.toFixed(2)})`;
            ctx.fill();
          }
        }
      }

      // 4. Draw Nodes (Vertices)
      for (let i = 0; i < projected.length; i++) {
        const p = projected[i];
        const depthRatio = (p.z + globeRadius) / (2 * globeRadius);
        const clampedDepth = Math.max(0.12, Math.min(1.0, depthRatio));

        // Node size and alpha based on 3D depth
        const radius = clampedDepth > 0.65 ? 1.8 : 1.1;
        let nodeAlpha = clampedDepth * 0.65;

        // Subtle pulsing for active states
        if (currentAiState === 'listening') {
          nodeAlpha *= 0.8 + 0.3 * Math.sin(t * 6 + i);
        } else if (currentAiState === 'processing') {
          nodeAlpha *= 0.7 + 0.45 * Math.sin(t * 12 + i * 2);
        } else if (currentAiState === 'speaking') {
          nodeAlpha *= 0.75 + 0.35 * Math.cos(t * 7 + i);
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(216, 75, 16, ${nodeAlpha.toFixed(3)})`;
        ctx.fill();
      }

      // 5. Special AI State Outer Ring / Wave Silhouettes
      // LISTENING: Expanding delicate acoustic soundwave rings
      if (currentAiState === 'listening') {
        const numWaves = 3;
        for (let w = 0; w < numWaves; w++) {
          const wavePhase = (t * 0.8 + w / numWaves) % 1;
          const ringR = globeRadius * (1.02 + wavePhase * 0.28);
          const ringA = (1 - wavePhase) * 0.32;

          ctx.beginPath();
          ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(216, 75, 16, ${ringA.toFixed(3)})`;
          ctx.lineWidth = 0.85;
          ctx.stroke();
        }
      }

      // PROCESSING: Micro orbital tick markers along the spherical perimeter
      if (currentAiState === 'processing') {
        ctx.save();
        const numTicks = 24;
        const tickAngleOffset = t * 1.5;
        const outerR = globeRadius * 1.12;
        for (let k = 0; k < numTicks; k++) {
          const ang = tickAngleOffset + (k / numTicks) * Math.PI * 2;
          const tickLen = k % 4 === 0 ? 5 : 2;
          const xStart = cx + Math.cos(ang) * outerR;
          const yStart = cy + Math.sin(ang) * outerR;
          const xEnd = cx + Math.cos(ang) * (outerR + tickLen);
          const yEnd = cy + Math.sin(ang) * (outerR + tickLen);

          ctx.beginPath();
          ctx.moveTo(xStart, yStart);
          ctx.lineTo(xEnd, yEnd);
          ctx.strokeStyle = `rgba(216, 75, 16, 0.28)`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
        ctx.restore();
      }

      // SPEAKING: Harmonic voice frequency amplitude oscillation along equator
      if (currentAiState === 'speaking') {
        ctx.save();
        ctx.beginPath();
        const segments = 48;
        const voiceBaseR = globeRadius * 1.08;
        for (let s = 0; s <= segments; s++) {
          const ang = (s / segments) * Math.PI * 2;
          const voiceMod = Math.sin(ang * 8 + t * 14) * Math.cos(ang * 3 - t * 8);
          const r = voiceBaseR + voiceMod * 6.5;
          const x = cx + Math.cos(ang) * r;
          const y = cy + Math.sin(ang) * r;
          if (s === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = 'rgba(216, 75, 16, 0.32)';
        ctx.lineWidth = 1.1;
        ctx.stroke();
        ctx.restore();
      }

      // 6. Interactive Click Ripple Feedback
      if (stateRef.current.rippleAlpha > 0.01) {
        stateRef.current.rippleRadius += 4.5;
        stateRef.current.rippleAlpha *= 0.94;

        ctx.beginPath();
        ctx.arc(cx, cy, stateRef.current.rippleRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(216, 75, 16, ${stateRef.current.rippleAlpha.toFixed(3)})`;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', updateDimensions);
    };
  }, []);

  return (
    <div
      className="central-network-container"
      onClick={handleClick}
      onMouseMove={handleMouseMove}
      title="FRIDAY Neural Core — Click to cycle AI state"
    >
      <canvas ref={canvasRef} className="central-network-canvas" />
    </div>
  );
}
