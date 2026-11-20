(() => {
  const share = document.querySelector('.selection-share');
  const shareUrl = document.querySelector('#selection-share-url');
  const shareResult = document.querySelector('[data-share-result]');
  document.querySelector('[data-selection-share]')?.addEventListener('click', () => {
    shareUrl.value = location.href.split('#')[0].split('?')[0];
    shareResult.textContent = '';
    share.showModal();
  });
  document.querySelector('[data-share-dismiss]')?.addEventListener('click', () => share.close());
  document.querySelector('[data-selection-copy]')?.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(shareUrl.value);
      shareResult.textContent = document.documentElement.lang === 'en' ? 'Link copied' : 'Ссылка скопирована';
    } catch {
      shareUrl.focus();
      shareUrl.select();
      shareResult.textContent = document.documentElement.lang === 'en' ? 'Press Ctrl+C or ⌘C to copy the link.' : 'Нажмите Ctrl+C или ⌘C, чтобы скопировать ссылку.';
    }
  });
  const dialog = document.querySelector('.selection-viewer');
  if (!dialog) return;
  const photos = [...document.querySelectorAll('.selection-photo')];
  let current = 0;
  function show(index) {
    current = (index + photos.length) % photos.length;
    const photo = photos[current];
    const img = dialog.querySelector('img');
    img.src = photo.dataset.full;
    img.alt = photo.dataset.title;
    dialog.querySelector('[data-title]').textContent = photo.dataset.title;
    dialog.querySelector('[data-position]').textContent = `${current + 1} / ${photos.length}`;
    dialog.querySelector('footer a').hidden = !photo.dataset.specimen;
    dialog.querySelector('footer a').href = photo.dataset.specimen || '#';
  }
  photos.forEach((photo, index) => photo.addEventListener('click', () => {
    show(index); dialog.showModal();
  }));
  dialog.querySelector('[data-dismiss]').addEventListener('click', () => dialog.close());
  dialog.querySelectorAll('[data-move]').forEach(button => button.addEventListener('click', () => show(current + Number(button.dataset.move))));
  dialog.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault(); show(current + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if(event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
})();
