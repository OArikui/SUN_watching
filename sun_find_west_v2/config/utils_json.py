import json
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


def json_loader(filepath: Path) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.exception("JSON format error")
        raise
    except FileNotFoundError:
        logger.exception("File not found")
        raise


def json_saver(data: dict, filepath: Path) -> dict:
    logger.info(f"Saving JSON to {filepath}")
    try:
        if not filepath.parent.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {filepath.parent}")

        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        sha256_file(filepath)

        logger.info(f"JSON saved successfully: {filepath}")
        return data
    except Exception:
        logger.exception(f"Failed to save JSON: {filepath}")
        raise


def sha256_file(filepath: Path, save: bool = True) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    hashV = h.hexdigest()

    if save:
        savepath = filepath.parent / f"{filepath.name}_valid"
        with open(savepath, "w", encoding="ascii") as f:
            f.write(hashV)
    return hashV


def sha256_valid(filepath: Path) -> bool:
    actual = sha256_file(filepath, False)
    expect_path = Path(str(filepath) + "_valid")
    if expect_path.exsist:
        with open(expect_path, "r", encoding="ascii") as f:
            expected = f.read()
    else:
        expected = None
    return actual == expected
