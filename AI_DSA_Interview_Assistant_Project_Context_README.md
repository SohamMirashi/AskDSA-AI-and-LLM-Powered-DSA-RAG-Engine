# AI-Powered DSA Interview Assistant — Project Context README

> **Purpose of this document:** This README is a detailed, portable context file for another ChatGPT conversation, LLM, developer, or collaborator. It captures the project's goals, decisions, architecture, technology choices, implementation roadmap, constraints, and open questions discussed so far. Use it as the source of truth when continuing project planning or implementation.
>
> **Important:** This is a planned project architecture, not a claim that the system has already been built. Performance targets and resume metrics must only be reported after they have been measured.

---

## 1. Project Overview

### Working description

Build an **AI-powered browser extension for data structures and algorithms (DSA) interview preparation**. The extension integrates into coding-practice websites and provides contextual learning assistance while the user is viewing a problem.

Target platforms include:

- LeetCode
- GeeksforGeeks (GFG)
- Codeforces
- CodeChef
- HackerRank

The extension should recognize the problem the user is currently viewing and provide relevant information from a central DSA knowledge base. A companion backend powers search, company-question intelligence, recommendations, and AI tutoring.

This is intended to be a substantial portfolio/resume project demonstrating backend engineering, search and retrieval, AI integration, systems programming, browser-extension development, data engineering, evaluation, and cloud deployment—not merely a generic chatbot wrapper.

### Product positioning

Position the product as an **AI-powered interview-preparation and learning assistant**, not a tool designed to bypass the learning process. The primary user experience should support progressive hints, concept explanations, debugging guidance, related-problem discovery, and interview preparation. Full solutions may be offered as an explicit, user-requested learning mode rather than automatically revealed.

### Core user journey

1. A user opens a supported coding problem.
2. The extension identifies the platform and extracts the problem title, URL, and any available metadata.
3. The extension matches the page to a canonical problem record in the backend.
4. It displays a contextual side panel or popup.
5. The user can view company associations, difficulty, topic/pattern information, similar problems, hints, explanations, and recommendations.
6. When the user asks a question, the backend retrieves relevant context and invokes an LLM.
7. The answer streams back to the extension.
8. If the user opts in to progress tracking, their bookmarks, notes, solved status, and learning preferences are stored.

---

## 2. Goals and Non-Goals

### Main goals

- Identify the current problem on supported coding websites.
- Build a structured, searchable DSA problem knowledge base.
- Ingest company-wise DSA problem lists from a public repository supplied by the project owner.
- Show company associations and source/provenance for those associations.
- Support keyword, semantic, and metadata-filtered retrieval.
- Recommend related, prerequisite, and follow-up problems.
- Offer progressive AI hints and grounded explanations.
- Explain user-submitted code and help reason about errors and edge cases.
- Provide a useful browser-extension interface rather than relying solely on a standalone chat website.
- Measure retrieval quality, response quality, latency, and cost.
- Deploy the system with repeatable builds, monitoring, and secure configuration.
- Keep the architecture understandable and cost-conscious during early development.

### Non-goals for the initial MVP

- Do not start with Kubernetes, multi-cloud deployment, or a large collection of microservices.
- Do not build every feature before validating the core user journey.
- Do not claim millions of embeddings, production-scale traffic, or percentage improvements without measurement.
- Do not assume all sites expose the same DOM structure or metadata.
- Do not depend on scraping restricted or copyrighted content in violation of source terms. Prefer official APIs, permissively licensed datasets, user-provided data, or sources whose terms permit the intended use.
- Do not make an LLM the source of truth for company-question frequency. Treat repository data as evidence with provenance and limitations.

---

## 3. Confirmed Technology Decisions

The user has explicitly chosen a **Go + C++ architecture, with Python only where it is genuinely useful or where the AI/ML ecosystem makes it the practical choice**.

| Component | Preferred technology | Responsibility |
|---|---|---|
| Browser extension | TypeScript + React | Extension UI, page integration, user interactions |
| Extension build tooling | Plasmo or another maintained extension framework; compare options before committing | Packaging, content scripts, background/service-worker setup |
| Main backend/API gateway | Go | HTTP APIs, auth, orchestration, rate limits, streaming, service coordination |
| Search/retrieval performance components | C++ | Custom inverted index, BM25, scoring/ranking, performance-sensitive algorithms |
| AI/ML utilities | Python, only where needed | Embeddings, model tooling, evaluation and optional reranking |
| Relational database | PostgreSQL | Users, canonical problem records, company associations, progress, notes, bookmarks |
| Vector database | Qdrant is the preferred production candidate; ChromaDB is an acceptable prototype alternative | Store embeddings and searchable text chunks |
| Cache/rate-limit store | Redis | Cache, throttling, short-lived state, idempotency where appropriate |
| LLM access | Provider API behind a Go interface | Hints, explanations, code feedback, grounded tutoring |
| Local development | Docker Compose | Reproducible local services |
| CI | GitHub Actions | Formatting, tests, linting, build checks |
| Cloud | AWS is the initial deployment preference | Host services and managed storage |
| Object storage | Amazon S3, if needed | Dataset snapshots, import files, backups/artifacts |
| Monitoring | Structured logs first; Prometheus/Grafana or managed alternatives later | Latency, errors, throughput, resource use |
| API contract | OpenAPI for HTTP; gRPC only if justified for internal service calls | Typed service interfaces |

### Language boundaries

**Go should own the main application flow.** It should not simply forward every operation through several unnecessary services.

**C++ should be introduced for a clear reason.** A custom BM25/inverted-index engine is a useful systems component and a strong learning exercise, but it must be benchmarked against a mature implementation. Do not move vector search into C++ merely because C++ is fast: a vector database already provides optimized indexing and search.

**Python should not be used for the main backend by default.** Use it for embedding generation, model-specific tooling, evaluation scripts, or a local inference pipeline if a suitable Go implementation is impractical. If using a hosted embedding/LLM API, Go can call that API directly; Python may not be necessary for that particular task.

### Important architecture choice

Begin with a **modular monolith in Go plus separately executed C++ and optional Python components only where there is a real boundary**. Do not create a microservice for every module. The initial system can run locally with Docker Compose and be deployed as a small number of containers.

---

## 4. High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│ Browser: LeetCode / GFG / Codeforces / CodeChef / HackerRank │
└──────────────────────────────┬───────────────────────────────┘
                               │ DOM/page metadata
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Browser Extension: TypeScript + React                        │
│ Content scripts • side panel/popup • platform adapters       │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTPS + SSE
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Go Application/API                                            │
│ Auth • validation • orchestration • rate limits • streaming  │
└────────────┬─────────────────┬─────────────────┬─────────────┘
             │                 │                 │
             ▼                 ▼                 ▼
       PostgreSQL            Redis         Retrieval/AI orchestration
             │                                   │
             │                     ┌─────────────┼─────────────┐
             │                     ▼             ▼             ▼
             │                C++ search    Vector DB     LLM/embedding API
             │                (BM25/index)  (Qdrant)      (Python optional)
             │                     └─────────────┬─────────────┘
             │                                   ▼
             └──────────────────────────── Context + grounded response
                                                 │
                                                 ▼
                                      Streamed result to extension

Offline / administrative data flow:
Source datasets and company repository
        → Go import/validation pipeline (or small scripts when useful)
        → normalized PostgreSQL records and raw snapshots
        → chunking and embedding generation
        → vector database
        → retrieval/evaluation test suite
```

The diagram is logical, not a requirement to deploy every box as a separate service.

---

## 5. Functional Requirements

### 5.1 Problem detection

For each supported platform, implement an independent adapter that attempts to extract:

- Platform identifier
- Canonical problem URL or platform problem ID
- Problem title
- Difficulty, if available
- Tags/topics, if available
- Statement text, only when permitted and necessary
- Relevant page metadata

The extension should not assume a single DOM selector will remain valid forever. Prefer stable IDs, semantic attributes, and URL patterns. Add adapter tests with saved HTML fixtures where feasible. When extraction fails, let the user correct the title or search manually.

Problem matching should use, in order of usefulness:

1. Platform + platform-specific problem ID
2. Canonical URL
3. Normalized title plus platform/source evidence
4. Fuzzy matching as a fallback, with confidence and user confirmation if ambiguous

Do not treat identical titles on different platforms as automatically identical problems.

### 5.2 Contextual extension panel

Suggested tabs or sections:

- **Hints:** progressive hints, from a nudge to a more explicit approach
- **Explain:** concept, algorithm, correctness intuition, complexity
- **Related:** similar problems and prerequisite/follow-up problems
- **Companies:** companies associated with the problem, based on the imported repository
- **Practice plan:** recommended next problems
- **Notes/progress:** bookmarks, notes, status, and revision tracking

Start with a small panel containing problem identity, company associations, related problems, and progressive hints. Add the rest after the core flow is reliable.

### 5.3 Company intelligence

The user has identified a repository containing company folders, where each company lists commonly asked DSA problem names and difficulty levels. The exact repository URL has not yet been provided in this conversation.

Ingest the repository while preserving:

- Company name and canonical company ID
- Original problem name
- Listed difficulty
- Repository URL, file path, and commit/version where possible
- Import timestamp
- Match status and confidence against the canonical problem catalog

A company association is evidence that a repository lists a problem; it is not proof of a verified interview frequency. If the source does not provide numeric counts, do not fabricate counts or label a problem “asked 20 times.” Use transparent wording such as “listed in the Google folder in source repository X.”

### 5.4 AI tutoring

Potential modes:

- Progressive hint 1, hint 2, hint 3
- Explain the underlying DSA pattern
- Explain brute-force and optimized approaches
- Explain time and space complexity
- Help reason about code and edge cases
- Compare algorithms
- Generate a practice sequence

The default experience should avoid revealing a full solution immediately. Give users a control to request a more explicit explanation or solution.

### 5.5 Similar-problem recommendations

Combine multiple signals:

- Topic/pattern overlap
- Shared tags
- Semantic similarity
- Difficulty distance
- Graph relationships such as prerequisite/variant/follow-up
- User goals and opt-in progress data
- Company associations where supported by source data

Do not use embedding similarity alone to claim that two problems teach the same technique.

---

## 6. Data Collection and Ingestion

This is the first major engineering workstream.

### Step 1 — Inventory sources and rights

Before coding scrapers, identify:

- The exact company-question repository URL
- Its license and data format
- Whether its entries use platform URLs, IDs, titles, or only names
- Permitted sources for problem statements, tags, and editorials
- Official APIs or permissively licensed datasets available for each platform
- What data is essential for the MVP

Keep the initial dataset narrow enough to validate the product. Company-list data can be useful even if full problem statements are not collected.

### Step 2 — Build a raw-data import layer

Save source snapshots in versioned JSON, JSONL, or CSV files. Retain source provenance rather than overwriting it with normalized values.

Possible record:

```json
{
  "source_type": "company_repository",
  "company_name": "Example Company",
  "problem_title": "Example Problem",
  "listed_difficulty": "Medium",
  "source_repository": "repository URL",
  "source_path": "company-folder/problem-list.md",
  "source_revision": "commit SHA or version",
  "imported_at": "ISO-8601 timestamp"
}
```

The example is illustrative, not actual data from the repository.

### Step 3 — Normalize and validate

- Normalize whitespace, casing, punctuation, and common title variations.
- Normalize difficulty into a controlled set: `easy`, `medium`, `hard`, `unknown`.
- Keep the original title alongside the normalized title.
- Deduplicate repeated source entries without erasing provenance.
- Validate URLs and source references.
- Record malformed or unmatched entries for manual review.
- Do not silently discard uncertain records.

### Step 4 — Create a canonical problem catalog

Suggested `problems` fields:

- `id` — internal stable ID
- `title`
- `normalized_title`
- `platform`
- `platform_problem_id` — nullable
- `canonical_url`
- `difficulty`
- `statement` — nullable and only stored if permitted
- `tags` or a normalized relation to topic records
- `content_source`
- `created_at`, `updated_at`

Use separate platform-mapping records when one underlying problem is represented on multiple websites. Preserve source-specific identity.

### Step 5 — Resolve company repository entries

Match each company-list entry to the canonical catalog. Use platform IDs/URLs where available; otherwise title matching and fuzzy matching can suggest candidates. Store:

- Source company
- Canonical problem ID, if matched
- Original title
- Listed difficulty
- Source reference
- Match method/confidence
- Review status

Do not force uncertain matches. Provide an unresolved-record report.

### Step 6 — Add problem content only from appropriate sources

Collect permitted metadata and content needed by the product. Avoid indiscriminate scraping of protected pages or solutions. Respect rate limits, robots directives where applicable, platform terms, licenses, and privacy requirements. If the user manually supplies a problem statement or code for assistance, process only what is needed for that request and apply a clear retention policy.

### Step 7 — Clean and chunk content for retrieval

Use structure-aware chunking rather than blindly splitting every N characters. Keep each chunk associated with its parent problem.

Possible chunk types:

- `problem_statement`
- `constraints_examples`
- `concept`
- `hint`
- `approach`
- `complexity`
- `editorial` — only where content is permitted
- `pattern_guide`
- `user_note` — private, user-specific content, if implemented

Each chunk should have metadata such as:

```json
{
  "problem_id": "internal-id",
  "chunk_type": "pattern_guide",
  "platform": "leetcode",
  "difficulty": "medium",
  "topics": ["sliding-window"],
  "source_id": "source-record-id",
  "content_version": 1
}
```

Do not embed duplicate copies of the same content without a reason. Preserve code blocks when chunking explanatory text.

### Step 8 — Make ingestion idempotent

Repeated runs should not create duplicate problems or embeddings. Use stable IDs/content hashes, versioned documents, upserts, and a deletion/update policy. Log the number of inserted, updated, skipped, failed, unmatched, and duplicate records.

### Step 9 — Store the normalized data

- PostgreSQL: canonical records, source mappings, company associations, users and progress.
- S3 or versioned local files: raw source snapshots and import artifacts when useful.
- Vector DB: embedding vectors and retrieval-ready chunks.
- Redis: not the source of truth; only cache and short-lived operational state.

---

## 7. Embeddings and Vector Retrieval

### Embedding strategy

Start with one suitable embedding model and a small benchmark dataset. A hosted embedding API can be called from Go if the provider supports it. If using a Python-only library or local model, isolate it behind a small Python process/service.

Possible options to evaluate:

- A compact sentence-transformer model for inexpensive local experiments
- A suitable BGE/E5-family model
- A hosted embedding API if its cost, privacy, and latency fit the project

Choose based on retrieval evaluation, language/code behavior, memory requirements, and licensing—not popularity alone.

### Vector store

**Qdrant is the preferred candidate for the deployable version; ChromaDB is acceptable for a quick prototype.** Pick one initially rather than operating both.

Store:

- Vector
- Chunk/document ID
- Text or retrievable content reference
- Problem/source identifiers
- Filterable metadata

Do not store all application state in the vector database. PostgreSQL remains the system of record.

### Initial retrieval flow

1. Receive a user query and current problem context.
2. Normalize the query and classify the intent where useful.
3. Apply platform/topic/difficulty/company filters if requested.
4. Run keyword search and vector search.
5. Merge the rankings.
6. Rerank and deduplicate.
7. Select a context budget.
8. Send the selected context to the LLM.
9. Return the response with references to source problem records.

---

## 8. C++ Search and Ranking Engine

C++ is intended for demonstrable systems work, not as a requirement to reimplement every database.

### Recommended first C++ component

Build a **custom inverted-index and BM25 search engine** over a controlled problem/chunk corpus. This provides a concrete reason to use C++ and an objective way to measure its performance.

### Suggested modules

1. **Text normalization/tokenization**
   - Lowercasing where appropriate
   - Token boundaries
   - Punctuation handling
   - Optional stemming/stop words only after evaluation
   - Special handling for algorithm names, code identifiers, and terms such as `C++`, `BFS`, `DP`, `4Sum`

2. **Inverted index**
   - Term → document postings
   - Term frequency
   - Document length
   - Corpus statistics
   - Stable document IDs

3. **BM25 scoring**
   - Implement the standard BM25 ranking function
   - Unit-test against hand-computed examples
   - Compare results with a trusted implementation

4. **Metadata filtering**
   - Filter by platform, difficulty, topic, and canonical IDs
   - Decide whether filters run before or after candidate retrieval
   - Ensure filters do not accidentally exclude relevant results

5. **Hybrid rank fusion**
   - Combine lexical ranking with vector retrieval results
   - Begin with Reciprocal Rank Fusion (RRF) or normalized scores
   - Tune only on a held-out evaluation set

6. **Diversity reranking**
   - Add Maximal Marginal Relevance (MMR) only if the result set needs diversity
   - Avoid selecting near-duplicate chunks for the final context

7. **Benchmark and tests**
   - Search relevance tests
   - Empty-query and malformed-query behavior
   - Large/small corpus benchmarks
   - Memory use, throughput, and p50/p95/p99 latency

### How Go calls C++

Recommended initial interface: a separate C++ process exposing a narrow, versioned API. Options include a small HTTP service or gRPC. Start with whichever has the lowest implementation burden and cleanest testability. Avoid CGO initially because it introduces build and deployment complexity; reconsider it only if measurements justify in-process calls.

Example logical request:

```json
{
  "query": "minimum window substring",
  "top_k": 20,
  "filters": {
    "difficulty": "hard",
    "topic": "sliding-window"
  }
}
```

The actual contract should be defined and versioned before implementation.

### Performance claims

Do not put “42% faster,” “sub-200 ms,” or any other performance figure on the resume until the benchmark exists, the baseline is defined, and the result is reproducible. Compare the custom C++ engine to a sensible baseline on the same hardware and corpus.

---

## 9. Go Backend

Go is the main backend language.

### Responsibilities

- HTTP API and request validation
- Current-problem resolution
- User and session/authentication flows
- Orchestration of PostgreSQL, Redis, retrieval, and LLM calls
- Rate limiting and quotas
- SSE streaming
- Request timeouts, cancellation, and retry policy
- Structured logs and metrics
- Background import/admin jobs where appropriate
- Stable API contracts for the extension

### Suggested package organization

```text
backend-go/
  cmd/
    api/
  internal/
    api/
    auth/
    config/
    problems/
    companies/
    retrieval/
    tutoring/
    recommendations/
    cache/
    persistence/
    ratelimit/
    observability/
  migrations/
  openapi/
  tests/
  Dockerfile
  go.mod
```

Treat this as a starting point; keep the codebase small until the boundaries become useful.

### Initial API endpoints

Names are illustrative and may change when the API contract is designed.

- `GET /healthz` — liveness
- `GET /readyz` — dependency readiness
- `POST /v1/problems/resolve` — match platform/page metadata to a canonical problem
- `GET /v1/problems/{id}` — fetch problem metadata
- `GET /v1/problems/{id}/companies` — source-backed company associations
- `GET /v1/problems/{id}/related` — related problems
- `POST /v1/search` — keyword/semantic search
- `POST /v1/tutor/hints` — generate the next hint
- `POST /v1/tutor/chat` — grounded tutoring conversation
- `POST /v1/code-review` — reason about submitted code
- `GET /v1/progress` and relevant write endpoints — opt-in user progress
- `POST /v1/bookmarks` — save a problem
- `GET /v1/companies/{id}/problems` — source-backed company list

Protect user-specific endpoints with authentication and authorization. Validate all inputs and cap payload sizes.

### Concurrency

Use Go concurrency when independent I/O tasks can safely run in parallel, for example:

- Cache lookup alongside independent metadata retrieval
- Lexical and vector retrieval in parallel
- Parallel calls to independent services, if they do not duplicate costly work

Use request-scoped deadlines and cancellation. Limit concurrency to protect external APIs and databases. Do not launch unlimited goroutines for user-controlled work.

### Streaming

Start with **Server-Sent Events (SSE)** for one-way streamed LLM output. WebSockets are unnecessary unless the product later needs sustained two-way communication. Handle disconnects, cancellation, keepalives, proxy buffering, and errors explicitly.

### Authentication and security

For the first version, decide whether accounts are required. A public read-only/basic tutoring MVP can avoid complex account flows. If accounts are added, use a well-maintained authentication approach, secure cookies or carefully managed tokens, password/OAuth best practices, authorization checks, and secret management. Do not invent a custom cryptographic scheme.

### Provider abstraction

Keep the LLM provider behind a Go interface so the implementation can switch between compatible providers. The abstraction should expose only needed features (e.g. chat completion and streaming); do not overgeneralize it into a large framework.

---

## 10. Python — Only Where It Adds Value

Python is optional, not the primary backend.

Use it for one or more of the following when needed:

- Local embedding generation using Python-first libraries
- Local model inference if a model's supported runtime makes Python the practical choice
- Cross-encoder reranking when a suitable model library requires Python
- Retrieval/LLM evaluation scripts and data analysis
- Offline experiments to compare models and chunking strategies

Do not add a Python microservice solely because the architecture diagram contains one. If the system uses hosted embedding and LLM APIs that Go can call directly, the online system may need no Python service at all. Python can still be useful for offline evaluation and experimentation.

Any Python service should have a narrow contract, health check, pinned dependencies, timeout handling, and resource limits.

---

## 11. LLM/RAG Pipeline

### Query intent

Classify requests into a small set of intents:

- `hint`
- `concept_explanation`
- `problem_explanation`
- `similar_problem_search`
- `company_lookup`
- `code_debugging`
- `complexity_analysis`
- `practice_plan`

A rules-based classifier can be enough for the MVP. A model-based classifier should be added only if it demonstrably improves routing.

### Context assembly

Build the final prompt from:

1. A stable system instruction
2. The user's current problem metadata
3. Retrieved, relevant chunks
4. Relevant conversation history, bounded by a token budget
5. The latest user request
6. Output constraints for the selected tutoring mode

Include source IDs or links in the internal context so the answer can cite the evidence it used. Do not ask the model to invent citations.

### Progressive hints

Track which hint level the user has already received. Generate the next hint using the problem and prior hints, without repeating previous hints. If evidence is insufficient, the assistant should say so rather than fabricate a problem-specific detail.

### Grounding and hallucination controls

- Retrieve before generating for knowledge-base-dependent answers.
- Distinguish source facts from generated suggestions.
- Attach source references to retrieved facts.
- Ask the model to abstain when context is insufficient.
- Validate structured outputs where applicable.
- Treat model-produced code and complexity claims as untrusted until tested/reviewed.
- Never claim a measured hallucination reduction without a defined evaluation protocol.

### Advanced techniques — later, not in the first version

- **HyDE:** generate hypothetical relevant text and search using its embedding; evaluate whether it improves recall enough to justify the extra LLM call.
- **RRF:** combine lexical and vector rankings without requiring their raw scores to share a scale.
- **MMR:** select relevant but diverse chunks.
- **Context compression:** remove redundant retrieved context under a token budget.
- **Multi-LLM routing:** route based on quality, latency, and cost only after a single-provider baseline works.
- **Adaptive RAG:** use different retrieval paths for hints, code debugging, company search, and conceptual explanations.

Do not implement every advanced technique up front. Add each one behind a benchmark and an explicit reason.

---

## 12. Browser Extension Implementation

### Suggested technology

- TypeScript
- React
- Plasmo or a comparable maintained framework
- Browser Extension Manifest V3
- Fetch/streaming APIs for communication with the Go backend

Choose framework and package versions after checking current maintenance, browser support, and build output. The extension should not contain provider API secrets.

### Core extension components

```text
extension/
  src/
    contents/
      leetcode.ts
      gfg.ts
      codeforces.ts
      codechef.ts
      hackerrank.ts
    components/
      AssistantPanel.tsx
      ProblemHeader.tsx
      HintList.tsx
      CompanyList.tsx
      RelatedProblems.tsx
    background/
    lib/
      api.ts
      problemResolver.ts
      platformRegistry.ts
      streaming.ts
    styles/
  tests/
  manifest configuration
```

Exact paths depend on the chosen framework.

### Platform adapter interface

Each adapter should implement a common conceptual contract:

- Determine whether the current URL belongs to the platform.
- Extract a platform problem identifier when available.
- Extract title and visible metadata.
- Return a normalized problem-page object.
- Report extraction confidence or missing fields.

Build and test one platform adapter first. LeetCode is a reasonable starting point, but the choice should be validated against actual page behavior. Then add the other platforms incrementally.

### UI behavior

- Use a popup or side panel for a simple first release.
- If injecting a panel into the page, isolate styles (e.g. with Shadow DOM where appropriate) to reduce CSS conflicts.
- Avoid disrupting the site's editor, keyboard shortcuts, or submission flow.
- Provide loading, empty, unsupported-page, error, retry, and rate-limit states.
- Let the user edit/confirm a detected title if matching fails.
- Show provenance for company information.
- Make data collection and progress tracking transparent and opt-in.

### Permissions and privacy

Request only the browser permissions required by the supported domains and features. Explain what page information is sent to the backend. Do not transmit editor contents automatically; only send code when the user explicitly invokes code-help functionality. Provide a clear retention policy for submitted code, chats, and progress data.

---

## 13. Databases and Data Model

### PostgreSQL — source of truth

Suggested logical entities:

- `users` — optional until accounts are needed
- `problems`
- `platform_problem_mappings`
- `topics`
- `problem_topics`
- `companies`
- `company_problem_sources`
- `content_sources`
- `content_chunks` or references to chunk records
- `bookmarks`
- `user_problem_progress`
- `user_notes`
- `conversation_sessions`
- `conversation_messages` — only if history persistence is needed
- `ingestion_runs`

Important constraints and indexes:

- Unique platform + platform problem ID when available
- Index normalized title and canonical URL
- Foreign keys for canonical relationships
- Index company/problem associations
- Explicit timestamps and provenance
- Retention/deletion policy for personal data

Normalize relationships rather than storing every company/topic association as an opaque array if those associations need querying, integrity, or analytics.

### Vector DB

Qdrant or ChromaDB stores vectors and searchable chunks. Use stable chunk IDs and payload fields that support the intended filters. Keep database versions and collection schemas controlled.

### Redis

Use for:

- Frequently repeated search/recommendation results
- Short-lived session/state data if required
- Rate limiting
- Idempotency keys where appropriate
- Carefully bounded response caching

Cache keys should include relevant context, model/prompt version, and user scope where applicable. Never return one user's private notes or conversation to another user because of an incomplete cache key. Avoid caching sensitive code or private responses by default.

---

## 14. Evaluation and Testing

Evaluation is a core project component, not a final optional polish step.

### 14.1 Create a fixed evaluation dataset

Build a manually reviewed set of queries that represent real use cases:

- Exact problem title lookup
- Problem-title variants
- Topic/pattern search
- Company-specific search
- Similar-problem discovery
- Hint generation
- Code debugging with supplied code
- Queries where the corpus lacks enough evidence

Record the expected relevant problem/chunk IDs and the expected behavior. Split development and held-out test data to avoid tuning to the final benchmark.

### 14.2 Retrieval metrics

Measure:

- **Recall@K:** fraction of relevant items retrieved in the top K
- **Precision@K:** fraction of the top K that are relevant
- **MRR:** rank of the first relevant result
- **NDCG@K:** ranking quality when relevance grades differ

Report metrics by query category, not only one aggregate number.

### 14.3 Answer-quality evaluation

Use a documented rubric to judge:

- Factual correctness
- Relevance to the user's problem
- Grounding in retrieved evidence
- Hint usefulness and progression
- Correctness of complexity analysis
- Unsupported-claim rate
- Whether abstention is appropriate when context is insufficient

Combine deterministic checks, human review, and LLM-assisted evaluation cautiously. An LLM judge is not ground truth.

### 14.4 System and performance metrics

Measure:

- API latency: p50, p95, p99
- Lexical search latency
- Vector search latency
- Reranking latency
- Time to first streamed token
- End-to-end response time
- Cache hit rate
- Error and timeout rate
- Token usage and cost per request
- Memory and CPU usage
- Ingestion throughput and failure rate

Document hardware, corpus size, workload, concurrency, and baseline when publishing benchmark results.

### 14.5 Testing layers

- Unit tests for normalization, BM25, scoring, and problem matching
- Integration tests for Go + PostgreSQL + Redis + retrieval
- Contract tests for Go/C++ and Go/optional Python interfaces
- Fixture tests for each extension platform adapter
- End-to-end tests for detection → resolution → retrieval → streamed response
- Load tests for concurrent requests and cancellation
- Security tests for authorization, rate limiting, input limits, and secret exposure

---

## 15. Deployment and DevOps

### Stage 1 — Local development

Use Docker Compose for PostgreSQL, Redis, vector DB, and the services that need containerization. Run the extension through the chosen browser-extension development workflow. Keep a documented `.env.example` with variable names but no real secrets.

### Stage 2 — Containerization

Create separate images only for actual deployable processes, such as:

- Go API
- C++ search service (if it runs separately)
- Python embedding/reranking service (only if required)
- Supporting databases during local development

Use multi-stage Docker builds, non-root runtime users, small runtime images, health checks, and pinned dependencies. Do not package the entire development toolchain into production images.

### Stage 3 — CI with GitHub Actions

On each pull request:

1. Format and lint Go, C++, and TypeScript.
2. Run unit tests.
3. Build each relevant component.
4. Run integration/contract tests where practical.
5. Build container images.
6. Run dependency/security checks.

Deployment should be a separate protected workflow with environment-specific configuration.

### Stage 4 — AWS initial deployment

Prefer a simple, low-cost architecture for the first deployed version. One possible path:

- Go API and C++ search service: container hosting on ECS/Fargate, or a small EC2 instance if cost and operational tradeoffs favor it
- PostgreSQL: managed PostgreSQL (e.g. RDS) if budget permits; otherwise a carefully managed single-instance setup for a demonstration
- Redis: managed Redis-compatible service only if the cost is justified; otherwise use a small local/deployed instance for a demo with explicit limitations
- Vector database: hosted Qdrant or self-hosted on the same small environment, after evaluating cost and persistence requirements
- S3: raw data snapshots and backup/artifact storage when needed
- Secrets: AWS Secrets Manager or SSM Parameter Store
- Logs: CloudWatch or an equivalent supported log platform
- HTTPS: managed TLS and a domain/reverse proxy configuration appropriate to the hosting option

Exact AWS choices must be re-evaluated against current pricing and service availability before deployment. Keep the initial architecture small; do not deploy EKS/Kubernetes until there is a clear operational need.

### Stage 5 — Extension distribution

For development, load the unpacked extension in a test browser. Before public distribution:

- Check each target site's terms and extension policies.
- Minimize permissions.
- Document privacy practices.
- Test supported pages and fallback behavior.
- Provide an update/release process.
- Do not bundle server-side API keys into the extension.

### Stage 6 — Operations

Add:

- Health and readiness checks
- Structured request logs with request IDs
- Error rates and latency dashboards
- Dependency timeouts and bounded retries
- Database backups and restore tests
- Ingestion job monitoring
- Budget alerts and LLM usage caps
- Incident/debugging notes

Prometheus/Grafana can be added when metrics justify the extra deployment work. Begin with reliable logs, health checks, and a few important metrics.

---

## 16. Security, Privacy, and Responsible Data Handling

- Keep LLM, database, and cloud credentials server-side.
- Use TLS for production traffic.
- Validate request sizes and all user-controlled parameters.
- Apply rate limits and usage quotas.
- Restrict extension host permissions.
- Do not collect editor code or page content without user action and clear notice.
- Avoid logging API keys, raw tokens, private code, or sensitive chat content.
- Set a retention policy and implement deletion for account data if accounts are supported.
- Restrict CORS to the required origins; do not treat CORS as authentication.
- Apply authorization to every user-specific object.
- Keep dependency versions current and scan for known vulnerabilities.
- Respect dataset licenses and website terms; retain source provenance.
- Clearly distinguish source-backed company associations from estimates or model-generated recommendations.

---

## 17. Recommended Build Order

The order below is deliberately incremental. Each stage should leave a working, testable artifact.

### Phase A — Requirements and data audit

1. Obtain the exact company-question repository URL.
2. Inspect its folder structure, format, license, and source quality.
3. Choose the first supported platform.
4. Define the minimum user journey and API contract.
5. Create a small sample dataset and hand-reviewed retrieval benchmark.
6. Create the repository, formatting rules, and architecture decision notes.

**Deliverable:** documented data model, source audit, and a small test corpus.

### Phase B — Data foundation

7. Build a reproducible company-repository importer.
8. Normalize company names, problem titles, and difficulty.
9. Create PostgreSQL migrations and canonical problem tables.
10. Resolve source entries against canonical problems.
11. Generate an unmatched/ambiguous records report.
12. Add idempotency and ingestion tests.

**Deliverable:** queryable, source-attributed company/problem dataset.

### Phase C — Basic product slice

13. Build one extension adapter.
14. Extract the current problem's title, URL, and platform ID where available.
15. Implement Go problem-resolution and company-lookup endpoints.
16. Build a minimal extension panel showing the detected problem and source-backed company associations.
17. Test on real pages and saved fixtures.

**Deliverable:** a useful extension before adding an LLM.

### Phase D — Search foundation

18. Add allowed problem descriptions and/or curated DSA concept documents.
19. Implement a baseline keyword search.
20. Implement embeddings using a hosted API or optional Python embedding component.
21. Set up one vector DB.
22. Add vector retrieval and metadata filtering.
23. Evaluate search against the fixed dataset.

**Deliverable:** searchable DSA knowledge base with measured baseline quality.

### Phase E — C++ search engine

24. Implement tokenization and an inverted index in C++.
25. Implement and unit-test BM25.
26. Expose a narrow API to Go.
27. Compare C++ results with a trusted baseline.
28. Add hybrid ranking/RRF.
29. Add MMR only if diversity evaluation supports it.
30. Benchmark latency and memory on a defined corpus.

**Deliverable:** tested, benchmarked lexical retrieval component.

### Phase F — Grounded AI tutoring

31. Define a Go LLM-provider interface.
32. Implement a basic grounded hint/explanation flow.
33. Retrieve context before answering.
34. Stream results through SSE.
35. Add progressive hint levels and source references.
36. Add code debugging as an explicit user-triggered action.
37. Add timeouts, rate limits, cost controls, and safe fallbacks.
38. Evaluate answer quality and unsupported claims.

**Deliverable:** contextual AI tutor integrated with retrieval.

### Phase G — Extension expansion

39. Improve the panel and error/empty states.
40. Add related-problem recommendations.
41. Add remaining platform adapters one at a time.
42. Add company and difficulty filters.
43. Add bookmarks/notes/progress only if they fit the initial scope.
44. Add privacy and permissions documentation.

**Deliverable:** multi-platform extension with consistent behavior.

### Phase H — Production hardening

45. Add Redis only where caching/rate limiting is useful.
46. Add PostgreSQL indexes and review query plans.
47. Add request IDs, structured logs, health checks, and key metrics.
48. Dockerize deployable services.
49. Add GitHub Actions CI.
50. Load-test and address actual bottlenecks.
51. Deploy to a cost-conscious AWS environment.
52. Configure TLS, secrets, backups, monitoring, and budget alerts.
53. Publish documentation, screenshots/demo, architecture diagram, and measured evaluation results.

**Deliverable:** reproducibly deployed portfolio project.

### Phase I — Advanced improvements

Only after the previous stages work:

- HyDE and query expansion
- More sophisticated rerankers
- Adaptive retrieval by query intent
- Multi-LLM routing
- Personalized practice plans
- Interview simulation
- More advanced observability
- Horizontal scaling and orchestration if measured demand requires it

---

## 18. Suggested Repository Layout

This is a logical starting point, not a mandate to create all directories immediately.

```text
dsa-interview-assistant/
├── extension/
│   ├── src/
│   ├── tests/
│   └── README.md
├── backend-go/
│   ├── cmd/
│   ├── internal/
│   ├── migrations/
│   ├── openapi/
│   ├── tests/
│   └── Dockerfile
├── retrieval-cpp/
│   ├── include/
│   ├── src/
│   ├── tests/
│   ├── benchmarks/
│   ├── CMakeLists.txt
│   └── Dockerfile
├── ai-tools-python/          # optional; omit if unnecessary
│   ├── embeddings/
│   ├── evaluation/
│   ├── tests/
│   └── pyproject.toml
├── data/
│   ├── schemas/
│   ├── samples/
│   └── README.md
├── evaluation/
│   ├── retrieval/
│   ├── answer_quality/
│   └── benchmark_results/
├── deploy/
│   ├── compose.yaml
│   ├── aws/
│   └── monitoring/
├── docs/
│   ├── architecture.md
│   ├── data-sources.md
│   ├── api.md
│   ├── privacy.md
│   └── decisions/
├── .github/
│   └── workflows/
├── .env.example
└── README.md
```

Do not commit `.env`, API keys, production data, or private user information. Include sample data that is redistributable.

---

## 19. Recommended MVP Scope

The full vision is intentionally ambitious. The first release should prove one end-to-end path:

1. Import the company-question repository.
2. Store normalized company/problem mappings in PostgreSQL.
3. Build one browser adapter, preferably for one target platform.
4. Detect the current problem and resolve it.
5. Display company associations with provenance.
6. Add lexical search and related-problem lookup.
7. Add one grounded AI hint flow with SSE.
8. Add a small vector retrieval layer if the knowledge base warrants it.
9. Test retrieval and response quality.
10. Deploy the Go API and required data services at low cost.

C++ should be introduced when the baseline search and evaluation set exist, so there is something meaningful to compare against. If the C++ BM25 engine is part of the project's learning goal from day one, implement it after a simple baseline and keep its interface narrow.

This MVP is already demonstrable. Add additional platforms, personalized analytics, and advanced RAG techniques after it works reliably.

---

## 20. Resume and Portfolio Guidelines

The goal is to produce evidence of engineering, not just a long technology list.

Strong resume bullets should be written only after the work and measurements exist. Useful dimensions include:

- Number of canonical problem records and company associations imported
- Number of supported platforms and adapter test coverage
- Recall@K, MRR, and NDCG on a documented retrieval benchmark
- Search p50/p95 latency and corpus/hardware details
- End-to-end time-to-first-token and response latency
- Ingestion throughput and duplicate/error rates
- Cache hit rate and request cost, if caching is implemented
- CI coverage and successful reproducible deployment

Use this format:

> Built **[component]** using **[technology]** for **[measurable purpose]**, evaluated on **[dataset/workload]**, achieving **[measured result]** against **[baseline]**.

Do not claim “96.6% retrieval accuracy,” “91.8% hallucination reduction,” “10M+ embeddings,” “sub-200 ms,” or any similar figure merely because those appeared in the inspiration project. Establish your own definitions, benchmark, and evidence.

---

## 21. Important Design Trade-Offs

### Go vs Python backend

Go is the selected main backend because the project owner wants to demonstrate concurrency, networking, APIs, and service orchestration. Python remains available for model tooling. This is a design choice, not a claim that Go is always faster or better for every backend workload.

### C++ vs an existing search engine

A custom C++ BM25 engine demonstrates systems fundamentals and allows low-level optimization. Mature search engines may provide better features and relevance out of the box. Keep the custom engine only if it adds measurable value or is a central learning objective.

### Vector database choice

Use one vector database initially. Qdrant is the current preferred deployable candidate; ChromaDB remains a prototype option. Decide based on metadata filtering, operational complexity, persistence, deployment cost, and measured performance.

### Microservices vs modular monolith

Start as a modular Go application plus only the separate processes genuinely needed for C++ and optional Python. Separate more services only when deployment, isolation, or scaling requirements justify it.

### Cloud cost

Prefer a working small AWS deployment over an elaborate multi-cloud system. Track recurring database, compute, storage, networking, and LLM costs. Use budgets/alerts and shut down unused resources. Confirm current prices before selecting services.

### Search techniques

Hybrid retrieval, RRF, HyDE, MMR, and reranking are options to test—not a checklist that must be implemented. Keep techniques that improve measured relevance or user experience without unjustified latency/cost.

---

## 22. Open Questions to Resolve

These are genuinely undecided and should be clarified before their implementation depends on them:

1. **Company repository:** What is its exact URL, license, and data format?
2. **Initial platform:** Which coding website should be supported first?
3. **Data rights:** Which sources may legally and practically be used for statements, editorials, tags, and code?
4. **LLM provider:** Which provider and model meet quality, cost, latency, and regional requirements?
5. **Embeddings:** Hosted API or local model? This determines whether an online Python service is needed.
6. **Vector DB:** Qdrant or ChromaDB for the first release?
7. **C++ interface:** HTTP or gRPC for the search service?
8. **Authentication:** Should the MVP require accounts, or should it begin with limited anonymous usage?
9. **Progress tracking:** Which information should be stored, and for how long?
10. **Deployment budget:** What monthly cost is acceptable?
11. **Browsers:** Chromium only at first, or Firefox support too?
12. **Extension framework:** Confirm the current maintenance and compatibility of Plasmo before committing.
13. **Content retention:** Should chats and submitted code be stored, and can users delete them?
14. **Distribution:** Personal/local use first, or eventual public extension-store release?

When continuing in another chat, ask only the questions necessary for the next implementation step. Do not block basic planning on every open question.

---

## 23. Instructions for the Next LLM or Developer

When using this README as context:

1. Treat the chosen language split as **Go for the main backend, C++ for a focused search/performance engine, and Python only where it is practically needed**.
2. Treat the browser extension as the primary user interface, not a standalone ChatGPT-style website.
3. Treat company-question data as source-attributed evidence, not guaranteed verified interview-frequency data.
4. Do not assume the repository URL is known; ask for it when implementation reaches ingestion.
5. Do not invent implementation status, performance numbers, benchmark outcomes, or cloud costs.
6. Avoid proposing every advanced technique at once. Follow the build phases and deliver working increments.
7. Prefer minimum-cost and free/local development where practical, then deploy a small AWS version when the product is stable.
8. When asked to implement a component, provide a short purpose, exact file path, complete code, run instructions, and test steps.
9. Keep the frontend focused and practical; prioritize the data pipeline, retrieval quality, backend correctness, and evaluation.
10. Explain architectural trade-offs and avoid extra services that do not provide clear value.
11. Check current documentation/pricing before relying on cloud or framework-specific details.
12. Keep user privacy, source licensing, extension permissions, and secure secret management in scope.

---

## 24. One-Sentence Project Summary

**An AI-powered, multi-platform browser extension for DSA interview preparation, backed by a Go API, a C++ lexical retrieval/ranking engine, PostgreSQL, Redis, a vector database, and optional Python-based embedding/model tooling, with source-attributed company-question intelligence, grounded tutoring, recommendations, evaluation, and cost-conscious cloud deployment.**
