# 🧠 Digital Brain

> Transforma tu WhatsApp en un segundo cerebro. Captura sin fricción, organización con IA, repaso espaciado.

Un bot de WhatsApp que actúa como sistema de gestión de conocimiento personal. Desarrollado para el Kelea Challenge. Acepta texto, enlaces, PDFs, audios, vídeos e imágenes; los organiza con IA; y te los devuelve cuando los necesitas.

---

## Índice

- [Concepto](#concepto)
- [Arquitectura](#arquitectura)
- [Flujo principal](#flujo-principal)
- [Comandos](#comandos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Simulador local](#simulador-local)
- [Base de datos](#base-de-datos)
- [Módulos](#módulos)
- [Principios de diseño](#principios-de-diseño)

---

## Concepto

La mayoría de las apps de notas tienen el problema opuesto al que dicen resolver: añaden fricción al capturar. Digital Brain se basa en tres principios del reto Kelea:

**Captura primero, piensa después.** Manda lo que sea en el momento: un enlace, una foto de pizarra, un audio de 30 segundos. El bot lo guarda sin pedirte que lo clasifiques.

**La IA propone, tú decides.** Cuando quieras, ejecutas `/process`. La IA agrupa tus notas por tema, propone un resumen estructurado y espera tu confirmación. Nada se guarda sin que tú lo apruebes.

**El conocimiento se consolida con el repaso.** Un sistema de repetición espaciada te envía recordatorios proactivos y genera quizzes de tus temas guardados.

---

## Arquitectura

```
WhatsApp
    │
    ▼
WhatsAppComms          ← FastAPI + Twilio webhook, cola async (1.5s entre mensajes)
    │
    ▼
MessageRouter          ← Deduplicación por SID, enrutado mensaje/estado/comando
    ├── StateProcessor ← Máquina de estados: selección de grupo, validación, borrado
    └── CommandProcessor ← Ejecuta todos los /comandos
         │
         ├── InboxManager   ← Inbox persistente SQLite, multi-usuario, con metadatos
         ├── AIProcessor    ← Resolución lazy + detección de grupos + propuestas
         │    └── ContentExtractor ← PDF, audio, vídeo, web, YouTube, imagen (OCR)
         ├── Saver          ← Base de conocimiento SQLite, búsqueda, export Markdown
         ├── ReminderManager ← Recordatorios puntuales + repaso proactivo programado
         ├── Quizzer        ← Generación y evaluación de quizzes con IA
         └── StreakManager  ← Racha, puntuación y sistema de vidas
```

Todas las tablas comparten el mismo fichero `cerebro.db` con WAL mode activado para evitar bloqueos en escrituras concurrentes.

---

## Flujo principal

### Captura (tiempo real, sin fricción)

```
Usuario manda: texto / URL / PDF / audio / vídeo / imagen
                             │
              ┌──────────────┼──────────────────┐
              │              │                  │
          Texto           Multimedia         URL externa
          (guardar         (PDF/audio/         (guardar como
          directo)         vídeo → extraer     [WEB_PENDING]
                          y guardar)           o [YT_PENDING])

Bot responde: "📥 Guardado (3 pendientes)"
              📝 texto: 2
              🔗 enlace: 1
```

Las imágenes, webs y vídeos de YouTube **no se procesan en la captura**. Se guardan como marcadores lazy (`[IMAGE_PENDING]`, `[WEB_PENDING]`, `[YT_PENDING]`) y se resuelven cuando el usuario ejecuta `/process`.

### Procesado multi-tema

```
Usuario: /process
    │
    ▼
AIProcessor.detectar_grupos()
    ├── Resuelve pendientes: OCR imágenes, scraping webs, transcripción YT
    └── LLM detecta grupos temáticos

    Si 1 grupo → genera propuesta directamente
    Si varios  → muestra menú de selección

Bot: "🗂️ He encontrado 3 grupos:
      1. Python y async (5 notas)
      2. Recetas mediterráneas (3 notas)
      3. Historia romana (4 notas)
      
      Puedes combinar: 1, 2, 1 3, 1 2 3, todos"

Usuario: "1 3"  (o "2", o "todos", o "1,3", o "1 y 3")
    │
    ▼
AIProcessor.generar_propuesta(notas_de_grupos_1_y_3)
    │
    ▼
Bot: "📝 Proposed Topic: Python async + Historia romana
      [resumen en Markdown]
      
      Save this? (Yes/No)"

Usuario: "Yes"
    │
    ▼
Saver.guardar_conocimiento_final()
InboxManager.vaciar()
StreakManager.registrar_topic()
```

---

## Comandos

| Comando | Descripción |
|---|---|
| `/process` | Analiza el inbox, detecta grupos temáticos y propone organización |
| `/rectify [texto]` | Añade contexto o correcciones al inbox antes de procesar |
| `/list` | Dashboard: estado del cerebro + desglose del inbox por tipo |
| `/remember [pregunta]` | Búsqueda inteligente en el conocimiento guardado |
| `/weekly` | Síntesis semanal generada por IA |
| `/quiz` | Genera un quiz de repaso activo con 5 preguntas |
| `/interval [horas]` | Configura el intervalo de repaso proactivo (ej. `/interval 24`) |
| `/remind [texto]` | Programa un recordatorio puntual |
| `/export` | Exporta todo el conocimiento a ficheros Markdown (compatible con Obsidian) |
| `/remove` | Elimina toda la base de conocimiento (pide confirmación) |
| `/help` | Lista de comandos |

---

## Instalación

**Requisitos:** Python 3.10+, cuenta Twilio, API key de Gemini, ffmpeg instalado en el sistema.

```bash
# 1. Clonar el repositorio
git clone <repo>
cd digital-brain

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 4. Arrancar el servidor
python main.py
```

**`requirements.txt`**
```
fastapi
uvicorn
twilio
python-dotenv
google-generativeai
pypdf
pydub
speechrecognition
youtube-transcript-api
beautifulsoup4
requests
Pillow
apscheduler
```

**Dependencias del sistema:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## Configuración

Crea un fichero `.env` en la raíz del proyecto:

```env
GEMINI_API_KEY=tu_api_key_de_google_ai_studio
TWILIO_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_TOKEN=tu_auth_token
TWILIO_PHONE=whatsapp:+14155238886
```

**Twilio Sandbox:** Para desarrollo, usa el [Sandbox de WhatsApp de Twilio](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn). El webhook debe apuntar a:

```
https://tu-dominio.com/whatsapp
```

Para exponer el servidor local puedes usar [ngrok](https://ngrok.com):
```bash
ngrok http 8000
# Copia la URL https://xxxx.ngrok.io/whatsapp al webhook de Twilio
```

---

## Simulador local

Para desarrollo y testing sin necesidad de WhatsApp ni Twilio:

```bash
python simulator.py
```

El simulador admite comandos especiales para simular adjuntos:

```
!pdf C:\ruta\archivo.pdf         ← simula envío de PDF
!audio C:\ruta\audio.ogg         ← simula nota de voz
!video C:\ruta\video.mp4         ← simula vídeo
!image C:\ruta\imagen.jpg        ← simula imagen
!debug                           ← muestra el inbox con metadatos
exit                             ← cierra el simulador
```

---

## Base de datos

`cerebro.db` (SQLite, WAL mode) contiene cuatro tablas:

**`inbox`** — Notas en espera de procesamiento
| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER | Clave primaria |
| `usuario` | TEXT | Número de WhatsApp |
| `texto` | TEXT | Contenido de la nota |
| `tipo` | TEXT | texto / enlace / pdf / audio / video / youtube / imagen |
| `fecha` | TIMESTAMP | Momento de captura |
| `estado` | TEXT | `pendiente` / `procesado` |

**`topics`** — Conocimiento estructurado y validado
| Campo | Tipo | Descripción |
|---|---|---|
| `id` | INTEGER | Clave primaria |
| `tema` | TEXT | Título del topic |
| `resumen` | TEXT | Resumen en Markdown |
| `fuentes` | TEXT | Tipos de contenido origen |
| `fecha` | TIMESTAMP | Momento de guardado |

**`usuarios`** — Estado del sistema de gamificación
| Campo | Descripción |
|---|---|
| `telefono` | Clave primaria |
| `racha` | Racha de quizzes acertados |
| `puntuacion` | Puntuación acumulada |
| `vidas` | Vidas restantes (3 por defecto) |
| `topics_nuevos` | Temas desde el último quiz |

**`config`** — Preferencias por usuario
| Campo | Descripción |
|---|---|
| `usuario` | Clave primaria |
| `intervalo_horas` | Frecuencia de repaso proactivo |

---

## Módulos

| Fichero | Responsabilidad |
|---|---|
| `main.py` | Arranque y composición de dependencias |
| `WhatsAppComms.py` | Servidor FastAPI, webhook Twilio, cola async |
| `message_router.py` | Entrada de todos los mensajes, deduplicación, enrutado |
| `command_processor.py` | Lógica de cada `/comando` |
| `state_processor.py` | Máquina de estados (selección de grupo, validación, borrado) |
| `state_manager.py` | Almacén en memoria del estado actual por usuario |
| `inbox_manager.py` | CRUD del inbox persistente |
| `ai_processor.py` | Resolución lazy, detección de grupos, generación de propuestas |
| `content_extractor.py` | Extracción de contenido: PDF, audio, vídeo, web, YouTube, OCR |
| `llm_manager.py` | Cliente Gemini con reintentos y backoff en cuota 429 |
| `saver.py` | Base de conocimiento: guardar, buscar, exportar, resumen semanal |
| `reminder_manager.py` | Recordatorios puntuales y repaso proactivo programado |
| `quizzer.py` | Generación y evaluación de quizzes de repaso activo |
| `streak_manager.py` | Racha, puntuación y sistema de vidas |
| `simulator.py` | Simulador de consola para desarrollo local |

---

## Principios de diseño

**Captura sin fricción.** Cualquier tipo de contenido se acepta y confirma en menos de 1 segundo. El procesamiento pesado (OCR, scraping, transcripción) ocurre solo cuando el usuario lo pide con `/process`.

**La IA propone, el humano decide.** Nada se guarda en el cerebro sin confirmación explícita del usuario. La IA puede equivocarse; el humano corrige con `/rectify`.

**Formatos abiertos.** El conocimiento se exporta a Markdown estándar compatible con Obsidian, MkDocs o cualquier editor de texto. No hay lock-in.

**Multi-usuario desde el origen.** Cada operación de inbox, estado y configuración está asociada al número de WhatsApp del remitente. Varias personas pueden usar la misma instancia de forma aislada.

**Resiliencia ante la API.** `LLMManager` implementa reintentos con backoff exponencial ante errores de cuota (HTTP 429). Los fallos de extracción de contenido no bloquean el flujo: se guarda la referencia original para no perder la entrada.
