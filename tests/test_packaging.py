import importlib
from pathlib import Path


def test_packaged_defaults_bootstrap_into_runtime_home(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_home = tmp_path / "krionis-home"
    monkeypatch.setenv("KRIONIS_HOME", str(runtime_home))
    monkeypatch.delenv("KRIONIS_CONFIG_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    import rag_llm_api_pipeline.config_loader as config_loader

    config_loader = importlib.reload(config_loader)
    cfg = config_loader.load_config()

    assert (
        Path(config_loader.get_config_path()) == runtime_home / "config" / "system.yaml"
    )
    assert (runtime_home / "config" / "system.yaml").exists()
    assert (runtime_home / "data" / "manuals" / "sample.txt").exists()
    assert cfg["settings"]["data_dir"] == str(
        (runtime_home / "data" / "manuals").resolve()
    )
    assert cfg["retriever"]["index_dir"] == str((runtime_home / "indices").resolve())


def test_orchestrator_bridge_falls_back_to_pipeline_runtime_config(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_home = tmp_path / "krionis-home"
    monkeypatch.setenv("KRIONIS_HOME", str(runtime_home))
    monkeypatch.delenv("KRIONIS_CONFIG_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    import rag_llm_api_pipeline.config_loader as config_loader
    from rag_orchestrator.api.config_bridge import resolve_system_yaml

    config_loader = importlib.reload(config_loader)
    expected = Path(config_loader.get_config_path()).resolve()
    resolved = Path(
        resolve_system_yaml(
            system=None,
            systems_root=str(tmp_path / "missing-systems"),
            fallback_yaml=str(tmp_path / "missing.yaml"),
        )
    ).resolve()

    assert resolved == expected
