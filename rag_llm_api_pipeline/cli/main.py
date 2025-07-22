# CLI tool for querying
import argparse, sys
from rag_llm_api_pipeline.retriever import build_index, get_answer, list_indexed_data
from rag_llm_api_pipeline.config_loader import load_config

def main():
    parser = argparse.ArgumentParser(description="RAG CLI")
    parser.add_argument("--system", required=True, help="System name")
    parser.add_argument("--question", help="Ask a question")
    parser.add_argument("--build-index", action="store_true", help="Build index")
    parser.add_argument("--serve", action="store_true", help="Run API server")
    parser.add_argument("--list-data", action="store_true", help="List indexed data")
    parser.add_argument("--show-chunks", action="store_true", help="Show retrieved chunks")
    parser.add_argument("--precision", choices=["fp32", "fp16", "bfloat16"], help="Override model precision")

    args = parser.parse_args()
    config = load_config()
    if args.precision:
        config["llm"]["precision"] = args.precision

    if args.build_index:
        build_index(args.system)
        sys.exit(0)

    if args.list_data:
        list_indexed_data(args.system)
        sys.exit(0)

    if args.serve:
        from rag_llm_api_pipeline.api.server import start_api_server
        start_api_server()
        sys.exit(0)

    if args.question:
        answer, chunks = get_answer(args.system, args.question)
        print(f"\nAnswer:\n{answer}\n")
        if args.show_chunks:
            print("Chunks:\n", "\n".join(chunks))
