// ReservaApp — main.js

// Auto-dismiss flash messages after 4s
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
      el.style.transition = 'opacity .3s, transform .3s';
      el.style.opacity = '0';
      el.style.transform = 'translateX(100%)';
      setTimeout(() => el.remove(), 300);
    });
  }, 4000);

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', e => {
    const sidebar = document.getElementById('sidebar');
    if (sidebar && sidebar.classList.contains('sidebar--open')) {
      if (!sidebar.contains(e.target) && !e.target.closest('.dash-topbar__menu')) {
        sidebar.classList.remove('sidebar--open');
      }
    }
  });
});
