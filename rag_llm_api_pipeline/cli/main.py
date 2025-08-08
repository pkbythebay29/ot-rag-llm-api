# rag_llm_api_pipeline/cli/main.py
import argparse
import sys
import os
import threading
import time
import yaml

from rag_llm_api_pipeline.retriever import build_index, get_answer, list_indexed_data
from rag_llm_api_pipeline.config_loader import load_config

CONFIG_PATH = "config/system.yaml"


def _save_precision_override(precision: str):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}

    cfg.setdefault("llm", {})
    cfg.setdefault("models", {})
    cfg["models"]["model_precision"] = precision
    cfg["llm"]["precision"] = precision  # legacy compatibility

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"[INFO] Set precision -> {precision} in {CONFIG_PATH}")


def _ticker(start_ts: float, stop_flag: list[bool]):
    while not stop_flag[0]:
        elapsed = time.time() - start_ts
        print(f"[⏱️] Still running... {elapsed:.1f}s elapsed")
        time.sleep(10)


def main():
    parser = argparse.ArgumentParser(description="RAG CLI")
    parser.add_argument("--system", required=True, help="System name")
    parser.add_argument("--question", help="Ask a question")
    parser.add_argument("--build-index", action="store_true", help="Build index")
    parser.add_argument("--serve", action="store_true", help="Run API server")
    parser.add_argument("--list-data", action="store_true", help="List indexed data")
    parser.add_argument("--precision", choices=["fp32", "fp16", "bfloat16", "bf16"],
                        help="Override model precision (persisted to config/system.yaml)")
    parser.add_argument("--hide-sources", action="store_true",
                        help="Hide printing retrieved source chunks")
    parser.add_argument("--no-ticker", action="store_true", help="Disable 10s progress ticker")
    args = parser.parse_args()

    cfg = load_config()

    if args.precision:
        prec = "bf16" if args.precision == "bfloat16" else args.precision
        _save_precision_override(prec)

    if args.build_index:
        try:
            report = build_index(args.system)
            if isinstance(report, dict) and report:
                print("\n[Build Index Report]")
                for k in ["total_sec", "embed_sec", "index_write_sec", "num_chunks"]:
                    if k in report:
                        print(f"  {k}: {report[k]}")
                if report.get("load_parse"):
                    print("  load_parse per file:")
                    for it in report["load_parse"]:
                        base = f"    - {it.get('file','?')}: {it.get('chunks',0)} chunks, {it.get('sec',0)}s"
                        if it.get("error"):
                            base += f" (ERROR: {it['error']})"
                        print(base)
        except Exception as e:
            print(f"[ERROR] build-index failed: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.list_data:
        try:
            list_indexed_data(args.system)
        except Exception as e:
            print(f"[ERROR] list-data failed: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.serve:
        try:
            try:
                from rag_llm_api_pipeline.api.server import start_api_server
                start_api_server()
            except ImportError:
                import uvicorn
                uvicorn.run("rag_llm_api_pipeline.api.server:app", host="0.0.0.0", port=8000, reload=False)
        except Exception as e:
            print(f"[ERROR] serve failed: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.question:
        show_qt = cfg.get("settings", {}).get("show_query_time", True)
        show_ts = cfg.get("settings", {}).get("show_token_speed", True)
        show_ct = cfg.get("settings", {}).get("show_chunk_timing", True)

        start = time.time()
        stop = [False]
        ticker = None
        if not args.no_ticker:
            ticker = threading.Thread(target=_ticker, args=(start, stop), daemon=True)
            ticker.start()

        try:
            answer, chunks, stats = get_answer(args.system, args.question)
        except Exception as e:
            stop[0] = True
            if ticker:
                ticker.join()
            print(f"[ERROR] query failed: {e}")
            sys.exit(1)

        stop[0] = True
        if ticker:
            ticker.join()

        print("\nAnswer:\n")
        print(answer or "(no answer)")
        print()

        # Stats
        parts = []
        if show_qt and "query_time_sec" in stats:
            parts.append(f"Query Time: {stats['query_time_sec']}s")
        if show_ts and "tokens_per_sec" in stats:
            parts.append(
                f"Token Speed: {stats['tokens_per_sec']} tok/s "
                f"({stats.get('gen_tokens', 0)} tokens in {stats.get('gen_time_sec', 0)}s)"
            )
        if show_ct and "retrieval" in stats:
            r = stats["retrieval"]
            parts.append(
                f"Retrieval: embed={r.get('embed_query_sec','?')}s, "
                f"search={r.get('faiss_search_sec','?')}s, stitch={r.get('context_stitch_sec','?')}s"
            )
        if parts:
            print("[Stats] " + " | ".join(parts))

        # ALWAYS show sources unless suppressed
        if not args.hide_sources and isinstance(chunks, list):
            print("\nSources:\n")
            for i, ch in enumerate(chunks, 1):
                print(f"[{i}] {ch[:500]}...\n")

        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
