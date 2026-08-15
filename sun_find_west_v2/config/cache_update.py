import logging
from pathlib import Path

import utils_json

logger = logging.getLogger(__name__)


def generate_defaultJ_schemaJ(defaultpath: Path, schemapath: Path) -> dict:
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

    utils_json.json_saver(data=data, filepath=defaultpath)

    return data


def generate_configT_defaultJ(configpath: Path, textpath: Path) -> str:
    "reset to default json"

    data = utils_json.json_loader(configpath)

    txt = ""
    for hk, hv in data.items():
        txt += f"\n==={hk}===\n"
        for hhk, hhv in hv.items():
            txt += f"\n---{hhk}---\n"
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


def generate_outlinesJ_defaultJ(outlinepath: Path, defaultpath: Path) -> dict:
    "generate outlines based on default json"
    data = utils_json.json_loader(defaultpath)

    outline = {}

    for hk, hv in data.items():
        ls_h2 = {}
        for hhk, hhv in hv.items():
            ls_h2[hhk] = list(hhv.keys())
        outline[hk] = ls_h2

    return utils_json.json_saver(data=outline, filepath=outlinepath)


def generate_configJ_configT(textpath: Path, configpath: Path) -> dict:
    if not textpath.exists():
        logger.error(f"file not found:{str(textpath)}")

    with open(textpath, "r", encoding="utf-8") as f:
        text = f.read().split("\n")

    stash = {}
    data_h1 = {}
    data_h2 = {}
    h1 = ""
    h2 = ""
    for i, line in enumerate(text):
        if ":" in line[:3]:
            cleaned = ""
            for c in line:
                if c == " ":
                    continue
                cleaned += c
            k, vd = tuple(cleaned.split(":"))
            v, d = tuple(vd.split("/"))
            stash[k] = v
            stash[k + "-desc"] = d
        if line[:3] == "---":
            if stash:
                data_h2[h2] = stash
            h2 = line.split("---")[1]
            stash = {}
        if line[:3] == "===":
            if data_h2:
                data_h1[h1] = data_h2
            h1 = line.split("===")[1]
            data_h2 = {}
        if i == len(text) - 1:
            if stash:
                data_h2[h2] = stash
            if data_h2:
                data_h1[h1] = data_h2
    return json_saver(data=data_h1, filepath=configpath)


reset_json(DEFAULT_JSON_PATH, CONFIG_SCHEMA_PATH)
reset_text(DEFAULT_JSON_PATH, CONFIG_TEXT_PATH)
generate_outlines(OUTLINE_JSON_PARH, DEFAULT_JSON_PATH)
