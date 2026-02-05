// FlowDiff Interactive Call Tree
(function() {
    'use strict';

    // Make window.treeData global for diff-panel.js
    window.window.treeData = null;
    let expandedNodes = new Set();
    let searchMatches = [];
    let currentSearchIndex = 0;
    let testsHidden = false;

    // Initialize
    async function init() {
        try {
            // Fetch call tree data
            const response = await fetch('/api/tree');
            if (!response.ok) {
                throw new Error('Failed to load call tree data');
            }
            window.window.treeData = await response.json();

            // Update stats
            updateStats();

            // Render tree
            renderTree();

            // Setup event listeners
            setupEventListeners();

            // Load saved HTML path banner
            await loadSavedHtmlPath();

        } catch (error) {
            console.error('Error loading tree:', error);
            document.getElementById('call-tree').innerHTML =
                `<div class="loading">Error loading call tree: ${error.message}</div>`;
        }
    }

    async function loadSavedHtmlPath() {
        try {
            console.log('[FlowDiff] Fetching saved HTML path...');
            const response = await fetch('/api/saved-html-path');

            if (!response.ok) {
                console.warn('[FlowDiff] API response not OK:', response.status);
                return;
            }

            const data = await response.json();
            console.log('[FlowDiff] Saved HTML path data:', data);

            if (data.html_path && data.file_url) {
                const banner = document.getElementById('saved-report-banner');
                const link = document.getElementById('saved-report-link');

                if (!banner || !link) {
                    console.error('[FlowDiff] Banner elements not found in DOM');
                    return;
                }

                // Extract just the filename for display
                const filename = data.html_path.split('/').pop();
                link.href = data.file_url;
                link.textContent = filename;

                // Show banner
                banner.classList.remove('hidden');
                console.log('[FlowDiff] Banner displayed:', filename);
            } else {
                console.warn('[FlowDiff] No html_path or file_url in response');
            }
        } catch (error) {
            console.error('[FlowDiff] Error loading saved HTML path:', error);
        }
    }

    function closeBanner() {
        document.getElementById('saved-report-banner').classList.add('hidden');
    }

    function updateStats() {
        document.getElementById('project-name').textContent = window.treeData.metadata.project;
        document.getElementById('function-count').textContent = `${window.treeData.metadata.function_count} functions`;
        document.getElementById('entry-points').textContent = `${window.treeData.trees.length} entry points`;
    }

    function renderTree() {
        const container = document.getElementById('call-tree');
        container.innerHTML = '';

        // Render each entry point tree as a separate collapsed section
        window.treeData.trees.forEach((tree, index) => {
            const treeSection = document.createElement('div');
            treeSection.className = 'entry-point-tree';

            // Mark test trees
            const fileName = tree.function.file_name.toLowerCase();
            const funcName = tree.function.name.toLowerCase();
            if (fileName.includes('test') || funcName.includes('test')) {
                treeSection.dataset.isTest = 'true';
                if (testsHidden) {
                    treeSection.classList.add('hidden-test');
                }
            }

            const treeElement = renderNode(tree, 0, `tree-${index}`);
            treeSection.appendChild(treeElement);

            container.appendChild(treeSection);
        });
    }

    function renderNode(node, depth, path) {
        const div = document.createElement('div');
        div.className = 'tree-node-container';
        div.dataset.path = path;

        // Create node element
        const nodeDiv = document.createElement('div');
        nodeDiv.className = 'tree-node';
        nodeDiv.dataset.depth = depth;
        if (node.children && node.children.length > 0) {
            nodeDiv.classList.add('has-children');
        }
        // Highlight changed functions
        if (node.function.has_changes) {
            nodeDiv.classList.add('has-changes');
        }

        // Indentation
        for (let i = 0; i < depth; i++) {
            const indent = document.createElement('span');
            indent.className = 'tree-indent';
            indent.textContent = '│';
            nodeDiv.appendChild(indent);
        }

        // Expand/collapse toggle
        const expand = document.createElement('span');
        expand.className = 'tree-expand';
        if (node.children && node.children.length > 0) {
            expand.classList.add('collapsed');
            expand.onclick = (e) => {
                e.stopPropagation();
                toggleNode(path);
            };
        } else {
            expand.classList.add('leaf');
        }
        nodeDiv.appendChild(expand);

        // Icon
        const icon = document.createElement('span');
        icon.className = 'tree-icon';
        // Use server icon for script entry points
        if (node.function.name.startsWith('<script:')) {
            icon.textContent = '🚀';  // Rocket for server scripts
        } else {
            icon.textContent = node.function.is_entry_point ? '🎯' : '📦';
        }
        nodeDiv.appendChild(icon);

        // Label
        const label = document.createElement('span');
        label.className = 'tree-label';
        label.onclick = () => toggleNode(path);

        // Function name with file prefix (e.g., "test_sqlite::main")
        const funcName = document.createElement('span');
        funcName.className = 'function-name';
        funcName.dataset.qualifiedName = node.function.qualified_name;  // For diff-panel click navigation
        const fileName = node.function.file_name.replace('.py', '');

        // Handle script entry points specially
        let displayName = node.function.name;
        if (displayName.startsWith('<script:')) {
            // Extract script name: "<script:server>" -> "server"
            displayName = displayName.replace('<script:', '').replace('>', '');
            funcName.textContent = `${fileName} [script]`;
        } else {
            funcName.textContent = `${fileName}::${displayName}`;
        }

        label.appendChild(funcName);

        // Don't show parameters, return type, or file location in tree - they're in the tooltip

        nodeDiv.appendChild(label);

        // Info icon
        const infoIcon = document.createElement('span');
        infoIcon.className = 'info-icon';
        infoIcon.textContent = 'ⓘ';
        infoIcon.onclick = (e) => {
            e.stopPropagation();
            showInfo(node.function);
        };
        nodeDiv.appendChild(infoIcon);

        div.appendChild(nodeDiv);

        // Children container
        if (node.children && node.children.length > 0) {
            const childrenDiv = document.createElement('div');
            childrenDiv.className = 'tree-children collapsed';
            childrenDiv.dataset.path = path;

            node.children.forEach((child, index) => {
                const childPath = `${path}-${index}`;
                const childElement = renderNode(child, depth + 1, childPath);
                childrenDiv.appendChild(childElement);
            });

            div.appendChild(childrenDiv);
        }

        return div;
    }

    function toggleNode(path) {
        const container = document.querySelector(`.tree-node-container[data-path="${path}"]`);
        if (!container) return;

        const expand = container.querySelector('.tree-expand');
        const children = container.querySelector('.tree-children');

        if (!children || !expand) return;

        if (expand.classList.contains('collapsed')) {
            // Expand
            expand.classList.remove('collapsed');
            expand.classList.add('expanded');
            children.classList.remove('collapsed');
            expandedNodes.add(path);
        } else {
            // Collapse
            expand.classList.remove('expanded');
            expand.classList.add('collapsed');
            children.classList.add('collapsed');
            expandedNodes.delete(path);
        }
    }

    function showInfo(func) {
        const panel = document.getElementById('info-panel');
        const overlay = document.getElementById('info-panel-overlay');

        panel.classList.remove('hidden');
        overlay.classList.add('active');

        // Update panel content
        const fileName = func.file_name.replace('.py', '');

        // Handle script entry points specially in title
        let displayTitle;
        if (func.name.startsWith('<script:')) {
            displayTitle = `${fileName} [script entry point]`;
        } else {
            displayTitle = `${fileName}::${func.name}`;
        }
        document.getElementById('info-title').textContent = displayTitle;

        // Location with wrapped path
        document.getElementById('info-location').innerHTML = `
            <code style="word-wrap: break-word; white-space: pre-wrap;">${func.file_path}:${func.line_number}</code>
        `;

        // Signature with return type
        // For scripts, show a special message
        if (func.name.startsWith('<script:')) {
            document.getElementById('info-signature').innerHTML = `
                <code>Script entry point (launches server/application)</code>
            `;
        } else {
            const params = func.parameters.length > 0 ? func.parameters.join(', ') : '';
            const returnType = func.return_type ? ` → ${func.return_type}` : '';
            document.getElementById('info-signature').innerHTML = `
                <code>${func.name}(${params})${returnType}</code>
            `;
        }

        // Parameters
        if (func.parameters && func.parameters.length > 0) {
            const paramsList = func.parameters.map(p => `<li><code>${p}</code></li>`).join('');
            document.getElementById('info-parameters').innerHTML = `
                <ul class="info-list">${paramsList}</ul>
            `;
        } else {
            document.getElementById('info-parameters').innerHTML = `
                <span class="empty-state">No parameters</span>
            `;
        }

        // Documentation
        if (func.documentation && func.documentation.trim()) {
            // Escape HTML and preserve newlines
            const escapedDoc = func.documentation
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\n/g, '<br>');
            document.getElementById('info-documentation').innerHTML = `
                <div class="documentation-text">${escapedDoc}</div>
            `;
        } else {
            document.getElementById('info-documentation').innerHTML = `
                <span class="empty-state">No documentation</span>
            `;
        }

        // Local variables
        if (func.local_variables && func.local_variables.length > 0) {
            const varsList = func.local_variables.map(v => `<li><code>${v}</code></li>`).join('');
            document.getElementById('info-locals').innerHTML = `
                <ul class="info-list">${varsList}</ul>
            `;
        } else {
            document.getElementById('info-locals').innerHTML = `
                <span class="empty-state">No local variables</span>
            `;
        }

        // Calls
        if (func.calls && func.calls.length > 0) {
            const callsList = func.calls.map(c => `<li><code>${c}</code></li>`).join('');
            document.getElementById('info-calls').innerHTML = `
                <ul class="info-list">${callsList}</ul>
            `;
        } else {
            document.getElementById('info-calls').innerHTML = `
                <span class="empty-state">No function calls</span>
            `;
        }

        // Called by
        if (func.called_by && func.called_by.length > 0) {
            const calledByList = func.called_by.map(c => `<li><code>${c}</code></li>`).join('');
            document.getElementById('info-called-by').innerHTML = `
                <ul class="info-list">${calledByList}</ul>
            `;
        } else {
            document.getElementById('info-called-by').innerHTML = `
                <span class="empty-state">Entry point (not called by anyone)</span>
            `;
        }
    }

    function closeInfoPanel() {
        document.getElementById('info-panel').classList.add('hidden');
        document.getElementById('info-panel-overlay').classList.remove('active');
    }

    function toggleTests() {
        testsHidden = !testsHidden;
        const btn = document.getElementById('toggle-tests');

        if (testsHidden) {
            btn.textContent = 'Show Tests';
            btn.classList.add('active');
            document.querySelectorAll('.entry-point-tree[data-is-test="true"]').forEach(tree => {
                tree.classList.add('hidden-test');
            });
        } else {
            btn.textContent = 'Hide Tests';
            btn.classList.remove('active');
            document.querySelectorAll('.entry-point-tree[data-is-test="true"]').forEach(tree => {
                tree.classList.remove('hidden-test');
            });
        }
    }

    function setupEventListeners() {
        // Close banner (optional)
        const closeBannerBtn = document.getElementById('close-banner');
        if (closeBannerBtn) {
            closeBannerBtn.onclick = closeBanner;
        }

        // Close info panel
        document.getElementById('close-info').onclick = closeInfoPanel;

        // Click outside info panel to close
        document.getElementById('info-panel-overlay').onclick = closeInfoPanel;

        // Expand all
        document.getElementById('expand-all').onclick = () => {
            document.querySelectorAll('.tree-expand.collapsed').forEach(expand => {
                const container = expand.closest('.tree-node-container');
                if (container) {
                    toggleNode(container.dataset.path);
                }
            });
        };

        // Collapse all
        document.getElementById('collapse-all').onclick = () => {
            document.querySelectorAll('.tree-expand.expanded').forEach(expand => {
                const container = expand.closest('.tree-node-container');
                if (container) {
                    toggleNode(container.dataset.path);
                }
            });
        };

        // Toggle tests (optional - only in index.html)
        const toggleTestsBtn = document.getElementById('toggle-tests');
        if (toggleTestsBtn) {
            toggleTestsBtn.onclick = toggleTests;
        }

        // Diff modal elements (only in index.html)
        const showDiffBtn = document.getElementById('show-diff');
        if (showDiffBtn) {
            showDiffBtn.onclick = () => {
                document.getElementById('diff-modal').classList.remove('hidden');
            };

            document.getElementById('close-diff-modal').onclick = () => {
                document.getElementById('diff-modal').classList.add('hidden');
            };

            document.getElementById('cancel-diff').onclick = () => {
                document.getElementById('diff-modal').classList.add('hidden');
            };

            // Click outside modal to close
            document.getElementById('diff-modal').onclick = (e) => {
                if (e.target.id === 'diff-modal') {
                    document.getElementById('diff-modal').classList.add('hidden');
                }
            };

            // Load diff
            document.getElementById('load-diff').onclick = async () => {
                const beforeSelect = document.getElementById('diff-before');
                const afterSelect = document.getElementById('diff-after');
                const beforeCustom = document.getElementById('diff-before-custom').value.trim();
                const afterCustom = document.getElementById('diff-after-custom').value.trim();

                const beforeRef = beforeCustom || beforeSelect.value;
                const afterRef = afterCustom || afterSelect.value;

                console.log('Loading diff:', beforeRef, 'vs', afterRef);

                try {
                    const response = await fetch('/api/diff', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ before: beforeRef, after: afterRef })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to load diff');
                    }

                    const diffData = await response.json();
                    displayDiff(diffData);
                    document.getElementById('diff-modal').classList.add('hidden');
                } catch (error) {
                    alert('Error loading diff: ' + error.message);
                }
            };
        }

        // Search with Enter to navigate
        const searchInput = document.getElementById('search');

        searchInput.oninput = (e) => {
            const query = e.target.value.toLowerCase();
            performSearch(query);
        };

        searchInput.onkeydown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                navigateToNextMatch();
            }
        };
    }

    function displayDiff(diffData) {
        // TODO: Implement diff visualization
        // This will show before/after comparison with highlighted changes
        console.log('Diff data:', diffData);
        alert('Diff view coming soon! Data received: ' + JSON.stringify(diffData, null, 2));
    }

    function performSearch(query) {
        // Clear previous highlights
        document.querySelectorAll('.search-match, .search-highlight, .current-match').forEach(el => {
            el.classList.remove('search-match', 'search-highlight', 'current-match');
        });

        searchMatches = [];
        currentSearchIndex = 0;

        if (query.length < 2) return;

        // Find matches
        document.querySelectorAll('.function-name').forEach(el => {
            if (el.textContent.toLowerCase().includes(query)) {
                el.classList.add('search-highlight');
                el.closest('.tree-node').classList.add('search-match');
                searchMatches.push(el);

                // Expand parent nodes to show match
                let container = el.closest('.tree-node-container');
                while (container) {
                    const parent = container.parentElement.closest('.tree-node-container');
                    if (parent) {
                        const expand = parent.querySelector('.tree-expand');
                        if (expand && expand.classList.contains('collapsed')) {
                            toggleNode(parent.dataset.path);
                        }
                    }
                    container = parent;
                }
            }
        });

        // Highlight first match
        if (searchMatches.length > 0) {
            highlightCurrentMatch();
        }
    }

    function navigateToNextMatch() {
        if (searchMatches.length === 0) return;

        // Move to next match
        currentSearchIndex = (currentSearchIndex + 1) % searchMatches.length;
        highlightCurrentMatch();
    }

    function highlightCurrentMatch() {
        // Remove previous current match highlight
        document.querySelectorAll('.current-match').forEach(el => {
            el.classList.remove('current-match');
        });

        // Highlight current match
        const currentMatch = searchMatches[currentSearchIndex];
        currentMatch.classList.add('current-match');

        // Scroll to match (center it in the viewport)
        const treeContainer = document.querySelector('.tree-container');
        const matchNode = currentMatch.closest('.tree-node');

        if (matchNode && treeContainer) {
            const containerRect = treeContainer.getBoundingClientRect();
            const nodeRect = matchNode.getBoundingClientRect();
            const scrollOffset = nodeRect.top - containerRect.top - (containerRect.height / 2) + (nodeRect.height / 2);

            treeContainer.scrollBy({
                top: scrollOffset,
                behavior: 'smooth'
            });
        }
    }

    // Start
    init();
})();
