# Main package init — can be empty or expose core methods if desired
from .retriever import get_answer as get_answer, build_index as build_index

__all__ = ["get_answer", "build_index"]
