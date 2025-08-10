
from rag_llm_api_pipeline.retriever import get_answer

def test_get_answer():
    system_yaml = "rag_llm_api_pipeline/config/system.yaml"
    with open(system_yaml, "w") as f:
        f.write("assets:\\n  - name: TestAsset\\n    docs:\\n      - manuals/test.txt")
    
    answer, sources = get_answer("TestAsset", "What is this about?")
    assert isinstance(answer, str)
    assert isinstance(sources, list)
    assert len(sources) > 0
