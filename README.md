# Medicalidad AI Chatbot

Asistente conversacional empresarial que responde preguntas sobre el funcionamiento, la información y los procesos del negocio de Medicalidad. Combina **RAG** (conocimiento documental) con **consultas SQL de solo lectura** sobre MariaDB (datos reales y actualizados), de modo que los usuarios no necesitan conocer SQL ni la estructura de la base de datos.

## Características

- Preguntas en lenguaje natural sobre el negocio.
- Recuperación de contexto documental mediante RAG.
- Generación dinámica de consultas SQL, validadas antes de ejecutarse.
- Ejecución con conexión de **solo lectura** a MariaDB.
- Respuestas comprensibles para usuarios no técnicos, basadas en información verificable.
- Arquitectura modular, mantenible y extensible.

## Stack tecnológico

| Tecnología | Responsabilidad |
|---|---|
| Python | Lenguaje principal |
| FastAPI | Backend y endpoints |
| LangChain | Orquestación de LLM y RAG |
| Ollama | Modelos locales y/o embeddings |
| MariaDB | Base de datos empresarial |
| LLM API | Modelo de lenguaje principal (API Key) |
| Vector Store | Almacenamiento y recuperación de embeddings |
| Pydantic | Validación de datos y configuración |
| Pytest | Pruebas automatizadas |
| Docker | Ejecución y despliegue |

## Arquitectura

Flujo de una petición:

1. El usuario envía una pregunta.
2. FastAPI la recibe y valida.
3. Se identifica la intención (documental, datos, o ambas).
4. LangChain coordina el procesamiento.
5. RAG recupera los documentos relevantes.
6. El modelo interpreta la pregunta y el contexto.
7. Si se requieren datos dinámicos, se genera una consulta SQL.
8. La consulta pasa por validación de seguridad.
9. Se ejecuta en MariaDB con conexión de solo lectura.
10. El resultado vuelve al modelo para su interpretación.
11. El modelo construye la respuesta en lenguaje natural.
12. FastAPI devuelve la respuesta al cliente.

**Principio clave:** RAG no reemplaza a SQL ni viceversa. RAG aporta conocimiento y contexto; SQL aporta datos estructurados y actualizados; el LLM interpreta y comunica. No se consulta la base de datos para preguntas resolubles solo con documentación, ni se inventa información documental cuando se necesitan datos reales.

## Estructura del proyecto

```text
.
├── AGENTS.md                 # Guía para agentes y contribuidores
├── README.md
├── .env.example              # Plantilla de variables de entorno
├── requirements.txt          # Dependencias con versiones fijadas
├── Dockerfile
├── docker-compose.yml
├── src/
│   ├── backend/              # API FastAPI, lógica RAG/SQL y pruebas
│   │   ├── app/
│   │   │   ├── main.py       # Punto de entrada FastAPI
│   │   │   ├── core/         # Configuración, logging, excepciones
│   │   │   ├── api/          # Rutas, esquemas y dependencias
│   │   │   ├── services/     # Lógica de negocio (chat, intención, SQL)
│   │   │   ├── rag/          # Ingesta, chunking, embeddings, retriever, vector store
│   │   │   ├── database/     # Conexión, inspección de esquema, ejecución
│   │   │   ├── llm/          # Cliente LLM y cadenas LangChain
│   │   │   ├── security/     # Validación de SQL
│   │   │   └── prompts/      # Prompts del sistema
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   └── integration/
│   │   └── scripts/          # Utilidades (p. ej. ingesta de documentos)
│   └── frontend/             # UI de chat (HTML/CSS/JS estático, sin build)
│       ├── index.html
│       ├── css/styles.css
│       └── js/               # app.js (interfaz), api.js (cliente SSE)
├── data/
│   ├── documents/            # Documentos fuente para RAG
│   └── vector_store/         # Persistencia del vector store (no versionada)
└── docs/
```

## Requisitos previos

- Python 3.11 o superior (por confirmar al fijar dependencias)
- Docker y Docker Compose
- Acceso a una instancia de MariaDB
- [Ollama](https://ollama.com/) instalado, con los modelos necesarios descargados
- API Key del proveedor LLM

## Configuración

1. Copia la plantilla de variables de entorno:

   ```bash
   cp .env.example .env
   ```

2. Ajusta los valores en `.env`. El archivo se lee siempre desde la raíz del proyecto, sin importar desde qué carpeta se ejecute la app.

   Variables disponibles (definidas en `src/backend/app/core/config.py`):

   | Variable | Descripción | Por defecto |
   |---|---|---|
   | `OLLAMA_BASE_URL` | URL del servidor Ollama | `http://localhost:11434` |
   | `LLM_MODEL` | Modelo que conversa con el usuario | `llama3.2:3b` |
   | `SQL_MODEL` | Modelo que escribe las consultas SQL | `qwen2.5-coder:14b` |
   | `DB_HOST`, `DB_PORT` | Servidor MariaDB/MySQL | `localhost`, `3306` |
   | `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Base y usuario **de solo lectura**. Si `DB_NAME` o `DB_USER` están vacíos, el chat no consulta datos | vacíos |
   | `SQL_MAX_ROWS` | Máximo de filas que recibe el modelo | `100` |
   | `SQL_TIMEOUT_SECONDS` | Tiempo máximo por consulta | `15` |
   | `CORS_ORIGINS` | Orígenes permitidos por CORS (JSON) | `[]` (sin CORS) |

   Variables previstas (aún no implementadas): `LLM_API_KEY`, `EMBEDDING_MODEL`, `VECTOR_STORE_PATH`.

### Base de datos (preguntas sobre datos)

El chat responde preguntas sobre los datos así:

1. `SQL_MODEL` decide si la pregunta necesita datos y escribe un `SELECT`, guiado por el diccionario de datos.
2. `app/security/sql_validator.py` valida la consulta: una sola sentencia de lectura, solo tablas del diccionario, sin funciones peligrosas, y con `LIMIT` obligatorio.
3. La consulta se ejecuta en una sesión de solo lectura y con tiempo límite. Si falla, el modelo recibe el error y lo intenta una vez más.
4. `LLM_MODEL` redacta la respuesta en lenguaje natural usando solo las filas obtenidas.

Para configurarla:

- Crea un usuario con permiso solo de lectura, por ejemplo `GRANT SELECT ON <base>.* TO 'medicalidad_ro'@'%';`, y pon sus datos en `.env`.
- Descarga el modelo SQL: `ollama pull qwen2.5-coder:14b`. En equipos sin GPU, `qwen2.5-coder:7b` también funciona; en ese caso ajusta `SQL_MODEL`.
- Revisa `data/documents/diccionario_datos.md`. Solo se pueden consultar las tablas que tienen una sección `## Tabla: <nombre>`. Completa las partes marcadas **POR COMPLETAR** y *(confirmar)*, porque la calidad de las respuestas depende de este archivo. Los cambios se aplican sin reiniciar la app.

El SQL generado queda en el log del servidor (nivel INFO). Las filas obtenidas nunca se escriben en el log.

> Nunca subas `.env` al repositorio ni uses credenciales con permisos de escritura.

### Modelo local (Ollama)

El chat responde con un modelo local servido por Ollama.

1. Instala [Ollama](https://ollama.com/download) y verifica que esté corriendo (en Windows y macOS se inicia como aplicación; en Linux, con `ollama serve`):

   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Descarga el modelo:

   ```bash
   ollama pull llama3.2:3b
   ```

3. Comprueba que aparece en la lista con `ollama list`.

Si Ollama corre en otra máquina o usas otro modelo, cambia `OLLAMA_BASE_URL` o `LLM_MODEL` en `.env`. Si Ollama no está disponible, el chat muestra un mensaje de error genérico.

## Instalación y ejecución

### Local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd src/backend
uvicorn app.main:app --reload
```

Las pruebas se ejecutan igualmente desde `src/backend`: `pytest`.

### Docker

```bash
docker compose up --build
```

### Ingesta de documentos

Coloca los documentos en `data/documents/` y ejecuta:

```bash
cd src/backend
python scripts/ingest_documents.py
```

## API

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/chat` | Envía una pregunta y recibe la respuesta completa |
| `POST` | `/chat/stream` | Igual, pero la respuesta llega en streaming (SSE) |
| `GET` | `/health` | Estado del servicio |

Documentación interactiva (Swagger) en `http://localhost:8000/docs` cuando el servidor está activo.

### Streaming (`/chat/stream`)

Respuesta `text/event-stream`. Cada evento tiene la forma `event: <nombre>` seguida de `data: <JSON>`:

| Evento | Datos | Descripción |
|---|---|---|
| `token` | `{"text": "..."}` | Fragmento de la respuesta |
| `done` | `{}` | Respuesta completa |
| `error` | `{"message": "..."}` | Fallo durante la generación |

Prueba rápida: `curl -N -X POST localhost:8000/chat/stream -H "Content-Type: application/json" -d '{"question":"hola"}'`

## Interfaz web

La UI de chat se sirve en `http://localhost:8000/` desde la carpeta `src/frontend/`, sin pasos de build. Muestra el historial de la sesión (se pierde al recargar) y las respuestas se muestran en streaming.

Estado actual: el servicio de chat (`app/services/chat_service.py`) responde con el modelo local de Ollama, en español, usando el historial de la conversación. Cuando la pregunta lo requiere, consulta la base de datos (ver "Base de datos"). Todavía no usa RAG.

Ejemplo (esquema tentativo):

```json
POST /chat
{ "question": "¿Cuántas citas hubo el mes pasado?" }
```

## Seguridad

- Conexión a MariaDB exclusivamente de **solo lectura**.
- Todo SQL generado por el modelo se valida antes de ejecutarse (solo `SELECT`, sin sentencias múltiples ni operaciones de escritura o DDL).
- Secretos únicamente por variables de entorno.
- No se exponen datos sensibles en logs ni en respuestas innecesarias.

## Pruebas

```bash
cd src/backend
pytest
```

Las pruebas usan modelos y una base de datos falsos: no necesitan Ollama ni MariaDB.

## Estado del proyecto

En fase inicial: el chat responde con el modelo local (Ollama), en streaming, y consulta la base de datos con SQL generado y validado. RAG sigue pendiente de implementación.

## Contribución

Consulta [AGENTS.md](AGENTS.md) para las convenciones del proyecto. No agregues dependencias sin justificarlas y mantén sus versiones fijadas en `requirements.txt`.
