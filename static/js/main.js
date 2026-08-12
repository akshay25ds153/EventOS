document.addEventListener('DOMContentLoaded', function () {

    const body = document.body;
    const htmlEl = document.documentElement;
    const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
    const accentSwatches = document.querySelectorAll('#accentSwatchGrid .color-swatch-btn');
    const fontBtns = document.querySelectorAll('.font-btn');
    const radiusBtns = document.querySelectorAll('#radiusGrid .radius-btn');
    const compactToggle = document.getElementById('compactModeToggle');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const animationsToggle = document.getElementById('animationsToggle');
    const reducedMotionToggle = document.getElementById('reducedMotionToggle');
    const resetBtn = document.getElementById('resetThemeBtn');

    // Accent mappings (Slug <-> Hex code from template buttons)
    const accentSlugs = {
        '#2563EB': 'ocean',
        '#4F46E5': 'indigo',
        '#8B5CF6': 'violet',
        '#0D9488': 'teal',
        '#10B981': 'emerald',
        '#F43F5E': 'rose'
    };
    const accentHexes = {
        'ocean': '#2563EB',
        'indigo': '#4F46E5',
        'violet': '#8B5CF6',
        'teal': '#0D9488',
        'emerald': '#10B981',
        'rose': '#F43F5E'
    };

    // Font mappings (Slug <-> Display names)
    const fontSlugs = {
        'Plus Jakarta Sans': 'plus-jakarta',
        'Inter': 'inter',
        'Poppins': 'poppins',
        'Outfit': 'outfit'
    };
    const fontDisplayNames = {
        'plus-jakarta': 'Plus Jakarta Sans',
        'inter': 'Inter',
        'poppins': 'Poppins',
        'outfit': 'Outfit'
    };

    // ==========================================================================
    // DEBOUNCED DATABASE SAVE
    // ==========================================================================
    let saveTimer = null;
    function syncPreferencesWithBackend() {
        if (!window.EMS_AUTH) return;

        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            const payload = {
                theme: htmlEl.getAttribute('data-theme') || 'light',
                accent: htmlEl.getAttribute('data-accent') || 'indigo',
                font: htmlEl.getAttribute('data-font') || 'plus-jakarta',
                border_radius: htmlEl.getAttribute('data-radius') || 'rounded',
                compact: htmlEl.getAttribute('data-compact') === 'true',
                animations: htmlEl.getAttribute('data-animations') === 'true',
                reduced_motion: htmlEl.getAttribute('data-motion') === 'true'
            };

            fetch('/api/profile/preferences/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.getCookie ? window.getCookie('csrftoken') : ''
                },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                console.log("EventOS preferences synced with database profile:", data);
            })
            .catch(err => console.error("EventOS preferences database sync failed:", err));
        }, 300);
    }

    // ==========================================================================
    // INITIALIZATION & SYNC FROM RENDERED DATA-ATTRIBUTES
    // ==========================================================================

    // Fetch values from server-rendered html tags (falling back to localStorage for guests)
    const activeTheme = htmlEl.getAttribute('data-theme') || localStorage.getItem('ems-theme') || 'light';
    const activeAccent = htmlEl.getAttribute('data-accent') || localStorage.getItem('ems-accent') || 'indigo';
    const activeFont = htmlEl.getAttribute('data-font') || localStorage.getItem('ems-font') || 'plus-jakarta';
    const activeRadius = htmlEl.getAttribute('data-radius') || localStorage.getItem('ems-radius') || 'rounded';
    const activeCompact = htmlEl.getAttribute('data-compact') ? htmlEl.getAttribute('data-compact') === 'true' : localStorage.getItem('ems-compact') === 'true';
    const activeAnimations = htmlEl.getAttribute('data-animations') ? htmlEl.getAttribute('data-animations') === 'true' : localStorage.getItem('ems-animations') !== 'false';
    const activeMotion = htmlEl.getAttribute('data-motion') ? htmlEl.getAttribute('data-motion') === 'true' : localStorage.getItem('ems-motion') === 'true';

    applyTheme(activeTheme);
    applyAccentColor(activeAccent);
    applyFont(activeFont);
    applyRadius(activeRadius);
    applyCompact(activeCompact);
    applyAnimations(activeAnimations);
    applyReducedMotion(activeMotion);

    // Synchronize toggle switch inputs
    if (darkModeToggle) darkModeToggle.checked = (activeTheme === 'dark');
    if (compactToggle) compactToggle.checked = activeCompact;
    if (animationsToggle) animationsToggle.checked = activeAnimations;
    if (reducedMotionToggle) reducedMotionToggle.checked = activeMotion;

    // Sidebar collapse state
    const savedSidebarState = localStorage.getItem('ems-sidebar-state') || 'expanded';
    if (savedSidebarState === 'collapsed') body.classList.add('sidebar-collapse');
    else body.classList.remove('sidebar-collapse');

    // ==========================================================================
    // EVENT LISTENERS
    // ==========================================================================

    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', function () {
            body.classList.toggle('sidebar-collapse');
            localStorage.setItem('ems-sidebar-state', body.classList.contains('sidebar-collapse') ? 'collapsed' : 'expanded');
        });
    }

    accentSwatches.forEach(swatch => {
        swatch.addEventListener('click', function () {
            const rawVal = this.getAttribute('data-accent');
            applyAccentColor(rawVal);
            localStorage.setItem('ems-accent', htmlEl.getAttribute('data-accent'));
            syncPreferencesWithBackend();
        });
    });

    fontBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const rawVal = this.getAttribute('data-font');
            applyFont(rawVal);
            localStorage.setItem('ems-font', htmlEl.getAttribute('data-font'));
            syncPreferencesWithBackend();
        });
    });

    radiusBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const val = this.getAttribute('data-radius');
            applyRadius(val);
            localStorage.setItem('ems-radius', val);
            syncPreferencesWithBackend();
        });
    });

    if (compactToggle) {
        compactToggle.addEventListener('change', function () {
            applyCompact(this.checked);
            localStorage.setItem('ems-compact', this.checked);
            syncPreferencesWithBackend();
        });
    }

    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', function () {
            const theme = this.checked ? 'dark' : 'light';
            applyTheme(theme);
            localStorage.setItem('ems-theme', theme);
            syncPreferencesWithBackend();
        });
    }

    if (animationsToggle) {
        animationsToggle.addEventListener('change', function () {
            applyAnimations(this.checked);
            localStorage.setItem('ems-animations', this.checked);
            syncPreferencesWithBackend();
        });
    }

    if (reducedMotionToggle) {
        reducedMotionToggle.addEventListener('change', function () {
            applyReducedMotion(this.checked);
            localStorage.setItem('ems-motion', this.checked);
            syncPreferencesWithBackend();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', function () {
            localStorage.clear();
            applyTheme('light');
            applyAccentColor('indigo');
            applyFont('plus-jakarta');
            applyRadius('rounded');
            applyCompact(false);
            applyAnimations(true);
            applyReducedMotion(false);

            if (darkModeToggle) darkModeToggle.checked = false;
            if (compactToggle) compactToggle.checked = false;
            if (animationsToggle) animationsToggle.checked = true;
            if (reducedMotionToggle) reducedMotionToggle.checked = false;

            syncPreferencesWithBackend();
        });
    }

    // ==========================================================================
    // STYLING HELPERS
    // ==========================================================================

    function applyTheme(theme) {
        htmlEl.setAttribute('data-theme', theme);
        body.classList.toggle('dark-mode', theme === 'dark');

        if (darkModeToggle) {
            const label = darkModeToggle.closest('.d-flex')?.querySelector('i');
            if (label) {
                label.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
                label.style.color = theme === 'dark' ? '#F59E0B' : '#6366F1';
            }
        }
    }

    function applyAccentColor(val) {
        let slug = val;
        let hex = val;
        if (accentHexes[val]) {
            hex = accentHexes[val];
        } else if (accentSlugs[val]) {
            slug = accentSlugs[val];
        } else {
            slug = 'indigo';
            hex = '#4F46E5';
        }

        htmlEl.setAttribute('data-accent', slug);
        accentSwatches.forEach(sw => {
            const swColor = sw.getAttribute('data-accent');
            const isActive = swColor === hex || swColor === slug;
            sw.style.borderColor = isActive ? '#000000' : 'transparent';
            sw.style.outlineOffset = isActive ? '2px' : '0';
        });
    }

    function applyFont(val) {
        let slug = val;
        if (fontSlugs[val]) {
            slug = fontSlugs[val];
        }

        htmlEl.setAttribute('data-font', slug);
        fontBtns.forEach(btn => {
            const btnFont = btn.getAttribute('data-font');
            const isActive = btnFont === val || btnFont === fontDisplayNames[slug];
            btn.classList.toggle('active', isActive);
            const icon = btn.querySelector('.font-check');
            if (icon) {
                icon.className = isActive ? 'bi bi-check-circle-fill text-dark font-check' : 'bi bi-circle text-muted font-check';
            }
        });
    }

    function applyRadius(val) {
        htmlEl.setAttribute('data-radius', val);
        radiusBtns.forEach(btn => {
            const isActive = btn.getAttribute('data-radius') === val;
            btn.classList.toggle('active', isActive);
            const icon = btn.querySelector('.radius-check');
            if (icon) {
                icon.className = isActive ? 'bi bi-check-circle-fill text-dark radius-check' : 'bi bi-circle text-muted radius-check';
            }
        });
    }

    function applyCompact(enabled) {
        htmlEl.setAttribute('data-compact', enabled);
        body.classList.toggle('compact-theme', enabled);
    }

    function applyAnimations(enabled) {
        htmlEl.setAttribute('data-animations', enabled);
    }

    function applyReducedMotion(enabled) {
        htmlEl.setAttribute('data-motion', enabled);
    }
});


/* ==========================================================================
   GLOBAL LIVE SEARCH — Navbar + Command Palette
   ========================================================================== */
(function () {
    'use strict';

    const SEARCH_URL = '/search/';
    let debounceTimer = null;

    // -----------------------------------------------------------------------
    // TYPE BADGE COLORS
    // -----------------------------------------------------------------------
    const typeMeta = {
        Event:    { bg: '#EEF2FF', color: '#4338CA' },
        Member:   { bg: '#F0FDF4', color: '#166534' },
        Category: { bg: '#FFF7ED', color: '#9A3412' },
        Venue:    { bg: '#F0F9FF', color: '#0369A1' },
    };

    function badge(type) {
        const m = typeMeta[type] || { bg: '#F4F4F5', color: '#3F3F46' };
        return `<span style="background:${m.bg};color:${m.color};font-size:0.68rem;font-weight:700;
                    padding:2px 8px;border-radius:99px;white-space:nowrap;">${type}</span>`;
    }

    // -----------------------------------------------------------------------
    // BUILD RESULT HTML
    // -----------------------------------------------------------------------
    function buildResult(r, isDark) {
        const hoverBg = isDark ? '#1D1F28' : '#F8FAFC';
        return `
            <a href="${r.url}" class="search-result-item d-flex align-items-center gap-3 px-4 py-3 text-decoration-none"
               style="border-bottom:1px solid ${isDark ? '#2A2C37' : '#F1F3F9'};
                      color:${isDark ? '#ECEEF2' : '#09090B'};transition:background 0.15s;"
               onmouseover="this.style.background='${hoverBg}'"
               onmouseout="this.style.background='transparent'">
                <i class="bi ${r.icon} fs-5" style="color:${isDark ? '#8B8FA8' : '#71717A'};min-width:20px;"></i>
                <div class="flex-grow-1 min-w-0">
                    <div class="fw-semibold text-truncate" style="font-size:0.88rem;">${r.title}</div>
                    <div class="text-truncate" style="font-size:0.76rem;color:${isDark ? '#8B8FA8' : '#71717A'};">${r.subtitle}</div>
                </div>
                ${badge(r.type)}
                <i class="bi bi-arrow-right" style="color:${isDark ? '#55586A' : '#D4D4D8'};font-size:0.8rem;"></i>
            </a>`;
    }

    function buildEmpty(query, isDark) {
        return `<div class="px-4 py-5 text-center" style="color:${isDark ? '#55586A' : '#A1A1AA'};">
                    <i class="bi bi-search d-block mb-2" style="font-size:1.5rem;"></i>
                    <div style="font-size:0.85rem;">No results for <strong>"${query}"</strong></div>
                    <div style="font-size:0.75rem;margin-top:4px;">Try events, members, categories or venues</div>
                </div>`;
    }

    function buildHeader(count, query, isDark) {
        return `<div class="px-4 py-2 d-flex align-items-center justify-content-between"
                    style="border-bottom:1px solid ${isDark ? '#2A2C37' : '#F1F3F9'};
                           font-size:0.72rem;font-weight:700;letter-spacing:0.07em;
                           color:${isDark ? '#55586A' : '#A1A1AA'};text-transform:uppercase;">
                    <span>${count} result${count !== 1 ? 's' : ''} for "${query}"</span>
                    <kbd style="background:${isDark ? '#1D1F28' : '#F4F4F5'};border:1px solid ${isDark ? '#2A2C37' : '#E4E4E7'};
                         border-radius:4px;padding:1px 6px;font-size:0.7rem;color:${isDark ? '#8B8FA8' : '#71717A'};">ESC</kbd>
                </div>`;
    }

    // -----------------------------------------------------------------------
    // NAVBAR SEARCH
    // -----------------------------------------------------------------------
    const navInput   = document.getElementById('navbarSearchInput');
    const navResults = document.getElementById('navbarSearchResults');
    const navSpinner = document.getElementById('navbarSearchSpinner');

    function isDarkMode() {
        return document.body.classList.contains('dark-mode');
    }

    function styleDropdown(el, dark) {
        el.style.background = dark ? '#16181F' : '#FFFFFF';
        el.style.borderColor = dark ? '#2A2C37' : '#E4E4E7';
    }

    function showNavResults(data) {
        if (!navResults) return;
        const dark = isDarkMode();
        styleDropdown(navResults, dark);

        let html = buildHeader(data.count, data.query, dark);
        if (data.count === 0) {
            html += buildEmpty(data.query, dark);
        } else {
            data.results.forEach(r => { html += buildResult(r, dark); });
        }
        navResults.innerHTML = html;
        navResults.classList.remove('d-none');
    }

    function hideNavResults() {
        if (navResults) navResults.classList.add('d-none');
    }

    async function doNavSearch(query) {
        if (navSpinner) navSpinner.classList.remove('d-none');
        try {
            const res = await fetch(`${SEARCH_URL}?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            showNavResults(data);
        } catch (_) {
            hideNavResults();
        } finally {
            if (navSpinner) navSpinner.classList.add('d-none');
        }
    }

    if (navInput) {
        navInput.addEventListener('input', function () {
            const q = this.value.trim();
            clearTimeout(debounceTimer);
            if (q.length < 2) { hideNavResults(); return; }
            debounceTimer = setTimeout(() => doNavSearch(q), 280);
        });

        navInput.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') { hideNavResults(); this.blur(); }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!navInput.contains(e.target) && !navResults?.contains(e.target)) {
                hideNavResults();
            }
        });

        // Reopen if clicking back into input while query is long enough
        navInput.addEventListener('focus', function () {
            if (this.value.trim().length >= 2 && navResults?.innerHTML) {
                navResults.classList.remove('d-none');
            }
        });
    }

    // -----------------------------------------------------------------------
    // COMMAND PALETTE (sidebar ⌘K) — enhanced with backend results
    // -----------------------------------------------------------------------
    const cmdInput   = document.getElementById('cmdInput');
    const cmdList    = document.getElementById('cmdList');
    const cmdBackdrop = document.querySelector('.cmd-palette-backdrop');

    // Static nav links already in the command palette
    function filterStaticItems(query) {
        if (!cmdList) return;
        const q = query.toLowerCase();
        const items = cmdList.querySelectorAll('.cmd-item[data-cmd]');
        items.forEach(item => {
            const label = (item.getAttribute('data-cmd') || '').toLowerCase();
            item.style.display = label.includes(q) ? '' : 'none';
        });
    }

    async function doCommandSearch(query) {
        if (!cmdList) return;

        // Remove previous live results block
        const prev = cmdList.querySelector('.cmd-live-results');
        if (prev) prev.remove();

        if (query.length < 2) { filterStaticItems(query); return; }

        filterStaticItems(query);

        try {
            const res = await fetch(`${SEARCH_URL}?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            if (!data.results.length) return;

            const dark = isDarkMode();
            let html = `<div class="cmd-live-results">
                <div class="px-4 py-1" style="font-size:0.7rem;font-weight:700;letter-spacing:0.07em;
                     color:${dark ? '#55586A' : '#A1A1AA'};text-transform:uppercase;border-top:1px solid ${dark ? '#2A2C37' : '#F1F3F9'};margin-top:4px;">
                    Live Results
                </div>`;
            data.results.forEach(r => {
                html += `<a href="${r.url}" class="cmd-item d-flex align-items-center gap-3">
                    <i class="bi ${r.icon}" style="min-width:18px;color:${dark ? '#8B8FA8' : '#71717A'};"></i>
                    <div class="flex-grow-1">
                        <div style="font-size:0.85rem;font-weight:600;">${r.title}</div>
                        <div style="font-size:0.75rem;color:${dark ? '#55586A' : '#A1A1AA'};">${r.subtitle}</div>
                    </div>
                    ${badge(r.type)}
                </a>`;
            });
            html += `</div>`;

            const block = document.createElement('div');
            block.innerHTML = html;
            cmdList.appendChild(block.firstElementChild);
        } catch (_) { /* silent fail */ }
    }

    if (cmdInput) {
        cmdInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            const q = this.value.trim();
            debounceTimer = setTimeout(() => doCommandSearch(q), 250);
        });
    }

});

// ==========================================================================
// UNIVERSAL GRID / TABLE VIEW SWITCHER MODULE
// ==========================================================================
window.switchView = function (view, isUserAction = true) {
    const gridView = document.getElementById('gridView') || 
                     document.getElementById('eventsGridView') || 
                     document.getElementById('budgetsGridView') || 
                     document.getElementById('categoriesGridView') || 
                     document.getElementById('venuesGridView') || 
                     document.getElementById('membersGridView') || 
                     document.getElementById('vendorsGridView') || 
                     document.getElementById('contractsGridView') || 
                     document.getElementById('resourcesGridView');

    const tableView = document.getElementById('tableView') || 
                      document.getElementById('eventsTableView') || 
                      document.getElementById('budgetsTableView') || 
                      document.getElementById('categoriesTableView') || 
                      document.getElementById('venuesTableView') || 
                      document.getElementById('membersTableView') || 
                      document.getElementById('vendorsTableView') || 
                      document.getElementById('contractsTableView') || 
                      document.getElementById('resourcesTableView');

    const btnGrid = document.getElementById('btnGridView');
    const btnTable = document.getElementById('btnTableView');

    if (!gridView || !tableView) return;

    if (view === 'table') {
        gridView.classList.add('d-none');
        tableView.classList.remove('d-none');
        if (btnTable) {
            btnTable.classList.add('active', 'btn-dark');
            btnTable.classList.remove('text-muted');
        }
        if (btnGrid) {
            btnGrid.classList.remove('active', 'btn-dark');
            btnGrid.classList.add('text-muted');
        }
    } else {
        gridView.classList.remove('d-none');
        tableView.classList.add('d-none');
        if (btnGrid) {
            btnGrid.classList.add('active', 'btn-dark');
            btnGrid.classList.remove('text-muted');
        }
        if (btnTable) {
            btnTable.classList.remove('active', 'btn-dark');
            btnTable.classList.add('text-muted');
        }
    }

    if (isUserAction) {
        localStorage.setItem('ems-view-preference', view);
    }
};

document.addEventListener('DOMContentLoaded', function () {
    const savedView = localStorage.getItem('ems-view-preference');
    if (savedView) {
        window.switchView(savedView, false);
    }
});

// ==========================================================================
// FLOATING HOVER OVERLAY TOOLTIP MODULE FOR MINIMIZED SIDEBAR
// ==========================================================================
(function () {
    let tooltipEl = null;

    function getTooltipEl() {
        if (!tooltipEl) {
            tooltipEl = document.getElementById('sidebarHoverOverlay');
            if (!tooltipEl) {
                tooltipEl = document.createElement('div');
                tooltipEl.id = 'sidebarHoverOverlay';
                tooltipEl.className = 'sidebar-hover-overlay-pill';
                document.body.appendChild(tooltipEl);
            }
        }
        return tooltipEl;
    }

    document.addEventListener('mouseover', function (e) {
        if (!document.body.classList.contains('sidebar-collapse')) {
            const el = getTooltipEl();
            if (el) el.classList.remove('show');
            return;
        }

        const target = e.target.closest('.sidebar-desktop [data-tooltip]');
        if (target) {
            const text = target.getAttribute('data-tooltip');
            if (!text) return;

            const el = getTooltipEl();
            const rect = target.getBoundingClientRect();
            el.textContent = text;
            el.style.top = (rect.top + rect.height / 2) + 'px';
            el.style.left = (rect.right + 12) + 'px';
            el.classList.add('show');
        }
    });

    document.addEventListener('mouseout', function (e) {
        const target = e.target.closest('.sidebar-desktop [data-tooltip]');
        if (target) {
            const el = getTooltipEl();
            if (el) el.classList.remove('show');
        }
    });
})();

// ==========================================================================
// ENTERPRISE REPORTING & EXPORT UTILITY
// ==========================================================================
window.exportData = function(type, buttonEl) {
    if (!buttonEl) return;
    
    const originalHtml = buttonEl.innerHTML;
    buttonEl.disabled = true;
    buttonEl.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Generating...`;
    
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.set('export', type);
    
    const downloadUrl = window.location.pathname + '?' + urlParams.toString();
    
    const tempLink = document.createElement('a');
    tempLink.href = downloadUrl;
    tempLink.setAttribute('download', '');
    document.body.appendChild(tempLink);
    tempLink.click();
    document.body.removeChild(tempLink);
    
    setTimeout(() => {
        buttonEl.disabled = false;
        buttonEl.innerHTML = originalHtml;
    }, 2500);
};


