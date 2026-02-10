// Architecture Diagram - Interactive visualization
(function() {
    'use strict';

    let architectureData = null;
    let currentZoom = 1.0;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let originalViewBox = null;

    async function initArchitecture() {
        try {
            const response = await fetch('/api/architecture');

            if (response.status === 404) {
                console.log('[Architecture] No architecture data available');
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to load architecture data');
            }

            architectureData = await response.json();
            renderArchitectureDiagram();
            setupZoomAndPan();
            showArchitectureSection();
        } catch (error) {
            console.error('[Architecture] Error loading diagram:', error);
        }
    }

    /**
     * Find all architectural blocks that a function belongs to.
     * Returns array of block IDs.
     */
    function findBlocksForFunction(qualifiedName) {
        if (!architectureData || !architectureData.blocks) {
            return [];
        }

        const matchingBlocks = [];
        const normalizedName = qualifiedName.toLowerCase();

        for (const block of architectureData.blocks) {
            for (const prefix of block.functions) {
                if (matchesPrefix(normalizedName, prefix)) {
                    matchingBlocks.push(block.id);
                    console.log(`[Architecture] Matched "${qualifiedName}" to block "${block.id}" via prefix "${prefix}"`);
                    break;
                }
            }
        }

        if (matchingBlocks.length === 0) {
            console.warn(`[Architecture] No matches found for "${qualifiedName}"`);
        }

        return matchingBlocks;
    }

    /**
     * Check if a function name matches a prefix pattern.
     */
    function matchesPrefix(normalizedName, prefix) {
        // Normalize prefix: convert slashes to dots, remove extensions
        let normalizedPrefix = prefix.toLowerCase()
            .replace(/\//g, '.')
            .replace(/\.(py|sh|js|ts)$/g, '')
            .replace(/\.(py|sh|js|ts)\./g, '.')
            .replace(/::/g, '.')
            .replace(/\.+$/, '');

        // Empty prefix matches all
        if (normalizedPrefix === '') {
            return true;
        }

        // Exact prefix match
        if (normalizedName.startsWith(normalizedPrefix + '.') || normalizedName === normalizedPrefix) {
            return true;
        }

        // Check if prefix parts appear consecutively in name parts
        const nameParts = normalizedName.split('.');
        const prefixParts = normalizedPrefix.split('.');

        for (let i = 0; i <= nameParts.length - prefixParts.length; i++) {
            let allMatch = true;
            for (let j = 0; j < prefixParts.length; j++) {
                if (nameParts[i + j] !== prefixParts[j]) {
                    allMatch = false;
                    break;
                }
            }
            if (allMatch) {
                return true;
            }
        }

        return false;
    }

    /**
     * Render the SVG architecture diagram in the panel.
     */
    function renderArchitectureDiagram() {
        if (!architectureData || !architectureData.svg) {
            console.warn('[Architecture] No SVG data to render');
            return;
        }

        const container = document.getElementById('architecture-svg-container');
        if (!container) {
            console.error('[Architecture] SVG container not found');
            return;
        }

        container.innerHTML = architectureData.svg;

        const svg = container.querySelector('svg');
        if (svg) {
            setupSvgViewBox(svg);
        }

        addBlockClickHandlers();
        console.log('[Architecture] Diagram rendered');
    }

    /**
     * Setup SVG viewBox for proper scaling.
     */
    function setupSvgViewBox(svg) {
        if (!svg.getAttribute('viewBox')) {
            const width = svg.getAttribute('width');
            const height = svg.getAttribute('height');
            if (width && height) {
                const w = parseFloat(width);
                const h = parseFloat(height);
                svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
            }
        }

        const viewBox = svg.getAttribute('viewBox');
        if (viewBox) {
            const parts = viewBox.split(/\s+/).map(parseFloat);
            originalViewBox = {
                x: parts[0],
                y: parts[1],
                width: parts[2],
                height: parts[3]
            };
        }

        svg.removeAttribute('width');
        svg.removeAttribute('height');
        svg.style.width = '100%';
        svg.style.height = '100%';
    }

    /**
     * Setup zoom and pan controls.
     */
    function setupZoomAndPan() {
        const container = document.getElementById('architecture-svg-container');
        const svg = container ? container.querySelector('svg') : null;

        if (!svg || !container) {
            return;
        }

        setupZoomButtons();
        setupPanDrag(container);
        updateTransform();
    }

    function setupZoomButtons() {
        const zoomInBtn = document.getElementById('zoom-in-btn');
        const zoomOutBtn = document.getElementById('zoom-out-btn');
        const resetBtn = document.getElementById('reset-zoom-btn');
        const collapseBtn = document.getElementById('collapse-architecture-btn');

        if (zoomInBtn) zoomInBtn.onclick = () => zoomBy(0.2);
        if (zoomOutBtn) zoomOutBtn.onclick = () => zoomBy(-0.2);
        if (resetBtn) resetBtn.onclick = resetZoomAndPan;
        if (collapseBtn) collapseBtn.onclick = hideArchitectureSection;
    }

    function setupPanDrag(container) {
        container.addEventListener('mousedown', (e) => {
            if (e.button === 0) {
                isDragging = true;
                dragStartX = e.clientX;
                dragStartY = e.clientY;
                container.classList.add('grabbing');
                e.preventDefault();
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging && originalViewBox) {
                const deltaX = e.clientX - dragStartX;
                const deltaY = e.clientY - dragStartY;

                const containerRect = container.getBoundingClientRect();
                const scaleX = (originalViewBox.width / currentZoom) / containerRect.width;
                const scaleY = (originalViewBox.height / currentZoom) / containerRect.height;

                panX = deltaX * scaleX;
                panY = deltaY * scaleY;

                updateTransform();
            }
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                container.classList.remove('grabbing');
            }
        });
    }

    /**
     * Zoom in or out by delta amount.
     */
    function zoomBy(delta) {
        currentZoom = Math.max(0.1, Math.min(5.0, currentZoom + delta));
        updateTransform();
    }

    /**
     * Reset zoom to 100% and pan to origin.
     */
    function resetZoomAndPan() {
        currentZoom = 1.0;
        panX = 0;
        panY = 0;
        updateTransform();
    }

    /**
     * Update SVG viewBox based on current zoom and pan.
     */
    function updateTransform() {
        const container = document.getElementById('architecture-svg-container');
        const svg = container ? container.querySelector('svg') : null;

        if (!svg || !originalViewBox) {
            return;
        }

        const newWidth = originalViewBox.width / currentZoom;
        const newHeight = originalViewBox.height / currentZoom;
        const newX = originalViewBox.x - panX;
        const newY = originalViewBox.y - panY;

        svg.setAttribute('viewBox', `${newX} ${newY} ${newWidth} ${newHeight}`);

        const zoomLevelElem = document.getElementById('zoom-level');
        if (zoomLevelElem) {
            zoomLevelElem.textContent = `${Math.round(currentZoom * 100)}%`;
        }
    }

    /**
     * Add click handlers to SVG elements for interactive behavior.
     */
    function addBlockClickHandlers() {
        const svg = document.querySelector('#architecture-svg-container svg');
        if (!svg) {
            return;
        }

        const nodes = svg.querySelectorAll('g.node');
        nodes.forEach(node => {
            node.style.cursor = 'pointer';

            const title = node.querySelector('title');
            const blockId = title ? title.textContent.trim() : null;

            if (blockId) {
                node.addEventListener('click', () => handleBlockClick(blockId));
                node.addEventListener('mouseenter', () => highlightBlock(blockId, true));
                node.addEventListener('mouseleave', () => highlightBlock(blockId, false));
            }
        });
    }

    /**
     * Handle click on an architectural block.
     */
    function handleBlockClick(blockId) {
        const block = architectureData.blocks.find(b => b.id === blockId);
        if (!block) {
            return;
        }

        highlightBlockManually(blockId, true);
        showBlockInfo(block);
    }

    /**
     * Find the SVG shape element for a given block ID.
     */
    function findBlockShape(blockId) {
        const svg = document.querySelector('#architecture-svg-container svg');
        if (!svg) {
            return null;
        }

        const nodes = svg.querySelectorAll('g.node');
        for (const node of nodes) {
            const title = node.querySelector('title');
            if (title && title.textContent.trim() === blockId) {
                return node.querySelector('polygon') ||
                       node.querySelector('ellipse') ||
                       node.querySelector('rect');
            }
        }
        return null;
    }

    /**
     * Apply highlight styling to a shape element.
     */
    function applyHighlightStyle(shape, color, strokeWidth, shadowOpacity) {
        if (!shape.dataset.originalStroke) {
            shape.dataset.originalStroke = shape.getAttribute('stroke') || 'black';
            shape.dataset.originalStrokeWidth = shape.getAttribute('stroke-width') || '1';
        }

        shape.style.stroke = color;
        shape.style.strokeWidth = strokeWidth;
        shape.style.filter = `drop-shadow(0 0 ${strokeWidth === '10' ? '15' : '12'}px rgba(${shadowOpacity}))`;
    }

    /**
     * Remove highlight styling from a shape element.
     */
    function removeHighlightStyle(shape) {
        if (shape.dataset.originalStroke) {
            shape.setAttribute('stroke', shape.dataset.originalStroke);
            shape.setAttribute('stroke-width', shape.dataset.originalStrokeWidth);
            delete shape.dataset.originalStroke;
            delete shape.dataset.originalStrokeWidth;
        }
        shape.style.stroke = '';
        shape.style.strokeWidth = '';
        shape.style.filter = '';
    }

    /**
     * Highlight a manually selected block with green color.
     */
    function highlightBlockManually(blockId, isSelected) {
        const shape = findBlockShape(blockId);
        if (!shape) {
            return;
        }

        if (isSelected) {
            applyHighlightStyle(shape, '#27ae60', '10', '39, 174, 96, 0.9');
        } else {
            removeHighlightStyle(shape);
        }
    }

    /**
     * Display information about an architectural block.
     */
    function showBlockInfo(block) {
        const infoHtml = `
            <div class="block-info-popup">
                <h3>${block.label}</h3>
                <p>${block.description}</p>
                <p><strong>Function Patterns:</strong></p>
                <ul>
                    ${block.functions.map(f => `<li><code>${f}</code></li>`).join('')}
                </ul>
            </div>
        `;
        showArchitectureToast(infoHtml, 5000);
    }

    /**
     * Show a temporary toast message with block information.
     */
    function showArchitectureToast(html, duration = 3000) {
        const existing = document.querySelector('.architecture-toast');
        if (existing) {
            existing.remove();
        }

        const toast = document.createElement('div');
        toast.className = 'architecture-toast';
        toast.innerHTML = html;
        toast.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            background: white;
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            max-width: 400px;
            animation: slideInRight 0.3s ease;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    /**
     * Highlight or unhighlight an architectural block.
     */
    function highlightBlock(blockId, isHighlighted) {
        const shape = findBlockShape(blockId);

        if (!shape) {
            console.warn(`[Architecture] No shape found for blockId: "${blockId}"`);
            return;
        }

        if (isHighlighted) {
            applyHighlightStyle(shape, '#3498db', '8', '52, 152, 219, 0.8');
            console.log(`[Architecture] Applied highlight to block: "${blockId}"`);
        } else {
            removeHighlightStyle(shape);
        }
    }

    /**
     * Show the architecture section at the bottom of the page.
     */
    function showArchitectureSection() {
        const section = document.getElementById('architecture-section');
        const panel = document.getElementById('architecture-panel');
        const showBtn = document.getElementById('show-architecture-btn');

        if (section) {
            section.style.display = 'block';
        }
        if (showBtn) {
            showBtn.style.display = 'none';
        }

        if (panel) {
            const updatePanelHeight = () => {
                const width = panel.offsetWidth;
                const height = width / 1.618;
                panel.style.height = `${height}px`;
                console.log(`[Architecture] Panel sized: ${width}px x ${height}px (golden ratio)`);
            };

            updatePanelHeight();
            window.addEventListener('resize', updatePanelHeight);
        }
    }

    /**
     * Hide the architecture section.
     */
    function hideArchitectureSection() {
        const section = document.getElementById('architecture-section');
        const showBtn = document.getElementById('show-architecture-btn');

        if (section) {
            section.style.display = 'none';
        }
        if (showBtn) {
            showBtn.style.display = 'inline-block';
        }
    }

    /**
     * Called when a function is selected in the call tree.
     * Highlights all corresponding architectural blocks.
     */
    function onFunctionSelected(qualifiedName) {
        console.log('[Architecture] onFunctionSelected called with:', qualifiedName);

        if (!architectureData) {
            console.warn('[Architecture] No architecture data available');
            return;
        }

        clearAllBlockHighlights();

        const blockIds = findBlocksForFunction(qualifiedName);
        console.log('[Architecture] Found matching blocks:', blockIds);

        if (blockIds.length > 0) {
            blockIds.forEach(blockId => {
                console.log('[Architecture] Attempting to highlight block:', blockId);
                highlightBlock(blockId, true);
            });
        } else {
            console.warn('[Architecture] No matching blocks found for function:', qualifiedName);
            if (architectureData.blocks) {
                console.log('[Architecture] Available blocks:', architectureData.blocks.map(b => ({
                    id: b.id,
                    label: b.label,
                    functions: b.functions
                })));
            }
        }
    }

    /**
     * Clear all block highlights in the diagram.
     */
    function clearAllBlockHighlights() {
        const svg = document.querySelector('#architecture-svg-container svg');
        if (!svg) {
            return;
        }

        const shapes = svg.querySelectorAll('polygon, ellipse, rect');
        shapes.forEach(shape => {
            shape.style.stroke = '';
            shape.style.strokeWidth = '';
            shape.style.filter = '';
        });
    }

    /**
     * Scroll the SVG container to show a specific block.
     */
    function scrollToBlock(blockId) {
        const svg = document.querySelector('#architecture-svg-container svg');
        if (!svg) {
            return;
        }

        const nodes = svg.querySelectorAll('g.node');
        for (const node of nodes) {
            const title = node.querySelector('title');
            if (title && title.textContent.trim() === blockId) {
                node.scrollIntoView({ behavior: 'smooth', block: 'center' });
                break;
            }
        }
    }

    // Export functions for use by other scripts
    window.initArchitecture = initArchitecture;
    window.onFunctionSelected = onFunctionSelected;

    // Setup show architecture button listener
    const showArchitectureBtn = document.getElementById('show-architecture-btn');
    if (showArchitectureBtn) {
        showArchitectureBtn.onclick = showArchitectureSection;
    }

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initArchitecture);
    } else {
        initArchitecture();
    }

})();
