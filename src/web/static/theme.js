(function() {
    'use strict';

    const THEME_KEY = 'flowdiff-theme';
    const THEME_ATTR = 'data-theme';

    function getStoredTheme() {
        return localStorage.getItem(THEME_KEY);
    }

    function setStoredTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
    }

    function getCurrentTheme() {
        return document.documentElement.getAttribute(THEME_ATTR) || 'light';
    }

    function setTheme(theme) {
        document.documentElement.setAttribute(THEME_ATTR, theme);
        setStoredTheme(theme);

        // Dispatch event for components that need to react
        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    }

    function toggleTheme() {
        const current = getCurrentTheme();
        const newTheme = current === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
    }

    function initializeTheme() {
        const initialTheme = getStoredTheme() || 'light';
        setTheme(initialTheme);

        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }
    }

    // Initialize on page load
    initializeTheme();

    // Expose globally
    window.FlowDiffTheme = {
        getCurrentTheme,
        setTheme,
        toggleTheme
    };
})();
