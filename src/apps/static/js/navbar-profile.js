/* Conserva la activación nativa de summary con Enter/Espacio. */
(() => {
  document.querySelectorAll('[data-navbar-disclosure]').forEach((disclosure) => {
    const trigger = disclosure.querySelector(':scope > summary');
    const syncExpanded = () => trigger.setAttribute('aria-expanded', String(disclosure.open));
    const close = (restoreFocus = false) => {
      disclosure.open = false;
      syncExpanded();
      if (restoreFocus) trigger.focus();
    };
    const items = () => Array.from(disclosure.querySelectorAll('a[href], button:not([disabled]), summary'))
      .filter((item) => item !== trigger && item.getClientRects().length);

    syncExpanded();
    disclosure.addEventListener('toggle', syncExpanded);
    disclosure.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && disclosure.open) {
        event.preventDefault();
        event.stopPropagation();
        close(true);
      } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        disclosure.open = true;
        syncExpanded();
        const targets = items();
        if (!targets.length) return;
        const index = targets.indexOf(document.activeElement);
        const next = index < 0
          ? (event.key === 'ArrowDown' ? 0 : targets.length - 1)
          : (index + (event.key === 'ArrowDown' ? 1 : -1) + targets.length) % targets.length;
        targets[next].focus();
      }
    });
    disclosure.addEventListener('focusout', (event) => {
      if (!disclosure.contains(event.relatedTarget)) close();
    });
    document.addEventListener('click', (event) => {
      if (!disclosure.contains(event.target)) close();
    });
    window.matchMedia('(min-width: 1280px)').addEventListener('change', () => close());
  });
})();
