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
# func1 setting the parameter with GUI

# part2 saving parameter json from txtfile and load the json.(if not __name__=="__main__")

#   for bury the empty,prepare defult json

# part3 if saving or loading failed,suggesting func1 to user(or error and finish process)

# part3 else styling parameters as a argument

# (find_west:from find_west_setting import parameters)
