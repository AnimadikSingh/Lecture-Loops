const state = { catalog: [], material: null, courseId: null, view: "notes", cardIndex: 0 };
const select = document.querySelector("#course-select");
const content = document.querySelector("#content");
const status = document.querySelector("#status");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
}

function showEmpty() {
  content.replaceChildren(document.querySelector("#empty-template").content.cloneNode(true));
  status.textContent = "Waiting for your first generated course";
}

async function selectCourse(courseId) {
  state.courseId = courseId;
  state.cardIndex = 0;
  const item = state.catalog.find(course => course.id === courseId);
  try {
    const response = await fetch(`materials/${encodeURIComponent(item.file)}`);
    if (!response.ok) throw new Error("Course material could not be loaded.");
    state.material = await response.json();
    status.textContent = `${item.flashcard_count} flashcards · ${item.quiz_count} quiz questions`;
    render();
  } catch (error) {
    status.textContent = error.message;
    showEmpty();
  }
}

function renderNotes() {
  const topics = state.material.topics.map(topic => `<article class="topic"><h3>${escapeHtml(topic.title)}</h3><p>${escapeHtml(topic.notes)}</p></article>`).join("");
  content.innerHTML = `<section class="summary"><h2>${escapeHtml(state.material.title)}</h2><p>${escapeHtml(state.material.summary)}</p></section><section class="topic-list">${topics}</section>`;
}

function renderCards() {
  const cards = state.material.flashcards || [];
  if (!cards.length) return showEmpty();
  const card = cards[state.cardIndex];
  content.innerHTML = `<div class="card-layout"><button class="round-button" id="previous-card" type="button" aria-label="Previous flashcard">‹</button><article class="flashcard" id="flashcard"><span class="card-label">Flashcard ${state.cardIndex + 1} of ${cards.length}</span><h2>${escapeHtml(card.front)}</h2><button class="button" id="reveal-card" type="button">Reveal answer</button><p class="answer"><strong>Answer</strong><br>${escapeHtml(card.back)}</p></article><button class="round-button" id="next-card" type="button" aria-label="Next flashcard">›</button></div>`;
  document.querySelector("#reveal-card").addEventListener("click", event => { document.querySelector("#flashcard").classList.add("is-revealed"); event.currentTarget.remove(); });
  document.querySelector("#previous-card").addEventListener("click", () => { state.cardIndex = (state.cardIndex - 1 + cards.length) % cards.length; renderCards(); });
  document.querySelector("#next-card").addEventListener("click", () => { state.cardIndex = (state.cardIndex + 1) % cards.length; renderCards(); });
}

function renderQuiz() {
  const questions = (state.material.quiz || []).map((item, index) => `<article class="question" id="question-${index}"><h3>Question ${index + 1}</h3><p>${escapeHtml(item.question)}</p><button class="button reveal-answer" type="button" data-target="question-${index}">Reveal answer</button><p class="quiz-answer answer"><strong>Answer</strong><br>${escapeHtml(item.answer)}</p></article>`).join("");
  content.innerHTML = `<section class="question-list">${questions}</section>`;
  content.querySelectorAll(".reveal-answer").forEach(button => button.addEventListener("click", () => { document.querySelector(`#${button.dataset.target}`).classList.add("is-revealed"); button.remove(); }));
}

function render() {
  if (!state.material) return showEmpty();
  if (state.view === "cards") return renderCards();
  if (state.view === "quiz") return renderQuiz();
  renderNotes();
}

document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => {
  document.querySelector(".tab.is-active").classList.remove("is-active");
  tab.classList.add("is-active");
  state.view = tab.dataset.view;
  render();
}));
select.addEventListener("change", () => selectCourse(select.value));

async function start() {
  try {
    const response = await fetch("materials/index.json");
    if (!response.ok) throw new Error("The course catalog is not available yet.");
    const catalog = await response.json();
    state.catalog = Array.isArray(catalog.courses) ? catalog.courses : [];
    if (!state.catalog.length) return showEmpty();
    select.innerHTML = state.catalog.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title)}</option>`).join("");
    select.disabled = false;
    await selectCourse(state.catalog[0].id);
  } catch (error) {
    status.textContent = error.message;
    showEmpty();
  }
}
start();
