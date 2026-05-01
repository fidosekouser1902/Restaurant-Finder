from pathlib import Path

from recommender.common import paths


def test_project_root_contains_src_recommender():
    root = paths.project_root()
    assert (root / "src" / "recommender").is_dir()
    assert Path(paths.__file__).resolve().relative_to(root)


def test_project_hf_home_under_dot_cache():
    root = paths.project_root()
    h = paths.project_hf_home()
    assert h == root / ".cache" / "huggingface"
