# 🎓 JoSSAkha - JEE Rank & Institute Explorer

> **Democratising engineering college guidance for Tier 2 & 3 India — in your language, on any device.**

---

## 📌 Table of Contents

1. [Problem Statement](#-problem-statement)
2. [What This App Does](#-what-this-app-does)
3. [Architecture Overview](#-architecture-overview)
4. [Data Pipeline](#-data-pipeline)
5. [Application Stack](#-application-stack)
6. [Key Features](#-key-features)
7. [Tech Stack & Dependencies](#-tech-stack--dependencies)
8. [Project Structure](#-project-structure)
9. [How It Works — Step by Step](#-how-it-works--step-by-step)
10. [Multilingual Support](#-multilingual-support)
11. [RAG Pipeline Deep Dive](#-rag-pipeline-deep-dive)
12. [Edge Device & Low-Compute Design](#-edge-device--low-compute-design)
13. [Configuration Reference](#-configuration-reference)
14. [Example Queries](#-example-queries)
15. [Limitations & Future Work](#-limitations--future-work)

---

## 🚨 Problem Statement

Every year, over **1.2 million students** appear for JEE (Joint Entrance Examination) in India. After results, they face one of the most stressful decisions of their lives — choosing the right branch and college through **JoSSA (Joint Seat Allocation Authority)** counselling.

Students from **Tier 2 and Tier 3 cities** face a compounded disadvantage:

- No access to professional counsellors or paid mentorship services
- Language barriers — official JoSSA portals are English-only
- Limited internet bandwidth and low-end devices
- Cutoff data scattered across years and categories, impossible to compare manually
- No one to ask: *"With my rank of 4,500 in OBC-NCL, what can I realistically get?"*

This project is built to fill that gap — a **free, multilingual, AI-powered counselling assistant** that runs on low-compute infrastructure and speaks to students in their own language.

---

## ✅ What This App Does

The **JoSSA Rank & Institute Explorer** is a Retrieval-Augmented Generation (RAG) application that lets students:

- Ask natural-language questions about **JoSSA cutoff ranks** from 2021–2025
- Get precise, grounded answers — **no hallucinations**, only data-backed responses
- Query in **10 Indian languages** including Hindi, Tamil, Telugu, Kannada, and more
- Explore results via an **interactive Databricks dashboard** embedded directly in the app
- View the exact data rows that were used to generate the answer (full transparency)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE LAYER                           │
│                                                                         │
│   Student Query (any Indian language)                                   │
│          │                                                              │
│          ▼                                                              │
│   ┌─────────────────┐        ┌──────────────────────────────────┐      │
│   │  Streamlit App  │        │  Databricks Dashboard (embedded) │      │
│   │  (app.py)       │        │  Visual cutoff charts & trends   │      │
│   └────────┬────────┘        └──────────────────────────────────┘      │
└────────────│────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       TRANSLATION LAYER (SarvamAI)                      │
│                                                                         │
│   [Regional Language] ──► [English]   (pre-processing)                 │
│   [English Answer]    ──► [Regional]  (post-processing)                │
└─────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAG PIPELINE (LangChain)                        │
│                                                                         │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │  RETRIEVAL STAGE                                              │    │
│   │                                                               │    │
│   │  Query Parser ──► Rule-based SQL Builder ──► Databricks SQL  │    │
│   │                                                               │    │
│   │  Extracts: rank, category, year, institute, program keywords  │    │
│   │  Returns: Top 30 matching rows as LangChain Documents         │    │
│   └───────────────────────────────────────────────────────────────┘    │
│                                │                                        │
│                                ▼                                        │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │  GENERATION STAGE                                             │    │
│   │                                                               │    │
│   │  ChatDatabricks (GPT-5-4) + Context Prompt                   │    │
│   │  ► Answers strictly from retrieved context                    │    │
│   │  ► Returns "I do not have data" if not found                  │    │
│   └───────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER (Databricks Platform)                   │
│                                                                         │
│  ┌────────────────────┐    ┌──────────────────────────────────────┐    │
│  │  Unity Catalog     │    │  Databricks Volumes                  │    │
│  │  hackathon.        │    │  /Volumes/hackathon/hack_data/       │    │
│  │  hack_data.        │    │  ├── 2021.xlsx                       │    │
│  │  jossa_data_cleaned│    │  ├── 2022.xlsx                       │    │
│  │  (SQL Warehouse)   │    │  ├── 2023.xlsx                       │    │
│  └────────────────────┘    │  ├── 2024.xlsx                       │    │
│                            │  ├── 2025.xlsx                       │    │
│                            │  ├── merged_data.csv                 │    │
│                            │  ├── data_with_embeddings.csv        │    │
│                            │  └── chroma_db/ (vector store)       │    │
│                            └──────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Pipeline

The data pipeline is implemented in `EDA.ipynb` and runs entirely on the Databricks platform.

### Stage 1 — Ingestion & Cleaning

Raw JoSSA counselling data is provided as year-wise Excel files (2021–2025), stored in Databricks Volumes. Each file is loaded using `pandas`, and irrelevant columns (`Round`, `Quota`) are dropped. Null rows are removed to ensure data integrity before further processing.

```
2021.xlsx ──┐
2022.xlsx ──┤
2023.xlsx ──┼──► pd.read_excel() ──► dropna() ──► Cleaned DataFrames
2024.xlsx ──┤
2025.xlsx ──┘
```

### Stage 2 — Institute Name Normalisation

Institute names are standardised to include both the full name and the common abbreviation, enabling more natural language matching:

```
"Indian Institute of Technology Madras"
        ──► "Indian Institute of Technology Madras (IIT Madras)"
```

This normalisation applies to IITs, NITs, and IIITs, and is critical for the SQL-based retrieval in `app.py` to work correctly across different query phrasings.

### Stage 3 — RAG Context Generation

Each row is converted into a rich natural-language sentence that serves as the retrieval unit for the RAG system:

```
"In 2023, admission to the Computer Science and Engineering program at
 Indian Institute of Technology Bombay (IIT Bombay) under the OPEN
 category for Gender-Neutral candidates had an opening rank of 67
 and a closing rank of 119."
```

This format ensures the LLM receives fully self-contained, unambiguous context, rather than raw tabular data.

### Stage 4 — Vector Embedding (Offline)

RAG context sentences are encoded using a custom `sentence-transformers` pipeline:

| Component | Detail |
|---|---|
| Base model | `sentence-transformers/all-MiniLM-L6-v2` |
| Architecture | Transformer → Pooling → Dense (384-dim output) |
| Device | CUDA if available, else CPU |
| Batch size | 64 |
| Output | 384-dimensional float vectors |

Embeddings are stored back in the dataframe and serialised to `data_with_embeddings.csv`.

> **Why `all-MiniLM-L6-v2`?** At only ~22M parameters, it is extremely lightweight — critical for Databricks clusters running on low-compute nodes targeting edge accessibility.

### Stage 5 — ChromaDB Vector Store

Embeddings are pushed into a **ChromaDB** persistent vector store, with a Databricks-volume-compatible copy strategy (pure binary file copy to bypass metadata restrictions on Databricks Volumes):

```
Local compute (/tmp/chroma_db)
   └──► safe_copy_to_volume()
          └──► Databricks Volume (/Volumes/hackathon/hack_data/datasets/chroma_db)
```

A custom `CustomDatabricksEmbeddings` wrapper makes the model compatible with the LangChain `Embeddings` interface, enabling seamless integration with LangChain's `Chroma` vector store class.

### Stage 6 — Structured Table (Unity Catalog)

A cleaned, queryable SQL table `hackathon.hack_data.jossa_data_cleaned` is maintained in Databricks Unity Catalog. This serves as the primary retrieval backend for the live application, offering fast, parametrised SQL queries via the Databricks SQL warehouse.

---

## 🖥️ Application Stack

The live application (`app.py`) is a **Streamlit** web application with the following logical layers:

### Layer 1 — UI (Streamlit)
Provides a clean, accessible interface: a text input for the query, a language selector dropdown, an "Ask" button, an expandable data viewer, and an embedded Databricks dashboard for visual exploration.

### Layer 2 — Translation (SarvamAI `mayura:v1`)
Before the query touches any data, it is translated from the user's chosen language into English. The LLM answer is translated back to the user's language before display. This bidirectional translation is handled by the `sarvamai` SDK using the `mayura:v1` model in `code-mixed` mode, which handles mixed-script inputs gracefully.

### Layer 3 — Query Parsing & SQL Retrieval
The English query is parsed using a rule-based extractor (regex) that identifies:

| Entity | Example | SQL Condition |
|---|---|---|
| Rank | `4500` | `closing_rank BETWEEN 4000 AND 5000` |
| Category | `OBC-NCL`, `OPEN`, `SC` | `seat_category = 'OBC-NCL'` |
| Year | `2023` | `year = 2023` |
| Institute | `IIT Madras` | `institute_name LIKE '%Indian Institute of Technology Madras%'` |
| Program | `CSE`, `ECE` | `academic_program_name LIKE '%Computer%'` |

This retrieves up to **30 matching rows** as `LangChain Document` objects.

### Layer 4 — RAG Answer Generation (LangChain + ChatDatabricks)
A `create_stuff_documents_chain` chain passes all retrieved documents as context to the `ChatDatabricks` LLM endpoint (`databricks-gpt-5-4`). The system prompt explicitly instructs the model to:
- Answer only from provided context
- Say *"I do not have data for that specific request"* if the answer isn't present
- Never hallucinate or guess numbers

### Layer 5 — Dashboard Visualisation
If a rank is detected in the query, a Databricks dashboard is embedded via an `<iframe>` with the rank passed as a URL filter parameter, giving students an instant visual view of their competitive landscape.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🌐 10 Indian Languages | Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi, English |
| 📅 5 Years of Data | JoSSA cutoff data from 2021 to 2025 |
| 🛡️ Hallucination-Free | LLM is strictly grounded — answers only from retrieved SQL data |
| 📊 Visual Dashboard | Embedded Databricks dashboard filtered by the user's rank |
| 🔍 Transparent Retrieval | Data expander shows exact rows used to generate the answer |
| 📱 Low-Bandwidth Friendly | Lightweight model choices, minimal JS, Streamlit's mobile-friendly layout |
| ⚡ Fast SQL Retrieval | Direct parameterised queries — no slow vector similarity search at runtime |
| 🆓 Free for Students | No paywall, no registration, no ads |

---

## 🛠️ Tech Stack & Dependencies

### Databricks Platform Services

| Service | Role |
|---|---|
| **Databricks SQL Warehouse** (`65ce16d60ab74bcf`) | Serves live cutoff data queries |
| **Databricks Unity Catalog** | Hosts the cleaned JoSSA table (`hackathon.hack_data.jossa_data_cleaned`) |
| **Databricks Volumes** | Stores raw Excel files, embeddings, and ChromaDB |
| **Databricks Model Serving** | Hosts the LLM endpoint (`databricks-gpt-5-4`) |
| **Databricks Dashboards** | Embedded visual analytics for cutoff trends |

### Python Libraries

| Library | Version | Purpose |
|---|---|---|
| `streamlit` | latest | Web application framework |
| `langchain` | latest | RAG orchestration |
| `langchain-databricks` | latest | `ChatDatabricks` LLM wrapper |
| `langchain-chroma` | latest | Vector store integration |
| `databricks-sdk` | latest | Authentication & SQL connection |
| `databricks-sql-connector` | latest | SQL Warehouse queries |
| `sentence-transformers` | latest | `all-MiniLM-L6-v2` embeddings |
| `chromadb` | latest | Persistent vector store |
| `sarvamai` | latest | Multilingual translation |
| `pandas` | latest | Data manipulation |
| `torch` | latest | Tensor operations for embeddings |
| `openpyxl` | latest | Reading `.xlsx` raw data files |

---

## 📁 Project Structure

```
jossa-explorer/
│
├── app.py                      # Main Streamlit application
├── EDA.ipynb                   # Data pipeline & embedding notebook (Databricks)
├── README.md                   # This file
│
└── Databricks Volumes/
    └── /Volumes/hackathon/hack_data/
        ├── datasets/
        │   ├── 2021.xlsx           # Raw JoSSA data (Year 1)
        │   ├── 2022.xlsx           # Raw JoSSA data (Year 2)
        │   ├── 2023.xlsx           # Raw JoSSA data (Year 3)
        │   ├── 2024.xlsx           # Raw JoSSA data (Year 4)
        │   ├── 2025.xlsx           # Raw JoSSA data (Year 5)
        │   ├── merged_data.csv     # Filtered & merged (top 7 IITs)
        │   ├── data_with_embeddings.csv  # merged_data + 384-dim vectors
        │   └── chroma_db/          # Persisted ChromaDB vector store
        │
        └── Unity Catalog Table:
            └── hackathon.hack_data.jossa_data_cleaned
```

---

## 🔄 How It Works — Step by Step

```
Student types a question in Tamil:
"IIT மதராஸில் CSE க்கு 2023ல் closing rank என்ன?"

          │
          ▼

[1] LANGUAGE DETECTION
    Selected language: Tamil (ta-IN)

          │
          ▼

[2] TRANSLATION TO ENGLISH (SarvamAI mayura:v1)
    "What was the closing rank for CSE at IIT Madras in 2023?"

          │
          ▼

[3] ENTITY EXTRACTION (Regex Parser in app.py)
    ├── Institute detected: "IIT Madras" → LIKE '%Indian Institute of Technology Madras%'
    ├── Program detected: "CSE" → LIKE '%Computer%'
    └── Year detected: "2023" → year = 2023

          │
          ▼

[4] SQL QUERY EXECUTION (Databricks SQL Warehouse)
    SELECT institute_name, academic_program_name, degree_type,
           seat_category, opening_rank, closing_rank, year
    FROM hackathon.hack_data.jossa_data_cleaned
    WHERE LOWER(institute_name) LIKE LOWER('%indian institute of technology madras%')
      AND LOWER(academic_program_name) LIKE LOWER('%Computer%')
      AND year = 2023
    ORDER BY closing_rank ASC LIMIT 30;

    Returns: 6 rows across different seat categories

          │
          ▼

[5] DOCUMENT WRAPPING (LangChain Documents)
    Each row → Document(page_content="Institute: ..., Program: ...,
                          Category: ..., Opening: ..., Closing: ..., Year: ...")

          │
          ▼

[6] LLM GENERATION (ChatDatabricks — GPT-5-4)
    System Prompt: "Answer only from the provided context. Do not guess."
    Context: 6 retrieved documents
    Input: "What was the closing rank for CSE at IIT Madras in 2023?"

    Answer: "In 2023, the closing rank for Computer Science and Engineering
             at IIT Madras ranged from 119 (OPEN, Gender-Neutral) to 544
             (OBC-NCL, Gender-Neutral)."

          │
          ▼

[7] TRANSLATION BACK TO TAMIL (SarvamAI)
    "2023-ல், IIT மதராஸில் கணினி அறிவியல் பொறியியலுக்கான இறுதி தரவரிசை
     119 (OPEN, பாலின-நடுநிலை) முதல் 544 (OBC-NCL) வரை இருந்தது."

          │
          ▼

[8] DISPLAY
    ✅ Answer shown in Tamil
    🔍 Data expander shows 6 source rows
    📊 Dashboard embedded (if rank detected)
```

---

## 🌐 Multilingual Support

Translation is handled by **SarvamAI's `mayura:v1`** model, India's leading language model built specifically for Indian languages. The app supports bidirectional translation between English and:

| Language | Code | Script |
|---|---|---|
| English | `en-IN` | Latin |
| Hindi | `hi-IN` | Devanagari |
| Tamil | `ta-IN` | Tamil |
| Telugu | `te-IN` | Telugu |
| Kannada | `kn-IN` | Kannada |
| Malayalam | `ml-IN` | Malayalam |
| Marathi | `mr-IN` | Devanagari |
| Gujarati | `gu-IN` | Gujarati |
| Bengali | `bn-IN` | Bengali |
| Punjabi | `pa-IN` | Gurmukhi |

Translation uses `code-mixed` mode, which gracefully handles inputs that mix the regional script with English terms (e.g., "IIT Madras-ல் CSE"), reflecting how students in Tier 2/3 cities naturally type.

---

## 🔬 RAG Pipeline Deep Dive

The retrieval system uses a **hybrid SQL-first RAG** approach, deliberately avoiding vector similarity search at runtime for three reasons:

1. **Speed** — SQL queries on a serverless warehouse return in milliseconds; vector similarity search adds latency
2. **Precision** — Admission cutoffs require exact filtering (rank within ±500, exact category, exact year); semantic similarity can miss these hard constraints
3. **Low-compute** — No embedding model needs to run at query time, reducing cluster requirements

### Why Not Pure Vector Search?

A student asking *"What can I get with rank 5000 in OBC?"* needs results where `closing_rank ≥ 5000` — a hard numerical filter. A vector search would return semantically similar sentences but might miss the numerical boundary. The SQL retriever guarantees the filter is applied exactly.

### LLM System Prompt Design

```
"You are a highly accurate academic admissions assistant.
 Use the following pieces of retrieved context to answer the user's question.
 If the answer is not present in the context, explicitly say
 'I do not have data for that specific request.'
 Do not hallucinate or guess numbers. Keep the answer concise."
```

This prompt is deliberately conservative. In an education context, a wrong number (e.g., telling a student they can get IIT Bombay CSE with rank 500 when the actual cutoff is 119) could cause real harm. The model is instructed to fail loudly rather than guess silently.

---

## ⚡ Edge Device & Low-Compute Design

This project was built with Tier 2/3 India in mind, where students may be accessing the app on:
- Entry-level Android phones with 2–3 GB RAM
- Shared home broadband with 5–10 Mbps bandwidth
- Government school computer labs with old hardware

Every architectural choice reflects this constraint:

| Choice | Why |
|---|---|
| **`all-MiniLM-L6-v2`** (22M params) for embeddings | Runs on CPU; no GPU required for the offline pipeline |
| **SQL retrieval at runtime** (no embedding model) | Zero ML compute needed per query |
| **Streamlit** UI | Renders as a lightweight single-page app; minimal JavaScript |
| **Databricks Serverless SQL** | Pay-per-query; no always-on cluster cost |
| **`max_tokens=512`** for LLM | Keeps responses short, reduces latency, lowers cost |
| **ChromaDB** (embedded, file-based) | No separate vector DB server to maintain |
| **SarvamAI `mayura:v1`** | Purpose-built for Indian language nuances; more accurate than general multilingual models |

---

## ⚙️ Configuration Reference

All configurable values are defined at the top of `app.py`:

| Variable | Value | Description |
|---|---|---|
| `WAREHOUSE_ID` | `65ce16d60ab74bcf` | Databricks SQL Warehouse ID |
| `SARVAM_API_KEY` | `sk_ewpqphlu_...` | SarvamAI API key for translation |
| `DASHBOARD_ID` | `01f14083a67b1244a44ccd7d35e99447` | Databricks dashboard for visual embed |
| `ORG_ID` | `7474648620124818` | Databricks organisation ID |
| `LLM_ENDPOINT` | `databricks-gpt-5-4` | Model serving endpoint name |
| SQL Table | `hackathon.hack_data.jossa_data_cleaned` | Unity Catalog table with cutoff data |

> ⚠️ **Security note:** API keys should be moved to Databricks Secrets or environment variables before any production deployment.

---

## 💡 Example Queries

The following questions can be asked in English or any of the 10 supported Indian languages:

```
# By rank
"What programs can I get with JEE rank 4500 in OPEN category?"
"Show me institutes where closing rank is around 8000 for OBC-NCL"

# By institute and branch
"What was the closing rank for CSE at IIT Bombay in 2023?"
"Show me Civil Engineering cutoff at IIT Madras for SC category"

# Trend analysis
"How has the IIT Delhi Computer Science cutoff changed from 2021 to 2024?"

# Comparison
"Compare NIT Trichy vs NIT Warangal for Mechanical Engineering"

# Women-specific
"What was the closing rank for Female candidates in Electrical Engineering at IIT Roorkee?"

# Broad exploration
"Which IIT has the lowest closing rank for Aerospace Engineering?"
```

---

## 🚧 Limitations & Future Work

### Current Limitations

- **Institute coverage in vector store**: The ChromaDB vector store currently covers only the top 7 IITs for embeddings. The SQL table (`jossa_data_cleaned`) covers all participating institutes and is the primary retrieval backend.
- **Round-specific filtering**: `Round` and `Quota` columns were dropped during preprocessing; queries about specific counselling rounds are not supported.
- **API key exposure**: API keys are hardcoded in `app.py` and should be moved to Databricks Secrets.
- **No user memory**: The app is stateless — each question is independent, with no conversation history.

### Planned Improvements

- [ ] Expand ChromaDB coverage to all NITs and IIITs
- [ ] Add voice input using SarvamAI's speech-to-text API, enabling access for low-literacy users
- [ ] Branch comparison side-by-side view
- [ ] College predictor mode: *"Given my rank, show me all realistic options"*
- [ ] Parent-facing mode with simplified language and school-name-based explanations
- [ ] Offline-capable PWA (Progressive Web App) for areas with intermittent connectivity
- [ ] SMS/WhatsApp bot interface for feature phones

---

## 👥 Built For

This project was built during a hackathon on the **Databricks platform**, targeting engineering aspirants from Tier 2 and Tier 3 cities across India who lack access to professional counsellors. The goal is to put the same information that urban, well-resourced students take for granted into the hands of every student with a smartphone — in their own language, for free.

---

*Built with ❤️ for India's next generation of engineers.*