// Cliente del backend. No maneja el DOM ni el estado de la UI.

const STREAM_URL = "/chat/stream";

/**
 * Envía una pregunta y consume el stream SSE.
 *
 * Eventos esperados del backend (ver app/api/routes/chat.py):
 *   event: token  data: {"text": "..."}
 *   event: done   data: {}
 *   event: error  data: {"message": "..."}
 *
 * @param {string} question
 * @param {{history?: {role: "user" | "assistant", content: string}[], onToken: (text: string) => void, signal?: AbortSignal}} options
 *   `history` son los turnos previos completos, en orden.
 * @returns {Promise<void>} resuelve al recibir "done"; lanza Error en fallo.
 */
export async function streamChat(question, { history = [], onToken, signal } = {}) {
  const response = await fetch(STREAM_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ question, history }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`El servidor respondió con estado ${response.status}.`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Los eventos SSE se separan con una línea en blanco.
    let separatorIndex;
    while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);

      const finished = handleEvent(rawEvent, onToken);
      if (finished === "done") return;
    }
  }

  // El stream terminó sin evento "done": tratarlo como incompleto.
  throw new Error("La respuesta se interrumpió antes de completarse.");
}

/**
 * Interpreta un bloque SSE. Devuelve "done" si el stream terminó correctamente.
 */
function handleEvent(rawEvent, onToken) {
  let eventName = "message";
  const dataLines = [];

  for (const line of rawEvent.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }

  if (dataLines.length === 0) return null;

  const payload = JSON.parse(dataLines.join("\n"));

  switch (eventName) {
    case "token":
      onToken(payload.text);
      return null;
    case "done":
      return "done";
    case "error":
      throw new Error(payload.message || "Ocurrió un error al generar la respuesta.");
    default:
      return null;
  }
}
