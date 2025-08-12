# 📜 Changelog

All notable changes to this project will be documented in this file.  
This project adheres to [Semantic Versioning](https://semver.org/).

---
## [0.7.1] - 2025-08-12
###Added
    _StopOnSequences now:
        Converts all stop_sequences to lowercase and trims whitespace during initialization.
        Performs lowercase, whitespace-trimmed matching during generation.
###Changed
    Matching is now case-insensitive:
        "Answer:" matches "answer:", "ANSWER:", "Answer:" etc.
    Matching ignores leading/trailing whitespace in both the stop sequence and model output.
    Still matches only when the entire stop phrase appears at the end of the decoded text buffer.
###Removed
    None — fully backward-compatible; existing YAML still works without changes.


## [0.7.0] - 2025-08-11
-Stabilize device handling (no Accelerate conflict): model uses device_map="auto"; pipeline not passed device on CUDA.
-Safe truncation: trims context only, preserves Question + Answer:.
-Decoding presets via llm.preset (baseline|beam|explore|drafts) with auto‑clean of invalid sampling args.
-Retriever: cached SentenceTransformer + optional L2 normalization (retriever.normalize_embeddings) with .normflag.
-System.yaml - Improved the context enforcement with stricter guidelines to pass to the retriever and wrapper with additional
-Decoding presets via llm.preset (baseline, beam, explore, drafts), with auto-removal of invalid sampling args.
-Compatible with temperature/top_p/top_k when do_sample: true


## [0.6.0] - 2025-08-10
- **Included default web UX for testing if custom website is not built - packaged with pip**
- **changlog now included in pypi**
- **server.py is updated to handle runtime assembly**
- **JSONValue variable is removed due to recursion issues and response model handling is fixed**


## [0.5.1] - 2025-08-10

###Changed
- **formatting and code readibility following lint and ruff checks**
- **type consistency and additional security checks with bandit**
- **minor bug fixes**


## [0.5.0] - 2025-08-08
### Added
- **Telemetry toggles in YAML**:  
  `settings.show_query_time`, `settings.show_token_speed`, `settings.show_chunk_timing`.
- **Token speed & latency** across CLI/API/Web:  
  Tokens/sec, gen token count, generation time, total query time.
- **Chunk-level timing**:
  - Query: embed time, FAISS search time, context stitching time.
  - Index build: per-file load/parse timing, batched embedding time, FAISS write time.
- **Minimal web UI refresh**:
  - Centered card layout, system fonts, subtle 3-dot “Thinking…” animation.  
  - Enter-to-submit, stats panel, retrieved chunk metadata.
- **Harmony (OpenAI gpt-oss) optional path**:  
  `models.use_harmony: true` + prompt rendering via Harmony when using openai/gpt-oss models.
- **Memory/allocator knobs** in YAML (`models.memory_strategy`):
  - `use_expandable_segments` → sets `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
  - `max_memory_gb` (optional cap).
- **Embedding batching** control for both build + query: `retriever.encode_batch_size`.
- **CLI**: periodic 10-second ticker while a query is running.

### Changed
- **Default LLM** → `Qwen/Qwen3-4B-Instruct-2507` (quality/VRAM sweet spot).
- **Embedding model moved under `retriever`** (fixes earlier ValueError when reading config).
- **Device handling**:
  - HF pipeline now receives a numeric device index (`-1` CPU / `0` GPU).
  - GPU uses `device_map="auto"`, CPU uses `device_map=None`, preventing `accelerate` device type errors.
- **Anti-repetition defaults** in YAML: `repetition_penalty: 1.05`, `no_repeat_ngram_size: 4`, `return_full_text=False`.

### Fixed
- Frequent **“device must be an int / accelerate device”** errors by standardizing device selection and pipeline args.
- Reduced **output loops/echoing prompts** via repetition penalties + no-repeat n-gram + prompt guardrails.

### Docs
- Updated `README.md` with:
  - New **system.yaml** layout and parameter explanations.
  - How to toggle telemetry + memory behavior.
  - Notes on Harmony usage and model switching.

### Migration notes
- Move your embedding model to:
  ```yaml
  retriever:
    embedding_model: sentence-transformers/all-MiniLM-L6-v2


## [0.2.0] - 2025-07-22

### ✨ Added
- **New CLI flags:**
  - `--show-chunks`: Display retrieved document chunks for transparency
  - `--list-data`: List all ingested documents for a system
  - `--precision [fp32|fp16|bf16]`: Run model inference at a lower precision for GPU efficiency
- **Web UI:**
  - Added lightweight `webapp/index.html` served by API
  - Allows users to query the system from a browser
- **QUICKSTART.md:**
  - Step-by-step instructions to set up, index, and query

### 🛠️ Changed
- Updated `system.yaml`:
  - `precision` field added for model precision
  - Data directory now single-level (`data/manuals`) with auto-discovery
- Updated `loader.py`:
  - Cleaner multimodal loader with better error handling
- Updated `retriever.py`:
  - Auto-discovers files in `data_dir` without requiring explicit `docs` list
- Updated `llm_wrapper.py`:
  - Supports lower precision (`fp16`/`bf16`)
  - Safer truncation of long prompts


- Better error messages on missing configs and models

---


## [0.1.0] - 2025-05
_(initial release)_
