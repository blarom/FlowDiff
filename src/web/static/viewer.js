// FlowDiff Interactive Graph Viewer
// Uses D3.js for rendering and interaction

(function() {
    'use strict';

    let graphData = null;
    let svg, g, zoom;
    let selectedNode = null;

    // Initialize
    async function init() {
        try {
            // Fetch graph data
            const response = await fetch('/api/graph');
            if (!response.ok) {
                throw new Error('Failed to load graph data');
            }
            graphData = await response.json();

            // Update stats
            updateStats();

            // Setup SVG
            setupSVG();

            // Render graph
            render();

        } catch (error) {
            console.error('Error loading graph:', error);
            document.getElementById('graph-container').innerHTML =
                `<div class="loading">Error loading graph: ${error.message}</div>`;
        }
    }

    function updateStats() {
        const stats = document.getElementById('stats');
        const nodeCount = Object.keys(graphData.nodes).length;
        const edgeCount = graphData.edges.length;
        stats.textContent = `${nodeCount} nodes, ${edgeCount} edges`;
    }

    function setupSVG() {
        svg = d3.select('#graph');
        g = svg.append('g');

        // Setup zoom
        zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Setup controls
        d3.select('#zoom-in').on('click', () => {
            svg.transition().call(zoom.scaleBy, 1.3);
        });

        d3.select('#zoom-out').on('click', () => {
            svg.transition().call(zoom.scaleBy, 0.7);
        });

        d3.select('#zoom-reset').on('click', () => {
            svg.transition().call(zoom.transform, d3.zoomIdentity);
        });

        d3.select('#fit-view').on('click', fitToView);
    }

    function render() {
        // Clear previous
        g.selectAll('*').remove();

        // Define arrow markers with different orientations
        const defs = g.append('defs');

        // Create markers for different angles (we'll create them dynamically)
        // Base marker definition
        function createArrowMarker(id, angle) {
            defs.append('marker')
                .attr('id', id)
                .attr('viewBox', '0 0 10 10')
                .attr('refX', 10)  // Position tip at path end
                .attr('refY', 5)   // Center vertically
                .attr('markerWidth', 7)
                .attr('markerHeight', 7)
                .attr('orient', angle)  // Set specific angle
                .append('path')
                .attr('d', 'M 0 0 L 10 5 L 0 10 z')
                .attr('class', 'edge-arrow');
        }

        // Create markers for common directions
        createArrowMarker('arrow-right', 0);      // 0° - pointing right
        createArrowMarker('arrow-down', 90);      // 90° - pointing down
        createArrowMarker('arrow-left', 180);     // 180° - pointing left
        createArrowMarker('arrow-up', 270);       // 270° - pointing up (or -90)

        // Render edges first (so they're behind nodes)
        renderEdges();

        // Render nodes
        renderNodes();

        // Fit to view initially
        setTimeout(fitToView, 100);
    }

    function renderEdges() {
        const edgeGroup = g.append('g').attr('class', 'edges');

        graphData.edges.forEach(edge => {
            if (edge.points && edge.points.length >= 2) {
                // Use Graphviz's raw path points (they already end at node boundaries)
                const line = d3.line()
                    .x(d => d[0])
                    .y(d => d[1])
                    .curve(d3.curveLinear);

                // Calculate arrow direction based on last meaningful segment
                const markerId = getArrowMarkerId(edge.points);

                edgeGroup.append('path')
                    .attr('d', line(edge.points))
                    .attr('class', 'edge')
                    .attr('data-source', edge.source)
                    .attr('data-target', edge.target)
                    .attr('marker-end', `url(#${markerId})`);
            }
        });
    }

    function getArrowMarkerId(points) {
        // Find the last "meaningful" segment (filter out very short segments < 2px)
        // that might give incorrect angles
        const MIN_SEGMENT_LENGTH = 2;

        let last = points[points.length - 1];
        let prev = null;

        // Work backwards to find a segment that's long enough
        for (let i = points.length - 2; i >= 0; i--) {
            const dx = last[0] - points[i][0];
            const dy = last[1] - points[i][1];
            const length = Math.sqrt(dx * dx + dy * dy);

            if (length >= MIN_SEGMENT_LENGTH) {
                prev = points[i];
                break;
            }
        }

        if (!prev) {
            // Fallback: use second-to-last point even if segment is short
            prev = points[Math.max(0, points.length - 2)];
        }

        // Calculate angle in degrees
        const angle = Math.atan2(last[1] - prev[1], last[0] - prev[0]) * (180 / Math.PI);

        // Map angle to nearest cardinal direction (0°, 90°, 180°, 270°)
        // For orthogonal routing, angles should be close to these values
        if (angle >= -45 && angle < 45) {
            return 'arrow-right';  // 0° (pointing right)
        } else if (angle >= 45 && angle < 135) {
            return 'arrow-down';   // 90° (pointing down)
        } else if (angle >= 135 || angle < -135) {
            return 'arrow-left';   // 180° (pointing left)
        } else {
            return 'arrow-up';     // 270° (pointing up)
        }
    }

    function renderNodes() {
        const nodeGroup = g.append('g').attr('class', 'nodes');

        Object.entries(graphData.nodes).forEach(([nodeId, node]) => {
            const nodeG = nodeGroup.append('g')
                .attr('class', `node ${getNodeClass(nodeId)}`)
                .attr('data-id', nodeId)
                .attr('transform', `translate(${node.x - node.width/2}, ${node.y - node.height/2})`);

            // Rectangle
            nodeG.append('rect')
                .attr('width', node.width)
                .attr('height', node.height)
                .attr('rx', 5);

            // Label
            nodeG.append('text')
                .attr('x', node.width / 2)
                .attr('y', node.height / 2)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .text(node.label);

            // Interaction
            nodeG.on('click', () => onNodeClick(nodeId, node))
                  .on('mouseenter', (event) => showTooltip(event, nodeId, node))
                  .on('mouseleave', hideTooltip);
        });
    }

    function getNodeClass(nodeId) {
        // Determine node class from ID or data
        // For now, use simple heuristic: if it ends with number, likely collapsed
        const node = graphData.nodes[nodeId];
        if (node.label && node.label.includes('(')) {
            return 'folder';
        }
        return 'module';
    }

    function onNodeClick(nodeId, node) {
        // Toggle selection
        if (selectedNode === nodeId) {
            // Deselect
            selectedNode = null;
            clearHighlight();
        } else {
            // Select and highlight connections
            selectedNode = nodeId;
            highlightConnections(nodeId);
        }
    }

    function highlightConnections(nodeId) {
        // Clear previous
        clearHighlight();

        // Highlight node
        d3.selectAll('.node').classed('highlighted', false);
        d3.select(`.node[data-id="${nodeId}"]`).classed('highlighted', true);

        // Highlight connected edges
        const connectedEdges = graphData.edges.filter(e =>
            e.source === nodeId || e.target === nodeId
        );

        connectedEdges.forEach(edge => {
            d3.selectAll('.edge')
                .filter(function() {
                    const source = d3.select(this).attr('data-source');
                    const target = d3.select(this).attr('data-target');
                    return source === edge.source && target === edge.target;
                })
                .classed('highlighted', true);

            // Highlight connected nodes
            const otherNode = edge.source === nodeId ? edge.target : edge.source;
            d3.select(`.node[data-id="${otherNode}"]`).classed('highlighted', true);
        });
    }

    function clearHighlight() {
        d3.selectAll('.node').classed('highlighted', false);
        d3.selectAll('.edge').classed('highlighted', false);
    }

    function showTooltip(event, nodeId, node) {
        const tooltip = d3.select('#tooltip');

        // Build tooltip content with useful information
        let content = `<strong>${nodeId}</strong><br>`;

        // Show the Graphviz tooltip if available (has file count, LOC, type info)
        if (node.tooltip) {
            content += `${node.tooltip}`;
        } else {
            // Fallback: show basic info
            content += `Module path: ${nodeId}`;
        }

        tooltip.html(content)
               .classed('visible', true)
               .style('left', (event.pageX + 15) + 'px')
               .style('top', (event.pageY - 15) + 'px');
    }

    function hideTooltip() {
        d3.select('#tooltip').classed('visible', false);
    }

    function fitToView() {
        const bounds = g.node().getBBox();
        const parent = svg.node().parentElement;
        const fullWidth = parent.clientWidth;
        const fullHeight = parent.clientHeight;

        const width = bounds.width;
        const height = bounds.height;

        const midX = bounds.x + width / 2;
        const midY = bounds.y + height / 2;

        if (width === 0 || height === 0) return;

        // Calculate scale
        const scale = 0.9 / Math.max(width / fullWidth, height / fullHeight);

        // Calculate translate
        const translate = [
            fullWidth / 2 - scale * midX,
            fullHeight / 2 - scale * midY
        ];

        svg.transition()
           .duration(750)
           .call(
               zoom.transform,
               d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
           );
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            selectedNode = null;
            clearHighlight();
        } else if (event.key === '+' || event.key === '=') {
            svg.transition().call(zoom.scaleBy, 1.3);
        } else if (event.key === '-' || event.key === '_') {
            svg.transition().call(zoom.scaleBy, 0.7);
        } else if (event.key === '0') {
            svg.transition().call(zoom.transform, d3.zoomIdentity);
        } else if (event.key === 'f' || event.key === 'F') {
            fitToView();
        }
    });

    // Start
    init();
})();
