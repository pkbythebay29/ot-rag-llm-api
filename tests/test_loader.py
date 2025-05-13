import os
from rag_llm_api_pipeline.loader import load_docs

def test_load_text_file():
    test_file = "rag_llm_api_pipeline/data/manuals/test.txt"
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, "w") as f:
        f.write("This is a test document. It should be chunked properly.")
    
    chunks = load_docs(test_file)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
