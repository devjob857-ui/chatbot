# AGENTS.md — Medicalidad AI Chatbot

## 1. Contexto del proyecto

Medicalidad AI es un asistente conversacional empresarial diseñado para responder preguntas relacionadas con el funcionamiento, la información y los procesos del negocio de Medicalidad.

El sistema utilizará inteligencia artificial para interpretar preguntas en lenguaje natural, recuperar información documental y consultar datos reales de una base de datos MariaDB.

El objetivo principal es permitir que los usuarios realicen preguntas sobre el negocio sin necesidad de conocer SQL, la estructura de la base de datos o los detalles técnicos del sistema.

### Objetivos principales

- Responder preguntas relacionadas con el negocio de Medicalidad.
- Consultar información actualizada de MariaDB mediante consultas SQL generadas dinámicamente.
- Utilizar RAG para proporcionar contexto documental al modelo.
- Interpretar correctamente el significado de las tablas, columnas, relaciones y datos.
- Generar respuestas comprensibles para usuarios no técnicos.
- Proporcionar respuestas basadas en información verificable.
- Mantener una arquitectura modular, mantenible y extensible.
- Garantizar la seguridad y confidencialidad de la información empresarial.

## 2. Stack tecnológico

El proyecto utilizará las siguientes tecnologías:

| Tecnología | Responsabilidad |
|---|---|
| Python | Lenguaje principal |
| FastAPI | Framework backend y exposición de endpoints |
| LangChain | Orquestación de componentes LLM y RAG |
| RAG | Recuperación de conocimiento documental |
| Ollama | Ejecución de modelos locales y/o generación de embeddings |
| MariaDB | Base de datos empresarial |
| LLM API | Modelo de lenguaje principal mediante API Key |
| Vector Store | Almacenamiento y recuperación de embeddings |
| Pydantic | Validación de datos y configuración |
| Pytest | Pruebas automatizadas |
| Docker | Entorno de ejecución y despliegue |

No introducir dependencias adicionales sin justificar su necesidad.

Las versiones de las dependencias deben estar declaradas y controladas en los archivos de configuración del proyecto.

## 3. Arquitectura general

El sistema debe implementar una arquitectura modular por responsabilidades.

Flujo general:

1. El usuario envía una pregunta.
2. FastAPI recibe y valida la petición.
3. El sistema identifica la intención de la pregunta.
4. LangChain coordina el procesamiento.
5. RAG recupera los documentos relevantes.
6. El modelo interpreta la pregunta y el contexto.
7. Cuando se requiere información dinámica, se genera una consulta SQL.
8. La consulta pasa por un proceso de validación de seguridad.
9. Se ejecuta la consulta en MariaDB mediante una conexión de solo lectura.
10. El resultado se entrega al modelo para su interpretación.
11. El modelo construye una respuesta en lenguaje natural.
12. FastAPI devuelve la respuesta al cliente.

### Principio arquitectónico

RAG no reemplaza las consultas SQL y SQL no reemplaza RAG.

Cada mecanismo tiene una responsabilidad diferente:

- RAG proporciona conocimiento y contexto.
- SQL proporciona información estructurada y actualizada.
- El LLM interpreta, relaciona y comunica la información.

El sistema no debe consultar MariaDB para preguntas que puedan resolverse exclusivamente con documentación.

Tampoco debe inventar información documental cuando una pregunta requiere datos reales de la base de datos.

## 4. Estructura del proyecto

Organizar el código utilizando separación por responsabilidades.

Estructura inicial propuesta:

```text
medicalidad-ai/
│
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   ├── main.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   └── health.py
│   │   ├── schemas/
│   │   │   └── chat.py
│   │   └── dependencies.py
│   │
│   ├── services/
│   │   ├── chat_service.py
│   │   └── intent_service.py
│   │
│   ├── rag/
│   │   ├── ingestion.py
│   │   ├── document_loader.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── retriever.py
│   │   └── vector_store.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── schema_inspector.py
│