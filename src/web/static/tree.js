// FlowDiff Interactive Call Tree
(function() {
    'use strict';

    // State variables
    window.treeData = null;
    let expandedNodes = new Set();
    let searchMatches = [];
    let currentSearchIndex = 0;
    let includeFilterRegex = null;
    let includeFilterTopLevelOnly = false;
    let excludeFilterRegex = null;
    let excludeFilterTopLevelOnly = false;
    let changedNodes = [];
    let currentChangedIndex = 0;
    let currentSelectedNode = null;
    let currentTreeView = 'after';

    async function init() {
        try {
            const response = await fetch('/api/tree');
            if (!response.ok) {
                throw new Error('Failed to load call tree data');
            }
            window.treeData = await response.json();

            updateStats();
            renderTree();
            setupEventListeners();
            await loadSavedHtmlPath();
        } catch (error) {
            console.error('Error loading tree:', error);
            document.getElementById('call-tree').innerHTML =
                `<div class="loading">Error loading call tree: ${error.message}</div>`;
        }
    }

    async function loadSavedHtmlPath() {
        try {
            const response = await fetch('/api/saved-html-path');
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            if (!data.html_path || !data.file_url) {
                return;
            }

            const banner = document.getElementById('saved-report-banner');
            const link = document.getElementById('saved-report-link');

            if (!banner || !link) {
                console.error('[FlowDiff] Banner elements not found in DOM');
                return;
            }

            const filename = data.html_path.split('/').pop();
            link.href = data.file_url;
            link.textContent = filename;
            banner.classList.remove('hidden');
        } catch (error) {
            console.error('[FlowDiff] Error loading saved HTML path:', error);
        }
    }

    function closeBanner() {
        document.getElementById('saved-report-banner').classList.add('hidden');
    }

    function updateStats() {
        const metadata = window.treeData.metadata;

        updateRunDirectory(metadata);
        updateAnalysisInfo(metadata);
        updateDiffInfo(metadata);
    }

    function updateRunDirectory(metadata) {
        const runDir = metadata.run_dir || '';
        const homeDir = runDir.includes('/Users/')
            ? runDir.replace(/^\/Users\/[^\/]+/, '~')
            : runDir;
        const runDirElem = document.getElementById('run-dir');
        if (runDirElem) {
            runDirElem.textContent = homeDir;
        }
    }

    function updateAnalysisInfo(metadata) {
        const analysisInfoElem = document.getElementById('analysis-info');
        if (!analysisInfoElem) {
            return;
        }

        const inputPath = metadata.input_path || metadata.project || '';
        const shortPath = inputPath.includes('/Users/')
            ? inputPath.replace(/^\/Users\/[^\/]+/, '~')
            : inputPath;
        const funcCount = metadata.function_count || 0;
        const entryCount = metadata.entry_point_count || window.treeData.trees.length;
        analysisInfoElem.textContent = `${shortPath} (${funcCount} functions, ${entryCount} entry points)`;
    }

    function updateDiffInfo(metadata) {
        if (!metadata.before_ref) {
            return;
        }

        const diffComparisonCard = document.getElementById('diff-comparison-card');
        const diffInfoElem = document.getElementById('diff-info');

        // Use full descriptions if available, otherwise format the ref
        const beforeDesc = metadata.before_description || formatRefDescription(metadata.before_ref);
        const afterDesc = metadata.after_description || formatRefDescription(metadata.after_ref);

        if (diffComparisonCard) {
            document.getElementById('current-flow-desc').textContent = afterDesc;
            document.getElementById('reference-flow-desc').textContent = beforeDesc;

            if (metadata.analysis_timestamp) {
                const timestampElem = document.getElementById('comparison-timestamp');
                if (timestampElem) {
                    const timestamp = new Date(metadata.analysis_timestamp);
                    timestampElem.textContent = `Analyzed ${getTimeAgo(timestamp)}`;
                }
            }

            diffComparisonCard.style.display = 'block';
        } else if (diffInfoElem) {
            let diffInfo = `Current flow <strong>${afterDesc}</strong> compared with reference flow <strong>${beforeDesc}</strong>`;

            if (metadata.analysis_timestamp) {
                const timestamp = new Date(metadata.analysis_timestamp);
                diffInfo += ` <span style="color: #95a5a6; font-size: 0.9em;">(${getTimeAgo(timestamp)})</span>`;
            }

            diffInfoElem.innerHTML = diffInfo;
        }
    }

    function getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);

        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;

        const days = Math.floor(seconds / 86400);
        if (days === 1) return 'yesterday';
        if (days < 7) return `${days} days ago`;
        return date.toLocaleDateString();
    }

    function formatRefDescription(ref) {
        if (ref === 'working') return 'Latest uncommitted changes';
        if (ref === 'HEAD') return 'Latest commit';
        if (ref.startsWith('HEAD~')) {
            const n = ref.substring(5) || '1';
            return `${n} commit${n === '1' ? '' : 's'} ago`;
        }
        return `Commit ${ref}`;
    }

    function renderTree() {
        const container = document.getElementById('call-tree');
        container.innerHTML = '';

        const trees = currentTreeView === 'before' ? window.treeData.before_trees : window.treeData.trees;

        trees.forEach((tree, index) => {
            if (!shouldRenderTopLevelNode(tree)) {
                return;
            }

            const treeElement = renderNode(tree, 0, `tree-${index}`);

            if (treeElement.childNodes.length > 0) {
                const treeSection = document.createElement('div');
                treeSection.className = 'entry-point-tree';
                treeSection.appendChild(treeElement);
                container.appendChild(treeSection);
            }
        });

        markPathsToChanges();
        changedNodes = Array.from(document.querySelectorAll('.tree-node.has-changes'));
        currentChangedIndex = 0;
        updateChangeCounter();
    }

    function shouldRenderTopLevelNode(tree) {
        if (includeFilterTopLevelOnly && includeFilterRegex) {
            if (!includeFilterRegex.test(tree.function.name) && !includeFilterRegex.test(tree.function.file_name)) {
                return false;
            }
        }
        if (excludeFilterTopLevelOnly && excludeFilterRegex) {
            if (excludeFilterRegex.test(tree.function.name) || excludeFilterRegex.test(tree.function.file_name)) {
                return false;
            }
        }
        return true;
    }

    function markPathsToChanges() {
        const changedNodeElements = document.querySelectorAll('.tree-node.has-changes');

        changedNodeElements.forEach(changedNode => {
            let container = changedNode.closest('.tree-node-container');
            while (container) {
                const parent = container.parentElement.closest('.tree-node-container');
                if (parent) {
                    const parentNode = parent.querySelector('.tree-node');
                    if (parentNode && !parentNode.classList.contains('has-changes')) {
                        parentNode.classList.add('path-to-change');
                    }
                }
                container = parent;
            }
        });
    }

    function shouldRenderNode(node) {
        if (!includeFilterTopLevelOnly && includeFilterRegex) {
            if (!includeFilterRegex.test(node.function.name) && !includeFilterRegex.test(node.function.file_name)) {
                return false;
            }
        }
        if (!excludeFilterTopLevelOnly && excludeFilterRegex) {
            if (excludeFilterRegex.test(node.function.name) || excludeFilterRegex.test(node.function.file_name)) {
                return false;
            }
        }
        return true;
    }

    function renderNode(node, depth, path) {
        if (!shouldRenderNode(node)) {
            return document.createDocumentFragment();
        }

        const div = document.createElement('div');
        div.className = 'tree-node-container';
        div.dataset.path = path;

        const nodeDiv = createNodeElement(node, depth, path);
        div.appendChild(nodeDiv);

        if (node.children && node.children.length > 0) {
            const childrenDiv = createChildrenContainer(node, depth, path);
            div.appendChild(childrenDiv);
        }

        return div;
    }

    function createNodeElement(node, depth, path) {
        const nodeDiv = document.createElement('div');
        nodeDiv.className = 'tree-node';
        nodeDiv.dataset.depth = depth;

        if (node.children && node.children.length > 0) {
            nodeDiv.classList.add('has-children');
        }
        if (node.function.has_changes) {
            nodeDiv.classList.add('has-changes');
        }

        appendIndentation(nodeDiv, depth);
        appendExpandToggle(nodeDiv, node, path);
        appendIcon(nodeDiv, node);
        appendLabel(nodeDiv, node, path);
        appendActionIcons(nodeDiv, node);

        return nodeDiv;
    }

    function appendIndentation(nodeDiv, depth) {
        for (let i = 0; i < depth; i++) {
            const indent = document.createElement('span');
            indent.className = 'tree-indent';
            indent.textContent = '\u2502';
            nodeDiv.appendChild(indent);
        }
    }

    function appendExpandToggle(nodeDiv, node, path) {
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
    }

    function appendIcon(nodeDiv, node) {
        const icon = document.createElement('span');
        icon.className = 'tree-icon';

        if (node.function.name.startsWith('<script:')) {
            icon.textContent = '\uD83D\uDE80';
        } else if (node.function.is_entry_point) {
            icon.textContent = '\uD83C\uDFAF';
        }

        nodeDiv.appendChild(icon);
    }

    function appendLabel(nodeDiv, node, path) {
        const label = document.createElement('span');
        label.className = 'tree-label';
        label.onclick = () => {
            selectNode(nodeDiv);
            toggleNode(path);
        };

        const funcName = document.createElement('span');
        funcName.className = 'function-name';
        funcName.dataset.qualifiedName = node.function.qualified_name;

        const fileName = node.function.file_name.replace('.py', '');
        let displayName = node.function.name;

        if (displayName.startsWith('<script:')) {
            displayName = displayName.replace('<script:', '').replace('>', '');
            funcName.textContent = `${fileName} [script]`;
        } else {
            funcName.textContent = `${fileName}::${displayName}`;
        }

        label.appendChild(funcName);
        nodeDiv.appendChild(label);
    }

    function appendActionIcons(nodeDiv, node) {
        if (node.function.has_changes) {
            const diffIcon = document.createElement('span');
            diffIcon.className = 'diff-icon';
            diffIcon.textContent = '\u238E';
            diffIcon.title = 'View diff';
            diffIcon.onclick = (e) => {
                e.stopPropagation();
                viewDiff(node.function);
            };
            nodeDiv.appendChild(diffIcon);
        }

        const infoIcon = document.createElement('span');
        infoIcon.className = 'info-icon';
        infoIcon.textContent = '\u24D8';
        infoIcon.onclick = (e) => {
            e.stopPropagation();
            showInfo(node.function);
        };
        nodeDiv.appendChild(infoIcon);
    }

    function createChildrenContainer(node, depth, path) {
        const childrenDiv = document.createElement('div');
        childrenDiv.className = 'tree-children collapsed';
        childrenDiv.dataset.path = path;

        node.children.forEach((child, index) => {
            const childPath = `${path}-${index}`;
            const childElement = renderNode(child, depth + 1, childPath);
            childrenDiv.appendChild(childElement);
        });

        return childrenDiv;
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

        const fileName = func.file_name.replace('.py', '');
        const isScript = func.name.startsWith('<script:');
        const displayTitle = isScript
            ? `${fileName} [script entry point]`
            : `${fileName}::${func.name}`;

        document.getElementById('info-title').textContent = displayTitle;

        document.getElementById('info-location').innerHTML = `
            <code style="word-wrap: break-word; white-space: pre-wrap;">${func.file_path}:${func.line_number}</code>
        `;

        if (isScript) {
            document.getElementById('info-signature').innerHTML = `
                <code>Script entry point (launches server/application)</code>
            `;
        } else {
            const params = func.parameters.length > 0 ? func.parameters.join(', ') : '';
            const returnType = func.return_type ? ` \u2192 ${func.return_type}` : '';
            document.getElementById('info-signature').innerHTML = `
                <code>${func.name}(${params})${returnType}</code>
            `;
        }

        renderInfoList('info-parameters', func.parameters, 'No parameters');
        renderDocumentation('info-documentation', func.documentation);
        renderInfoList('info-locals', func.local_variables, 'No local variables');
        renderInfoList('info-calls', func.calls, 'No function calls');
        renderInfoList('info-called-by', func.called_by, 'Entry point (not called by anyone)');
    }

    function renderInfoList(elementId, items, emptyMessage) {
        const element = document.getElementById(elementId);
        if (items && items.length > 0) {
            const listHtml = items.map(item => `<li><code>${item}</code></li>`).join('');
            element.innerHTML = `<ul class="info-list">${listHtml}</ul>`;
        } else {
            element.innerHTML = `<span class="empty-state">${emptyMessage}</span>`;
        }
    }

    function renderDocumentation(elementId, documentation) {
        const element = document.getElementById(elementId);
        if (documentation && documentation.trim()) {
            const escapedDoc = documentation
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\n/g, '<br>');
            element.innerHTML = `<div class="documentation-text">${escapedDoc}</div>`;
        } else {
            element.innerHTML = `<span class="empty-state">No documentation</span>`;
        }
    }

    function closeInfoPanel() {
        document.getElementById('info-panel').classList.add('hidden');
        document.getElementById('info-panel-overlay').classList.remove('active');
    }

    async function viewDiff(func) {
        try {
            const response = await fetch(`/api/diff/${encodeURIComponent(func.qualified_name)}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch diff: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.method === 'external' && data.viewer && data.diff_content) {
                showInlineDiff(func, data.diff_content);
                showToast(`Note: Attempted ${data.viewer} (showing inline)`, 'info');
            } else if (data.diff_content) {
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
        let modal = document.getElementById('diff-modal');
        if (!modal) {
            modal = createDiffModal();
        }

        document.getElementById('diff-modal-title').textContent = `Diff: ${func.name}`;

        const contentDiv = document.getElementById('diff-modal-content');
        contentDiv.innerHTML = '';

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
            } catch (e) {
                console.error('[FlowDiff] Error rendering diff with diff2html:', e);
                contentDiv.innerHTML = `<pre><code>${escapeHtml(diffContent)}</code></pre>`;
                applyManualDiffColors(contentDiv);
            }
        } else {
            contentDiv.innerHTML = `<pre><code>${escapeHtml(diffContent)}</code></pre>`;
            applyManualDiffColors(contentDiv);
        }

        modal.classList.remove('hidden');
    }

    function applyManualDiffColors(container) {
        const codeBlock = container.querySelector('code');
        if (!codeBlock) return;

        const lines = codeBlock.textContent.split('\n');
        const coloredHtml = lines.map(line => {
            const escaped = escapeHtml(line);
            if (line.startsWith('+') && !line.startsWith('+++')) {
                return `<span style="background-color: #e6ffed; display: block;">${escaped}</span>`;
            }
            if (line.startsWith('-') && !line.startsWith('---')) {
                return `<span style="background-color: #ffecec; display: block;">${escaped}</span>`;
            }
            if (line.startsWith('@@')) {
                return `<span style="background-color: #e1f5fe; color: #0277bd; display: block;">${escaped}</span>`;
            }
            return `<span style="display: block;">${escaped}</span>`;
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
                    <button class="diff-modal-close" id="close-diff-modal-btn">\u00d7</button>
                </div>
                <div class="diff-modal-body">
                    <div id="diff-modal-content"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        const closeModal = () => modal.classList.add('hidden');

        modal.querySelector('.diff-modal-overlay').onclick = closeModal;
        modal.querySelector('#close-diff-modal-btn').onclick = closeModal;

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                closeModal();
            }
        });

        return modal;
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        const bgColor = type === 'error' ? '#e74c3c' : '#3498db';
        const duration = type === 'error' ? 3000 : 5000;

        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${bgColor};
            color: white;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
            max-width: 400px;
            line-height: 1.4;
        `;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function applyFilter() {
        const includeStr = getInputValue('filter-include-regex');
        const excludeStr = getInputValue('filter-exclude-regex');

        includeFilterTopLevelOnly = getCheckboxValue('filter-include-top-level');
        excludeFilterTopLevelOnly = getCheckboxValue('filter-exclude-top-level');

        includeFilterRegex = compileFilterRegex(includeStr, 'filter-include-regex');
        if (includeStr && !includeFilterRegex) return;

        excludeFilterRegex = compileFilterRegex(excludeStr, 'filter-exclude-regex');
        if (excludeStr && !excludeFilterRegex) return;

        renderTree();
    }

    function getInputValue(elementId) {
        const element = document.getElementById(elementId);
        return element ? element.value.trim() : '';
    }

    function getCheckboxValue(elementId) {
        const element = document.getElementById(elementId);
        return element ? element.checked : false;
    }

    function compileFilterRegex(pattern, inputId) {
        if (!pattern) return null;

        try {
            const input = document.getElementById(inputId);
            if (input) input.style.borderColor = '';
            return new RegExp(pattern, 'i');
        } catch (e) {
            const input = document.getElementById(inputId);
            if (input) {
                input.style.borderColor = '#e74c3c';
                setTimeout(() => { input.style.borderColor = ''; }, 1000);
            }
            return null;
        }
    }

    function setupEventListeners() {
        setupBannerListeners();
        setupInfoPanelListeners();
        setupTreeControls();
        setupFilterControls();
        setupSearchListeners();
        setupKeyboardShortcuts();
        setupDiffModalListeners();
    }

    function setupBannerListeners() {
        const closeBannerBtn = document.getElementById('close-banner');
        if (closeBannerBtn) {
            closeBannerBtn.onclick = closeBanner;
        }
    }

    function setupInfoPanelListeners() {
        document.getElementById('close-info').onclick = closeInfoPanel;
        document.getElementById('info-panel-overlay').onclick = closeInfoPanel;
    }

    function setupTreeControls() {
        document.getElementById('expand-all').onclick = () => {
            document.querySelectorAll('.tree-expand.collapsed').forEach(expand => {
                const container = expand.closest('.tree-node-container');
                if (container) {
                    toggleNode(container.dataset.path);
                }
            });
        };

        document.getElementById('collapse-all').onclick = () => {
            document.querySelectorAll('.tree-expand.expanded').forEach(expand => {
                const container = expand.closest('.tree-node-container');
                if (container) {
                    toggleNode(container.dataset.path);
                }
            });
        };

        const toggleBtn = document.getElementById('toggle-tree-view');
        if (toggleBtn) {
            toggleBtn.onclick = () => {
                currentTreeView = currentTreeView === 'after' ? 'before' : 'after';
                updateToggleButtonStyle(toggleBtn);
                renderTree();
            };
        }

        const jumpToNextChangeBtn = document.getElementById('next-change');
        const jumpToPrevChangeBtn = document.getElementById('prev-change');
        if (jumpToNextChangeBtn && jumpToPrevChangeBtn) {
            jumpToNextChangeBtn.onclick = jumpToNextChange;
            jumpToPrevChangeBtn.onclick = jumpToPrevChange;
        }
    }

    function updateToggleButtonStyle(toggleBtn) {
        if (currentTreeView === 'before') {
            toggleBtn.textContent = 'Before (Reference)';
            toggleBtn.style.background = '#fff';
            toggleBtn.style.borderColor = '#e74c3c';
            toggleBtn.style.color = '#e74c3c';
        } else {
            toggleBtn.textContent = 'After (Current)';
            toggleBtn.style.background = '#fff';
            toggleBtn.style.borderColor = '#4CAF50';
            toggleBtn.style.color = '#4CAF50';
        }
    }

    function setupFilterControls() {
        const filterInputs = [
            'filter-include-regex',
            'filter-exclude-regex'
        ];

        const filterCheckboxes = [
            'filter-include-top-level',
            'filter-exclude-top-level'
        ];

        filterInputs.forEach(id => {
            const input = document.getElementById(id);
            if (input) input.oninput = applyFilter;
        });

        filterCheckboxes.forEach(id => {
            const checkbox = document.getElementById(id);
            if (checkbox) checkbox.onchange = applyFilter;
        });
    }

    function setupSearchListeners() {
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

    function setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    navigateDown();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    navigateUp();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    collapseCurrentNode();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    expandCurrentNode();
                    break;
                case 'n':
                    if (document.getElementById('next-change')) {
                        e.preventDefault();
                        jumpToNextChange();
                    }
                    break;
                case 'p':
                    if (document.getElementById('next-change')) {
                        e.preventDefault();
                        jumpToPrevChange();
                    }
                    break;
            }
        });
    }

    function setupDiffModalListeners() {
        const showDiffBtn = document.getElementById('show-diff');
        if (!showDiffBtn) return;

        showDiffBtn.onclick = () => {
            document.getElementById('diff-modal').classList.remove('hidden');
        };

        document.getElementById('close-diff-modal').onclick = () => {
            document.getElementById('diff-modal').classList.add('hidden');
        };

        document.getElementById('cancel-diff').onclick = () => {
            document.getElementById('diff-modal').classList.add('hidden');
        };

        document.getElementById('diff-modal').onclick = (e) => {
            if (e.target.id === 'diff-modal') {
                document.getElementById('diff-modal').classList.add('hidden');
            }
        };

        document.getElementById('load-diff').onclick = loadDiffFromModal;
    }

    async function loadDiffFromModal() {
        const beforeSelect = document.getElementById('diff-before');
        const afterSelect = document.getElementById('diff-after');
        const beforeCustom = document.getElementById('diff-before-custom').value.trim();
        const afterCustom = document.getElementById('diff-after-custom').value.trim();

        const beforeRef = beforeCustom || beforeSelect.value;
        const afterRef = afterCustom || afterSelect.value;

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
    }

    function displayDiff(diffData) {
        console.log('Diff data:', diffData);
        alert('Diff view coming soon! Data received: ' + JSON.stringify(diffData, null, 2));
    }

    function performSearch(query) {
        document.querySelectorAll('.search-match, .search-highlight, .current-match').forEach(el => {
            el.classList.remove('search-match', 'search-highlight', 'current-match');
        });

        searchMatches = [];
        currentSearchIndex = 0;

        if (query.length < 2) return;

        let searchRegex;
        try {
            searchRegex = new RegExp(query, 'i');
        } catch (e) {
            searchRegex = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
        }

        document.querySelectorAll('.function-name').forEach(el => {
            if (searchRegex.test(el.textContent)) {
                el.classList.add('search-highlight');
                el.closest('.tree-node').classList.add('search-match');
                searchMatches.push(el);
                expandParentsToShow(el);
            }
        });

        if (searchMatches.length > 0) {
            highlightCurrentMatch();
        }
    }

    function expandParentsToShow(element) {
        let container = element.closest('.tree-node-container');
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

    function navigateToNextMatch() {
        if (searchMatches.length === 0) return;

        currentSearchIndex = (currentSearchIndex + 1) % searchMatches.length;
        highlightCurrentMatch();
    }

    function highlightCurrentMatch() {
        document.querySelectorAll('.current-match').forEach(el => {
            el.classList.remove('current-match');
        });

        const currentMatch = searchMatches[currentSearchIndex];
        currentMatch.classList.add('current-match');

        scrollToElementInTree(currentMatch.closest('.tree-node'));
    }

    function scrollToElementInTree(element) {
        const treeContainer = document.querySelector('.tree-container');
        if (!element || !treeContainer) return;

        const containerRect = treeContainer.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();
        const scrollOffset = elementRect.top - containerRect.top - (containerRect.height / 2) + (elementRect.height / 2);

        treeContainer.scrollBy({
            top: scrollOffset,
            behavior: 'smooth'
        });
    }

    function updateChangeCounter() {
        const counterElem = document.getElementById('change-counter');
        if (!counterElem) return;

        if (changedNodes.length === 0) {
            counterElem.textContent = 'No changes';
            counterElem.style.color = '#aaa';
        } else {
            counterElem.textContent = `${currentChangedIndex + 1} of ${changedNodes.length}`;
            counterElem.style.color = '#f0ad4e';
            counterElem.style.fontWeight = '600';
        }
    }

    function getVisibleTreeNodes() {
        const allNodes = document.querySelectorAll('.tree-node');
        return Array.from(allNodes).filter(node => {
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
        document.querySelectorAll('.tree-node.selected').forEach(node => {
            node.classList.remove('selected');
        });

        nodeElement.classList.add('selected');
        currentSelectedNode = nodeElement;

        const funcNameElem = nodeElement.querySelector('.function-name');
        if (funcNameElem && funcNameElem.dataset.qualifiedName) {
            const qualifiedName = funcNameElem.dataset.qualifiedName;

            const clickedIndex = changedNodes.indexOf(nodeElement);
            if (clickedIndex !== -1) {
                currentChangedIndex = clickedIndex;
                updateChangeCounter();
            }

            if (window.highlightChangeInPanel && nodeElement.classList.contains('has-changes')) {
                window.highlightChangeInPanel(qualifiedName);
            }

            if (window.onFunctionSelected) {
                window.onFunctionSelected(qualifiedName);
            }
        }

        scrollToElementInTree(nodeElement);
    }

    function navigateDown() {
        const visibleNodes = getVisibleTreeNodes();
        if (visibleNodes.length === 0) return;

        if (!currentSelectedNode) {
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
        if (changedNodes.length === 0) return;

        currentChangedIndex = (currentChangedIndex - 1 + changedNodes.length) % changedNodes.length;
        scrollToChange(changedNodes[currentChangedIndex]);
        updateChangeCounter();
    }

    function jumpToNextChange() {
        if (changedNodes.length === 0) return;

        currentChangedIndex = (currentChangedIndex + 1) % changedNodes.length;
        scrollToChange(changedNodes[currentChangedIndex]);
        updateChangeCounter();
    }

    function scrollToChange(targetNode) {
        expandParentsToShow(targetNode);
        scrollToElementInTree(targetNode);
        flashHighlight(targetNode);
    }

    function flashHighlight(element) {
        const originalBoxShadow = element.style.boxShadow;
        element.style.boxShadow = '0 0 0 4px #f0ad4e, 0 0 20px rgba(240, 173, 78, 0.4)';
        setTimeout(() => {
            element.style.boxShadow = originalBoxShadow;
        }, 1000);
    }

    // Start
    init();

    // Expose selectNode globally for diff-panel.js to use
    window.selectTreeNode = selectNode;

    // Expose function to switch to before view and scroll to function
    window.showInBeforeTree = function(qualifiedName) {
        // Switch to before view if not already
        if (currentTreeView !== 'before') {
            currentTreeView = 'before';

            // Update toggle button
            const toggleBtn = document.getElementById('toggle-tree-view');
            if (toggleBtn) {
                toggleBtn.textContent = 'Before (Reference)';
                toggleBtn.style.background = '#fff';
                toggleBtn.style.borderColor = '#e74c3c';
                toggleBtn.style.color = '#e74c3c';
            }

            // Re-render tree with before view
            renderTree();
        }

        // Now find and scroll to the function
        const functionNames = document.querySelectorAll('.function-name');
        let found = false;

        for (const nameElem of functionNames) {
            if (nameElem.dataset.qualifiedName === qualifiedName) {
                found = true;
                const node = nameElem.closest('.tree-node');
                if (node) {
                    // Expand parent nodes to reveal the function
                    let container = node.closest('.tree-node-container');
                    while (container) {
                        const parent = container.parentElement.closest('.tree-node-container');
                        if (parent) {
                            const expand = parent.querySelector('.tree-expand');
                            const children = parent.querySelector('.tree-children');

                            // If collapsed, expand it
                            if (expand && children && expand.classList.contains('collapsed')) {
                                expand.classList.remove('collapsed');
                                expand.classList.add('expanded');
                                children.classList.remove('collapsed');
                            }
                        }
                        container = parent;
                    }

                    // Use existing selectNode function
                    selectNode(node);
                }
                break;
            }
        }

        if (!found) {
            // Extract just the function name for display
            const displayName = qualifiedName.split('::').pop() || qualifiedName;

            showToast(`"${displayName}" was deleted but wasn't part of any active flow, so it has no representation in the flow tree`, 'info');
        }
    };
})();
