/**
 * app.js — AttendEase Frontend Scripts
 * Handles sidebar toggle, DataTables init, live date/time, and CSRF headers.
 */

'use strict';

/* ── DOMContentLoaded ─────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initDate();
  initDataTables();
  initAutoCloseFlash();
});

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
function initSidebar() {
  const sidebar      = document.getElementById('sidebar');
  const mainWrapper  = document.getElementById('mainWrapper');
  const toggleBtn    = document.getElementById('sidebarToggle');
  const mobileToggle = document.getElementById('mobileSidebarToggle');
  const overlay      = document.getElementById('sidebarOverlay');

  if (!sidebar) return;

  // Restore collapsed state
  const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
  if (collapsed) sidebar.classList.add('collapsed');

  // Desktop toggle
  toggleBtn?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
  });

  // Mobile toggle
  function openMobile() {
    sidebar.classList.add('mobile-open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeMobile() {
    sidebar.classList.remove('mobile-open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  mobileToggle?.addEventListener('click', openMobile);
  overlay?.addEventListener('click', closeMobile);

  // Close mobile sidebar on nav link click
  sidebar.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth < 768) closeMobile();
    });
  });
}

/* ── Live Date ────────────────────────────────────────────────────────────── */
function initDate() {
  const el = document.getElementById('currentDate');
  if (!el) return;

  function updateDate() {
    const now = new Date();
    el.textContent = now.toLocaleDateString('en-IN', {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  updateDate();
  setInterval(updateDate, 60_000);
}

/* ── DataTables ───────────────────────────────────────────────────────────── */
function initDataTables() {
  if (typeof $.fn?.DataTable === 'undefined') return;

  document.querySelectorAll('table.data-table').forEach(table => {
    $(table).DataTable({
      pageLength: 25,
      language: {
        search: '',
        searchPlaceholder: 'Search…',
        lengthMenu: 'Show _MENU_ entries',
        info: 'Showing _START_–_END_ of _TOTAL_',
        paginate: {
          previous: '<i class="bi bi-chevron-left"></i>',
          next:     '<i class="bi bi-chevron-right"></i>',
        },
      },
      dom: '<"row align-items-center mb-3"<"col-sm-6"l><"col-sm-6"f>>rtip',
      columnDefs: [{ orderable: false, targets: -1 }],
    });
  });
}

/* ── Auto-close flash messages after 5 seconds ──────────────────────────── */
function initAutoCloseFlash() {
  document.querySelectorAll('.flash-alert').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert?.close();
    }, 5000);
  });
}

/* ── CSRF helper for fetch() requests ────────────────────────────────────── */
function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content ?? '';
}

function fetchWithCsrf(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  });
}
