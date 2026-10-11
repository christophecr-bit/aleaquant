/* Catalogue descriptif : sources locales et exemples historiques restent séparés. */
(() => {
  'use strict';

  const SOURCES = Object.freeze({
    study: { url: '/data/portfolio_study.json', label: 'Étude locale', origin: 'local_study' },
    evolution: { url: '/data/portfolio_evolution.json', label: 'Évolution locale', origin: 'local_evolution' },
    local: { url: '/data/portfolio_search.json', label: 'Pipeline local', origin: 'local_pipeline' },
    archive: { url: '/data/portfolio_pipeline.json', label: 'Exemples historiques du ZIP', origin: 'archive' }
  });
  const SCHEMA = 'aleaquant-portfolio-pipeline-v1';
  const $ = (id) => document.getElementById(id);
  const numberFormat = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 3 });
  const integerFormat = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 });
  const moneyFormat = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 });
  const sourceCache = new Map();
  const viewMemory = new Map();
  let dataset;
  let activeSource = 'local';
  let activeBudget = 'all';
  let activePool = 'all';
  let selectedId;
  let loadSequence = 0;
  let studies = [];
  let activeStudyId;
  let evolutions = [];
  let activeEvolutionId;
  let explicitSourceChoice = false;

  function sourceUrl(key) {
    if (key === 'study') return studies.find((study) => study.id === activeStudyId)?.url || SOURCES.study.url;
    if (key === 'evolution') return evolutions.find((entry) => entry.id === activeEvolutionId)?.url || SOURCES.evolution.url;
    return SOURCES[key].url;
  }
  function viewKey() {
    if (activeSource === 'study') return 'study:' + (activeStudyId || 'current');
    if (activeSource === 'evolution') return 'evolution:' + (activeEvolutionId || 'current');
    return activeSource;
  }

  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }
  function finite(value) { return typeof value === 'number' && Number.isFinite(value); }
  function amount(value) { return finite(value) ? moneyFormat.format(value) : '—'; }
  function integer(value) { return finite(value) ? integerFormat.format(value) : '—'; }
  function decimal(value) { return finite(value) ? numberFormat.format(value) : '—'; }
  function percent(value) {
    if (!finite(value)) return '—';
    if (value === 0) return '0 %';
    if (Math.abs(value) < 0.00001) return (value * 100).toExponential(3).replace('.', ',') + ' %';
    return new Intl.NumberFormat('fr-FR', { style: 'percent', maximumFractionDigits: 3 }).format(value);
  }
  function simpleValue(value) {
    if (value === null || value === undefined || value === '') return '—';
    if (Array.isArray(value)) return value.map(simpleValue).join(' · ');
    if (typeof value === 'object') return Object.entries(value).map(([key, item]) => key + ' : ' + simpleValue(item)).join(' ; ');
    return String(value);
  }
  function probabilityDetail(value) {
    if (!finite(value) || value <= 0) return value === 0 ? 'Probabilité nulle dans le modèle déclaré.' : 'Valeur indisponible.';
    return 'Environ 1 chance sur ' + integer(1 / value) + ' par tirage.';
  }
  function isStudy() { return dataset?.origin === 'local_study'; }
  function isEvolution() { return dataset?.origin === 'local_evolution'; }
  function isLocal() { return dataset?.origin === 'local_pipeline' || isStudy() || isEvolution(); }
  function referenceRole(profile) {
    const role = profile.reference_benchmark?.role;
    return ['same_pool', 'full_domain'].includes(role) && profile.reference_benchmark.selection_eligible === false &&
      dataset.controlled?.roles?.[role]?.includes(profile.id) ? role : undefined;
  }
  function referenceName(role) {
    return role === 'same_pool' ? 'RANDOM · mêmes pools' : role === 'full_domain' ? 'RANDOM · domaine complet' : 'Construction étudiée';
  }
  function benchmarkCohort(role, phase = 'comparison') {
    return dataset.reference_benchmark?.qualification?.[phase]?.cohorts?.find((cohort) => cohort.role === role);
  }
  function qualifiedReference(profile, phase = 'comparison') {
    const role = referenceRole(profile);
    const cohort = role && benchmarkCohort(role, phase);
    return cohort?.status === 'qualified' && Array.isArray(cohort.control_ids) && cohort.control_ids.includes(profile.id);
  }
  function benchmarkPresence(members) {
    const qualified = members.filter((profile) => qualifiedReference(profile));
    if (qualified.length) return 'Références qualifiées : ' + [...new Set(qualified.map(referenceRole))].map(referenceName).join(' ; ') + '.';
    if (members.some(referenceRole)) return 'Références déclarées ; leur qualification n’est pas confirmée dans cette source.';
    return 'Aucune référence RANDOM qualifiée de ces deux rôles dans cette cohorte.';
  }
  function studyTitle(value) {
    return simpleValue(value).replace(/\bablation overlap\b/gi, 'Étude du poids de recouvrement').replace(/Effet de minimize_overlap/gi, 'Effet du poids de recouvrement')
      .replace(/\bablation\b/gi, 'étude de l’effet du poids de recouvrement');
  }
  function mainProfiles() {
    if (Array.isArray(dataset.controlled?.main_record_ids)) {
      const ids = new Set(dataset.controlled.main_record_ids);
      return dataset.profiles.filter((profile) => ids.has(profile.id));
    }
    return dataset.profiles.filter((profile) => !referenceRole(profile));
  }
  function countItems(value) { return Array.isArray(value) ? value.length : finite(value) ? value : undefined; }
  function operatorName(value) {
    return ({ starting_portfolio: 'Parent initial', replace_number_v1: 'Remplacement d’un numéro',
      swap_numbers_v1: 'Échange de numéros', replace_grid_v1: 'Remplacement d’une grille',
      grid_crossover_v1: 'Croisement de deux parents' })[value] || simpleValue(value);
  }
  function rejectionSummary(value) {
    if (!Array.isArray(value)) return simpleValue(value);
    if (!value.length) return '0';
    const reasons = new Map();
    value.forEach((proposal) => {
      const reason = proposal?.reason || 'non précisé';
      reasons.set(reason, (reasons.get(reason) || 0) + 1);
    });
    const names = { duplicate_portfolio: 'Contenu déjà présent', invalid_constraints: 'Contraintes invalides',
      operator_proposal_rejected: 'Proposition non retenue par l’opérateur', requested_guarantee_not_proved: 'Garantie demandée non prouvée' };
    return value.length + ' · ' + [...reasons].map(([reason, count]) => integer(count) + ' ' + (names[reason] || reason)).join(' ; ');
  }
  function actualBudget(profile) { return profile.budget_actual_eur ?? profile.budget_eur; }
  function profileTitle(profile) {
    const role = referenceRole(profile);
    if (role) return referenceName(role) + ' · référence ' + (dataset.controlled.roles[role].indexOf(profile.id) + 1);
    if (profile.study_factor) {
      const peers = mainProfiles().filter((entry) => entry.study_factor?.weight === profile.study_factor.weight);
      return 'Poids ' + decimal(profile.study_factor.weight) + ' · construction ' + (peers.findIndex((entry) => entry.id === profile.id) + 1);
    }
    const parent = profile.id?.match(/_parent(\d+)$/);
    if (isEvolution() && parent) return 'Parent initial ' + Number(parent[1]);
    const child = profile.id?.match(/_g(\d+)_p(\d+)$/);
    if (isEvolution() && child) return 'Génération ' + Number(child[1]) + ' · proposition ' + Number(child[2]);
    if (profile.display_name && profile.display_name !== profile.id) return profile.display_name;
    return familyTitle(profile) + ' · ' + integer(profile.grid_count) + ' grilles · fiche ' + (dataset.profiles.indexOf(profile) + 1);
  }
  function familyTitle(profile) {
    const source = profile.display_family || profile.family || '';
    const translations = {
      COVERAGE: 'Couverture', COMPLETE: 'Couverture', COVERING: 'Couverture',
      BALANCED: 'Équilibré', LOW_OVERLAP: 'Faible recouvrement',
      LOWOVERLAP: 'Faible recouvrement', SPREAD: 'Faible recouvrement',
      CONCENTRATED: 'Concentré', CLUSTERED: 'Concentré',
      RANDOM: 'Aléatoire (RANDOM)', GREEDY: 'Recherche gloutonne',
      STRUCTURED: 'Structuré', MUTATION: 'Mutation', CROSSOVER: 'Croisement'
    };
    return translations[String(source).toUpperCase()] || source || 'Famille non renseignée';
  }
  function isRandom(profile) {
    return String(profile.family || '').toUpperCase() === 'RANDOM' ||
      String(profile.display_family || '').toUpperCase() === 'RANDOM';
  }
  function localEvaluation(profile) {
    const evaluation = profile.evaluation || {};
    return evaluation.method === 'monte_carlo' && evaluation.replayed === true &&
      typeof profile.content_sha256 === 'string' && evaluation.content_sha256 === profile.content_sha256;
  }
  function evaluationLabel(profile) {
    if (localEvaluation(profile)) return 'Monte-Carlo exécuté par le moteur local';
    if (profile.evaluation?.method === 'imported_monte_carlo') return 'Monte-Carlo fourni avec le ZIP · non rejoué';
    return 'Évaluation non confirmée par ce catalogue';
  }
  function stateLabel(value) {
    return ({
      draft: 'Brouillon', invalid: 'Invalide', feasible: 'Faisable',
      evaluated: 'Évalué', certified: 'Certifié sous condition',
      search_exhausted: 'Recherche épuisée', proven_infeasible: 'Infaisabilité prouvée', complete: 'Terminée'
    })[value] || simpleValue(value);
  }

  function block(title, method, introduction) {
    const section = node('section', null, 'profile-block');
    const heading = node('div', null, 'block-heading');
    heading.append(node('h3', title), node('span', method, 'method-label'));
    section.append(heading);
    if (introduction) section.append(node('p', introduction, 'block-intro'));
    return section;
  }
  function stats(items) {
    const dl = node('dl', null, 'stat-grid');
    items.forEach(([label, value, note]) => {
      const container = node('div', null, 'stat');
      const dd = node('dd', value);
      if (note) dd.append(node('small', note));
      container.append(node('dt', label), dd);
      dl.append(container);
    });
    return dl;
  }
  function table(caption, headings, rows, numericColumns = []) {
    const wrapper = node('div', null, 'table-scroll');
    const element = node('table', null, 'catalogue-table');
    element.append(node('caption', caption));
    const thead = node('thead');
    const headerRow = node('tr');
    headings.forEach((label, index) => {
      const th = node('th', label, numericColumns.includes(index) ? 'numeric' : '');
      th.scope = 'col';
      headerRow.append(th);
    });
    thead.append(headerRow);
    const tbody = node('tbody');
    rows.forEach((values) => {
      const row = node('tr');
      values.forEach((value, index) => {
        const cell = node(index === 0 ? 'th' : 'td', null, numericColumns.includes(index) ? 'numeric' : '');
        if (index === 0) cell.scope = 'row';
        if (value && typeof value === 'object' && typeof value.nodeType === 'number') cell.append(value);
        else cell.textContent = simpleValue(value);
        row.append(cell);
      });
      tbody.append(row);
    });
    element.append(thead, tbody);
    wrapper.append(element);
    return wrapper;
  }
  function addProvenance(dl, label, value, isCode = false) {
    const dd = node('dd');
    dd.append(node(isCode ? 'code' : 'span', simpleValue(value)));
    dl.append(node('dt', label), dd);
  }
  function jsonDetails(title, value) {
    const details = node('details', null, 'configuration-detail');
    details.append(node('summary', title));
    const code = node('code', JSON.stringify(value, null, 2));
    const pre = node('pre', null, 'configuration-json');
    pre.append(code);
    details.append(pre);
    return details;
  }
  function protocolDetails(...children) {
    const details = node('details', null, 'configuration-detail protocol-details');
    details.append(node('summary', 'Protocole et reproductibilité'), ...children);
    return details;
  }
  function conceptLink(label, slug) {
    const link = node('a', label, 'concept-link');
    const anchors = {portefeuilles:'portefeuille',recouvrement:'recouvrement',score:'score',construction:'construction',
      'etude-parametre':'ablation',mutation:'mutation',croisement:'croisement','reference-random':'random',
      'monte-carlo':'monte-carlo','garantie-conditionnelle':'garantie',selection:'selection',pool:'pool',couverture:'couverture',graine:'graine'};
    link.href = '/comprendre/glossaire/#' + (anchors[slug] || slug);
    return link;
  }
  function listNotes(values, className = 'limitation-list') {
    const list = node('ul', null, className);
    const items = Array.isArray(values) ? values : values ? [values] : [];
    items.forEach((value) => list.append(node('li', simpleValue(value))));
    return list;
  }

  function configuration(profile) {
    if (profile.profile_object) return profile.profile_object;
    const id = profile.lineage?.profile_node_id;
    return dataset.graph?.nodes?.find((item) => item.id === id)?.data || null;
  }
  function maximumBudget(profile) {
    const config = configuration(profile);
    return profile.budget_max_eur ?? config?.constraints?.budget_max_eur ?? config?.profile?.constraints?.budget_max_eur;
  }
  function samePoolCohorts() { return Array.isArray(dataset.comparisons?.same_pool) ? dataset.comparisons.same_pool : []; }
  function differentPoolCohorts() { return Array.isArray(dataset.comparisons?.different_pools) ? dataset.comparisons.different_pools : []; }
  function poolKey(profile) {
    if (profile.pool_id) return String(profile.pool_id);
    const cohort = samePoolCohorts().find((item) => Array.isArray(item.profile_ids) && item.profile_ids.includes(profile.id));
    if (cohort?.pool_id) return String(cohort.pool_id);
    return 'numbers:' + (profile.pool_numbers || []).join(',') + '|stars:' + (profile.pool_stars || []).join(',');
  }
  function poolLabel(profile) {
    if (profile.pool_label || profile.pool_name) return String(profile.pool_label || profile.pool_name);
    const cohort = samePoolCohorts().find((item) => item.pool_id === poolKey(profile));
    if (cohort?.pool_label || cohort?.pool_name) return String(cohort.pool_label || cohort.pool_name);
    const counts = integer(profile.pool_numbers?.length) + ' numéros · ' + integer(profile.pool_stars?.length) + ' étoiles';
    const key = poolKey(profile);
    const similar = [...new Set(dataset.profiles.filter((item) => item.pool_numbers?.length === profile.pool_numbers?.length && item.pool_stars?.length === profile.pool_stars?.length).map(poolKey))];
    return counts + (similar.length > 1 ? ' · ensemble ' + (similar.indexOf(key) + 1) : '');
  }
  function profileByReference(reference) {
    const value = String(reference);
    return dataset.profiles.find((profile) => profile.id === value || profile.content_sha256 === value ||
      'portfolio:' + profile.content_sha256 === value || profile.lineage?.profile_node_id === value ||
      profile.lineage?.portfolio_node_id === value);
  }
  function profileLink(profile) {
    const link = node('a', profileTitle(profile), 'profile-reference-link');
    link.href = '#profile-section';
    link.addEventListener('click', (event) => {
      event.preventDefault();
      if ((activeBudget !== 'all' && String(actualBudget(profile)) !== activeBudget) ||
          (activePool !== 'all' && poolKey(profile) !== activePool)) {
        activeBudget = 'all';
        activePool = 'all';
        renderFilters();
        renderCohorts();
        renderComparisons();
      }
      selectProfile(profile.id, true);
    });
    return link;
  }
  function rememberView() {
    viewMemory.set(viewKey(), { budget: activeBudget, pool: activePool, selectedId });
  }

  function renderFilters() {
    const filters = $('budget-filters');
    const budgets = [...new Set(dataset.profiles.map(actualBudget).filter(finite))].sort((a, b) => a - b);
    if (activeBudget !== 'all' && !budgets.some((budget) => String(budget) === activeBudget)) activeBudget = 'all';
    filters.replaceChildren();
    [['all', 'Tous les budgets'], ...budgets.map((budget) => [String(budget), amount(budget)])].forEach(([value, label]) => {
      const button = node('button', label);
      button.type = 'button';
      button.dataset.budget = value;
      button.setAttribute('aria-pressed', String(value === activeBudget));
      filters.append(button);
    });
    const pools = new Map();
    dataset.profiles.forEach((profile) => { if (!pools.has(poolKey(profile))) pools.set(poolKey(profile), poolLabel(profile)); });
    if (activePool !== 'all' && !pools.has(activePool)) activePool = 'all';
    const select = $('pool-select');
    select.replaceChildren();
    [['all', 'Tous les pools'], ...pools].forEach(([value, label]) => {
      const option = node('option', label);
      option.value = value;
      select.append(option);
    });
    select.value = activePool;
    $('pool-filter').hidden = !isLocal() || pools.size < 2;
  }

  function visibleProfiles() {
    return dataset.profiles.filter((profile) =>
      (activeBudget === 'all' || String(actualBudget(profile)) === activeBudget) &&
      (activePool === 'all' || poolKey(profile) === activePool));
  }
  function groupsForProfiles(profiles) {
    const ids = new Set(profiles.map((profile) => profile.id));
    const declared = isLocal() && samePoolCohorts().length ? samePoolCohorts() : Array.isArray(dataset.cohorts) ? dataset.cohorts : [];
    const groups = declared.map((cohort) => ({
      cohort,
      profiles: (cohort.profile_ids || []).map((id) => dataset.profiles.find((profile) => profile.id === id)).filter((profile) => profile && ids.has(profile.id))
    })).filter((group) => group.profiles.length);
    const represented = new Set(groups.flatMap((group) => group.profiles.map((profile) => profile.id)));
    const remaining = profiles.filter((profile) => !represented.has(profile.id));
    [...new Set(remaining.map(actualBudget))].sort((a, b) => a - b).forEach((budget) => {
      const members = remaining.filter((profile) => actualBudget(profile) === budget);
      groups.push({ cohort: { budget_eur: budget, random_reference_available: members.some(isRandom) }, profiles: members });
    });
    if (!dataset.controlled) return groups;
    return groups.flatMap((group) => [undefined, 'same_pool', 'full_domain'].map((role) => ({
      ...group, role, profiles: group.profiles.filter((profile) => referenceRole(profile) === role)
    })).filter((group) => group.profiles.length));
  }
  function renderCohorts() {
    const container = $('profile-cohorts');
    container.replaceChildren();
    const profiles = visibleProfiles();
    groupsForProfiles(profiles).forEach(({ cohort, profiles: members, role }) => {
      const section = node('section', null, 'cohort');
      const heading = node('div', null, 'cohort-heading');
      const label = amount(cohort.budget_eur ?? actualBudget(members[0])) + (isLocal() ? ' · ' + poolLabel(members[0]) : '');
      const randomAvailable = cohort.random_reference_available === true;
      heading.append(node('h3', dataset.controlled ? referenceName(role) + ' · ' + label : label), node('p', members.length + ' fiche' + (members.length > 1 ? 's' : '') + ' · ' + (dataset.controlled ? role ? 'références conservées hors sélection' : 'constructions du plan principal' : isStudy() || isEvolution() ? benchmarkPresence(members) : randomAvailable ? 'référence RANDOM déclarée à coût et pool égaux' : 'référence RANDOM absente de cette cohorte')));
      const cards = node('div', null, 'profile-cards');
      members.forEach((profile) => {
        const button = node('button', null, 'profile-card');
        button.type = 'button';
        button.dataset.profileId = String(profile.id);
        button.setAttribute('aria-pressed', String(profile.id === selectedId));
        button.setAttribute('aria-controls', 'profile-section');
        button.append(node('span', familyTitle(profile), 'card-family'), node('span', profileTitle(profile), 'card-title'),
          node('span', integer(profile.grid_count) + ' grilles · coût ' + amount(actualBudget(profile)), 'card-facts'));
        if (isLocal()) {
          const reference = profile.generation?.method === 'reference_import';
          button.append(node('span', reference ? 'Grilles de référence ZIP · ' + (localEvaluation(profile) ? 'évaluation locale' : 'évaluation à confirmer') : stateLabel(profile.state), 'card-origin'));
        }
        const benchmarkRole = referenceRole(profile);
        if (benchmarkRole) button.append(node('span', referenceName(benchmarkRole) + (qualifiedReference(profile) ? ' · qualifiée' : ' · à qualifier') + ' · hors sélection', 'card-reference-role'));
        if (isStudy() && profile.study_factor) button.append(node('span', 'Poids de recouvrement : ' + decimal(profile.study_factor.weight), 'card-study-factor'));
        if (isEvolution() && !benchmarkRole) {
          button.append(node('span', 'Génération ' + integer(profile.generation?.generation_index) + ' · ' + operatorName(profile.lineage?.operator || profile.generation?.operator), 'card-evolution'));
          const flags = [profile.is_starting_parent ? 'Parent initial' : undefined, profile.is_survivor ? 'Population finale' : undefined, profile.is_finalist ? 'Confirmé séparément' : undefined].filter(Boolean);
          if (flags.length) button.append(node('span', flags.join(' · '), 'card-evolution-flags'));
        }
        if (benchmarkRole && profile.confirmation) button.append(node('span', 'Référence confirmée séparément', 'card-evolution-flags'));
        button.append(node('span', profile.id === selectedId ? 'Fiche affichée ↓' : 'Lire la fiche →', 'card-action'));
        button.addEventListener('click', () => selectProfile(profile.id, true));
        cards.append(button);
      });
      section.append(heading, cards);
      container.append(section);
    });
    if (!profiles.length) container.append(node('p', 'Aucune fiche pour ce budget et ce pool.', 'empty-profiles'));
    $('catalogue-status').textContent = profiles.length + ' fiche' + (profiles.length > 1 ? 's' : '') + ' affichée' + (profiles.length > 1 ? 's' : '') + ' · ' + SOURCES[activeSource].label + ' · ordre de la source, sans classement Monte-Carlo';
    return profiles;
  }
  function updateCardSelection() {
    document.querySelectorAll('.profile-card').forEach((button) => {
      const active = button.dataset.profileId === String(selectedId);
      button.setAttribute('aria-pressed', String(active));
      button.querySelector('.card-action').textContent = active ? 'Fiche affichée ↓' : 'Lire la fiche →';
    });
  }

  function summaryMetricName(id) {
    const names = {
      'portfolio.distinct_pairs': 'Paires couvertes',
      'portfolio.distinct_triples': 'Triplets couverts',
      'portfolio.number_frequency_sd': 'Dispersion des occurrences de numéros',
      'portfolio.max_number_overlap': 'Intersection maximale des numéros',
      'portfolio.any_prize_probability': 'Au moins une grille gagnante',
      'portfolio.multiple_prizes_probability': 'Au moins deux grilles gagnantes',
      'portfolio.at_least_3_numbers_probability': 'Au moins une grille avec 3 numéros',
      'portfolio.at_least_4_numbers_probability': 'Au moins une grille avec 4 numéros',
      'portfolio.mean_winning_grids': 'Moyenne des grilles gagnantes'
    };
    const definition = metricDefinition(id);
    return definition?.name || definition?.label || names[id.split('@')[0]] || id;
  }
  function summaryMetricValue(value, id) {
    const definition = metricDefinition(id);
    return ['ratio', 'probability', 'proportion'].includes(definition?.unit) || /probability/.test(id) ? percent(value) : decimal(value);
  }
  function differenceValue(value, id) {
    return /probability/.test(id) ? finite(value) ? decimal(value * 100) + ' pp' : '—' : decimal(value);
  }
  function benchmarkSummaryRows(summary, differences = false) {
    return Object.entries(summary || {}).filter(([, values]) => finite(values?.mean)).map(([id, values]) => [
      summaryMetricName(id), integer(values.n),
      (differences ? differenceValue : summaryMetricValue)(values.mean, id),
      (differences ? differenceValue : summaryMetricValue)(values.min, id),
      (differences ? differenceValue : summaryMetricValue)(values.max, id),
      (differences ? differenceValue : summaryMetricValue)(values.sd, id)
    ]);
  }
  function summaryRows(groups, paired) {
    return groups.flatMap((group) => Object.entries(group.metrics || {}).map(([id, values]) => [
      paired ? decimal(group.weight_b) + ' − ' + decimal(group.weight_a) : decimal(group.weight),
      integer(group.repetitions), summaryMetricName(id),
      summaryMetricValue(values?.mean, id), summaryMetricValue(values?.min, id), summaryMetricValue(values?.max, id)
    ]));
  }
  function renderStudy() {
    $('study-section').hidden = !isStudy();
    $('study-detail').replaceChildren();
    if (!isStudy()) return;
    const study = dataset.study || {};
    const analysis = dataset.analysis || {};
    $('study-title').textContent = study.title ? studyTitle(study.title) : 'Une étude sur plusieurs graines';
    $('study-question').textContent = study.axis?.parameter?.includes('minimize_overlap') ? 'Quand on renforce la pénalité sur les numéros communs entre grilles, qu’est-ce qui s’améliore et qu’est-ce qui se dégrade ?' : simpleValue(study.question);
    const content = $('study-detail');
    const main = mainProfiles();
    const first = main[0] || {};
    content.append(stats([
      ['Constructions étudiées', integer(main.length), 'Plan principal, références RANDOM séparées'],
      ['Poids étudiés', Array.isArray(study.axis?.values) ? study.axis.values.map(decimal).join(' · ') : '—', 'Pénalité de recouvrement des numéros'],
      ['Constructions par réglage', integer(study.repetitions), 'Dix essais correspondants dans ce plan'],
      ['Grilles par portefeuille', integer(first.grid_count), 'Coût réel : ' + amount(actualBudget(first))]
    ]));
    const dl = node('dl', null, 'provenance study-provenance');
    addProvenance(dl, 'Identifiant de l’étude', study.id || dataset.study_id, true);
    if (study.config_id) addProvenance(dl, 'Configuration de l’étude', study.config_id, true);
    addProvenance(dl, 'Exécution de l’étude', study.run_id || dataset.source?.study_run_id || dataset.run_id, true);
    if (dataset.run_id && dataset.run_id !== study.run_id) addProvenance(dl, 'Exécution du pipeline', dataset.run_id, true);
    addProvenance(dl, 'Paramètre variable', study.axis?.parameter, true);
    addProvenance(dl, 'Graines de génération', study.seeds, true);
    addProvenance(dl, 'Bornes de recherche', study.bounds);
    addProvenance(dl, 'Comparaison', integer(study.comparison?.draws) + ' tirages · graine ' + simpleValue(study.comparison?.seed));
    addProvenance(dl, 'Confirmation indépendante', integer(study.confirmation?.draws) + ' tirages · graine ' + simpleValue(study.confirmation?.seed));
    addProvenance(dl, 'Règle de sélection des finalistes', study.confirmation?.selection_rule);
    const protocol = protocolDetails(dl);
    protocol.append(conceptLink('Comprendre la graine de génération →', 'graine'));
    content.append(protocol);
    content.append(node('p', 'Quatre réglages sont essayés sur dix constructions correspondantes. Pour chaque essai, on conserve le même code de hasard — appelé graine — et les autres paramètres. Cela permet de comparer ce que le changement du poids produit, construction par construction.', 'source-reference-note'));
    content.append(node('p', 'Cette étude mesure l’effet du poids de recouvrement sur un pool fixe. Le recouvrement désigne les numéros communs entre deux grilles. Pour chaque paire de grilles, la pénalité souple vaut le poids multiplié par ce nombre au carré. Avec trois numéros communs, elle vaut neuf fois le poids, alors que ces grilles partagent trois paires de numéros. La récompense des nouvelles paires couvertes et cette pénalité sont deux composantes distinctes. Le poids nul conserve la construction grille après grille et ses autres objectifs. Les références aléatoires, lorsqu’elles sont qualifiées dans cette exécution, sont présentées séparément ci-dessous.', 'source-reference-note'));
    content.append(node('p', 'La sélection compare la couverture des paires et des triplets, la dispersion des occurrences et le maximum de numéros communs. La somme des intersections au carré est mesurée séparément. Réduire cette somme ne garantit donc pas une amélioration sur chacun des quatre critères de sélection.', 'source-reference-note'));
    content.append(conceptLink('Comprendre le recouvrement →', 'recouvrement'), document.createTextNode(' · '), conceptLink('Comprendre la pénalité →', 'penalite-recouvrement'), document.createTextNode(' · '), conceptLink('Comprendre le poids →', 'poids'), document.createTextNode(' · '), conceptLink('Comprendre les essais correspondants →', 'graines-appariees'), document.createTextNode(' · '), conceptLink('Comprendre le score souple →', 'score'), document.createTextNode(' · '), conceptLink('Comprendre l’étude d’un paramètre →', 'etude-parametre'));
    if (study.fixed_parameters) protocol.append(jsonDetails('Paramètres fixes de l’étude', study.fixed_parameters));
    if (study.starting_points) protocol.append(jsonDetails('Points de départ et références conservées', study.starting_points));
    if (study.bounds) protocol.append(jsonDetails('Bornes et arrêts déclarés de l’étude', study.bounds));
    if (dataset.study_run) protocol.append(jsonDetails('Exécution complète et provenance de l’étude', dataset.study_run));
    const factors = Array.isArray(analysis.by_factor) ? analysis.by_factor : [];
    const differences = Array.isArray(analysis.paired_differences) ? analysis.paired_differences : [];
    const summary = block('Les résultats des constructions', 'Plusieurs constructions · ordre des réglages déclaré', 'Moyenne, minimum et maximum décrivent les constructions obtenues pour chaque poids. Ces bornes entre constructions ne sont pas des intervalles de confiance. Les résultats des tirages simulés sont présentés séparément ; ils ne classent pas les constructions et ne servent pas à les sélectionner.');
    if (factors.length) summary.append(table('Résumé de structure par poids sur les constructions du plan', ['Poids', 'Constructions', 'Mesure', 'Moyenne', 'Minimum', 'Maximum'], summaryRows(factors, false), [0, 1, 3, 4, 5]));
    else summary.append(node('p', 'Le résumé des répétitions n’est pas publié dans cette source.', 'table-note'));
    const mc = analysis.monte_carlo_descriptive;
    if (mc?.status === 'complete' && Array.isArray(mc.by_factor)) {
      const detail = node('details', null, 'configuration-detail');
      detail.append(node('summary', 'Résumé Monte-Carlo du lot de comparaison, par poids'));
      detail.append(table('Comparaison descriptive · ' + integer(mc.draws) + ' tirages communs', ['Poids', 'Répétitions', 'Métrique', 'Moyenne', 'Minimum', 'Maximum'], summaryRows(mc.by_factor, false), [0, 1, 3, 4, 5]));
      detail.append(node('p', 'Ces différences descriptives n’établissent pas une différence statistiquement significative : les intervalles marginaux de Wilson ne mesurent pas la covariance des événements entre portefeuilles.', 'table-note'));
      summary.append(detail);
    }
    if (differences.length) {
      const details = node('details', null, 'configuration-detail study-paired-differences');
      details.append(node('summary', 'Comparer chaque poids au poids nul, construction par construction'));
      details.append(table('Différence poids B − poids A, appariée sur les mêmes graines de génération', ['Poids B − A', 'Constructions appariées', 'Métrique', 'Différence moyenne', 'Minimum', 'Maximum'], summaryRows(differences, true), [1, 3, 4, 5]), node('p', 'Le signe décrit le poids B moins le poids A, selon la métrique. Le poids nul conserve la même méthode et n’est pas un contrôle RANDOM. L’appariement ne transforme pas ces résultats en prédiction.', 'table-note'));
      if (mc?.status === 'complete' && Array.isArray(mc.paired_differences)) details.append(table('Différences Monte-Carlo descriptives B − A · lot de comparaison', ['Poids B − A', 'Paires', 'Métrique', 'Différence moyenne', 'Minimum', 'Maximum'], summaryRows(mc.paired_differences, true), [1, 3, 4, 5]), node('p', 'Pour une probabilité Monte-Carlo, une différence affichée de 1 % signifie un point de pourcentage ; aucune significativité n’est déduite de ce tableau.', 'table-note'));
      summary.append(details);
    }
    if (Array.isArray(analysis.synthesis)) summary.append(listNotes(analysis.synthesis, 'study-synthesis'));
    if (Object.keys(analysis).length) summary.append(jsonDetails('Consulter l’analyse complète et ses définitions', analysis));
    if (Array.isArray(analysis.finalist_ids)) {
      const finalists = node('div', null, 'study-finalists');
      finalists.append(node('h4', 'Fiches retenues pour la confirmation indépendante'));
      const list = node('ul');
      analysis.finalist_ids.forEach((id) => {
        const item = node('li');
        const profile = dataset.profiles.find((entry) => entry.id === id);
        item.append(profile ? profileLink(profile) : node('span', id));
        list.append(item);
      });
      finalists.append(list, node('p', 'Les autres constructions restent consultables. Les références RANDOM sont hors sélection et peuvent posséder leur propre confirmation indépendante. Pour une construction étudiée, l’absence de confirmation signifie qu’elle n’est pas finaliste, sans invalider son évaluation de comparaison.', 'table-note'));
      summary.append(finalists);
    }
    content.append(summary);
  }

  function renderReferences() {
    $('reference-section').hidden = !isStudy() && !isEvolution();
    const content = $('reference-detail');
    content.replaceChildren();
    if (!isStudy() && !isEvolution()) return;
    const benchmark = dataset.reference_benchmark;
    if (!benchmark?.qualification) {
      content.append(node('p', 'Cette archive ne publie pas de références RANDOM qualifiées pour les mêmes pools et le domaine complet.' + (isStudy() ? ' Le poids nul conserve la méthode de construction étudiée ; il ne remplace pas une construction aléatoire.' : ''), 'source-reference-note'), conceptLink('Comprendre la référence aléatoire RANDOM →', 'reference-random'));
      return;
    }
    const main = mainProfiles();
    const controls = dataset.profiles.filter((profile) => referenceRole(profile));
    content.append(stats([
      ['Constructions étudiées', integer(main.length), 'Analyse principale conservée séparément'],
      ['RANDOM · mêmes pools', integer(controls.filter((profile) => referenceRole(profile) === 'same_pool').length), 'Mêmes ensembles autorisés, même coût'],
      ['RANDOM · domaine complet', integer(controls.filter((profile) => referenceRole(profile) === 'full_domain').length), '50 numéros et 12 étoiles'],
      ['Rôle dans la sélection', 'Références uniquement', 'Aucun contrôle ne devient parent, survivant ou finaliste']
    ]));
    content.append(node('p', 'RANDOM construit les grilles par une méthode aléatoire déclarée, sans les objectifs de score de la méthode étudiée. Une famille nommée RANDOM ne suffit pas à qualifier la comparaison : les contraintes, les identités des contrôles et les lots d’évaluation doivent être vérifiés.'), conceptLink('Comprendre RANDOM →', 'reference-random'), document.createTextNode(' · '), conceptLink('Comprendre les pools →', 'pool'));
    const statuses = {qualified:'Qualifié',missing:'Absent',refused:'Qualification refusée',not_requested:'Non demandé'};
    const qualificationRows = ['comparison', 'confirmation'].flatMap((phase) => ['same_pool', 'full_domain'].map((role) => {
      const cohort = benchmarkCohort(role, phase);
      return [phase === 'comparison' ? 'Comparaison' : 'Confirmation indépendante', referenceName(role), statuses[cohort?.status] || 'Non confirmé', integer(cohort?.reference_count ?? cohort?.control_ids?.length), integer(cohort?.expected_count), simpleValue(cohort?.reasons?.length ? cohort.reasons : 'Aucun motif de refus déclaré')];
    }));
    content.append(table('Qualification des deux rôles et des deux lots', ['Lot', 'Référence', 'État', 'Références', 'Attendues', 'Motifs'], qualificationRows, [3,4]));
    content.append(node('p', 'Les résumés ci-dessous utilisent uniquement le lot de comparaison. Les moyennes, étendues et écarts-types décrivent la variation entre constructions, pas l’incertitude d’une simulation. Les confirmations des références sont consultables dans leurs fiches et utilisent un lot indépendant.', 'table-note'), conceptLink('Comprendre les tirages simulés →', 'monte-carlo'));
    const scalarHeaders = ['Métrique', 'Constructions', 'Moyenne', 'Minimum', 'Maximum', 'Écart-type'];
    ['same_pool', 'full_domain'].forEach((role) => {
      const values = benchmark[role] || {};
      const group = node('section', null, 'reference-role reference-' + role);
      group.append(node('h3', referenceName(role)), node('p', role === 'same_pool' ? 'La comparaison conserve les ensembles de numéros et d’étoiles autorisés ainsi que le coût. Elle décrit les différences entre la méthode étudiée et les constructions aléatoires à contraintes communes.' : 'Les références utilisent tout le domaine du jeu. Une comparaison avec les constructions étudiées inclut donc aussi l’effet du choix des pools ; elle n’isole pas seulement la méthode de construction.'));
      const cohort = benchmarkCohort(role);
      if (cohort?.status !== 'qualified') {
        group.append(node('p', 'Les différences ne sont pas présentées comme une comparaison qualifiée pour ce rôle.', 'source-reference-note'));
        content.append(group);
        return;
      }
      group.append(table('Références aléatoires · résumé du lot de comparaison', scalarHeaders, benchmarkSummaryRows(values.reference_summary), [1,2,3,4,5]));
      if (role === 'same_pool' && Array.isArray(values.paired_differences) && values.paired_differences.length) {
        const paired = node('details', null, 'configuration-detail reference-paired-differences');
        paired.append(node('summary', 'Constructions étudiées moins RANDOM, à graine de construction identique'));
        const rows = values.paired_differences.flatMap((entry) => benchmarkSummaryRows(entry.summary, true).map((row) => [decimal(entry.weight), ...row]));
        paired.append(table('Différences appariées étudiée − RANDOM sur les mêmes pools · distinctes des différences entre poids', ['Poids', ...scalarHeaders], rows, [0,2,3,4,5,6]), node('p', 'Chaque graine associe une construction étudiée et une référence RANDOM sur les mêmes pools. Les colonnes résument ces différences par graine. Le signe suit étudiée moins RANDOM ; pp signifie points de pourcentage pour les probabilités simulées. Aucune significativité ni supériorité de gain n’est déduite.', 'table-note'));
        paired.append(protocolDetails(jsonDetails('Détail des appariements et des valeurs par construction', values.paired_differences)));
        group.append(paired);
      }
      if (role === 'same_pool' && Array.isArray(values.main_groups)) {
        const descriptions = node('details', null, 'configuration-detail');
        descriptions.append(node('summary', 'Comparer les moyennes des groupes étudiés et des références'));
        const rows = values.main_groups.flatMap((entry) => Object.entries(entry.mean_differences || {}).filter(([, value]) => finite(value)).map(([id,value]) => [finite(entry.weight) ? 'Poids ' + decimal(entry.weight) : entry.generation_index === 0 ? 'Parents initiaux' : finite(entry.generation_index) ? 'Génération ' + integer(entry.generation_index) : 'Constructions étudiées', integer(entry.n), summaryMetricName(id), differenceValue(value,id)]));
        descriptions.append(table('Moyenne des constructions étudiées − moyenne RANDOM sur les mêmes pools', ['Groupe étudié', 'Constructions', 'Métrique', 'Différence des moyennes'], rows, [1,3]), node('p', 'Ces différences de moyennes sont descriptives. Elles ne constituent pas un appariement entre portefeuilles ni un test statistique. Les comparaisons entre poids conservent leur propre tableau.', 'table-note'));
        group.append(descriptions);
      }
      if (role === 'full_domain' && values.pool_effect?.summary) {
        const effect = node('details', null, 'configuration-detail reference-pool-effect');
        effect.append(node('summary', 'Voir l’effet descriptif du choix des pools entre références RANDOM'));
        const pairedRows = benchmarkSummaryRows(values.pool_effect.summary,true);
        if (values.pool_effect.paired === true && pairedRows.length) effect.append(table('RANDOM mêmes pools − RANDOM domaine complet · constructions correspondantes', scalarHeaders, pairedRows, [1,2,3,4,5]));
        else effect.append(table('Moyenne RANDOM mêmes pools − moyenne RANDOM domaine complet', ['Mesure','Différence des moyennes'], Object.entries(values.pool_effect.mean_differences || {}).filter(([,value])=>finite(value)).map(([id,value])=>[summaryMetricName(id),differenceValue(value,id)]), [1]), node('p', 'Ces groupes n’utilisent pas les mêmes graines de construction : les différences de moyennes sont descriptives, sans appariement par graine.', 'table-note'));
        effect.append(node('p', 'Le signe suit RANDOM sur les mêmes pools moins RANDOM sur le domaine complet. Cette comparaison conserve la méthode aléatoire et change les ensembles autorisés. Elle ne prouve pas un avantage économique.', 'table-note'));
        group.append(effect);
      }
      group.append(protocolDetails(jsonDetails('Valeurs complètes, vecteurs et définitions de ce rôle', values)));
      content.append(group);
    });
    if (benchmark.limitations?.length) content.append(protocolDetails(node('h3', 'Limites techniques déclarées pour les références'), listNotes(benchmark.limitations)));
    content.append(protocolDetails(jsonDetails('Qualification et analyse complète des références', benchmark), jsonDetails('Périmètre du plan contrôlé', dataset.controlled)));
  }

  function renderEvolution() {
    $('evolution-section').hidden = !isEvolution();
    const content = $('evolution-detail');
    content.replaceChildren();
    if (!isEvolution()) return;
    const evolution = dataset.evolution || {};
    const study = dataset.study || {};
    const comparison = study.comparison?.evaluation || study.comparison || {};
    const confirmation = study.confirmation?.evaluation || study.confirmation || dataset.confirmation_protocol || {};
    $('evolution-title').textContent = study.title || 'Une population de portefeuilles';
    $('evolution-question').textContent = simpleValue(study.question);
    content.append(stats([
      ['Générations terminées', integer(evolution.completed_generations), 'Les parents initiaux forment la génération 0'],
      ['Taille de population', integer(evolution.population_size), integer(countItems(evolution.final_survivor_ids)) + ' contenus dans la population finale'],
      ['Enfants acceptés', integer(countItems(evolution.accepted_children)), integer(countItems(evolution.proposal_count)) + ' propositions au total'],
      ['Propositions rejetées', integer(countItems(evolution.rejected_proposals)), 'Motifs conservés dans le journal']
    ]));
    const dl = node('dl', null, 'provenance evolution-provenance');
    addProvenance(dl, 'Exécution locale', dataset.run_id, true);
    addProvenance(dl, 'Étude / exécution', [study.id, study.run_id || dataset.source?.study_run_id], true);
    addProvenance(dl, 'Graine des opérateurs', evolution.generation_seed, true);
    addProvenance(dl, 'Comparaison commune', integer(comparison.draws) + ' tirages · graine ' + simpleValue(comparison.seed));
    addProvenance(dl, 'Confirmation indépendante', integer(confirmation.draws) + ' tirages · graine ' + simpleValue(confirmation.seed));
    addProvenance(dl, 'Règle de sélection', evolution.selection_rule, true);
    const protocol = protocolDetails(dl);
    content.append(protocol, node('p', 'Les portefeuilles de départ conservent leurs grilles. On modifie une construction complète en remplaçant ou échangeant des numéros, ou en remplaçant une grille. Un croisement combine des grilles de deux parents. Chaque enfant repasse les contraintes et la vérification de sa propre garantie ; aucune garantie parentale n’est héritée. Les évaluations utilisent de nouveaux tirages.', 'source-reference-note'));
    content.append(conceptLink('Comprendre les modifications (mutations) →', 'mutation'), document.createTextNode(' · '), conceptLink('Comprendre les croisements →', 'croisement'), document.createTextNode(' · '), conceptLink('Comprendre la sélection →', 'selection'));
    content.append(node('p', 'La sélection de population et des finalistes utilise les quatre critères géométriques déclarés. Le Monte-Carlo décrit les contenus conservés dans ce catalogue ; il n’intervient pas dans cette sélection et ne démontre aucun avantage de gain.', 'source-reference-note'));
    if (Array.isArray(evolution.initial_parent_ids) && Array.isArray(evolution.final_survivor_ids) && evolution.final_survivor_ids.length && evolution.final_survivor_ids.every((id) => evolution.initial_parent_ids.includes(id))) {
      content.append(node('p', 'Dans cette exécution, la population finale conserve uniquement des parents initiaux. Aucun enfant ne les a remplacés selon les quatre critères de sélection. Les enfants acceptés et leurs confirmations restent consultables.', 'source-reference-note evolution-outcome'));
    }
    const generations = Array.isArray(evolution.generations) ? evolution.generations : [];
    if (generations.length) content.append(table('Population et propositions par génération', ['Génération', 'Phase', 'Propositions', 'Enfants acceptés', 'Population retenue', 'Rejets'], generations.map((generation) => [
      integer(generation.generation_index), ({mutation:'Mutations', crossover:'Croisements'})[generation.phase] || simpleValue(generation.phase), integer(generation.proposal_count),
      integer(countItems(generation.accepted_ids)), integer(countItems(generation.survivor_ids)), rejectionSummary(generation.rejections)
    ]), [0, 2, 3, 4]));
    const groups = [
      ['Parents initiaux conservés', evolution.initial_parent_ids],
      ['Population finale retenue', evolution.final_survivor_ids],
      ['Fiches confirmées sur un nouveau lot de tirages', dataset.analysis?.finalist_ids]
    ];
    groups.forEach(([title, references]) => {
      if (!Array.isArray(references) || !references.length) return;
      const group = node('div', null, 'evolution-population');
      group.append(node('h3', title));
      const list = node('ul');
      references.forEach((reference) => {
        const item = node('li');
        const profile = profileByReference(reference);
        item.append(profile ? profileLink(profile) : node('code', reference));
        list.append(item);
      });
      group.append(list);
      content.append(group);
    });
    if (study.fixed_parameters) protocol.append(jsonDetails('Paramètres fixes et bornes des opérateurs', study.fixed_parameters));
    if (study.starting_points) protocol.append(jsonDetails('Provenance des portefeuilles parents', study.starting_points));
    protocol.append(jsonDetails('Journal complet des générations, propositions et rejets', evolution));
    if (dataset.analysis) protocol.append(jsonDetails('Sélection géométrique et analyse de cette exécution', dataset.analysis));
    if (dataset.study_run) protocol.append(jsonDetails('Définition et provenance complète de l’exécution', dataset.study_run));
  }

  function renderProfileConfiguration(profile) {
    const section = block('Le profil et son coût', 'Déclaration du profil', 'Le coût réel correspond aux grilles présentes. Le budget maximal est une contrainte de génération ; il est affiché séparément.');
    section.append(stats([
      ['Grilles', integer(profile.grid_count), '5 numéros et 2 étoiles par grille'],
      ['Coût réel', amount(actualBudget(profile)), 'Prix déclaré du portefeuille'],
      ['Budget maximal', amount(maximumBudget(profile)), 'Contrainte du profil'],
      ['Prix par grille', amount(profile.unit_price_eur), 'Jeu et règles déclarés']
    ]));
    const dl = node('dl', null, 'provenance profile-configuration');
    addProvenance(dl, 'État', stateLabel(profile.state));
    addProvenance(dl, 'Jeu', 'EuroMillions');
    addProvenance(dl, 'Pool', poolLabel(profile));
    addProvenance(dl, 'Famille', familyTitle(profile));
    const benchmarkRole = referenceRole(profile);
    if (benchmarkRole) {
      addProvenance(dl, 'Rôle de référence', referenceName(benchmarkRole));
      addProvenance(dl, 'Méthode', 'Construction aléatoire (random)');
      addProvenance(dl, 'Sélection', 'Exclu des parents, de la population et des finalistes');
    }
    if (profile.study_factor) addProvenance(dl, 'Poids de recouvrement', decimal(profile.study_factor.weight));
    if (isEvolution() && !benchmarkRole) {
      addProvenance(dl, 'Génération', profile.generation?.generation_index);
      addProvenance(dl, 'Opérateur', operatorName(profile.lineage?.operator || profile.generation?.operator));
      addProvenance(dl, 'Population finale', profile.is_survivor === true ? 'Retenu' : 'Hors de la population finale ; fiche conservée');
    }
    const config = configuration(profile);
    section.append(dl);
    if (profile.generation?.method === 'reference_import') section.append(node('p', 'Ces grilles proviennent d’un exemple du ZIP. Leur évaluation affichée ici appartient à l’exécution locale ; les résultats historiques restent dans l’autre source.', 'source-reference-note'));
    if (profile.state === 'search_exhausted') section.append(node('p', 'L’arrêt de la recherche ne prouve pas l’infaisabilité.', 'certificate-warning'));
    if (config) section.append(protocolDetails(jsonDetails('Profil complet et paramètres déclarés', config)));
    section.append(conceptLink('Comprendre le portefeuille →', 'portefeuilles'), document.createTextNode(' · '), conceptLink('Comprendre les ensembles autorisés →', 'pool'));
    return section;
  }
  function renderGeometry(profile) {
    const geometry = profile.geometry || {};
    const section = block('La géométrie du portefeuille', 'Calcul exact sur les grilles', 'L’union compte les numéros distincts présents. Le recouvrement est le nombre de numéros communs à deux grilles ; les étoiles sont décrites séparément. Ces mesures décrivent la structure, sans rendre une grille plus probable.');
    section.append(stats([
      ['Grilles', integer(geometry.grids ?? profile.grid_count), 'Taille du portefeuille'],
      ['Union des numéros', integer(geometry.union), 'Numéros distincts utilisés'],
      ['Recouvrement moyen', decimal(geometry.overlap_mean), 'Sur les paires de grilles'],
      ['Recouvrement maximal', integer(geometry.overlap_max), 'Sur les paires de grilles']
    ]));
    const columns = node('div', null, 'detail-two');
    const overlap = node('div');
    const histogram = geometry.overlap_hist || [];
    const overlapRows = Array.from({ length: 6 }, (_, count) => [String(count), integer(histogram[count] ?? histogram[String(count)])]);
    overlap.append(table('Distribution des intersections entre paires de grilles', ['Numéros communs', 'Paires de grilles'], overlapRows, [1]), node('p', 'Une paire de grilles est comptée une seule fois. Pour une seule grille, le recouvrement moyen et maximal sont indéfinis (—).', 'table-note'));
    const coverage = node('div');
    const coverageRows = [2, 3].map((size) => {
      const entry = geometry.coverage?.[String(size)] || {};
      return [size === 2 ? 'Paires' : 'Triplets', integer(entry.covered), integer(entry.possible), integer(entry.collisions)];
    });
    coverage.append(table('Couverture des sous-ensembles de numéros', ['Sous-ensemble', 'Couverts', 'Possibles', 'Collisions'], coverageRows, [1, 2, 3]), node('p', 'Une paire de numéros contient deux numéros ; un triplet en contient trois. Un sous-ensemble couvert apparaît dans au moins une grille. Les collisions comptent les paires de grilles qui partagent ce sous-ensemble ; s’il apparaît dans trois grilles, il produit trois collisions.', 'table-note'));
    const second = geometry.second || {};
    coverage.append(node('p', 'Étoiles : ' + integer(second.union) + ' valeurs distinctes · ' + integer(second.distinct_combinations) + ' combinaisons distinctes. Écart-type des occurrences de numéros : ' + decimal(geometry.occurrence_sd) + '.', 'table-note'));
    columns.append(overlap, coverage);
    section.append(columns);
    const exact = profile.exact || {};
    const jackpot = node('div', null, 'probability-card jackpot-card');
    jackpot.append(node('h4', 'Probabilité exacte du jackpot · 5 numéros + 2 étoiles'), node('p', percent(exact.jackpot_probability), 'value'), node('p', probabilityDetail(exact.jackpot_probability)), node('p', 'Calcul dans les règles déclarées, sur les grilles distinctes du portefeuille. Le budget et la géométrie ne rendent aucune combinaison individuelle plus probable.'));
    section.append(jackpot);
    const entries = registryEntries().filter((entry) => profile.metric_values && Object.prototype.hasOwnProperty.call(profile.metric_values, entry.id));
    if (entries.length) {
      const details = node('details', null, 'configuration-detail');
      details.append(node('summary', 'Toutes les métriques du registre pour ce portefeuille'));
      const rows = entries.map((entry) => [entry.name || entry.id, simpleValue(entry.version), formatMetric(profile, { metric_id: entry.id }), entry.evidence_method === 'exact' ? 'Calcul exact' : entry.evidence_method === 'monte_carlo' ? 'Estimation Monte-Carlo' : simpleValue(entry.evidence_method)]);
      details.append(table('Valeurs liées à ce portefeuille · les IC95 Monte-Carlo sont détaillés dans la section d’évaluation', ['Métrique', 'Version', 'Valeur', 'Méthode'], rows, [2]));
      section.append(details);
    }
    section.append(conceptLink('Comprendre une paire de numéros →', 'paire'), document.createTextNode(' · '), conceptLink('Comprendre une paire de grilles →', 'paire-grilles'), document.createTextNode(' · '), conceptLink('Comprendre les paires communes →', 'recouvrement-paires'), document.createTextNode(' · '), conceptLink('Comprendre la couverture →', 'couverture'));
    return section;
  }
  function renderCertificate(profile) {
    const certificate = profile.certificate;
    const verified = certificate?.method === 'exhaustive_enumeration' && certificate?.verification === 'independent_recalculation' &&
      typeof profile.content_sha256 === 'string' && certificate.content_sha256 === profile.content_sha256;
    const section = block('La garantie, sous condition', verified ? 'Énumération exhaustive liée aux grilles' : 'Certificat non vérifié', verified ? 'Pour chaque tirage conditionnel, au moins une grille atteint conjointement les minima de numéros et d’étoiles indiqués, sauf si la ligne affiche −1. Cette grille peut changer selon le tirage. Les meilleurs numéros d’une grille et les meilleures étoiles d’une autre ne s’additionnent pas.' : 'Un certificat doit vérifier conjointement les numéros et les étoiles sur une même grille, pour tous les cas de la condition annoncée.');
    const requested = certificate?.required ?? certificate?.requested;
    if (requested) {
      const description = finite(requested.required_numbers) && finite(requested.required_stars)
        ? 'au moins ' + integer(requested.required_numbers) + ' numéros et ' + integer(requested.required_stars) + ' étoiles sur une même grille'
        : simpleValue(requested);
      section.append(node('p', 'Garantie demandée : ' + description + '.', 'condition-stats'));
      if (certificate.fulfilled === true) section.append(node('p', 'La demande est satisfaite par le certificat lié à ces grilles.', 'condition-stats'));
      else if (certificate.fulfilled === false) section.append(node('p', 'Le certificat ne satisfait pas la garantie demandée. Cela ne prouve pas l’infaisabilité d’autres portefeuilles.', 'certificate-warning'));
    }
    if (!verified) {
      section.append(node('p', 'Aucun certificat conditionnel vérifié et lié à ces grilles n’est présenté pour ce profil.', 'certificate-warning'));
      if (certificate?.method) section.append(protocolDetails(jsonDetails('Méthode de vérification déclarée', certificate)));
    } else {
      const condition = node('div', null, 'certificate-condition');
      condition.append(node('strong', 'Condition à satisfaire dans le tirage'), node('p', simpleValue(certificate.condition)));
      section.append(condition);
      if (certificate.hypotheses) {
        const hypothesis = certificate.hypotheses;
        const description = !Array.isArray(hypothesis) && finite(hypothesis.pool_good_numbers) && finite(hypothesis.pool_good_stars)
          ? 'Hypothèse : le pool contient ' + (hypothesis.condition_mode === 'exactly' ? 'exactement ' : '') + integer(hypothesis.pool_good_numbers) + ' des 5 numéros tirés et ' + integer(hypothesis.pool_good_stars) + ' des 2 étoiles tirées.'
          : null;
        section.append(description ? node('p', description, 'condition-stats') : listNotes(hypothesis, 'hypothesis-list'));
      }
      section.append(node('p', integer(certificate.cases) + ' cas énumérés · probabilité de la condition : ' + percent(certificate.condition_probability) + '.', 'condition-stats'));
      const minima = certificate.minimum_best_numbers_by_required_stars || {};
      const rows = [0, 1, 2].map((stars) => {
        const minimum = minima[String(stars)];
        let description;
        if (minimum === -1) description = 'Pour au moins un tirage conditionnel, aucune grille n’atteint ce seuil d’étoiles.';
        else if (finite(minimum)) description = 'Au moins ' + integer(minimum) + ' numéro' + (minimum > 1 ? 's' : '') + ' et ' + stars + ' étoile' + (stars > 1 ? 's' : '') + ' sur une même grille.';
        else description = 'Résultat non renseigné.';
        return ['Au moins ' + stars + ' étoile' + (stars > 1 ? 's' : ''), minimum === -1 ? 'Aucun garant (−1)' : integer(minimum), description];
      });
      const certTable = table('Minimum garanti de numéros avec le nombre d’étoiles requis', ['Étoiles requises', 'Minimum de numéros', 'Garantie conjointe'], rows);
      certTable.classList.add('certificate-table');
      section.append(certTable);
    }
    section.append(node('p', '−1 signifie que, pour au moins un tirage conditionnel, aucune grille n’atteint le seuil d’étoiles. 0 + 2 n’est pas un rang gagnant EuroMillions. Un certificat conditionnel ne garantit pas un gain à chaque tirage.', 'table-note'));
    if (profile.proof) section.append(protocolDetails(jsonDetails('Preuve et limites déclarées', profile.proof)));
    section.append(conceptLink('Comprendre une garantie conditionnelle →', 'garantie-conditionnelle'));
    return section;
  }
  function confidenceInterval(metric) {
    const interval = metric?.ci95_wilson;
    let lower, upper;
    if (Array.isArray(interval)) [lower, upper] = interval;
    else if (interval && typeof interval === 'object') {
      lower = interval.lower ?? interval.low;
      upper = interval.upper ?? interval.high;
    }
    return finite(lower) && finite(upper) ? '[' + percent(lower) + ' ; ' + percent(upper) + ']' : '—';
  }
  function renderSimulation(profile, role) {
    const simulation = profile.simulation || {};
    const evaluation = profile.evaluation || {};
    const local = localEvaluation(profile);
    const imported = evaluation.method === 'imported_monte_carlo';
    const introduction = local
      ? (role === 'confirmation' ? 'Cette confirmation utilise un nouveau lot de tirages, distinct du lot de comparaison, sur l’empreinte des mêmes grilles' + (referenceRole(profile) ? ' de référence. ' : ' finalistes. ') : role === 'comparison' ? 'Le lot commun de comparaison évalue les constructions et références de cette étude. ' : '') + 'Cette évaluation a été exécutée par le moteur local sur l’empreinte des grilles affichées. Les intervalles à 95 % de Wilson expriment l’incertitude d’échantillonnage ; ces estimations ne prédisent pas les numéros du prochain tirage.'
      : imported
        ? 'Ces estimations ont été fournies avec les grilles du prototype dans le ZIP. Leur cohérence arithmétique est contrôlée ; leur simulation source n’a pas été reproduite dans cet import.'
        : 'Le catalogue ne dispose pas d’une évaluation confirmée et liée à l’empreinte des grilles de ce profil.';
    const title = local ? role === 'comparison' ? 'Comparaison · Monte-Carlo local' : role === 'confirmation' ? 'Confirmation indépendante · Monte-Carlo local' : 'Résultats Monte-Carlo du moteur local' : imported ? 'Résultats Monte-Carlo historiques du ZIP' : 'Évaluation du portefeuille';
    const section = block(title, role === 'confirmation' ? referenceRole(profile) ? 'Confirmation de référence · hors sélection' : 'Confirmation indépendante' : role === 'comparison' ? 'Comparaison sur tirages communs' : evaluationLabel(profile), introduction);
    if (role) section.classList.add('evaluation-' + role);
    if (!local && !imported) return section;
    section.append(node('p', integer(simulation.draws ?? evaluation.draws) + ' tirages simulés.', 'simulation-protocol'));
    section.append(protocolDetails(node('p', (local ? 'Exécution : ' + simpleValue(evaluation.run_id || evaluation.id || dataset.run_id) : 'Source : ' + simpleValue(dataset.source?.archive_name)) + ' · graine : ' + simpleValue(simulation.seed ?? evaluation.seed) + '.', 'simulation-protocol'), jsonDetails('Évaluation complète et environnement', evaluation)));
    if (local) section.append(node('p', evaluation.common_draws === true ? (role === 'confirmation' ? 'Les portefeuilles inclus dans ce lot de confirmation utilisent les mêmes tirages Monte-Carlo.' : 'Les portefeuilles de cette comparaison utilisent les mêmes tirages Monte-Carlo.') + (simulation.independent_of_generation === true || evaluation.independent_of_generation === true ? ' Le lot de tirages est déclaré indépendant de la génération.' : '') : 'Le protocole de tirages communs n’est pas confirmé dans cette évaluation.', 'simulation-caveat'));
    else section.append(node('p', 'Source historique consultée séparément. Le pipeline local possède ses propres générations, évaluations et références RANDOM ; ses résultats ne sont pas mélangés avec ceux du ZIP.', 'source-reference-note'));
    const cards = node('div', null, 'probability-row');
    [['Au moins une grille gagnante', 'any_prize'], ['Au moins deux grilles gagnantes', 'multiple_prizes']].forEach(([title, key]) => {
      const metric = simulation.metrics?.[key] || {};
      const card = node('div', null, 'probability-card');
      card.append(node('h4', title), node('p', percent(metric.probability), 'value'), node('p', 'IC 95 % (Wilson) : ' + confidenceInterval(metric), 'ci'));
      cards.append(card);
    });
    section.append(cards);
    section.append(node('p', 'Moyenne de grilles gagnantes simulée : ' + decimal(simulation.mean_winning_grids) + ' · espérance théorique : ' + decimal(simulation.theoretical_mean_winning_grids) + '.', 'simulation-caveat'));
    section.append(node('p', 'Une grille gagnante atteint un rang de gain déclaré par les règles du jeu ; cela ne signifie pas que le montant gagné dépasse le coût du portefeuille. Les fronts Pareto du pipeline local utilisent uniquement des métriques géométriques exactes.', 'simulation-caveat'));
    section.append(conceptLink('Comprendre le Monte-Carlo →', 'monte-carlo'));
    return section;
  }
  function renderConfirmation(profile) {
    if (profile.confirmation?.evaluation && profile.confirmation?.simulation) {
      const confirmation = { ...profile, evaluation: profile.confirmation.evaluation, simulation: profile.confirmation.simulation };
      const comparisonSeed = profile.simulation?.seed ?? profile.evaluation?.seed;
      const confirmationSeed = confirmation.simulation.seed ?? confirmation.evaluation.seed;
      const distinctStreams = !profile.evaluation?.draw_stream_sha256 || !confirmation.evaluation.draw_stream_sha256 || profile.evaluation.draw_stream_sha256 !== confirmation.evaluation.draw_stream_sha256;
      if (!localEvaluation(confirmation) || confirmation.evaluation.independent_of_comparison !== true || !finite(confirmationSeed) || confirmationSeed === comparisonSeed || !distinctStreams) {
        return block('Confirmation indépendante', 'Protocole à confirmer', 'Une donnée de confirmation est présente, mais son lien aux grilles et son indépendance par rapport au lot de comparaison ne sont pas confirmés par les métadonnées.');
      }
      const section = renderSimulation(confirmation, 'confirmation');
      if (referenceRole(profile)) section.append(node('p', 'Cette référence est confirmée pour documenter la comparaison. Elle demeure exclue des parents, des survivants et des finalistes ; cette confirmation ne constitue pas une sélection par performance.', 'source-reference-note'));
      const dl = node('dl', null, 'provenance');
      addProvenance(dl, 'Empreinte liée à la confirmation', confirmation.evaluation.content_sha256, true);
      addProvenance(dl, 'Environnement de confirmation', confirmation.evaluation.environment);
      section.append(protocolDetails(dl));
      return section;
    }
    if (referenceRole(profile)) return block('Confirmation indépendante de référence', 'Confirmation non publiée', 'Cette fiche est une référence hors sélection. Aucune confirmation indépendante liée à ses grilles n’est publiée dans cette source.');
    const finalist = dataset.analysis?.finalist_ids?.includes(profile.id) || profile.is_finalist === true || profile.finalist === true;
    return block('Confirmation indépendante', finalist ? 'Confirmation non publiée' : 'Non finaliste', finalist ? 'Cette fiche est déclarée finaliste, mais aucune confirmation liée à ses grilles n’est publiée dans cette source.' : 'Cette fiche n’a pas été retenue pour la confirmation indépendante. Son évaluation de comparaison reste disponible ; l’absence de confirmation n’est pas un échec.');
  }
  function renderGrids(profile) {
    const details = node('details', null, 'grids-detail');
    details.open = true;
    details.append(node('summary', 'Consulter les ' + integer(profile.grid_count) + ' grilles · vue du prompteur'));
    const content = node('div', null, 'grids-content');
    content.append(node('p', 'Pool des numéros : ' + simpleValue(profile.pool_numbers), 'pool-line'), node('p', 'Pool des étoiles : ' + simpleValue(profile.pool_stars), 'pool-line'));
    if (!window.AleaQuantPortfolioViewer) throw new Error('Le viewer des grilles n’a pas été chargé.');
    content.append(window.AleaQuantPortfolioViewer.create(profile));
    const compact = node('details', null, 'compact-grid-list');
    compact.append(node('summary', 'Voir aussi la liste compacte de toutes les grilles'));
    const list = node('ol', null, 'grids-list');
    (profile.grids || []).forEach((grid, index) => {
      const item = node('li');
      const numbers = node('span', null, 'number-set');
      numbers.setAttribute('aria-label', 'Numéros');
      const stars = node('span', null, 'star-set');
      stars.setAttribute('aria-label', 'Étoiles');
      grid[0].forEach((value) => numbers.append(node('span', String(value).padStart(2, '0'), 'ball')));
      grid[1].forEach((value) => stars.append(node('span', String(value).padStart(2, '0'), 'ball')));
      item.append(node('span', String(index + 1).padStart(2, '0'), 'grid-index'), numbers, stars);
      list.append(item);
    });
    compact.append(list, node('p', 'Pastilles rondes : numéros. Pastilles citron carrées : étoiles.', 'table-note'));
    content.append(compact);
    details.append(content);
    return details;
  }
  function renderGeneration(profile) {
    const benchmarkRole = referenceRole(profile);
    const section = block(benchmarkRole ? 'Génération de la référence RANDOM' : 'Génération et filiation', benchmarkRole ? referenceName(benchmarkRole) : 'Historique de ce portefeuille', benchmarkRole ? 'Cette référence utilise la méthode random et une graine déclarée. Elle ne participe pas à la filiation des constructions étudiées et reste exclue des parents, des populations retenues et des finalistes.' : 'Les liens relient le profil, les grilles produites, l’exécution de génération et l’évaluation. Les graines servent à reproduire une méthode ; elles ne sont pas sélectionnées pour leurs gains Monte-Carlo.');
    const generation = profile.generation || {};
    const run = profile.generation_run || {};
    const lineage = profile.lineage || {};
    const dl = node('dl', null, 'provenance');
    const visible = node('dl', null, 'provenance generation-readable');
    const readableMethod = benchmarkRole ? 'Construction aléatoire (random)' : isEvolution() ? operatorName(lineage.operator || generation.operator) : generation.method === 'prototype_greedy' ? 'Construction grille après grille' : generation.method === 'reference_import' ? 'Grilles reprises du prototype ZIP' : generation.method === 'random' ? 'Construction aléatoire (random)' : 'Méthode de construction déclarée';
    addProvenance(visible, 'Méthode de construction', readableMethod);
    if (isEvolution() && !benchmarkRole) addProvenance(visible, 'Génération', generation.generation_index);
    addProvenance(dl, 'Méthode / opérateur', [generation.method, lineage.operator || lineage.operation]);
    if (isEvolution() && !benchmarkRole) addProvenance(dl, 'Génération / opération', [generation.generation_index, operatorName(lineage.operator || generation.operator)]);
    addProvenance(dl, 'Graine de génération', generation.seed ?? run.seed ?? lineage.seed, true);
    addProvenance(dl, 'Graine du pool', generation.pool_seed, true);
    if (run.id || run.run_id) addProvenance(dl, 'Exécution de génération', run.id || run.run_id, true);
    if (run.state || run.status) addProvenance(dl, 'État de la génération', run.state || run.status);
    const parents = Array.isArray(lineage.parent_ids) ? lineage.parent_ids : [];
    const parentCell = node('dd');
    if (!parents.length) parentCell.textContent = benchmarkRole ? 'Aucun parent · construction aléatoire indépendante.' : 'Aucun parent déclaré · génération initiale ou référence importée.';
    parents.forEach((reference, index) => {
      if (index) parentCell.append(document.createTextNode(' · '));
      const parent = profileByReference(reference);
      parentCell.append(parent ? profileLink(parent) : node('span', 'Parent non chargé dans cette source'));
    });
    visible.append(node('dt', 'Parents'), parentCell);
    const protocol = protocolDetails(dl);
    section.append(visible, protocol);
    if (isEvolution() && parents.length === 2) section.append(node('p', 'Ce croisement utilise deux contenus parents distincts. La fiche et le certificat affichés portent sur les grilles concrètes de l’enfant.', 'source-reference-note'));
    if (Object.keys(generation).length) protocol.append(jsonDetails('Méthode de génération et paramètres', generation));
    if (run && Object.keys(run).length) protocol.append(jsonDetails('Exécution de génération complète', run));
    if (lineage.parameters || Object.keys(lineage).length) protocol.append(jsonDetails('Paramètres et liens de filiation', lineage));
    const relatedIds = new Set([lineage.profile_node_id, lineage.portfolio_node_id, profile.evaluation?.id, profile.proof?.id, run.id].filter(Boolean));
    const edges = dataset.graph?.edges?.filter((edge) => relatedIds.has(edge.source) || relatedIds.has(edge.target)) || [];
    if (edges.length) protocol.append(jsonDetails('Liens du graphe de provenance', edges));
    const limitations = [...(Array.isArray(profile.limitations) ? profile.limitations : []), ...(Array.isArray(run.limitations) ? run.limitations : []), ...(Array.isArray(profile.proof?.limitations) ? profile.proof.limitations : [])];
    if (limitations.length) {
      protocol.append(node('h4', 'Limites techniques de ce profil', 'profile-limits-title'), listNotes([...new Set(limitations)]));
    }
    section.append(conceptLink(benchmarkRole ? 'Comprendre RANDOM →' : isEvolution() && parents.length === 2 ? 'Comprendre le croisement →' : isEvolution() && !profile.is_starting_parent ? 'Comprendre la mutation →' : 'Comprendre la construction →', benchmarkRole ? 'reference-random' : isEvolution() && parents.length === 2 ? 'croisement' : isEvolution() && !profile.is_starting_parent ? 'mutation' : 'construction'));
    return section;
  }
  function renderProfileProvenance(profile) {
    const details = node('details', null, 'provenance-detail');
    details.append(node('summary', 'Protocole et reproductibilité'));
    const dl = node('dl', null, 'provenance');
    addProvenance(dl, 'Identifiant', profile.id, true);
    addProvenance(dl, 'Famille source', profile.family, true);
    addProvenance(dl, 'État / portée', [profile.state, profile.state_scope]);
    addProvenance(dl, 'Évaluation', evaluationLabel(profile));
    addProvenance(dl, 'Graine de simulation', profile.simulation?.seed ?? profile.evaluation?.seed, true);
    addProvenance(dl, 'SHA-256 des grilles', profile.content_sha256, true);
    addProvenance(dl, 'SHA-256 de configuration', profile.config_sha256, true);
    addProvenance(dl, 'Évaluation liée aux grilles', profile.evaluation?.content_sha256, true);
    addProvenance(dl, 'Environnement d’évaluation', profile.evaluation?.environment === 'not_recorded_by_source' ? 'Non enregistré dans la source ZIP.' : profile.evaluation?.environment);
    addProvenance(dl, 'Version du moteur', profile.evaluation?.engine_version || profile.evaluation?.evaluator_version || dataset.engine_version);
    if (profile.certificate) {
      addProvenance(dl, 'Méthode du certificat', profile.certificate.method, true);
      addProvenance(dl, 'Vérification du certificat', profile.certificate.verification, true);
      addProvenance(dl, 'SHA-256 du certificat', profile.certificate.content_sha256, true);
    }
    details.append(dl);
    return details;
  }
  function selectProfile(id, moveFocus = false) {
    const profile = dataset.profiles.find((item) => item.id === id);
    if (!profile) return;
    selectedId = profile.id;
    $('profile-title').textContent = profileTitle(profile);
    $('profile-subtitle').textContent = familyTitle(profile) + ' · ' + integer(profile.grid_count) + ' grilles · coût réel ' + amount(actualBudget(profile)) + ' · budget maximal ' + amount(maximumBudget(profile));
    $('profile-meta').replaceChildren(node('span', 'Géométrie exacte', 'pill exact'), node('span', localEvaluation(profile) ? 'MC local' : profile.evaluation?.method === 'imported_monte_carlo' ? 'MC historique du ZIP' : 'Évaluation à confirmer', 'pill'), node('span', stateLabel(profile.state), 'pill'));
    const children = [renderProfileConfiguration(profile), renderGrids(profile), renderGeometry(profile), renderCertificate(profile), renderSimulation(profile, isStudy() || isEvolution() ? 'comparison' : undefined)];
    if (isStudy() || isEvolution()) children.push(renderConfirmation(profile));
    children.push(renderGeneration(profile), renderProfileProvenance(profile));
    $('profile-detail').replaceChildren(...children);
    $('profile-section').hidden = false;
    updateCardSelection();
    rememberView();
    if (moveFocus) {
      const title = $('profile-title');
      title.tabIndex = -1;
      title.focus({ preventScroll: true });
      $('profile-section').scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    }
  }

  function registryEntries() {
    if (Array.isArray(dataset.metric_registry)) return dataset.metric_registry;
    return Array.isArray(dataset.metric_registry?.definitions) ? dataset.metric_registry.definitions : [];
  }
  function metricDefinition(id) {
    return registryEntries().find((entry) => entry.id === id || entry.id + '@v' + String(entry.version).replace(/^v/, '') === id || entry.id + '@' + entry.version === id);
  }
  function metricValue(profile, id) {
    const value = profile.metric_values?.[id] ?? profile.metric_values?.[id.split('@')[0]];
    if (Array.isArray(value)) return value;
    if (value !== undefined) return typeof value === 'object' && value !== null ? value.value : value;
    const base = id.split('@')[0];
    if (base === 'portfolio.distinct_pairs') return profile.geometry?.coverage?.['2']?.covered;
    if (base === 'portfolio.distinct_triples') return profile.geometry?.coverage?.['3']?.covered;
    if (base === 'portfolio.number_frequency_sd') return profile.geometry?.occurrence_sd;
    if (base === 'portfolio.max_number_overlap') return profile.geometry?.overlap_max;
    return null;
  }
  function formatMetric(profile, criterion) {
    const value = metricValue(profile, criterion.metric_id);
    const definition = metricDefinition(criterion.metric_id);
    if (Array.isArray(value)) return value.map(decimal).join(' · ');
    if (definition?.unit === 'ratio' || definition?.unit === 'probability' || definition?.unit === 'proportion') return percent(value);
    if (/distinct_pairs|distinct_triples|distinct_star_pairs|max_number_overlap|overlap_square_sum/.test(criterion.metric_id)) return integer(value);
    return decimal(value);
  }
  function comparisonGroup(cohort, differentPools) {
    const members = (cohort.profile_ids || []).map((id) => dataset.profiles.find((profile) => profile.id === id)).filter(Boolean);
    if (!members.length) return null;
    const details = node('details', null, 'comparison-cohort');
    details.open = true;
    const poolCount = new Set(members.map(poolKey)).size;
    const title = amount(cohort.budget_eur) + ' · ' + integer(cohort.grid_count) + ' grilles' + (differentPools ? ' · ' + integer(poolCount) + ' pool' + (poolCount > 1 ? 's' : '') + ' représenté' + (poolCount > 1 ? 's' : '') : ' · ' + poolLabel(members[0]));
    details.append(node('summary', title));
    const body = node('div', null, 'comparison-cohort-content');
    body.append(node('p', isStudy() || isEvolution() ? benchmarkPresence(members) : cohort.random_reference_available === true ? 'Référence RANDOM déclarée dans cette cohorte.' : 'Référence RANDOM absente de cette cohorte.', 'comparison-random-status'));
    const criteria = Array.isArray(cohort.criteria) ? cohort.criteria : [];
    const headers = ['Profil', 'Rôle', 'Pool', 'Coût réel', ...criteria.map((criterion) => (criterion.label || summaryMetricName(criterion.metric_id)) + (criterion.direction === 'max' ? ' ↑' : ' ↓')), 'Compromis descriptif'];
    const rows = members.map((profile) => [
      profileLink(profile), referenceRole(profile) ? referenceName(referenceRole(profile)) + ' · hors sélection' : 'Construction étudiée', poolLabel(profile), amount(actualBudget(profile)),
      ...criteria.map((criterion) => formatMetric(profile, criterion)),
      Array.isArray(cohort.pareto_ids) ? cohort.pareto_ids.includes(profile.id) ? 'Sur le front' : 'Dominé selon ces critères' : 'Non renseigné'
    ]);
    const numeric = Array.from({ length: criteria.length + 1 }, (_, index) => index + 3);
    body.append(table('Critères géométriques exacts · ordre de la source · aucune métrique Monte-Carlo dans le front', headers, rows, numeric));
    if (criteria.length) body.append(node('p', '↑ À maximiser · ↓ À minimiser. Un profil est sur le front si aucun autre profil de cette cohorte n’est au moins aussi bon sur tous les critères et strictement meilleur sur au moins un.', 'table-note'));
    body.append(node('p', 'Le front décrit les compromis des portefeuilles présents selon ces critères. Il ne prouve pas une optimalité globale ni un avantage de gain.' + (dataset.controlled ? ' Il inclut les références RANDOM à titre descriptif, tandis que la sélection des parents, survivants et finalistes porte uniquement sur les constructions étudiées.' : ''), 'table-note'));
    body.append(conceptLink('Comprendre les compromis Pareto →', 'pareto'), protocolDetails(jsonDetails('Cohorte et critères déclarés', cohort)));
    details.append(body);
    return details;
  }
  function renderComparisons() {
    const content = $('comparison-content');
    content.replaceChildren();
    $('comparison-section').hidden = false;
    if (!isLocal() || (!samePoolCohorts().length && !differentPoolCohorts().length)) {
      content.append(node('p', 'Les exemples historiques du ZIP ne contiennent pas ces deux protocoles avec référence RANDOM. Aucun front Pareto ni comparaison contrôlée n’est ajouté à leurs résultats.', 'source-reference-note'));
      $('comparison-filter-note').textContent = '';
      return;
    }
    $('comparison-filter-note').textContent = 'Le filtre budget s’applique aux deux protocoles. Le filtre pool restreint le premier ; le second conserve tous les pools présents dans la cohorte.';
    [
      ['Même pool · mêmes règles · même coût', isStudy() ? 'Comparer les constructions de l’étude de l’effet du poids de recouvrement sur les mêmes ensembles de numéros et d’étoiles. Les références RANDOM qualifiées sont identifiées par rôle ; le poids nul conserve la méthode étudiée.' : isEvolution() ? 'Comparer les parents, les enfants et les références qualifiées sur les mêmes ensembles autorisés et au même coût. Le front descriptif reste distinct de la sélection de population.' : 'Comparer les familles sur un même ensemble de numéros et d’étoiles, avec une référence RANDOM utilisant ce pool.', samePoolCohorts(), false],
      ['Pools libres · mêmes règles · même coût', 'Comparer à coût égal sans imposer les mêmes ensembles autorisés. Avec RANDOM sur le domaine complet, les différences incluent aussi l’effet du choix des pools. Ce protocole ne mesure donc pas seulement la méthode de construction.', differentPoolCohorts(), true]
    ].forEach(([title, introduction, cohorts, differentPools]) => {
      const section = block(title, 'Fronts Pareto géométriques', introduction);
      const visible = cohorts.filter((cohort) =>
        (activeBudget === 'all' || String(cohort.budget_eur) === activeBudget) &&
        (differentPools || activePool === 'all' || String(cohort.pool_id) === activePool));
      visible.forEach((cohort) => {
        const group = comparisonGroup(cohort, differentPools);
        if (group) section.append(group);
      });
      if (!visible.length) section.append(node('p', 'Aucune cohorte pour ces filtres.', 'empty-profiles'));
      content.append(section);
    });
  }
  function renderRegistry() {
    const entries = registryEntries();
    $('registry-section').hidden = !entries.length;
    $('metric-registry').replaceChildren();
    if (!entries.length) return;
    const details = node('details', null, 'registry-detail');
    details.append(node('summary', 'Consulter les ' + integer(entries.length) + ' définitions versionnées de cette exécution'));
    const rows = entries.map((entry) => [
      entry.id, simpleValue(entry.version), simpleValue(entry.scope), simpleValue(entry.definition),
      simpleValue(entry.unit), entry.direction === 'max' ? 'Maximiser' : entry.direction === 'min' ? 'Minimiser' : simpleValue(entry.direction),
      simpleValue(entry.evidence_method), simpleValue(entry.evaluator_version)
    ]);
    details.append(table('Registre fourni par le dictionnaire partagé', ['Identifiant', 'Version', 'Portée', 'Définition', 'Unité', 'Sens', 'Preuve', 'Version évaluateur'], rows));
    $('metric-registry').append(details, node('p', 'Les métriques géométriques et leurs conventions viennent de ce registre. Les estimations Monte-Carlo ne sont pas utilisées pour sélectionner les graines ou calculer les fronts présentés.', 'table-note'));
  }
  function renderDataset() {
    const source = dataset.source || {};
    const metricSource = dataset.metric_source || {};
    $('dataset-summary').textContent = dataset.controlled
      ? mainProfiles().length + ' constructions étudiées et ' + dataset.controlled.control_record_ids.length + ' références RANDOM, séparées entre mêmes pools et domaine complet. La comparaison commune et la confirmation indépendante restent liées aux grilles ; les références sont hors sélection.'
      : isEvolution()
      ? dataset.profiles.length + ' fiches de parents et enfants conservées dans cette exécution d’évolution locale. La population finale, les rejets et les deux lots d’évaluation restent identifiés séparément.'
      : isStudy()
      ? dataset.profiles.length + ' fiches construites pour l’étude « ' + studyTitle(dataset.study?.title || dataset.study?.id) + ' ». Le lot de comparaison et le lot de confirmation des finalistes sont séparés ; aucune grille des anciennes sources n’est remplacée.'
      : isLocal()
      ? dataset.profiles.length + ' fiches issues d’une exécution locale. Une fiche conserve le contexte du profil et de sa génération ; plusieurs fiches peuvent décrire les mêmes grilles. Les exemples réévalués localement sont identifiés dans leurs fiches.'
      : dataset.profiles.length + ' fiches fournies dans ' + simpleValue(source.archive_name) + '. Ces résultats historiques restent une source séparée du pipeline local.';
    const dl = $('dataset-provenance');
    dl.replaceChildren();
    addProvenance(dl, 'Source active', SOURCES[activeSource].label);
    addProvenance(dl, isLocal() ? 'Date d’exécution déclarée' : 'Date de l’archive fournie', source.date);
    if (isLocal()) addProvenance(dl, 'Exécution locale', dataset.run_id || source.run_id, true);
    else addProvenance(dl, 'SHA-256 de l’archive', source.archive_sha256, true);
    addProvenance(dl, 'Schéma / moteur', [dataset.schema, dataset.engine_version], true);
    if (dataset.configuration_sha256) addProvenance(dl, 'SHA-256 de la configuration', dataset.configuration_sha256, true);
    addProvenance(dl, 'Dictionnaire référencé', metricSource.path, true);
    addProvenance(dl, 'SHA-256 du dictionnaire référencé', metricSource.sha256, true);
    addProvenance(dl, isLocal() ? 'Définitions du dictionnaire' : 'Définitions au moment de l’import ZIP', metricSource.definitions_count);
    addProvenance(dl, 'Évaluation', isLocal() ? 'Résultats des évaluations locales liés aux empreintes des grilles ; protocole et environnement dans chaque fiche.' : 'Résultats Monte-Carlo historiques fournis avec le ZIP ; cohérence arithmétique contrôlée, simulation non reproduite.');
    if (dataset.verification_environment || dataset.execution_environment || dataset.environment) addProvenance(dl, isLocal() ? 'Environnement de l’exécution locale' : 'Environnement du contrôle d’import', dataset.execution_environment || dataset.environment || dataset.verification_environment);
    const limitations = $('dataset-limitations');
    limitations.replaceChildren();
    if (Array.isArray(dataset.search_runs) && dataset.search_runs.length) {
      const searches = node('details', null, 'configuration-detail');
      searches.append(node('summary', 'Résultat des recherches par profil'));
      const rows = dataset.search_runs.map((run) => [run.profile_id, stateLabel(run.status), integer(run.accepted), integer(run.attempts), simpleValue(run.rejections), simpleValue(run.stopped_reason)]);
      searches.append(table('Journal de génération déclaré par le moteur', ['Profil', 'État', 'Candidats acceptés', 'Propositions', 'Rejets', 'Motif d’arrêt'], rows, [2, 3]), node('p', 'Une recherche épuisée ou une borne atteinte ne prouve pas l’infaisabilité. Les preuves sont affichées et liées au contenu de chaque portefeuille.', 'table-note'));
      limitations.append(searches);
    }
    if (dataset.engine_sources) limitations.append(jsonDetails('Empreintes des sources du moteur de cette exécution', dataset.engine_sources));
    if (dataset.limitations?.length) limitations.append(protocolDetails(node('h3', isLocal() ? 'Limites déclarées de cette exécution' : 'Limites de la source historique', 'dataset-limits-title'), listNotes(dataset.limitations)));
    $('dataset-download').href = sourceUrl(activeSource);
    $('dataset-download').textContent = isEvolution() ? 'Télécharger les résultats d’évolution JSON' : isStudy() ? 'Télécharger les résultats de l’étude JSON' : isLocal() ? 'Télécharger les résultats locaux JSON' : 'Télécharger les exemples ZIP JSON';
    $('dataset-section').hidden = false;
    renderRegistry();
  }
  function renderSource() {
    $('source-note').textContent = dataset.controlled
      ? (isEvolution() ? 'Évolution' : 'Étude de l’effet du poids de recouvrement') + ' avec références aléatoires : ' + mainProfiles().length + ' constructions étudiées, plus des RANDOM sur les mêmes pools et sur le domaine complet. Les rôles et leur qualification sont détaillés ci-dessous.'
      : isEvolution()
      ? 'Évolution locale active : parents initiaux, nouveaux enfants, populations retenues et rejets. La filiation et les évaluations de comparaison et de confirmation sont liées aux grilles concrètes.'
      : isStudy()
      ? 'Étude locale active : une question, des paramètres fixes, plusieurs poids et graines de génération. Comparaison sur tirages communs et confirmation indépendante des finalistes sont identifiées séparément.'
      : isLocal()
      ? 'Pipeline local actif : générations, évaluations et références RANDOM de cette exécution. Les grilles reprises du ZIP sont identifiées, avec leur nouvelle évaluation locale.'
      : 'Exemples historiques du ZIP : grilles et résultats fournis avec le prototype, sans mélange avec les résultats locaux.';
    $('source-status').textContent = SOURCES[activeSource].label + ' chargé · ' + dataset.profiles.length + ' fiches';
    $('source-status').className = 'source-status ' + (isLocal() ? 'source-local' : 'source-archive');
    $('study-filter').hidden = !isStudy() && !isEvolution();
    $('study-select-label').textContent = isEvolution() ? 'Exécution d’évolution à consulter' : 'Étude à consulter';
    const entry = isEvolution() ? evolutions.find((item) => item.id === activeEvolutionId) : studies.find((item) => item.id === activeStudyId);
    $('study-index-note').textContent = (isEvolution() ? 'Exécution d’évolution' : 'Étude') + (dataset.controlled ? ' avec références RANDOM ; les archives précédentes restent disponibles.' : ' archivée ; son protocole reste consultable ci-dessous.');
    $('selection-intro').textContent = dataset.controlled
      ? 'Les constructions étudiées, les RANDOM sur les mêmes pools et les RANDOM sur le domaine complet sont séparés. Un pool est l’ensemble de numéros et d’étoiles autorisés pour construire les grilles. Les références sont exclues de la sélection et possèdent une confirmation propre.'
      : isEvolution()
      ? 'Chaque fiche conserve sa génération, son opérateur et ses parents. Les contenus écartés de la population finale restent consultables ; seuls les finalistes possèdent une confirmation indépendante.'
      : isStudy()
      ? 'Chaque fiche associe un poids et une graine de génération, au même coût et sur le même pool. Une pénalité de poids nul n’est pas une référence RANDOM.'
      : isLocal()
      ? 'Les fiches sont regroupées à coût égal et par pool. La référence RANDOM et les critères de comparaison sont déclarés pour chaque cohorte.'
      : 'Les exemples sont regroupés à coût égal. Leur archive ne contient pas de référence RANDOM à budget égal ; aucune supériorité n’est établie.';
  }

  function hideDataset() {
    $('profile-cohorts').replaceChildren();
    ['study-section', 'evolution-section', 'reference-section', 'profile-section', 'comparison-section', 'registry-section', 'dataset-section'].forEach((id) => { $(id).hidden = true; });
    $('pool-filter').hidden = true;
    $('budget-filters').replaceChildren();
  }
  function validateDataset(value, key) {
    if (!value || value.schema !== SCHEMA || !Array.isArray(value.profiles)) throw new Error('Schéma de catalogue non reconnu.');
    if (key === 'local' && value.origin !== 'local_pipeline') throw new Error('La source locale ne porte pas son origine déclarée.');
    if (key === 'study' && (value.origin !== 'local_study' || !value.study || typeof value.study.id !== 'string')) throw new Error('La source étude ne porte pas sa déclaration.');
    if (key === 'evolution' && (value.origin !== 'local_evolution' || !value.evolution || typeof value.evolution !== 'object')) throw new Error('La source évolution ne porte pas sa déclaration.');
    if (key === 'archive' && ['local_pipeline', 'local_study', 'local_evolution'].includes(value.origin)) throw new Error('La source historique contient une exécution locale.');
    if (!value.profiles.every((profile) => profile && typeof profile.id === 'string' && Array.isArray(profile.grids))) throw new Error('Profil incomplet dans le catalogue.');
    if (new Set(value.profiles.map((profile) => profile.id)).size !== value.profiles.length) throw new Error('Identifiants de profils répétés.');
    return value;
  }
  function embeddedSource(key) {
    if (key === 'study' && window.PORTFOLIO_STUDY_DATASETS?.[activeStudyId]) return window.PORTFOLIO_STUDY_DATASETS[activeStudyId];
    if (key === 'evolution' && window.PORTFOLIO_EVOLUTION_DATASETS?.[activeEvolutionId]) return window.PORTFOLIO_EVOLUTION_DATASETS[activeEvolutionId];
    const sources = window.PORTFOLIO_DATASETS;
    if (sources?.[key]) {
      const entry = key === 'evolution' ? evolutions.find((run) => run.id === activeEvolutionId) : studies.find((study) => study.id === activeStudyId);
      if (!['study', 'evolution'].includes(key) || !entry || entry.run_id === sources[key].run_id) return sources[key];
    }
    const value = window.PORTFOLIO_DATA;
    if (value && (value.origin === 'local_study' ? 'study' : value.origin === 'local_evolution' ? 'evolution' : value.origin === 'local_pipeline' ? 'local' : 'archive') === key) return value;
    return undefined;
  }
  function showError(error, key) {
    const status = $('catalogue-status');
    status.className = 'catalogue-status catalogue-error';
    status.textContent = 'La source « ' + SOURCES[key].label + ' » n’a pas pu être chargée. Rechargez cette source ou choisissez une autre source dans le sélecteur.';
    const link = node('a', ' Ouvrir son fichier JSON');
    link.href = sourceUrl(key);
    status.append(link);
    $('source-status').textContent = SOURCES[key].label + ' indisponible';
    $('source-status').className = 'source-status source-error';
    $('source-note').textContent = 'Cette source est indisponible. Les sélecteurs permettent de consulter une autre étude ou une autre source séparément.';
    console.error('Catalogue AleaQuant :', error instanceof Error ? error.message : String(error));
  }
  async function loadSource(key) {
    if (!SOURCES[key]) return;
    if (dataset) rememberView();
    activeSource = key;
    dataset = undefined;
    selectedId = undefined;
    $('catalogue-source').value = key;
    $('study-filter').hidden = !['study', 'evolution'].includes(key);
    $('study-select-label').textContent = key === 'evolution' ? 'Exécution d’évolution à consulter' : 'Étude à consulter';
    renderStudySelector();
    const request = ++loadSequence;
    hideDataset();
    $('catalogue-status').className = 'catalogue-status';
    $('catalogue-status').textContent = 'Chargement de la source « ' + SOURCES[key].label + ' »…';
    $('source-status').textContent = 'Chargement de ' + SOURCES[key].label + '…';
    $('source-note').textContent = 'Chargement de la source « ' + SOURCES[key].label + ' ». Les résultats de l’autre source ne sont pas affichés pendant ce chargement.';
    try {
      let value = (key === 'archive' ? sourceCache.get(key) : undefined) || embeddedSource(key);
      if (!value) {
        const response = await fetch(sourceUrl(key), { credentials: 'same-origin', cache: key === 'archive' ? 'default' : 'no-store' });
        if (!response.ok) throw new Error('Réponse HTTP ' + response.status);
        value = await response.json();
      }
      validateDataset(value, key);
      if (request !== loadSequence) return;
      dataset = value;
      if (key === 'archive') sourceCache.set(key, dataset);
      if (key === 'study' && !studies.length) {
        studies = [{ id: dataset.study.id, title: dataset.study.title || dataset.study.id, url: SOURCES.study.url, run_id: dataset.run_id }];
        activeStudyId = studies[0].id;
        renderStudySelector();
      }
      if (key === 'evolution' && !evolutions.length) {
        evolutions = [{ id: dataset.study?.run_id || dataset.source?.study_run_id || dataset.run_id,
          title: dataset.study?.title || dataset.run_id, url: SOURCES.evolution.url, run_id: dataset.run_id }];
        activeEvolutionId = evolutions[0].id;
        renderStudySelector();
      }
      const remembered = viewMemory.get(viewKey()) || {};
      activeBudget = remembered.budget || 'all';
      activePool = remembered.pool || 'all';
      selectedId = remembered.selectedId;
      renderSource();
      renderFilters();
      renderDataset();
      renderStudy();
      renderEvolution();
      renderReferences();
      const profiles = renderCohorts();
      renderComparisons();
      if (profiles.length) selectProfile(profiles.find((profile) => profile.id === selectedId)?.id || profiles[0].id);
    } catch (error) {
      if (request === loadSequence) {
        dataset = undefined;
        hideDataset();
        showError(error, key);
      }
    }
  }

  $('catalogue-source').addEventListener('change', (event) => {
    explicitSourceChoice = true;
    loadSource(event.target.value);
  });
  $('study-select').addEventListener('change', (event) => {
    if (dataset) rememberView();
    if (activeSource === 'evolution') activeEvolutionId = event.target.value;
    else activeStudyId = event.target.value;
    dataset = undefined;
    loadSource(activeSource === 'evolution' ? 'evolution' : 'study');
  });
  $('budget-filters').addEventListener('click', (event) => {
    if (!dataset) return;
    const button = event.target.closest('button[data-budget]');
    if (!button) return;
    activeBudget = button.dataset.budget;
    $('budget-filters').querySelectorAll('button').forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    const profiles = renderCohorts();
    renderComparisons();
    if (!profiles.some((profile) => profile.id === selectedId)) {
      if (profiles.length) selectProfile(profiles[0].id);
      else $('profile-section').hidden = true;
    }
    rememberView();
  });
  $('pool-select').addEventListener('change', (event) => {
    if (!dataset) return;
    activePool = event.target.value;
    const profiles = renderCohorts();
    renderComparisons();
    if (!profiles.some((profile) => profile.id === selectedId)) {
      if (profiles.length) selectProfile(profiles[0].id);
      else $('profile-section').hidden = true;
    }
    rememberView();
  });
  function normalizeStudyIndex(value) {
    const entries = Array.isArray(value) ? value : value?.studies || value?.entries || [];
    if (!Array.isArray(entries)) return [];
    const seen = new Set();
    return entries.filter((entry) => {
      if (!entry || typeof entry.id !== 'string' || !entry.id || seen.has(entry.id) || typeof entry.url !== 'string') return false;
      if (!/^\/data\/[a-zA-Z0-9_./-]+\.json$/.test(entry.url) || entry.url.includes('..')) return false;
      seen.add(entry.id);
      return true;
    }).sort((a, b) => (Date.parse(b.created_at || '') || 0) - (Date.parse(a.created_at || '') || 0));
  }
  function renderStudySelector() {
    $('study-select').replaceChildren();
    const list = activeSource === 'evolution' ? evolutions : studies;
    const activeId = activeSource === 'evolution' ? activeEvolutionId : activeStudyId;
    const entries = list.length ? list : [{ id: 'current', title: activeSource === 'evolution' ? 'Évolution courante' : 'Étude courante' }];
    entries.forEach((entry) => {
      const date = Date.parse(entry.created_at || '');
      const label = finite(date) ? new Intl.DateTimeFormat('fr-FR', {dateStyle:'short',timeStyle:'short'}).format(date) : '';
      const option = node('option', studyTitle(entry.title || 'Exécution archivée') + (label ? ' · ' + label : ''));
      option.value = entry.id;
      $('study-select').append(option);
    });
    if (activeId) $('study-select').value = activeId;
  }
  async function initialize() {
    const embeddedStudy = window.PORTFOLIO_DATASETS?.study || (window.PORTFOLIO_DATA?.origin === 'local_study' ? window.PORTFOLIO_DATA : undefined);
    const embeddedEvolution = window.PORTFOLIO_DATASETS?.evolution || (window.PORTFOLIO_DATA?.origin === 'local_evolution' ? window.PORTFOLIO_DATA : undefined);
    if (window.PORTFOLIO_STUDIES) studies = normalizeStudyIndex(window.PORTFOLIO_STUDIES);
    else if (embeddedStudy) studies = [{ id: embeddedStudy.study?.id || 'embedded-study', title: embeddedStudy.study?.title || 'Étude locale', url: SOURCES.study.url, run_id: embeddedStudy.run_id }];
    else if (!window.PORTFOLIO_DATA && !window.PORTFOLIO_DATASETS) {
      try {
        const response = await fetch('/data/portfolio_studies.json', { credentials: 'same-origin', cache: 'no-store' });
        if (response.ok) studies = normalizeStudyIndex(await response.json());
      } catch (_) { /* Le pipeline initial reste consultable lorsque l’index n’est pas publié. */ }
    }
    if (window.PORTFOLIO_EVOLUTIONS) evolutions = normalizeStudyIndex(window.PORTFOLIO_EVOLUTIONS);
    else if (embeddedEvolution) evolutions = [{ id: embeddedEvolution.study?.run_id || embeddedEvolution.run_id, title: embeddedEvolution.study?.title || 'Évolution locale', url: SOURCES.evolution.url, run_id: embeddedEvolution.run_id }];
    else if (!window.PORTFOLIO_DATA && !window.PORTFOLIO_DATASETS) {
      try {
        const response = await fetch('/data/portfolio_evolutions.json', { credentials: 'same-origin', cache: 'no-store' });
        if (response.ok) evolutions = normalizeStudyIndex(await response.json());
      } catch (_) { /* Cet index optionnel ne bloque pas les sources précédentes. */ }
    }
    activeStudyId = studies[0]?.id;
    activeEvolutionId = evolutions[0]?.id;
    renderStudySelector();
    if (explicitSourceChoice) return;
    const initial = studies.length ? 'study' : window.PORTFOLIO_DATA && !window.PORTFOLIO_DATASETS ? (window.PORTFOLIO_DATA.origin === 'local_evolution' ? 'evolution' : window.PORTFOLIO_DATA.origin === 'local_pipeline' ? 'local' : 'archive') : 'local';
    await loadSource(initial);
  }
  initialize();
})();
