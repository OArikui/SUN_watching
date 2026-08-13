from pathlib import Path


def get_parents(base_file: str | Path = __file__, point: str = "") -> Path:
    marker_name = "MARKER_" + point
    current = Path(base_file).resolve()

    if current.is_file():
        current = current.parent

    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists() or (parent / marker_name).exists():
            return parent

    return current.parent
