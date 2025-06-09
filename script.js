// script.js
let allQuestions = [];

const getEl = id => document.getElementById(id);
const toggleBtn = getEl('filter-toggle');
const filterContent = getEl('filter-content');

function setupFilterToggle() {
  toggleBtn.addEventListener('click', () => {
    const collapsed = filterContent.classList.toggle('collapsed');
    toggleBtn.textContent = collapsed ? '+' : '−';
    localStorage.setItem('filter-collapsed', collapsed);
  });

  if (localStorage.getItem('filter-collapsed') === 'true') {
    filterContent.classList.add('collapsed');
    toggleBtn.textContent = '+';
  }
}

function setupClearFilters() {
  getEl('clear-filters').addEventListener('click', () => {
    getEl('filter-search').value = '';
    ['filter-question', 'filter-quiz', 'filter-class', 'filter-user', 'filter-status']
      .forEach(id => Array.from(getEl(id).options).forEach(opt => opt.selected = true));
    getEl('filter-selected-only').checked = false;
    applyFilters();
  });

  document.querySelectorAll('.clear-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.filter;
      if (id === 'filter-selected-only') getEl(id).checked = false;
      else Array.from(getEl(id).options).forEach(opt => opt.selected = true);
      applyFilters();
    });
  });
}

function initFilters(data) {
  const setFilter = (id, values) => {
    const sel = getEl(id);
    sel.innerHTML = '';
    values.forEach(v => sel.append(new Option(v, v)));
    Array.from(sel.options).forEach(opt => opt.selected = true);
  };

  setFilter('filter-question', [...new Set(data.map(q => q.question_number))].sort((a, b) => a - b));
  setFilter('filter-class', [...new Set(data.map(q => q.class))]);
  setFilter('filter-user', [...new Set(data.map(q => `${q.first_name} ${q.last_name}`))]);
  Array.from(getEl('filter-status').options).forEach(opt => opt.selected = true);

  getEl('filter-class').addEventListener('change', () => updateQuizFilter(data));
  updateQuizFilter(data);
}

function updateQuizFilter(data) {
  const selectedClasses = Array.from(getEl('filter-class').selectedOptions).map(o => o.value);
  const quizzes = [...new Set(data.filter(q => selectedClasses.includes(q.class)).map(q => q.quiz_name))];
  const quizSelect = getEl('filter-quiz');
  quizSelect.innerHTML = '';
  quizzes.forEach(q => quizSelect.append(new Option(q, q)));
  Array.from(quizSelect.options).forEach(opt => opt.selected = true);
  applyFilters();
}

function applyFilters() {
  const getSelected = id => Array.from(getEl(id).selectedOptions).map(o => o.value);
  const query = getEl('filter-search').value.toLowerCase().trim();
  const questions = getSelected('filter-question').map(Number);
  const quizzes = getSelected('filter-quiz');
  const classes = getSelected('filter-class');
  const users = getSelected('filter-user');
  const statuses = getSelected('filter-status').map(s => s.toLowerCase());
  const selectedOnly = getEl('filter-selected-only').checked;

  const results = allQuestions.filter(q => {
    if (query && !([...q.question_body.filter(p => p.type === 'text').map(p => p.text), ...q.options].join(' ').toLowerCase().includes(query))) return false;
    if (!questions.includes(q.question_number)) return false;
    if (!quizzes.includes(q.quiz_name)) return false;
    if (!classes.includes(q.class)) return false;
    const fullName = `${q.first_name} ${q.last_name}`;
    if (!users.includes(fullName)) return false;
    if (!statuses.includes(q.status)) return false;
    return true;
  });

  updateURLParams({
    question: questions,
    quiz: quizzes,
    class: classes,
    user: users,
    status: statuses,
    search: query
  });

  renderQuestions(results, selectedOnly);
}

function renderQuestions(questions, selOnly) {
  const container = getEl('quiz-container');
  container.innerHTML = '';
  getEl('result-count').textContent = `Showing ${questions.length} of ${allQuestions.length} questions`;
  if (!questions.length) return container.textContent = 'No questions match the selected filters.';

  questions.forEach(q => {
    const d = document.createElement('div'); d.className = 'question';
    d.innerHTML = `<h2>Question ${q.question_number} – Quiz: "${q.quiz_name}" – Class: "${q.class}" – Attempt: "${q.attempt}" – ${q.first_name}, ${q.last_name}</h2>`;
    d.innerHTML += `<p><span class="status ${q.status}">${q.status.toUpperCase()}</span> — ${q.points_awarded}/${q.points_possible} pts</p>`;
    q.question_body.forEach(p => {
      if (p.type === 'text') d.innerHTML += `<p>${p.text}</p>`;
      else if (p.type === 'image') d.innerHTML += `<img src="/_OUTPUT/_images/${p.src}" alt="${p.alt || ''}">`;
    });
    const ul = document.createElement('ul'); ul.className = 'options';
    q.options.forEach(opt => {
      const isSel = q.selected_options.includes(opt);
      if (selOnly && !isSel) return;
      const li = document.createElement('li');
      li.className = isSel ? (q.status === 'correct' ? 'correct' : q.status === 'incorrect' ? 'incorrect' : 'partial') : '';
      li.textContent = opt + (isSel ? ' ← your answer' : '');
      ul.appendChild(li);
    });
    d.appendChild(ul);
    container.appendChild(d);
  });
}

getEl('toggle-theme').addEventListener('click', () => document.body.classList.toggle('dark'));

fetch('/_OUTPUT/extracted_questions_full.json')
  .then(r => r.json())
  .then(data => {
    allQuestions = data;
    initFilters(data);
    setupFilterToggle();
    setupClearFilters();
    [
      'filter-search', 'filter-question', 'filter-quiz', 'filter-class',
      'filter-user', 'filter-status', 'filter-selected-only'
    ].forEach(id => getEl(id).addEventListener('change', applyFilters));
    applyFilters();
  })
  .catch(e => getEl('quiz-container').textContent = '❌ Failed to load JSON: ' + e);

function updateURLParams(filters) {
  const params = new URLSearchParams();
  for (const [key, val] of Object.entries(filters)) {
    if (Array.isArray(val)) val.forEach(v => params.append(key, v));
    else if (val) params.set(key, val);
  }
  history.replaceState(null, '', '?' + params.toString());
}
