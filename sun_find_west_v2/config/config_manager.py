# part1 importing modules
GUISET = False
if GUISET:
    logfile = f"logs/config_{datetime.datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s %(funcName)s: %(message)s",
        filename=logfile,
        filemode="a",
    )

logger = logging.getLogger(__name__)

CONFIG_TEXT_PATH=Path("config/config/config.txt")
CONFIG_JSON_PATH=Path("config/config/config.txt")
DEFAULT_JSON_PATH=Path("config/defaults/default_config.json")
OUTLINE_JSON_PARH=Path("config/defaults/default_outline.json")
CONFIG_SCHEMA_PATH=Path("config/schemas/config_schema.json")

from config.utils_json import json_saver,json_loader

def gem_config_json(textpath: Path, jsonpath: Path)->dict:
    if not textpath.exist():
        logger.error(f"file not found:{str(textpath)}")

	with open(textpath,"r",encoding="utf-8") as f:
		text=f.read().split("\n")

	stash={}
	data_h1={}
	data_h2={}
	h1=""
	h2=""
	for i,line in enumerate(text):
		if not line.headswith("---","==="):
			cleaned=""
			for c in line:
				if c == " ":
					continue
				cleaned+=c
			k,vd=tuple(cleaned.split(":"))
			v,d=tuple(vd.split("/"))
			stash[k]=v
			stash[k+"-desc"]=d
		if line.headswith("---") or i=len(text)-1:
			if stash:
				data_h2[h2]=stash
			h2=line.split("---")[1]
			stash={}
		if line.headswith("===") or i=len(text)-1:
			if data_h2:
				data_h1[h1]=data_h2
			h1=line.split("===")[1]
			data_h2={}
	return json_saver(data=data_h1,jsonpath=jsonpath)

# func1 setting the parameter with GUI

# part2 saving parameter json from txtfile and load the json.(if not __name__=="__main__")
try:
	data=gem_config_json(CONFIG_TEXT_PATH,CONFIG_JSON_PATH)
	logger.info("__sucessful jenelate json from text")
except (KeyError,ValueError):
	logger.exception("__config text not TEKISETU")
	logger.info("__try load parameter from config json")

try:
	logger.info("__loading config from json")
	data=json_loader(CONFIG_JSON_PATH)
except:
	logger.error("__failed loading config from json")
#   for bury the empty,prepare defult json

try:
	default_config=json_loader(DEFAULT_JSON_PATH)
	logger.info("__sucessful default_config")
except:
	logger.warn("__failed loading default_config")

no_desc={}

for hk,hv in :

# part3 if saving or loading failed,suggesting func1 to user(or error and finish process)

# part3 else styling parameters as a argument

# (find_west:from find_west_setting import parameters)
