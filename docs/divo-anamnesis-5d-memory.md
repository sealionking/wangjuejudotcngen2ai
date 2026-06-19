# DiVo-Anamnesis: 5D Strategic Memory Engine for AI Agents

**DiVo Gen²AI | Technical Report | June 2026**

---

## Abstract

We present DiVo-Anamnesis, a 5-dimensional strategic memory engine. Building on the open-source Anamnesis (which provides 4D recall: semantic, temporal, relational, strategic), we introduce the **5th dimension — knowledge** — via an OpenSearch-based federation layer that unifies local episodic memories with external knowledge bases under a single RRF scoring function. Key innovations include: (1) extending 4D RRF to 5D with a configurable knowledge dimension, (2) hybrid BM25+neural search via OpenSearch with automatic fallback, and (3) an IDE session bridge that decrypts and indexes encrypted agent conversation databases into the knowledge dimension.

---

## 1. 5D Scoring Model

### 1.1 Dimension Decomposition

The upstream Anamnesis provides 4D recall (semantic, temporal, relational, strategic). DiVo-Anamnesis introduces the 5th dimension — **knowledge** — extending the scoring function:

$$\mathcal{S}_{5D}(q, m) = \underbrace{\sum_{d \in \mathcal{D}_4} w_d \cdot s_d(q, m)}_{\text{upstream 4D}} + \underbrace{w_k \cdot s_k(q, m)}_{\text{DiVo knowledge}}$$

where $\mathcal{D}_4 = \{\text{semantic}, \text{temporal}, \text{relational}, \text{strategic}\}$ and $\sum w_d + w_k = 1$.

| Dimension | Weight (default) | Source | Origin |
|-----------|-----------------|--------|--------|
| Semantic | 0.25 | pgvector | Upstream 4D |
| Temporal | 0.15 | PostgreSQL | Upstream 4D |
| Relational | 0.15 | Entity graph | Upstream 4D |
| Strategic | 0.25 | Weight field | Upstream 4D |
| **Knowledge** | **0.20** | **OpenSearch** | **DiVo extension** |

### 1.2 Reciprocal Rank Fusion

Each dimension produces an independent ranked list. The final score uses Reciprocal Rank Fusion (RRF):

$$\text{RRF}(m) = \sum_{d \in \mathcal{D}} w_d \cdot \frac{1}{K + \text{rank}_d(m)}$$

where $K = 60$ (standard RRF constant) and $\text{rank}_d(m)$ is the rank of memory $m$ in dimension $d$.

### 1.3 Strategic Weight Computation

The strategic dimension score combines multiple signals:

$$s_{\text{strat}}(m) = \alpha_{\text{auth}}(m) \cdot \text{confidence}(m) \cdot \log(1 + \text{access\_count}(m)) \cdot \text{decay}(m)$$

Authority coefficients:

| Authority Level | $\alpha_{\text{auth}}$ | Source |
|----------------|----------------------|--------|
| Explicit | 8.0 | User/planner direct decision |
| System | 2.0 | Automated extraction |
| Inferred | 1.0 | AI-inferred pattern |

Decay function:

$$\text{decay}(m) = \begin{cases} 1.0 & \text{if } \Delta t < T_{\text{grace}} \\ e^{-\lambda(\Delta t - T_{\text{grace}})} & \text{otherwise} \end{cases}$$

where $T_{\text{grace}} = 90$ days and $\lambda$ controls decay rate.

---

## 2. Knowledge Federation Layer

### 2.1 Hybrid Search Architecture

The knowledge dimension performs BM25 + neural vector search via OpenSearch:

$$\mathcal{S}_{\text{hybrid}}(q, d) = \beta \cdot \mathcal{S}_{\text{BM25}}(q, d) + (1 - \beta) \cdot \mathcal{S}_{\text{neural}}(q, d)$$

where $\beta = 0.3$ (keyword weight) by default, configurable per query.

### 2.2 Automatic Fallback Chain

```
Hybrid (BM25 + neural) ──failure──▶ Pure BM25 ──failure──▶ Empty result
         │                                │
    requires: neural plugin          requires: OpenSearch only
    + search_pipeline                + standard index
```

### 2.3 Multi-Index Federation

Knowledge search supports cross-index retrieval:

$$\mathcal{S}_{\text{knowledge}}(q) = \bigcup_{i \in \mathcal{I}} \text{search}_i(q)$$

where $\mathcal{I}$ is the set of configured OpenSearch indices (filtered by prefix `divo-*`).

---

## 3. IDE Session Bridge

### 3.1 Encrypted Database Decryption

The IDE session bridge extracts agent conversation data from encrypted SQLCipher databases:

$$\text{DB}_{\text{decrypted}} = \text{SQLCipher}(\text{DB}_{\text{encrypted}}, K_{\text{proc}})$$

where $K_{\text{proc}}$ is obtained by scanning the IDE agent process memory at runtime.

### 3.2 Dual-Layer Memory Representation

Extracted sessions are indexed in two layers:

| Layer | Format | Content | Use Case |
|-------|--------|---------|----------|
| L1 (Core) | Markdown | User queries + AI summaries | Lightweight recall |
| L2 (Detail) | JSON | Full message history | On-demand deep retrieval |

### 3.3 Incremental Indexing with Deduplication

Sessions are indexed using `session_id` as document ID, ensuring idempotent re-indexing:

$$\text{doc\_id} = \text{hash}(\text{session\_id})$$

Only sessions with `updated_at` newer than the last indexed timestamp are re-processed.

---

## 4. Hook Architecture

### 4.1 Lifecycle Hooks

The system provides a hook registry for injecting custom logic at operation boundaries:

| Hook Point | Trigger | Use Case |
|-----------|---------|----------|
| `pre_retain` | Before memory storage | Content validation, enrichment |
| `post_retain` | After memory storage | Audit logging, notification |
| `pre_recall` | Before retrieval | Query rewriting, access control |
| `post_recall` | After retrieval | Result augmentation, audit |
| `on_startup` | Application start | Module initialization |
| `on_shutdown` | Application stop | Cleanup, backup |

### 4.2 Hook Execution Model

Hooks execute sequentially within a hook point. Context is passed as a mutable dict:

$$\text{context}_{i+1} = h_i(\text{context}_i)$$

If hook $h_i$ raises an exception, it is logged and skipped — no cascade failure.

---

## 5. API Surface

### 5.1 Core 5D Recall Endpoint

```
POST /api/v1/divo/recall
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bank` | string | required | Memory bank name |
| `query` | string | required | Natural language query |
| `limit` | int | 10 | Max results |
| `dimension_weights` | object | see §1.1 | Override dimension weights |
| `knowledge_indices` | list\|null | null | OpenSearch indices to search |
| `knowledge_only` | bool | false | Skip local memories |

### 5.2 Response Structure

```json
{
  "memories": [
    {
      "id": "uuid-or-docid",
      "content": "...",
      "content_type": "fact|event|knowledge",
      "score": 0.85,
      "dimension_scores": {
        "semantic": 0.12,
        "temporal": 0.05,
        "relational": 0.0,
        "strategic": 0.15,
        "knowledge": 0.53
      },
      "is_knowledge": false,
      "source_index": ""
    }
  ],
  "total_candidates": 25,
  "knowledge_hits": 3,
  "retrieval_time_ms": 120.5
}
```

### 5.3 Session Bridge Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/divo/session/start` | POST | Recall recent context + detect cold start |
| `/divo/session/end` | POST | Retain handoff summary for next session |
| `/divo/knowledge/search` | POST | Direct OpenSearch hybrid search |
| `/divo/knowledge/status` | GET | OpenSearch connection health |
| `/divo/knowledge/indices` | GET | List available knowledge indices |
| `/divo/ide/status` | GET | IDE scraper health check |

---

## 6. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    DiVo-Anamnesis 5D Engine                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Upstream Anamnesis 4D (unchanged)            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐ │   │
│  │  │Semantic  │  │Temporal  │  │Relational│  │Strat-│ │   │
│  │  │(pgvector)│  │(PG index)│  │(Entity   │  │egic  │ │   │
│  │  │          │  │          │  │ Graph)   │  │(Wt)  │ │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──┬───┘ │   │
│  │       └──────────────┴──────┬───────┴─────────┘      │   │
│  │                    RRF Fusion (K=60)                   │   │
│  └──────────────────────────┬────────────────────────────┘   │
│                             │                                  │
│  ┌──────────────────────────┼────────────────────────────┐   │
│  │     DiVo Extension: 5th Dimension (Knowledge)         │   │
│  │  ┌─────────────────┐  ┌──────────────────────┐       │   │
│  │  │  OpenSearch      │  │  IDE Session Bridge  │       │   │
│  │  │  ┌─────┐┌──────┐│  │  ┌─────┐  ┌───────┐  │       │   │
│  │  │  │BM25 ││Neural││  │  │SQL  │  │Indexer│  │       │   │
│  │  │  │     ││Vector││  │  │Cipher│  │       │  │       │   │
│  │  │  └──┬──┘└──┬───┘│  │  └──┬──┘  └───┬───┘  │       │   │
│  │  │     └──┬────┘    │  │     │         │      │       │   │
│  │  │   Hybrid Search  │  │  Decrypt + Dedup     │       │   │
│  │  └────────┬─────────┘  └─────────┬────────────┘       │   │
│  └───────────┼──────────────────────┼─────────────────────┘   │
│              │                      │                          │
│              └──────────┬───────────┘                          │
│               5D RRF Fusion (4D + Knowledge)                  │
│                         │                                      │
│                    Ranked Results                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Upstream Compatibility

DiVo-Anamnesis extends the open-source Anamnesis without modifying upstream code:

| Component | Upstream (4D) | DiVo Extension (5D) |
|-----------|--------------|---------------------|
| Storage | PostgreSQL + pgvector | + OpenSearch indices |
| Retrieval | 4D RRF | + Knowledge dimension RRF |
| Embedding | sentence-transformers | Shared (same model) |
| API | `/api/v1/recall` | + `/api/v1/divo/recall` |
| Hooks | None | HookRegistry with 6 hook points |
| IDE Integration | None | SQLCipher decrypt + auto-index |

Extension mechanism: Python import + FastAPI middleware injection via `patch_app()`. Upstream codebase remains a read-only git submodule.

---

*DiVo Gen²AI | Agent Infrastructure*
*June 2026*
