
# ✅ rag-llm-api-pipeline — Roadmap 

---

## 🔧 Core Enhancements

- [x] Automatically respect `force_rebuild_index: true` in YAML to rebuild FAISS index on startup
- [x] Add robust error handling and logging for CLI and API endpoints
- [x] Support per-system overrides for LLM/embedding model in `system.yaml`
- [x] Support listing indexed chunks (`list_indexed_data`)
- [ ] Add optional batching and token limit controls for long context handling in `llm_wrapper.py` (P2)

---

## 🧠 ML/Model Improvements

- [x] Add precision configuration via YAML (`fp32`, `fp16`, `bf16`)  
- [x] Add support for using CPU or GPU via YAML (`use_cpu`)
- [ ] Abstract model loading to support Hugging Face, OpenAI, or Harmony APIs (flexible backend)
- [ ] Add support for quantized models (e.g., GGUF with llama.cpp or ctransformers backend) (P2)
- [ ] Allow per-model GPU/CPU fallback configuration (P2)
- [ ] Add offline model caching utility script (P3)

---

## 🛠️ CLI & API Features

- [x] Add CLI command to list all indexed systems and number of chunks
- [] Add timing metrics to CLI (prints every 10s and total time on answer)
- [] Return timing and sources metadata with CLI/API result
- [] Add API timer: time to respond for each query
- [x] Add optional flags for showing retrieved chunks (`--show-chunks`)
- [x] Add endpoint & CLI to rebuild index based on YAML
- [ ] Add richer metadata return (doc types, filenames, size) (P2)

---

## 📦 Packaging & Deployment

- [x] Update PyPI package with all features
- [x] Added `quickstart.md` with instructions and pip install
- [ ] Create a `Dockerfile` for fully portable deployment (P1)
- [ ] Add `Makefile` or `build.sh` for quick builds (P2)
- [ ] Add GitHub Actions for tests/lint/CI/CD (P2)

---

## 📁 File & Media Support

- [x] Multimodal loader: supports text, PDF, image (OCR), audio, video
- [x] Automatically loads all files in `data_dir` if `docs` list is empty
- [ ] YAML control for chunk size / overlap (P2)
- [ ] Add image captioning (not just OCR) (P3)
- [ ] Add speaker diarization for long audio (P3)
- [ ] Add video scene splitting for long content (P3)

---

## 📚 Usability & Documentation

- [x] `quickstart.md` added to root with steps
- [x] Improved `README.md` with pip install, API, CLI, website usage
- [x] Provide sample `system.yaml` and test config in repo
- [ ] Add Swagger/OpenAPI docs to FastAPI (P2)
- [ ] Add curl/Postman examples in README (P2)
- [ ] Add config schema validation via `pydantic` or similar (P2)

---

## 🧪 Testing & Observability

- [ ] Add unit tests for `loader.py` multimodal formats (P1)
- [ ] Add CLI test coverage using `subprocess` or `click.testing` (P1)
- [ ] Add integration tests for API + CLI + index + LLM (P1)
- [ ] Add opt-in telemetry/analytics for usage stats (P3)

---

## 🖥️ Web UI

- [x] Added minimal HTML/JS web UI (`index.html`)
- [x] Hooks into FastAPI backend
- [x] Displays answer, chunks, on screen
- [ ] Add copy-to-clipboard or export button (P3)
- [ ] Improve styling and branding (P2)

