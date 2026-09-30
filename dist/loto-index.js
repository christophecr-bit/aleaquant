// Filtre les tirages Loto par date sans supposer qu'une date identifie un tirage.
// Les journées à deux séances conservent leurs deux liens distincts.
(() => {
  const date = document.getElementById('loto-date');
  const list = document.getElementById('loto-index');
  const status = document.getElementById('loto-date-status');
  if (!date || !list || !status) return;
  const items = Array.from(list.querySelectorAll('li[data-date]'));
  date.addEventListener('change', () => {
    let shown = 0;
    for (const item of items) {
      item.hidden = Boolean(date.value) && item.dataset.date !== date.value;
      if (!item.hidden) shown += 1;
    }
    status.textContent = date.value
      ? (shown ? `${shown} tirage${shown > 1 ? 's' : ''} le ${date.value}.` : `Aucun tirage Loto le ${date.value}.`)
      : 'Choisir une date filtre la liste ; certaines dates ont deux tirages distincts.';
  });
})();
