# 📜 Changelog

All notable changes to this project will be documented in this file.  
This project adheres to [Semantic Versioning](https://semver.org/).

---

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
