from unittest.mock import MagicMock

from utils.artifact_store import ArtifactStore, ArtifactStoreConfig


def test_local_store_saves_json(tmp_path):
    cfg = ArtifactStoreConfig(mode="local", base_dir=tmp_path)
    store = ArtifactStore(cfg)
    rel = "json/test.json"
    payload = {"hello": "world"}

    path = store.save_json(relative_path=rel, document=payload)

    assert path.exists()
    assert path.read_text(encoding="utf-8").startswith("{")


def test_local_store_saves_file(tmp_path):
    cfg = ArtifactStoreConfig(mode="local", base_dir=tmp_path)
    store = ArtifactStore(cfg)
    src = tmp_path / "source.txt"
    src.write_text("example", encoding="utf-8")

    dest = store.save_file(relative_path="raw/source.txt", source=src)
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "example"


def test_remote_store_uses_client(monkeypatch, tmp_path):
    cfg = ArtifactStoreConfig(
        mode="s3",
        bucket="demo-bucket",
        endpoint="https://minio.local",
        base_dir=tmp_path,
        prefix="tenantA",
    )
    fake_client = MagicMock()
    monkeypatch.setattr("utils.artifact_store._build_remote_client", lambda config: fake_client)
    monkeypatch.setattr("utils.artifact_store.DEFAULT_LOCAL_BASE", tmp_path, raising=False)

    store = ArtifactStore(cfg)
    store.save_json(relative_path="json/doc.json", document={"ok": True})

    assert fake_client.put_object.called
    kwargs = fake_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "demo-bucket"
    assert kwargs["Key"] == "tenantA/json/doc.json"
    assert kwargs["Body"]
