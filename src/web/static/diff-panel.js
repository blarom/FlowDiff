// Diff Panel - Shows changed functions on the right
(function() {
    'use strict';

    // Wait for tree.js to load the data
    window.addEventListener('load', initDiffPanel);

    function initDiffPanel() {
        // Poll for tree data from tree.js
        const checkData = setInterval(() => {
            if (window.treeData) {
                clearInterval(checkData);
                populateDiffPanel();
            }
        }, 100);
    }

    function populateDiffPanel() {
        const changedFunctions = extractChangedFunctions(window.treeData.trees);

        // Update stats
        const stats = countChanges(changedFunctions);
        document.getElementById('stat-modified').textContent = stats.modified;
        document.getElementById('stat-added').textContent = stats.added;
        document.getElementById('stat-deleted').textContent = stats.deleted;

        // Render changed functions list
        renderChangedFunctions(changedFunctions);
    }

    function extractChangedFunctions(trees) {
        const changed = [];

        function traverse(node) {
            if (node.function.has_changes) {
                changed.push(node.function);
            }
            if (node.children) {
                node.children.forEach(child => traverse(child));
            }
        }

        trees.forEach(tree => traverse(tree));
        return changed;
    }

    function countChanges(functions) {
        // For now, we only track modified
        // Can enhance later to distinguish added/deleted
        return {
            modified: functions.length,
            added: 0,
            deleted: 0
        };
    }

    function renderChangedFunctions(functions) {
        const container = document.getElementById('changed-functions');

        if (functions.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center; padding: 2rem;">No changes detected</p>';
            return;
        }

        container.innerHTML = '';
        functions.forEach(func => {
            const elem = createChangedFunctionElement(func);
            container.appendChild(elem);
        });
    }

    function createChangedFunctionElement(func) {
        const div = document.createElement('div');
        div.className = 'changed-function';

        const name = document.createElement('div');
        name.className = 'changed-function-name';
        name.textContent = func.name;

        const location = document.createElement('div');
        location.className = 'changed-function-location';
        location.textContent = `${func.file_path}:${func.line_number}`;

        div.appendChild(name);
        div.appendChild(location);

        // Click to scroll to function in tree
        div.addEventListener('click', () => {
            scrollToFunction(func.qualified_name);
        });

        return div;
    }

    function scrollToFunction(qualifiedName) {
        // Find the function node in the tree
        const nodes = document.querySelectorAll('.tree-node');
        for (const node of nodes) {
            const nameElem = node.querySelector('.node-name');
            if (nameElem && nameElem.dataset.qualifiedName === qualifiedName) {
                // Expand parents if needed
                expandToNode(node);
                // Scroll into view
                node.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Highlight briefly
                node.style.backgroundColor = '#ffe69c';
                setTimeout(() => {
                    node.style.backgroundColor = '';
                }, 2000);
                break;
            }
        }
    }

    function expandToNode(node) {
        let current = node.parentElement;
        while (current) {
            if (current.classList.contains('tree-node')) {
                const toggle = current.querySelector('.node-toggle');
                if (toggle && toggle.textContent === '▶') {
                    toggle.click();
                }
            }
            current = current.parentElement;
        }
    }

})();
