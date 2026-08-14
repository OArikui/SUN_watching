import json
import logging
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

        logger.info(f"JSON saved successfully: {filepath}")
        return data
    except Exception:
        logger.exception(f"Failed to save JSON: {filepath}")
        raise
