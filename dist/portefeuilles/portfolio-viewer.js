/*
 * Consultation EuroMillions reprise du prompteur local AleaQuant.
 * Sources lues le 2026-10-09, sans modification :
 * /Users/chris/aleaquant/loto-keno-lab-generic/src/lottery_ui/prompter.py
 * SHA-256 826f308bb4316ad196560cea9ab262f9291070438f9ef5b8138fe7956017edf9
 * /Users/chris/aleaquant/loto-keno-lab-generic/src/lottery_ui/app.py — render_prompter
 * SHA-256 34a727cf16ae17f33919db384514bcdae5231da5924501dd8928af0eefa712f0
 *
 * numberRows et groupWindow suivent les helpers Python. Les entiers JS sont
 * limités aux entiers sûrs. La consultation conserve seulement le groupe
 * affiché en mémoire ; elle ne modifie jamais les grilles ou leur empreinte.
 * Aucune API DOM n'est utilisée avant l'appel à create(profile).
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.AleaQuantPortfolioViewer = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  const groupMemory = new Map();
  const numberDomain = Object.freeze(Array.from({ length: 50 }, (_, index) => index + 1));
  const starDomain = Object.freeze(Array.from({ length: 12 }, (_, index) => index + 1));
  let instanceSequence = 0;

  function strictInteger(value, name) {
    if (!Number.isSafeInteger(value)) throw new TypeError(name + ' must be a safe integer');
  }

  function iterableValues(values, name) {
    if (values == null || typeof values[Symbol.iterator] !== 'function') throw new TypeError(name + ' must be iterable');
    return Array.from(values);
  }

  function numberRows(values, selected, columns) {
    strictInteger(columns, 'columns');
    if (columns < 1) throw new RangeError('columns must be positive');
    const domain = iterableValues(values, 'values');
    if (!domain.length || domain.some((value) => !Number.isSafeInteger(value))) throw new TypeError('values must be nonempty safe integers');
    if (domain.some((value, index) => index > 0 && value <= domain[index - 1])) throw new RangeError('values must be unique integers in natural order');
    const chosenValues = iterableValues(selected, 'selected');
    if (chosenValues.some((value) => !Number.isSafeInteger(value))) throw new TypeError('selected values must be safe integers');
    const chosen = new Set(chosenValues);
    const allowed = new Set(domain);
    if ([...chosen].some((value) => !allowed.has(value))) throw new RangeError('selected values must belong to the domain');
    const rows = [];
    for (let start = 0; start < domain.length; start += columns) {
      rows.push(domain.slice(start, start + columns).map((value) => ({ value, selected: chosen.has(value) })));
    }
    return rows;
  }

  function groupWindow(total, index, size = 6) {
    strictInteger(total, 'total');
    strictInteger(index, 'index');
    strictInteger(size, 'size');
    if (total < 1 || size < 1) throw new RangeError('total and size must be positive');
    const count = Math.ceil(total / size);
    if (index < 0 || index >= count) throw new RangeError('group index outside portfolio');
    const start = index * size;
    return { index, count, start, stop: Math.min(total, start + size) };
  }

  function validateSelection(values, cardinality, maximum, label) {
    if (!Array.isArray(values) || values.length !== cardinality) throw new TypeError(label + ' must contain exactly ' + cardinality + ' values');
    if (values.some((value) => !Number.isSafeInteger(value) || value < 1 || value > maximum)) throw new RangeError(label + ' values are outside the game domain');
    if (new Set(values).size !== cardinality) throw new RangeError(label + ' values must be distinct');
  }

  function validateProfile(profile) {
    if (!profile || typeof profile !== 'object' || !Array.isArray(profile.grids) || profile.grids.length < 1) throw new TypeError('profile must contain a nonempty grids array');
    if (profile.game_id !== undefined && profile.game_id !== 'euromillions') throw new RangeError('this viewer requires an EuroMillions profile');
    if (profile.grid_count !== undefined) {
      strictInteger(profile.grid_count, 'grid_count');
      if (profile.grid_count !== profile.grids.length) throw new RangeError('grid_count must match the grids array');
    }
    profile.grids.forEach((grid, index) => {
      if (!Array.isArray(grid) || grid.length !== 2) throw new TypeError('grid ' + (index + 1) + ' must contain numbers and stars');
      validateSelection(grid[0], 5, 50, 'grid ' + (index + 1) + ' numbers');
      validateSelection(grid[1], 2, 12, 'grid ' + (index + 1) + ' stars');
    });
    const hash = typeof profile.content_sha256 === 'string' && profile.content_sha256.trim() ? profile.content_sha256 : null;
    const id = typeof profile.id === 'string' && profile.id.trim() ? profile.id : null;
    if (!hash && !id) throw new TypeError('profile must have a content_sha256 or id for its consultation state');
    return hash ? 'sha256:' + hash : 'id:' + id;
  }

  function element(document, tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  function pad(value) { return String(value).padStart(2, '0'); }

  function numberBoard(document, selected, kind, gridNumber) {
    const isStar = kind === 'stars';
    const label = isStar ? 'Étoiles' : 'Numéros';
    const domain = isStar ? starDomain : numberDomain;
    const columns = isStar ? 6 : 10;
    const board = element(document, 'table', null, 'portfolio-viewer-board portfolio-viewer-' + kind);
    board.dataset.component = kind;
    board.dataset.columns = String(columns);
    board.setAttribute('aria-label', 'Grille ' + gridNumber + ' — ' + label.toLowerCase() + ' de 1 à ' + domain.length);
    const caption = element(document, 'caption', label + ' · 1 à ' + domain.length);
    const body = element(document, 'tbody');
    numberRows(domain, selected, columns).forEach((row) => {
      const tr = element(document, 'tr');
      row.forEach((cell) => {
        const td = element(document, 'td');
        const state = cell.selected ? 'sélectionné' + (isStar ? 'e' : '') : 'non sélectionné' + (isStar ? 'e' : '');
        const number = element(document, 'span', pad(cell.value), 'portfolio-viewer-cell ' + (cell.selected ? 'is-selected' : 'is-unselected'));
        number.dataset.value = String(cell.value);
        number.dataset.selected = String(cell.selected);
        const accessibleText = (isStar ? 'Étoile ' : 'Numéro ') + pad(cell.value) + ' — ' + state;
        td.setAttribute('aria-label', accessibleText);
        number.title = accessibleText;
        if (cell.selected) {
          const mark = element(document, 'span', '✓', 'portfolio-viewer-mark');
          mark.setAttribute('aria-hidden', 'true');
          number.append(mark);
        }
        td.append(number);
        tr.append(td);
      });
      body.append(tr);
    });
    board.append(caption, body);
    return board;
  }

  function gridCard(document, grid, index) {
    const card = element(document, 'article', null, 'portfolio-viewer-grid');
    card.dataset.gridIndex = String(index);
    card.dataset.gridNumber = String(index + 1);
    const header = element(document, 'div', null, 'portfolio-viewer-grid-heading');
    header.append(element(document, 'h4', 'Grille ' + pad(index + 1)), element(document, 'span', '5 numéros + 2 étoiles', 'portfolio-viewer-grid-format'));
    const selection = element(document, 'p', null, 'portfolio-viewer-selection');
    const main = element(document, 'span', 'Numéros : ');
    main.append(element(document, 'strong', grid[0].map(pad).join(' · ')));
    const stars = element(document, 'span', 'Étoiles : ');
    stars.append(element(document, 'strong', grid[1].map(pad).join(' · ')));
    selection.append(main, stars);
    card.append(header, selection, numberBoard(document, grid[0], 'numbers', index + 1), numberBoard(document, grid[1], 'stars', index + 1));
    return card;
  }

  function create(profile) {
    const key = validateProfile(profile);
    if (typeof document === 'undefined' || typeof document.createElement !== 'function') throw new Error('create(profile) requires a browser DOM');
    const dom = document;
    const total = profile.grids.length;
    const remembered = groupMemory.get(key) ?? 0;
    const count = groupWindow(total, 0).count;
    let window = groupWindow(total, Math.min(remembered, count - 1));
    const instance = 'aq-portfolio-viewer-' + (++instanceSequence);
    const viewer = element(dom, 'section', null, 'portfolio-viewer');
    viewer.dataset.profileId = typeof profile.id === 'string' ? profile.id : '';
    viewer.dataset.totalGrids = String(total);
    viewer.setAttribute('aria-labelledby', instance + '-title');

    const header = element(dom, 'div', null, 'portfolio-viewer-heading');
    const introduction = element(dom, 'div');
    introduction.append(element(dom, 'span', 'CONSULTATION / VUE DU PROMPTEUR', 'portfolio-viewer-eyebrow'));
    const title = element(dom, 'h3', 'Consulter les grilles');
    title.id = instance + '-title';
    const summary = element(dom, 'p', null, 'portfolio-viewer-status');
    summary.id = instance + '-status';
    summary.setAttribute('role', 'status');
    summary.setAttribute('aria-live', 'polite');
    summary.setAttribute('aria-atomic', 'true');
    introduction.append(title, summary);

    const navigation = element(dom, 'div', null, 'portfolio-viewer-navigation');
    navigation.setAttribute('role', 'group');
    navigation.setAttribute('aria-label', 'Naviguer dans les groupes de grilles');
    const previous = element(dom, 'button', '← Précédent', 'portfolio-viewer-previous');
    previous.type = 'button';
    previous.setAttribute('aria-label', 'Groupe précédent');
    previous.setAttribute('aria-controls', instance + '-grids');
    const groupLabel = element(dom, 'label', 'Groupe', 'portfolio-viewer-group-label');
    groupLabel.htmlFor = instance + '-group';
    const groupSelect = element(dom, 'select', null, 'portfolio-viewer-group-select');
    groupSelect.id = instance + '-group';
    groupSelect.setAttribute('aria-controls', instance + '-grids');
    groupSelect.setAttribute('aria-describedby', summary.id);
    for (let index = 0; index < count; index += 1) {
      const group = groupWindow(total, index);
      const option = element(dom, 'option', (index + 1) + ' / ' + count + ' · grilles ' + (group.start + 1) + ' à ' + group.stop);
      option.value = String(index);
      groupSelect.append(option);
    }
    groupLabel.append(groupSelect);
    const next = element(dom, 'button', 'Suivant →', 'portfolio-viewer-next');
    next.type = 'button';
    next.setAttribute('aria-label', 'Groupe suivant');
    next.setAttribute('aria-controls', instance + '-grids');
    navigation.append(previous, groupLabel, next);
    header.append(introduction, navigation);

    const legend = element(dom, 'div', null, 'portfolio-viewer-legend');
    legend.setAttribute('aria-label', 'Légende des tableaux de numéros');
    legend.append(element(dom, 'span', '✓ Numéro sélectionné', 'portfolio-viewer-legend-number'), element(dom, 'span', '✓ Étoile sélectionnée', 'portfolio-viewer-legend-star'), element(dom, 'span', 'Cellule claire sans ✓ : non sélectionnée', 'portfolio-viewer-legend-empty'));
    const explanation = element(dom, 'p', 'Chaque grille montre tous les numéros de 1 à 50 et toutes les étoiles de 1 à 12. Les 5 numéros et les 2 étoiles choisis portent un ✓.', 'portfolio-viewer-explanation');
    const cards = element(dom, 'div', null, 'portfolio-viewer-cards');
    cards.id = instance + '-grids';
    cards.setAttribute('aria-describedby', summary.id);
    viewer.append(header, legend, explanation, cards);

    function render(index) {
      window = groupWindow(total, index);
      groupMemory.set(key, window.index);
      viewer.dataset.groupIndex = String(window.index);
      summary.textContent = 'Groupe ' + (window.index + 1) + ' / ' + window.count + ' — grilles ' + (window.start + 1) + ' à ' + window.stop + ' sur ' + total;
      groupSelect.value = String(window.index);
      const focused = dom.activeElement;
      previous.disabled = window.index === 0;
      next.disabled = window.index === window.count - 1;
      const groupCards = [];
      for (let index = window.start; index < window.stop; index += 1) groupCards.push(gridCard(dom, profile.grids[index], index));
      cards.replaceChildren(...groupCards);
      // Navigation controls remain in the DOM. At a boundary, move focus from
      // the newly disabled button to the still usable group selector.
      if ((focused === previous && previous.disabled) || (focused === next && next.disabled)) groupSelect.focus({ preventScroll: true });
    }

    previous.addEventListener('click', () => { if (window.index > 0) render(window.index - 1); });
    next.addEventListener('click', () => { if (window.index < window.count - 1) render(window.index + 1); });
    groupSelect.addEventListener('change', () => {
      const value = groupSelect.value;
      if (!/^(0|[1-9]\d*)$/.test(value)) return;
      const index = Number(value);
      if (Number.isSafeInteger(index) && index >= 0 && index < count) render(index);
    });
    render(window.index);
    return viewer;
  }

  return Object.freeze({ numberRows, groupWindow, create });
});
