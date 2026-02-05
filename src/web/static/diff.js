(function() {
    'use strict';

    let currentDiff = null;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        setupEventListeners();
        loadDefaultDiff();
    }

    function setupEventListeners() {
        document.getElementById('load-diff').addEventListener('click', () => loadDiff());
        document.getElementById('close-diff').addEventListener('click', () => {
            window.location.href = '/';
        });

        // Handle custom ref inputs
        document.getElementById('before-ref').addEventListener('change', function(e) {
            const customInput = document.getElementById('before-custom');
            customInput.style.display = e.target.value === 'custom' ? 'inline-block' : 'none';
        });

        document.getElementById('after-ref').addEventListener('change', function(e) {
            const customInput = document.getElementById('after-custom');
            customInput.style.display = e.target.value === 'custom' ? 'inline-block' : 'none';
        });
    }

    async function loadDefaultDiff() {
        await loadDiff('HEAD', 'working');
    }

    async function loadDiff(before, after) {
        if (!before) {
            const beforeSelect = document.getElementById('before-ref');
            before = beforeSelect.value === 'custom'
                ? document.getElementById('before-custom').value
                : beforeSelect.value;
        }

        if (!after) {
            const afterSelect = document.getElementById('after-ref');
            after = afterSelect.value === 'custom'
                ? document.getElementById('after-custom').value
                : afterSelect.value;
        }

        showLoading(true);

        try {
            const response = await fetch('/api/diff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ before, after })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load diff');
            }

            currentDiff = await response.json();
            renderDiff();
        } catch (error) {
            alert('Error: ' + error.message);
            console.error(error);
        } finally {
            showLoading(false);
        }
    }

    function renderDiff() {
        // Update titles with ref descriptions
        document.getElementById('after-title').textContent = currentDiff.after_description;
        document.getElementById('before-title').textContent = `${currentDiff.before_description} → ${currentDiff.after_description}`;

        // Update stats
        document.getElementById('stat-added').textContent = currentDiff.summary.added;
        document.getElementById('stat-deleted').textContent = currentDiff.summary.deleted;
        document.getElementById('stat-modified').textContent = currentDiff.summary.modified;

        // Left pane: Full current tree (after) with changes highlighted
        renderTree('after-tree', currentDiff.after_tree);

        // Right pane: Only changed functions
        renderChangesOnly('changes-summary', currentDiff.after_tree);

        document.getElementById('diff-summary').classList.remove('hidden');
        document.getElementById('diff-split-view').classList.remove('hidden');
    }

    function renderChangesOnly(containerId, trees) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        if (!trees || trees.length === 0) {
            container.innerHTML = '<p style="color: #999; padding: 1rem;">No changes found</p>';
            return;
        }

        // Extract only nodes with changes
        const changedNodes = [];
        function extractChanged(node) {
            if (node.function.has_changes) {
                changedNodes.push(node);
            }
            if (node.children) {
                node.children.forEach(child => extractChanged(child));
            }
        }

        trees.forEach(tree => extractChanged(tree));

        if (changedNodes.length === 0) {
            container.innerHTML = '<p style="color: #999; padding: 1rem;">No changes in tracked functions</p>';
            return;
        }

        // Render changed nodes
        changedNodes.forEach(node => {
            const elem = renderChangedNode(node);
            container.appendChild(elem);
        });
    }

    function renderChangedNode(node) {
        const div = document.createElement('div');
        div.className = 'tree-node modified';
        div.style.padding = '0.75rem';
        div.style.marginBottom = '0.5rem';

        const icon = '🟡';
        const location = `${node.function.file_path}:${node.function.line_number}`;

        const content = document.createElement('div');
        content.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <div>${icon} <strong>${node.function.name}</strong></div>
                    <div style="color: #999; font-size: 0.85rem; margin-top: 0.25rem;">${location}</div>
                </div>
            </div>
        `;

        div.appendChild(content);
        return div;
    }

    function renderTree(containerId, trees) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        if (!trees || trees.length === 0) {
            container.innerHTML = '<p style="color: #999; padding: 1rem;">No functions found</p>';
            return;
        }

        trees.forEach(tree => {
            const elem = renderTreeNode(tree);
            container.appendChild(elem);
        });
    }

    function renderTreeNode(node, depth = 0) {
        const div = document.createElement('div');
        div.className = 'tree-node';
        div.style.marginLeft = `${depth * 1.5}rem`;

        if (node.function.has_changes) {
            div.classList.add('modified');
        }

        const label = document.createElement('div');
        const icon = node.children && node.children.length > 0 ? '📁' : '📄';
        const location = `${node.function.file_path}:${node.function.line_number}`;
        label.innerHTML = `${icon} <strong>${node.function.name}</strong> <span style="color: #999; font-size: 0.85rem;">${location}</span>`;
        div.appendChild(label);

        const container = document.createElement('div');
        if (node.is_expanded && node.children && node.children.length > 0) {
            node.children.forEach(child => {
                container.appendChild(renderTreeNode(child, depth + 1));
            });
        }
        div.appendChild(container);

        return div;
    }

    function showLoading(show) {
        document.getElementById('loading').classList.toggle('hidden', !show);
    }
})();
