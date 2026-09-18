(() => {
  const breakpoint = 600;
  const toggle = document.querySelector('#mobile-menu-toggle');
  const menu = document.querySelector('#site-navigation');
  const nav = document.querySelector('.site-nav');
  if (!toggle || !menu || !nav) return;

  // This is the sole owner of the mobile-menu state. No storage is used.
  document.documentElement.classList.add('mobile-nav-ready');
  const close = () => {
    menu.classList.remove('open');
    document.body.classList.remove('nav-open');
    toggle.setAttribute('aria-expanded', 'false');
  };
  const toggleMenu = () => {
    const open = menu.classList.toggle('open');
    document.body.classList.toggle('nav-open', open);
    toggle.setAttribute('aria-expanded', String(open));
  };

  toggle.addEventListener('click', toggleMenu);
  menu.querySelectorAll('a').forEach(link => link.addEventListener('click', close));
  document.addEventListener('click', event => {
    if (menu.classList.contains('open') && !nav.contains(event.target)) close();
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
  window.addEventListener('resize', () => { if (window.innerWidth > breakpoint) close(); });
})();
