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
        const deletedFunctions = window.treeData.deleted_functions || [];

        // Update stats from metadata if available
        const metadata = window.treeData.metadata;
        if (metadata && metadata.functions_modified !== undefined) {
            document.getElementById('stat-modified').textContent = metadata.functions_modified;
            document.getElementById('stat-added').textContent = metadata.functions_added;
            document.getElementById('stat-deleted').textContent = metadata.functions_deleted;
        } else {
            // Fallback to local counting
            const stats = countChanges(changedFunctions, deletedFunctions);
            document.getElementById('stat-modified').textContent = stats.modified;
            document.getElementById('stat-added').textContent = stats.added;
            document.getElementById('stat-deleted').textContent = stats.deleted;
        }

        // Render changed functions list
        renderChangedFunctions(changedFunctions, deletedFunctions);
    }

    function extractChangedFunctions(trees) {
        const changed = [];
        const seen = new Set(); // Track qualified names to avoid duplicates

        function traverse(node) {
            if (node.function.has_changes) {
                // Only add if we haven't seen this function before
                if (!seen.has(node.function.qualified_name)) {
                    seen.add(node.function.qualified_name);
                    changed.push(node.function);
                }
            }
            if (node.children) {
                node.children.forEach(child => traverse(child));
            }
        }

        trees.forEach(tree => traverse(tree));
        return changed;
    }

    function extractDeletedFunctions(beforeTrees, afterTrees) {
        if (!beforeTrees || !afterTrees) {
            return [];
        }

        // Build a set of all qualified names in after_tree
        const afterNames = new Set();
        function collectAfterNames(node) {
            afterNames.add(node.function.qualified_name);
            if (node.children) {
                node.children.forEach(child => collectAfterNames(child));
            }
        }
        afterTrees.forEach(tree => collectAfterNames(tree));

        // Find functions in before_tree that have changes but don't exist in after_tree
        const deleted = [];
        const seen = new Set();

        function findDeleted(node) {
            // If this function has changes AND doesn't exist in after tree, it's deleted
            if (node.function.has_changes && !afterNames.has(node.function.qualified_name)) {
                if (!seen.has(node.function.qualified_name)) {
                    seen.add(node.function.qualified_name);
                    deleted.push(node.function);
                }
            }
            if (node.children) {
                node.children.forEach(child => findDeleted(child));
            }
        }

        beforeTrees.forEach(tree => findDeleted(tree));
        return deleted;
    }

    function countChanges(functions, deletedFunctions) {
        // For now, we only track modified
        // Can enhance later to distinguish added/deleted
        return {
            modified: functions.length,
            added: 0,
            deleted: deletedFunctions ? deletedFunctions.length : 0
        };
    }

    function renderChangedFunctions(functions, deletedFunctions) {
        const container = document.getElementById('changed-functions');

        if (functions.length === 0 && (!deletedFunctions || deletedFunctions.length === 0)) {
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

            // Show timestamp if available
            if (metadata && metadata.analysis_timestamp) {
                const timestamp = new Date(metadata.analysis_timestamp);
                const timeAgo = getTimeAgo(timestamp);
                message += `<div style="font-size: 0.8rem; color: #bbb; margin-top: 1rem;">Report from ${timeAgo}</div>`;
            }

            message += '</div>';
            container.innerHTML = message;
            return;
        }

        container.innerHTML = '';

        // Render deleted functions first (if any)
        if (deletedFunctions && deletedFunctions.length > 0) {
            const deletedHeader = document.createElement('div');
            deletedHeader.className = 'changes-section-header';
            deletedHeader.style.cssText = 'padding: 0.5rem 1rem; background: #2a1a1a; color: #ff6b6b; font-weight: 600; font-size: 0.9rem; border-left: 3px solid #ff6b6b;';
            deletedHeader.textContent = `🔴 Deleted (${deletedFunctions.length})`;
            container.appendChild(deletedHeader);

            deletedFunctions.forEach(func => {
                const elem = createDeletedFunctionElement(func);
                container.appendChild(elem);
            });
        }

        // Render modified/added functions
        if (functions.length > 0) {
            const changedHeader = document.createElement('div');
            changedHeader.className = 'changes-section-header';
            changedHeader.style.cssText = 'padding: 0.5rem 1rem; background: #1a251a; color: #90ee90; font-weight: 600; font-size: 0.9rem; border-left: 3px solid #90ee90; margin-top: 0.5rem;';
            changedHeader.textContent = `🟡 Modified/Added (${functions.length})`;
            container.appendChild(changedHeader);

            functions.forEach(func => {
                const elem = createChangedFunctionElement(func);
                container.appendChild(elem);
            });
        }
    }

    function getTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);

        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
        return date.toLocaleString();
    }

    function createChangedFunctionElement(func) {
        const div = document.createElement('div');
        div.className = 'changed-function';
        div.dataset.qualifiedName = func.qualified_name;  // Store for matching

        const name = document.createElement('div');
        name.className = 'changed-function-name';
        name.textContent = func.name;

        const location = document.createElement('div');
        location.className = 'changed-function-location';
        // Show only filename:line instead of full path
        location.textContent = `${func.file_name}:${func.line_number}`;

        div.appendChild(name);
        div.appendChild(location);

        // Click to scroll to function in tree
        div.addEventListener('click', () => {
            scrollToFunction(func.qualified_name);
        });

        return div;
    }

    function createDeletedFunctionElement(func) {
        const div = document.createElement('div');
        div.className = 'changed-function deleted-function';
        div.dataset.qualifiedName = func.qualified_name;  // Store for matching
        div.style.cssText = 'background: #2a1a1a; border-left: 3px solid #ff6b6b; opacity: 0.9; cursor: pointer;';

        const name = document.createElement('div');
        name.className = 'changed-function-name';
        name.style.cssText = 'text-decoration: line-through; color: #ff6b6b;';
        name.textContent = func.name;

        const location = document.createElement('div');
        location.className = 'changed-function-location';
        location.style.cssText = 'color: #ff9999;';
        // Show only filename:line instead of full path
        location.textContent = `${func.file_name}:${func.line_number}`;

        div.appendChild(name);
        div.appendChild(location);

        // Add click handler to switch to before view and show this function
        div.addEventListener('click', () => {
            if (window.showInBeforeTree) {
                window.showInBeforeTree(func.qualified_name);
            }
        });

        // Add hover effect
        div.addEventListener('mouseenter', () => {
            div.style.opacity = '1';
            div.style.boxShadow = '0 2px 4px rgba(255, 107, 107, 0.3)';
        });
        div.addEventListener('mouseleave', () => {
            div.style.opacity = '0.9';
            div.style.boxShadow = 'none';
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

                    // Select the node using tree.js's selectNode function
                    if (window.selectTreeNode) {
                        window.selectTreeNode(node);
                    } else {
                        // Fallback if selectTreeNode not available
                        node.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
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

    function highlightChangeInPanel(qualifiedName) {
        // Find the corresponding changed function in the diff panel
        const changedFunctions = document.querySelectorAll('.changed-function');

        // Remove previous selection
        changedFunctions.forEach(elem => {
            elem.classList.remove('selected');
        });

        // Find and highlight the matching function by exact qualified name match
        for (const elem of changedFunctions) {
            if (elem.dataset.qualifiedName === qualifiedName) {
                elem.classList.add('selected');
                elem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                break;
            }
        }
    }

    // Expose function for tree.js to call
    window.highlightChangeInPanel = highlightChangeInPanel;

})();
