# 🚧 rag-llm-api-pipeline — Roadmap

---

## 🔧 Core Enhancements

- [ ] Automatically respect `force_rebuild_index: true` in YAML to rebuild FAISS index on startup
- [ ] Add optional batching and token limit controls for long context handling in `llm_wrapper.py`
- [ ] Add robust error handling and logging for CLI and API endpoints
- [ ] Support per-system overrides for LLM/embedding model in `system.yaml`

---

## 🧠 ML/Model Improvements

- [ ] Add support for quantized models (e.g., GGUF with llama.cpp or ctransformers backend)
- [ ] Allow configuration of GPU usage per model (e.g., mixed CPU/GPU inference)
- [ ] Abstract model loading to allow switching between Hugging Face, local `.gguf`, or LoRA adapters
- [ ] Add offline model caching utility script

---

## 🛠️ CLI & API Features

- [ ] Add CLI command to list all indexed systems from YAML
- [ ] Add CLI to delete/rebuild index on demand
- [ ] Add API endpoint to trigger index rebuild
- [ ] Return metadata with API results (source filenames, doc types, etc.)

---

## 📦 Packaging & Deployment

- [ ] Create a `Dockerfile` for fully portable deployment
- [ ] Add optional `Makefile` or `build.sh` for local setup/testing
- [ ] Add GitHub Actions CI/CD for linting, testing, PyPI publishing

---

## 📁 File & Media Support

- [ ] Add YAML support for pre-chunking text (chunk size, overlap)
- [ ] Add image captioning or tagging (for more than just OCR)
- [ ] Add speaker diarization for audio and video
- [ ] Support splitting video into scenes for multi-chunk answers

---

## 📚 Usability & Documentation

- [ ] Add Swagger/OpenAPI tags and descriptions to FastAPI endpoints
- [ ] Add examples of `curl`/`Postman` usage for API in README
- [ ] Add configuration schema validation (e.g., `pydantic` or `Cerberus`)
- [ ] Provide sample `system.yaml` and test dataset in repo
- [ ] Add a `quickstart.md` guide

---

## 🧪 Testing & Observability

- [ ] Add unit tests for `loader.py` multimodal coverage
- [ ] Add integration tests for end-to-end query flow
- [ ] Add CLI test coverage via `subprocess` or `click.testing`
- [ ] Add telemetry hooks (opt-in) for usage analytics in enterprise deployments

---

## 🤝 Community & Feedback

- [ ] Add issue templates and contribution guide
- [ ] Add roadmap visualization (e.g., GitHub Projects or Notion)
- [ ] Create discussions board or feedback form

---

## 🪜 Priority Levels

- [P1] Must-have for robustness or first release polish  
- [P2] Nice-to-have, improves usability or flexibility  
- [P3] Exploratory or longer-term enhancements

---

