# Architecture Visualization Redesign

## Changes Made

### 1. Layout Change: From Left Panel to Bottom Section

**Before:**
- Fixed left panel (300px wide)
- Slide-in/slide-out toggle
- Position: fixed, left: 0

**After:**
- Bottom section (full width)
- Height: 38vh (golden ratio ~38.2%)
- Always visible when architecture data is available
- Width matches header width

### 2. Zoom and Pan Controls Added

#### Button Controls
- **Zoom In (+)**: Increase zoom by 20%
- **Zoom Out (-)**: Decrease zoom by 20%
- **Reset**: Return to 100% zoom and center position
- **Collapse (▼)**: Hide architecture section
- **Zoom Level Display**: Shows current zoom percentage (e.g., "100%")

#### Mouse Controls
- **Mouse Wheel**: Scroll up to zoom in, scroll down to zoom out (10% increments)
- **Click and Drag**: Pan the diagram by clicking and dragging
- **Cursor Feedback**: Changes to "grab" cursor when hovering, "grabbing" when dragging

#### Zoom Range
- Minimum: 10% (0.1x)
- Maximum: 500% (5.0x)

### 3. Technical Implementation

#### CSS Changes (`diff.html`)
```css
/* Architecture Section - Bottom */
.architecture-section {
    width: 100%;
    background: white;
    border-top: 3px solid #ddd;
    margin-top: 2rem;
}

.architecture-panel {
    width: 100%;
    height: 38vh;  /* Golden ratio */
    overflow: hidden;
}

#architecture-svg-container {
    cursor: grab;
    overflow: hidden;
}

#architecture-svg-container.grabbing {
    cursor: grabbing;
}

#architecture-svg-container svg {
    transition: transform 0.2s ease;
    transform-origin: top left;
}
```

#### JavaScript Changes (`architecture.js`)

**New Functions:**
- `setupZoomAndPan()`: Initialize all zoom/pan event listeners
- `zoomBy(delta)`: Adjust zoom level by delta amount
- `resetZoomAndPan()`: Reset to 100% zoom and center position
- `updateTransform()`: Apply CSS transform to SVG element
- `showArchitectureSection()`: Show the bottom section
- `hideArchitectureSection()`: Hide the bottom section (collapse)

**Removed Functions:**
- `showArchitecturePanel()`: Replaced with simpler show/hide
- `hideArchitecturePanel()`: Replaced with simpler show/hide
- `toggleArchitecturePanel()`: No longer needed (direct hide on collapse)

**State Variables:**
```javascript
let currentZoom = 1.0;
let panX = 0;
let panY = 0;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
```

### 4. User Experience Improvements

1. **More Space**: Full-width layout provides much more room for the diagram
2. **Golden Ratio Aesthetics**: 38vh height creates visually pleasing proportions
3. **Flexible Viewing**: Zoom and pan allow exploring large diagrams
4. **Intuitive Controls**: Both buttons and mouse controls for accessibility
5. **Visual Feedback**: Grab/grabbing cursor states, real-time zoom percentage
6. **Smooth Transitions**: 0.2s ease transform for smooth zoom/pan

### 5. Preserved Features

- ✅ Block clicking (shows tooltip with block info)
- ✅ Block hover highlighting (orange glow effect)
- ✅ Function-to-block mapping (highlights block when function selected)
- ✅ Block information tooltips (label, description, function patterns)
- ✅ SVG diagram generation via Graphviz

## Usage

Generate architecture diagram with:
```bash
flowdiff analyze . --generate-architecture
# or
flowdiff analyze . --arch
```

The architecture diagram will appear at the bottom of the page below the call tree and changes panel.

## Files Modified

1. `src/web/static/diff.html` - CSS and HTML for bottom section layout
2. `src/web/static/architecture.js` - Zoom/pan implementation and section show/hide

## Testing Checklist

- [ ] Architecture section appears at bottom (not left side)
- [ ] Width matches header width (100%)
- [ ] Height is approximately 38% of viewport (golden ratio)
- [ ] Zoom in button (+) works
- [ ] Zoom out button (-) works
- [ ] Reset button returns to 100%
- [ ] Zoom level display updates correctly
- [ ] Mouse wheel zoom works (scroll up = zoom in)
- [ ] Click-and-drag panning works
- [ ] Cursor changes to grab/grabbing appropriately
- [ ] Collapse button (▼) hides the section
- [ ] Block clicking shows tooltip
- [ ] Block hover highlighting works
- [ ] Function selection highlights corresponding block
- [ ] Zoom range limited to 10%-500%
