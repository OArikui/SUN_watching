import logging
from pathlib import Path

import utils_json

logger = logging.getLogger(__name__)


def reset_json(jsonpath: Path, schemapath: Path) -> dict:
    "reset to schema"
    schema = utils_json.json_loader(schemapath)

    if schema.get("type") != "object" or "properties" not in schema:
        msg = "_ENG_スキーマの形式が適切ではありません (ルートは 'properties' を持つ 'object' である必要があります)"
        logger.error(f"{msg}")
        raise ValueError(msg)

    def get_default_properties(child: dict) -> dict:
        son = {}
        for k, v in child.items():
            if v["type"] == "object":
                value = get_default_properties(v["properties"])
                son[k] = value
            else:
                son[k] = v["default"]
                son[k + "-desc"] = v["description"]

        return son

    try:
        data = get_default_properties(schema["properties"])
    except Exception as e:
        logger.error(f"_ENG_スキーマの解析中にエラーが発生しました: {e}")
        raise

    utils_json.json_saver(data=data, filepath=jsonpath)

    return data


def reset_text(jsonpath: Path, textpath: Path) -> str:
    "reset to default json"

    data = utils_json.json_loader(jsonpath)

    txt = ""
    for hk, hv in data.items():
        txt += f"==={hk}===\n"
        for hhk, hhv in hv.items():
            txt += f"---{hhk}---\n"
            for k, v in hhv.items():
                if k.endswith("-desc"):
                    continue
                desc_key = k + "-desc"
                d = hhv[desc_key]
                if len(k) < 10:
                    k += " " * (10 - len(k))
                v = str(v)
                if len(v) < 5:
                    v += " " * (5 - len(v))
                txt += f"{k} : {v}  /{d}\n"

    if not textpath.parent.exists():
        textpath.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {textpath.parent}")

    with open(textpath, "w", encoding="utf-8") as f:
        f.write(txt)

    return txt


def generate_outlines(outlinepath: Path, defaultpath: Path) -> dict:
    "generate outlines based on default json"
    data = utils_json.json_loader(defaultpath)

    outline = {}

    for hk, hv in data.items():
        ls_h2 = {}
        for hhk, hhv in hv.items():
            ls_h2[hhk] = list(hhv.keys())
        outline[hk] = ls_h2

    return utils_json.json_saver(data=outline, filepath=outlinepath)


CONFIG_TEXT_PATH = Path("config/config/config.txt")
CONFIG_JSON_PATH = Path("config/cache/config.json")
DEFAULT_JSON_PATH = Path("config/cache/default_config.json")
OUTLINE_JSON_PARH = Path("config/cache/default_outline.json")
CONFIG_SCHEMA_PATH = Path("config/schema/config_schema.json")
print("OUTLINE_JSON_PARH =", OUTLINE_JSON_PARH.resolve())

reset_json(DEFAULT_JSON_PATH, CONFIG_SCHEMA_PATH)
reset_text(DEFAULT_JSON_PATH, CONFIG_TEXT_PATH)
generate_outlines(OUTLINE_JSON_PARH, DEFAULT_JSON_PATH)
