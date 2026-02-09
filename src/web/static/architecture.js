// Architecture Diagram - Interactive visualization
(function() {
    'use strict';

    let architectureData = null;
    let functionToBlockMap = {};

    // Initialize architecture diagram
    async function initArchitecture() {
        try {
            const response = await fetch('/api/architecture');

            if (response.status === 404) {
                // No architecture data available
                console.log('[Architecture] No architecture data available');
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to load architecture data');
            }

            architectureData = await response.json();

            // Build function-to-block mapping
            buildFunctionToBlockMap();

            // Render architecture diagram
            renderArchitectureDiagram();

            // Show the panel
            showArchitecturePanel();

        } catch (error) {
            console.error('[Architecture] Error loading diagram:', error);
        }
    }

    function buildFunctionToBlockMap() {
        /**
         * Build mapping from function prefixes to block IDs.
         *
         * Example:
         * {
         *   "api::": "api_layer",
         *   "analyzer::": "analyzer_core",
         *   ...
         * }
         */
        functionToBlockMap = {};

        if (!architectureData || !architectureData.blocks) {
            return;
        }

        for (const block of architectureData.blocks) {
            for (const prefix of block.functions) {
                functionToBlockMap[prefix] = block.id;
            }
        }
    }

    function findBlockForFunction(qualifiedName) {
        /**
         * Find which architectural block a function belongs to.
         *
         * Args:
         *     qualifiedName: Qualified function name (e.g., "api::analyze")
         *
         * Returns:
         *     Block ID or null
         */
        if (!functionToBlockMap) {
            return null;
        }

        // Check each prefix to see if it matches
        for (const [prefix, blockId] of Object.entries(functionToBlockMap)) {
            // Handle empty prefix (matches all)
            if (prefix === "" || qualifiedName.startsWith(prefix)) {
                return blockId;
            }
        }

        return null;
    }

    function renderArchitectureDiagram() {
        /**
         * Render the SVG architecture diagram in the panel.
         */
        if (!architectureData || !architectureData.svg) {
            console.warn('[Architecture] No SVG data to render');
            return;
        }

        const container = document.getElementById('architecture-svg-container');
        if (!container) {
            console.error('[Architecture] SVG container not found');
            return;
        }

        // Insert SVG
        container.innerHTML = architectureData.svg;

        // Add click handlers to blocks
        addBlockClickHandlers();

        console.log('[Architecture] Diagram rendered');
    }

    function addBlockClickHandlers() {
        /**
         * Add click handlers to SVG elements for interactive behavior.
         */
        const svg = document.querySelector('#architecture-svg-container svg');
        if (!svg) {
            return;
        }

        // Find all graph nodes (blocks)
        const nodes = svg.querySelectorAll('g.node');

        nodes.forEach(node => {
            // Make clickable
            node.style.cursor = 'pointer';

            // Extract block ID from the node title or id attribute
            const title = node.querySelector('title');
            const blockId = title ? title.textContent.trim() : null;

            if (blockId) {
                node.addEventListener('click', () => {
                    handleBlockClick(blockId);
                });

                node.addEventListener('mouseenter', () => {
                    highlightBlock(blockId, true);
                });

                node.addEventListener('mouseleave', () => {
                    highlightBlock(blockId, false);
                });
            }
        });
    }

    function handleBlockClick(blockId) {
        /**
         * Handle click on an architectural block.
         * Shows info about the block and its functions.
         */
        const block = architectureData.blocks.find(b => b.id === blockId);
        if (!block) {
            return;
        }

        // Show block information in a tooltip or modal
        showBlockInfo(block);
    }

    function showBlockInfo(block) {
        /**
         * Display information about an architectural block.
         */
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

        // Simple toast-style notification
        showArchitectureToast(infoHtml, 5000);
    }

    function showArchitectureToast(html, duration = 3000) {
        /**
         * Show a temporary toast message with block information.
         */
        // Remove existing toast if any
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

    function highlightBlock(blockId, isHighlighted) {
        /**
         * Highlight or unhighlight an architectural block.
         */
        const svg = document.querySelector('#architecture-svg-container svg');
        if (!svg) {
            return;
        }

        // Find the node with this block ID
        const nodes = svg.querySelectorAll('g.node');
        nodes.forEach(node => {
            const title = node.querySelector('title');
            if (title && title.textContent.trim() === blockId) {
                const polygon = node.querySelector('polygon');
                const ellipse = node.querySelector('ellipse');
                const rect = node.querySelector('rect');

                const shape = polygon || ellipse || rect;

                if (shape) {
                    if (isHighlighted) {
                        shape.style.stroke = '#f0ad4e';
                        shape.style.strokeWidth = '3';
                        shape.style.filter = 'drop-shadow(0 0 8px rgba(240, 173, 78, 0.6))';
                    } else {
                        shape.style.stroke = '';
                        shape.style.strokeWidth = '';
                        shape.style.filter = '';
                    }
                }
            }
        });
    }

    function showArchitecturePanel() {
        /**
         * Show the architecture panel in the UI.
         */
        const panel = document.getElementById('architecture-panel');
        const toggleBtn = document.getElementById('architecture-toggle-btn');

        if (panel) {
            panel.style.display = 'block';
            // Auto-show the panel on load
            panel.classList.add('visible');
        }

        if (toggleBtn) {
            toggleBtn.style.display = 'block';
        }
    }

    function hideArchitecturePanel() {
        /**
         * Hide the architecture panel in the UI.
         */
        const panel = document.getElementById('architecture-panel');
        if (panel) {
            panel.style.display = 'none';
        }
    }

    function onFunctionSelected(qualifiedName) {
        /**
         * Called when a function is selected in the call tree.
         * Highlights the corresponding architectural block.
         */
        if (!architectureData) {
            return;
        }

        // Clear previous highlights
        clearAllBlockHighlights();

        // Find which block this function belongs to
        const blockId = findBlockForFunction(qualifiedName);

        if (blockId) {
            highlightBlock(blockId, true);

            // Auto-scroll to the block in the SVG (if needed)
            scrollToBlock(blockId);
        }
    }

    function clearAllBlockHighlights() {
        /**
         * Clear all block highlights in the diagram.
         */
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

    function scrollToBlock(blockId) {
        /**
         * Scroll the SVG container to show a specific block.
         */
        const svg = document.querySelector('#architecture-svg-container svg');
        if (!svg) {
            return;
        }

        // Find the node
        const nodes = svg.querySelectorAll('g.node');
        for (const node of nodes) {
            const title = node.querySelector('title');
            if (title && title.textContent.trim() === blockId) {
                // Scroll into view
                node.scrollIntoView({ behavior: 'smooth', block: 'center' });
                break;
            }
        }
    }

    function toggleArchitecturePanel() {
        /**
         * Toggle the visibility of the architecture panel.
         */
        const panel = document.getElementById('architecture-panel');
        if (!panel) {
            return;
        }

        panel.classList.toggle('visible');
    }

    // Export functions for use by other scripts
    window.initArchitecture = initArchitecture;
    window.onFunctionSelected = onFunctionSelected;
    window.toggleArchitecturePanel = toggleArchitecturePanel;

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initArchitecture);
    } else {
        initArchitecture();
    }

})();
