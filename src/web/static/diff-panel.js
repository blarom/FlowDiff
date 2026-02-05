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

        // Update stats from metadata if available
        const metadata = window.treeData.metadata;
        if (metadata && metadata.functions_modified !== undefined) {
            document.getElementById('stat-modified').textContent = metadata.functions_modified;
            document.getElementById('stat-added').textContent = metadata.functions_added;
            document.getElementById('stat-deleted').textContent = metadata.functions_deleted;
        } else {
            // Fallback to local counting
            const stats = countChanges(changedFunctions);
            document.getElementById('stat-modified').textContent = stats.modified;
            document.getElementById('stat-added').textContent = stats.added;
            document.getElementById('stat-deleted').textContent = stats.deleted;
        }

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
            const metadata = window.treeData.metadata;
            let message = '<div style="color: #999; text-align: center; padding: 2rem; line-height: 1.6;">';
            message += '<div style="font-size: 48px; margin-bottom: 1rem;">✓</div>';
            message += '<div style="font-weight: 600; margin-bottom: 0.5rem;">No changes detected</div>';

            if (metadata && metadata.before_ref === 'HEAD' && metadata.after_ref === 'working') {
                message += '<div style="font-size: 0.9rem; color: #aaa;">No uncommitted changes in working directory</div>';
                message += '<div style="font-size: 0.85rem; color: #aaa; margin-top: 1rem;">Try comparing commits:<br/>--before HEAD~1 --after HEAD</div>';
            } else if (metadata) {
                message += `<div style="font-size: 0.9rem; color: #aaa;">Comparing ${metadata.before_ref} → ${metadata.after_ref}</div>`;
            }

            message += '</div>';
            container.innerHTML = message;
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
        const functionNames = document.querySelectorAll('.function-name');
        for (const nameElem of functionNames) {
            if (nameElem.dataset.qualifiedName === qualifiedName) {
                const node = nameElem.closest('.tree-node');
                if (node) {
                    // Expand parents if needed
                    expandToNode(node);
                    // Scroll into view
                    node.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // Highlight briefly
                    node.style.backgroundColor = '#ffe69c';
                    setTimeout(() => {
                        node.style.backgroundColor = '';
                    }, 2000);
                }
                break;
            }
        }
    }

    function expandToNode(node) {
        // Walk up the tree and expand all parent containers
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
    }

})();
