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

COMFIG_ROOT=Path(__file__).parent

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
	config=json_loader(CONFIG_JSON_PATH)
except:
	logger.error("__failed loading config from json")


#   for bury the empty,prepare defult json

try:
	default_config=json_loader(DEFAULT_JSON_PATH)
	logger.info("__sucessful default_config")
except:
	logger.warn("__failed loading default_config")


default_outline=json_loader(OUTLINE_JSON_PARH)
def industrial(config_json:dict,default_json:dict,default_outline_json:dict)->dict:
	"no desc,no empty"
	buried_no_desc={}

	for hk,hv in default_outline.items():
		try:
			parent_config=config[hk]
		except KeyError:
			logger.debug(f"__found not {hk},use default value")
			buried_no_desc[hk]=default_config[hk]
			continue

		data_h1={}
		for hhk,hhv in hv.items():
			try:
				current_config=parent_config[hhk]
			except KeyError:
				logger.debug(f"__found not {hk}>{hhk},use default value")
				data_h1[hhk]=default_config[hk][hhk]
				continue
			data_h2={}
			for k in hhv:
				if k.endswith("-desc"):
					continue
				try:
					data_h2[k]=current_config[k]
				except:
					data_h2[k]=default_config[hk][hkk][k]
			data_h1[hhk]=data_h2
		buried_no_desc[hk]=data_h1
	return buried_no_desc
# part3 if saving or loading failed,suggesting func1 to user(or error and finish process)

# part3 else styling parameters as a argument

# (find_west:from find_west_setting import parameters)
