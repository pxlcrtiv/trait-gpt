"""Tests for the shared HF cache completeness helper."""

from trait_gpt.hf_cache import model_cached


def test_missing_marker_not_cached(tmp_path) -> None:
    assert not model_cached(tmp_path / "nope", "pytorch_model.bin")


def test_partial_download_not_cached(tmp_path) -> None:
    marker = tmp_path / "hub" / "models--x"
    (marker / "snapshots" / "partial").mkdir(parents=True)
    (marker / "snapshots" / "partial" / "pytorch_model.bin.incomplete").write_text("x")
    assert not model_cached(marker, "pytorch_model.bin")


def test_committed_weights_cached(tmp_path) -> None:
    marker = tmp_path / "hub" / "models--x"
    snap = marker / "snapshots" / "final"
    snap.mkdir(parents=True)
    (snap / "pytorch_model.bin").write_bytes(b"weights")
    assert model_cached(marker, "pytorch_model.bin")



def test_weights_plus_incomplete_rejected(tmp_path) -> None:
    marker = tmp_path / "hub" / "models--x"
    snap = marker / "snapshots" / "final"
    snap.mkdir(parents=True)
    (snap / "pytorch_model.bin").write_bytes(b"weights")
    (snap / "pytorch_model.bin.incomplete").write_text("x")
    assert not model_cached(marker, "pytorch_model.bin")


def test_empty_snapshot_dir_not_cached(tmp_path) -> None:
    marker = tmp_path / "hub" / "models--x"
    (marker / "snapshots" / "empty").mkdir(parents=True)
    assert not model_cached(marker, "pytorch_model.bin")
