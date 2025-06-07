# CLI tool for querying
import argparse
from ..retriever import get_answer
from ..retriever import build_index
import yaml
import os

CONFIG_PATH = "config/system.yaml"

def load_system_config(system_name: str) -> list[str]:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    for asset in config.get("assets", []):
        if asset["name"].lower() == system_name.lower():
            doc_paths = [os.path.join("data/manuals", p) for p in asset.get("docs", [])]
            return doc_paths
    raise ValueError(f"System '{system_name}' not found in config.")


def main():
    parser = argparse.ArgumentParser(description="Ask questions against an industrial system knowledge base.")
    parser.add_argument("--system", required=True, help="System name defined in config YAML.")
    parser.add_argument("--question", required=True, help="The question to ask.")
    parser.add_argument("--build-index", action="store_true", help="Rebuild index from scratch.")

    args = parser.parse_args()

    docs = load_system_config(args.system)

    if args.build_index:
        print(f"Building index for system: {args.system}")
        build_index(args.system, docs)

    print(f"Querying system '{args.system}': {args.question}")
    answer, sources = get_answer(args.system, args.question)

    print("\n🧠 Answer:\n", answer)
    print("\n📚 Sources used:\n")
    for i, chunk in enumerate(sources):
        print(f"--- Chunk {i+1} ---\n{chunk.strip()[:300]}\n")

if __name__ == "__main__":
    main()
