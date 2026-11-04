// Interfaz del chat: historial en memoria, render seguro y estados de carga/error.
import { streamChat } from "./api.js";

const MAX_CHARS = 2000;
/** Mensajes previos que se envían al backend (10 turnos). Debe coincidir con el backend. */
const MAX_HISTORY_MESSAGES = 20;

const messagesEl = document.getElementById("messages");
const emptyEl = document.getElementById("empty-state");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("question");
const sendBtn = document.getElementById("send");

/**
 * Historial en memoria, solo con turnos completos (pregunta + respuesta sin error).
 * Se pierde al recargar (fuera de alcance de la v1).
 */
const history = [];
let busy = false;

/** Crea una burbuja. Siempre usa textContent: nunca innerHTML (evita XSS). */
function addMessage(role, text = "", extraClass = "") {
  emptyEl.hidden = true;
  const el = document.createElement("div");
  el.className = `message ${role} ${extraClass}`.trim();
  el.textContent = text;
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
  inputEl.disabled = value;
}

async function handleSubmit(event) {
  event.preventDefault();
  if (busy) return;

  const question = inputEl.value.trim();
  if (!question) return;
  if (question.length > MAX_CHARS) {
    addMessage("bot", `La pregunta supera el límite de ${MAX_CHARS} caracteres.`, "error");
    return;
  }

  addMessage("user", question);
  inputEl.value = "";
  resizeInput();

  const botEl = addMessage("bot", "", "typing");
  let answer = "";
  setBusy(true);

  try {
    await streamChat(question, {
      history: history.slice(-MAX_HISTORY_MESSAGES),
      onToken(text) {
        answer += text;
        botEl.textContent = answer;
        scrollToBottom();
      },
    });
    botEl.classList.remove("typing");
    if (answer) {
      history.push({ role: "user", content: question }, { role: "assistant", content: answer });
    } else {
      botEl.textContent = "(Sin respuesta)";
    }
  } catch (err) {
    botEl.classList.remove("typing");
    botEl.classList.add("error");
    botEl.textContent = err.message || "No se pudo obtener la respuesta. Inténtalo de nuevo.";
  } finally {
    setBusy(false);
    inputEl.focus();
  }
}

/** Enter envía; Shift+Enter inserta salto de línea. */
function handleKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    formEl.requestSubmit();
  }
}

function resizeInput() {
  inputEl.style.height = "auto";
  inputEl.style.height = `${inputEl.scrollHeight}px`;
}

formEl.addEventListener("submit", handleSubmit);
inputEl.addEventListener("keydown", handleKeydown);
inputEl.addEventListener("input", resizeInput);
