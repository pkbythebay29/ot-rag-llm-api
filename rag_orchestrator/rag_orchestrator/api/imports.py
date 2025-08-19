import importlib.util
def is_installed(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is not None