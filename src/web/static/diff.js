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
        document.getElementById('before-title').textContent = currentDiff.before_description;
        document.getElementById('after-title').textContent = currentDiff.after_description;

        document.getElementById('stat-added').textContent = currentDiff.summary.added;
        document.getElementById('stat-deleted').textContent = currentDiff.summary.deleted;
        document.getElementById('stat-modified').textContent = currentDiff.summary.modified;

        renderTree('before-tree', currentDiff.before_tree);
        renderTree('after-tree', currentDiff.after_tree);

        document.getElementById('diff-summary').classList.remove('hidden');
        document.getElementById('diff-split-view').classList.remove('hidden');
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
