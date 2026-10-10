import React from 'react';

export default function HandCursorOverlay({ handPointers = [], isResizing = false }) {
  if (!handPointers || handPointers.length === 0) return null;

  const hasTwoHands = handPointers.length >= 2;

  return (
    <div className="hand-cursor-overlay-layer">
      {/* If 2 hands are present and zooming, draw a faint connecting line */}
      {hasTwoHands && (
        <svg className="two-hand-connector-svg">
          <line
            x1={handPointers[0].x}
            y1={handPointers[0].y}
            x2={handPointers[1].x}
            y2={handPointers[1].y}
            stroke="rgba(216, 75, 16, 0.45)"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
        </svg>
      )}

      {/* Render hand reticles */}
      {handPointers.map((hand) => {
        const { x, y, isPinching, handIndex } = hand;
        return (
          <div
            key={handIndex}
            className={`hand-reticle ${isPinching ? 'pinching' : ''}`}
            style={{
              transform: `translate3d(${x}px, ${y}px, 0)`
            }}
          >
            {/* Outer subtle target ring */}
            <div className="reticle-ring" />
            {/* Central focal node */}
            <div className="reticle-dot" />
            {/* Subtle pinch ripple feedback */}
            {isPinching && <div className="reticle-pulse" />}
          </div>
        );
      })}
    </div>
  );
}
