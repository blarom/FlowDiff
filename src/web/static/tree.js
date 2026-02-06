// FlowDiff Interactive Call Tree
(function() {
    'use strict';

    // Make treeData global for diff-panel.js
    window.treeData = null;
    let expandedNodes = new Set();
    let searchMatches = [];
    let currentSearchIndex = 0;
    let filterRegex = null;
    let filterTopLevelOnly = false;
    let changedNodes = [];
    let currentChangedIndex = 0;
    let currentSelectedNode = null;  // Track currently selected node for keyboard nav

    // Initialize
    async function init() {
        try {
            // Fetch call tree data
            const response = await fetch('/api/tree');
            if (!response.ok) {
                throw new Error('Failed to load call tree data');
            }
            window.treeData = await response.json();

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
        const metadata = window.treeData.metadata;

        // Update run directory (use ~ for home directory shorthand if applicable)
        const runDir = metadata.run_dir || '';
        const homeDir = runDir.includes('/Users/') ? runDir.replace(/^\/Users\/[^\/]+/, '~') : runDir;
        const runDirElem = document.getElementById('run-dir');
        if (runDirElem) {
            runDirElem.textContent = homeDir;
        }

        // Update analysis info: "<input_path> (X functions, Y entry points)"
        const analysisInfoElem = document.getElementById('analysis-info');
        if (analysisInfoElem) {
            const inputPath = metadata.input_path || metadata.project || '';
            const shortPath = inputPath.includes('/Users/') ? inputPath.replace(/^\/Users\/[^\/]+/, '~') : inputPath;
            const funcCount = metadata.function_count || 0;
            const entryCount = metadata.entry_point_count || window.treeData.trees.length;
            analysisInfoElem.textContent = `${shortPath} (${funcCount} functions, ${entryCount} entry points)`;
        }

        // Update diff info (only in diff.html)
        const diffInfoElem = document.getElementById('diff-info');
        if (diffInfoElem && metadata.before_ref) {
            const beforeDesc = formatRefDescription(metadata.before_ref);
            const afterDesc = formatRefDescription(metadata.after_ref);
            diffInfoElem.innerHTML = `Current flow <strong>${afterDesc}</strong> compared with reference flow <strong>${beforeDesc}</strong>`;
        }
    }

    function formatRefDescription(ref) {
        // Format git ref for display
        if (ref === 'working') {
            return 'Latest uncommitted changes';
        } else if (ref === 'HEAD') {
            return 'Latest commit';
        } else if (ref.startsWith('HEAD~')) {
            const n = ref.substring(5) || '1';
            return `${n} commit${n === '1' ? '' : 's'} ago`;
        } else {
            return `Commit ${ref}`;
        }
    }

    function renderTree() {
        const container = document.getElementById('call-tree');
        container.innerHTML = '';

        // Render each entry point tree as a separate collapsed section
        window.treeData.trees.forEach((tree, index) => {
            // Apply filter if set
            if (filterRegex && filterTopLevelOnly) {
                // Filter top-level only: hide if root doesn't match
                if (!filterRegex.test(tree.function.name) && !filterRegex.test(tree.function.file_name)) {
                    return; // Skip this tree
                }
            }

            const treeSection = document.createElement('div');
            treeSection.className = 'entry-point-tree';

            const treeElement = renderNode(tree, 0, `tree-${index}`);
            treeSection.appendChild(treeElement);

            container.appendChild(treeSection);
        });

        // Mark paths to changed nodes
        markPathsToChanges();

        // Collect all changed nodes for jump navigation
        changedNodes = Array.from(document.querySelectorAll('.tree-node.has-changes'));
        currentChangedIndex = 0;

        // Update change counter
        updateChangeCounter();
    }

    function markPathsToChanges() {
        // Find all nodes with changes
        const changedNodes = document.querySelectorAll('.tree-node.has-changes');

        changedNodes.forEach(changedNode => {
            // Walk up the tree and mark all parents
            let container = changedNode.closest('.tree-node-container');
            while (container) {
                const parent = container.parentElement.closest('.tree-node-container');
                if (parent) {
                    const parentNode = parent.querySelector('.tree-node');
                    if (parentNode && !parentNode.classList.contains('has-changes')) {
                        // Mark as part of path to change
                        parentNode.classList.add('path-to-change');
                    }
                }
                container = parent;
            }
        });
    }

    function renderNode(node, depth, path) {
        // Apply filter if set (for all nodes, not just top-level)
        if (filterRegex && !filterTopLevelOnly) {
            // Check if this node matches
            if (!filterRegex.test(node.function.name) && !filterRegex.test(node.function.file_name)) {
                // Node doesn't match - don't render it
                return document.createDocumentFragment(); // Return empty fragment
            }
        }

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
        label.onclick = () => {
            // Always select the node (changed or not)
            // selectNode already handles diff panel sync for changed nodes
            selectNode(nodeDiv);

            // Always toggle node expansion
            toggleNode(path);
        };

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

        // Diff icon (only for changed functions)
        if (node.function.has_changes) {
            const diffIcon = document.createElement('span');
            diffIcon.className = 'diff-icon';
            diffIcon.textContent = '⎆';  // Diff symbol
            diffIcon.title = 'View diff';
            diffIcon.onclick = (e) => {
                e.stopPropagation();
                viewDiff(node.function);
            };
            nodeDiv.appendChild(diffIcon);
        }

        // Info icon (always shown)
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

    async function viewDiff(func) {
        try {
            // Show loading state
            console.log('[FlowDiff] Fetching diff for:', func.qualified_name);

            // Fetch diff from server
            const response = await fetch(`/api/diff/${encodeURIComponent(func.qualified_name)}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch diff: ${response.statusText}`);
            }

            const data = await response.json();

            // If external viewer was attempted but failed, show notice
            if (data.method === 'external' && data.viewer) {
                console.log('[FlowDiff] Attempted to open in external viewer:', data.viewer);

                // Show inline diff immediately with a notice that external viewer was tried
                if (data.diff_content) {
                    showInlineDiff(func, data.diff_content);
                    // Show non-obtrusive toast
                    showToast(`Note: Attempted ${data.viewer} (showing inline)`, 'info');
                }
            } else if (data.diff_content) {
                // No external viewer, show inline diff immediately
                showInlineDiff(func, data.diff_content);
            } else {
                throw new Error(data.error || 'No diff available');
            }

        } catch (error) {
            console.error('[FlowDiff] Error viewing diff:', error);
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    function showInlineDiff(func, diffContent) {
        // Create or show diff modal
        let modal = document.getElementById('diff-modal');
        if (!modal) {
            modal = createDiffModal();
        }

        document.getElementById('diff-modal-title').textContent = `Diff: ${func.name}`;

        const contentDiv = document.getElementById('diff-modal-content');
        contentDiv.innerHTML = ''; // Clear previous content

        // Use diff2html to render the diff with syntax highlighting
        if (window.Diff2Html) {
            try {
                const diffHtml = Diff2Html.html(diffContent, {
                    drawFileList: false,
                    matching: 'lines',
                    outputFormat: 'line-by-line',
                    renderNothingWhenEmpty: false,
                    diffStyle: 'word',
                    colorScheme: 'light'
                });
                contentDiv.innerHTML = diffHtml;

                // Force add classes if they're missing (fallback)
                setTimeout(() => {
                    contentDiv.querySelectorAll('.d2h-code-line').forEach(line => {
                        const text = line.textContent || '';
                        if (text.startsWith('+') && !line.classList.contains('d2h-ins')) {
                            line.classList.add('d2h-code-line-ins');
                        } else if (text.startsWith('-') && !line.classList.contains('d2h-del')) {
                            line.classList.add('d2h-code-line-del');
                        }
                    });
                }, 100);
            } catch (e) {
                console.error('[FlowDiff] Error rendering diff with diff2html:', e);
                // Fallback to plain text with manual coloring
                contentDiv.innerHTML = `<pre><code>${escapeHtml(diffContent)}</code></pre>`;
                applyManualDiffColors(contentDiv);
            }
        } else {
            // Fallback if diff2html isn't loaded
            console.warn('[FlowDiff] Diff2Html library not loaded, using fallback');
            contentDiv.innerHTML = `<pre><code>${escapeHtml(diffContent)}</code></pre>`;
            applyManualDiffColors(contentDiv);
        }

        modal.classList.remove('hidden');
    }

    function applyManualDiffColors(container) {
        // Manually color diff lines if diff2html fails
        const codeBlock = container.querySelector('code');
        if (!codeBlock) return;

        const lines = codeBlock.textContent.split('\n');
        const coloredHtml = lines.map(line => {
            if (line.startsWith('+') && !line.startsWith('+++')) {
                return `<span style="background-color: #e6ffed; display: block;">${escapeHtml(line)}</span>`;
            } else if (line.startsWith('-') && !line.startsWith('---')) {
                return `<span style="background-color: #ffecec; display: block;">${escapeHtml(line)}</span>`;
            } else if (line.startsWith('@@')) {
                return `<span style="background-color: #e1f5fe; color: #0277bd; display: block;">${escapeHtml(line)}</span>`;
            } else {
                return `<span style="display: block;">${escapeHtml(line)}</span>`;
            }
        }).join('');

        codeBlock.innerHTML = coloredHtml;
    }

    function createDiffModal() {
        const modal = document.createElement('div');
        modal.id = 'diff-modal';
        modal.className = 'diff-modal';
        modal.innerHTML = `
            <div class="diff-modal-overlay"></div>
            <div class="diff-modal-content">
                <div class="diff-modal-header">
                    <h3 id="diff-modal-title">Diff</h3>
                    <button class="diff-modal-close" id="close-diff-modal-btn">×</button>
                </div>
                <div class="diff-modal-body">
                    <div id="diff-modal-content"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Close on overlay click
        modal.querySelector('.diff-modal-overlay').onclick = () => {
            modal.classList.add('hidden');
        };

        // Close on close button click
        modal.querySelector('#close-diff-modal-btn').onclick = () => {
            modal.classList.add('hidden');
        };

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                modal.classList.add('hidden');
            }
        });

        return modal;
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'error' ? '#e74c3c' : '#3498db'};
            color: white;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function applyFilter() {
        const regexInput = document.getElementById('filter-regex');
        const topLevelOnlyCheckbox = document.getElementById('filter-top-level-only');

        const regexStr = regexInput ? regexInput.value.trim() : '';
        filterTopLevelOnly = topLevelOnlyCheckbox ? topLevelOnlyCheckbox.checked : false;

        // Update filter regex
        if (regexStr) {
            try {
                filterRegex = new RegExp(regexStr, 'i'); // Case-insensitive
            } catch (e) {
                // Invalid regex, show error briefly
                regexInput.style.borderColor = '#e74c3c';
                setTimeout(() => {
                    regexInput.style.borderColor = '';
                }, 1000);
                return;
            }
        } else {
            filterRegex = null;
        }

        // Re-render tree with filter applied
        renderTree();
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

        // Filter controls
        const filterRegexInput = document.getElementById('filter-regex');
        const filterTopLevelCheckbox = document.getElementById('filter-top-level-only');
        if (filterRegexInput) {
            filterRegexInput.oninput = applyFilter;
        }
        if (filterTopLevelCheckbox) {
            filterTopLevelCheckbox.onchange = applyFilter;
        }

        // Jump to next change (only in diff.html)
        const jumpToNextChangeBtn = document.getElementById('next-change');
        const jumpToPrevChangeBtn = document.getElementById('prev-change');
        if (jumpToNextChangeBtn && jumpToPrevChangeBtn) {
            jumpToNextChangeBtn.onclick = jumpToNextChange;
            jumpToPrevChangeBtn.onclick = jumpToPrevChange;
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

        // Global keyboard shortcuts for navigation
        document.addEventListener('keydown', (e) => {
            // Only if not typing in input/textarea
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            // Arrow key navigation
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateDown();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateUp();
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                collapseCurrentNode();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                expandCurrentNode();
            }
            // n/p shortcuts for change navigation (only in diff.html)
            else if (document.getElementById('next-change')) {
                if (e.key === 'n') {
                    e.preventDefault();
                    jumpToNextChange();
                } else if (e.key === 'p') {
                    e.preventDefault();
                    jumpToPrevChange();
                }
            }
        });
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

    function updateChangeCounter() {
        const counterElem = document.getElementById('change-counter');
        if (counterElem) {
            if (changedNodes.length === 0) {
                counterElem.textContent = 'No changes';
                counterElem.style.color = '#aaa';
            } else {
                counterElem.textContent = `${currentChangedIndex + 1} of ${changedNodes.length}`;
                counterElem.style.color = '#f0ad4e';
                counterElem.style.fontWeight = '600';
            }
        }
    }

    function getVisibleTreeNodes() {
        // Get all tree nodes that are currently visible (not in collapsed children)
        const allNodes = document.querySelectorAll('.tree-node');
        return Array.from(allNodes).filter(node => {
            // Check if any parent container is collapsed
            let parent = node.closest('.tree-children');
            while (parent) {
                if (parent.classList.contains('collapsed')) {
                    return false;
                }
                parent = parent.parentElement.closest('.tree-children');
            }
            return true;
        });
    }

    function selectNode(nodeElement) {
        // Remove previous selection
        document.querySelectorAll('.tree-node.selected').forEach(node => {
            node.classList.remove('selected');
        });

        // Select the new node
        nodeElement.classList.add('selected');
        currentSelectedNode = nodeElement;

        // Get the function data
        const container = nodeElement.closest('.tree-node-container');
        const funcNameElem = nodeElement.querySelector('.function-name');

        if (funcNameElem && funcNameElem.dataset.qualifiedName) {
            // Find function in tree data
            const qualifiedName = funcNameElem.dataset.qualifiedName;

            // Update change counter if this is a changed node
            const clickedIndex = changedNodes.indexOf(nodeElement);
            if (clickedIndex !== -1) {
                currentChangedIndex = clickedIndex;
                updateChangeCounter();
            }

            // Sync with diff panel if it exists
            if (window.highlightChangeInPanel && nodeElement.classList.contains('has-changes')) {
                window.highlightChangeInPanel(qualifiedName);
            }
        }

        // Scroll to center the node
        const treeContainer = document.querySelector('.tree-container');
        if (treeContainer) {
            const containerRect = treeContainer.getBoundingClientRect();
            const nodeRect = nodeElement.getBoundingClientRect();
            const scrollOffset = nodeRect.top - containerRect.top - (containerRect.height / 2) + (nodeRect.height / 2);

            treeContainer.scrollBy({
                top: scrollOffset,
                behavior: 'smooth'
            });
        }
    }

    function navigateDown() {
        const visibleNodes = getVisibleTreeNodes();
        if (visibleNodes.length === 0) return;

        if (!currentSelectedNode) {
            // No selection yet, select first node
            selectNode(visibleNodes[0]);
        } else {
            const currentIndex = visibleNodes.indexOf(currentSelectedNode);
            if (currentIndex >= 0 && currentIndex < visibleNodes.length - 1) {
                selectNode(visibleNodes[currentIndex + 1]);
            }
        }
    }

    function navigateUp() {
        const visibleNodes = getVisibleTreeNodes();
        if (visibleNodes.length === 0) return;

        if (!currentSelectedNode) {
            // No selection yet, select first node
            selectNode(visibleNodes[0]);
        } else {
            const currentIndex = visibleNodes.indexOf(currentSelectedNode);
            if (currentIndex > 0) {
                selectNode(visibleNodes[currentIndex - 1]);
            }
        }
    }

    function expandCurrentNode() {
        if (!currentSelectedNode) return;

        const container = currentSelectedNode.closest('.tree-node-container');
        if (!container) return;

        const expand = container.querySelector('.tree-expand');
        const children = container.querySelector('.tree-children');

        if (expand && children && expand.classList.contains('collapsed')) {
            toggleNode(container.dataset.path);
        }
    }

    function collapseCurrentNode() {
        if (!currentSelectedNode) return;

        const container = currentSelectedNode.closest('.tree-node-container');
        if (!container) return;

        const expand = container.querySelector('.tree-expand');
        const children = container.querySelector('.tree-children');

        if (expand && children && expand.classList.contains('expanded')) {
            toggleNode(container.dataset.path);
        }
    }

    function jumpToPrevChange() {
        if (changedNodes.length === 0) {
            return;
        }

        // Move to previous changed node (with wrap-around)
        currentChangedIndex = (currentChangedIndex - 1 + changedNodes.length) % changedNodes.length;
        scrollToChange(changedNodes[currentChangedIndex]);
        updateChangeCounter();
    }

    function jumpToNextChange() {
        if (changedNodes.length === 0) {
            return;
        }

        // Move to next changed node
        currentChangedIndex = (currentChangedIndex + 1) % changedNodes.length;
        scrollToChange(changedNodes[currentChangedIndex]);
        updateChangeCounter();
    }

    function scrollToChange(targetNode) {
        // Expand parents to reveal the node
        let container = targetNode.closest('.tree-node-container');
        while (container) {
            const parent = container.parentElement.closest('.tree-node-container');
            if (parent) {
                const expand = parent.querySelector('.tree-expand');
                const children = parent.querySelector('.tree-children');
                if (expand && children && expand.classList.contains('collapsed')) {
                    expand.classList.remove('collapsed');
                    expand.classList.add('expanded');
                    children.classList.remove('collapsed');
                }
            }
            container = parent;
        }

        // Scroll to the changed node
        const treeContainer = document.querySelector('.tree-container');
        if (treeContainer) {
            const containerRect = treeContainer.getBoundingClientRect();
            const nodeRect = targetNode.getBoundingClientRect();
            const scrollOffset = nodeRect.top - containerRect.top - (containerRect.height / 2) + (nodeRect.height / 2);

            treeContainer.scrollBy({
                top: scrollOffset,
                behavior: 'smooth'
            });

            // Flash highlight
            const originalBoxShadow = targetNode.style.boxShadow;
            targetNode.style.boxShadow = '0 0 0 4px #f0ad4e, 0 0 20px rgba(240, 173, 78, 0.4)';
            setTimeout(() => {
                targetNode.style.boxShadow = originalBoxShadow;
            }, 1000);
        }
    }

    // Start
    init();
})();
