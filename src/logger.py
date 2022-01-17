# -----------------* Code-Based From *-----------------
# https://shian420.pixnet.net/blog/post/350291572-%5Bpython%5D-logging-幫你紀錄任何訊息
# -----------------------------------------------------
# --------------------* reference *--------------------
# https://titangene.github.io/article/python-logging.html
# https://www.w3schools.com/python/gloss_python_date_format_codes.asp
# https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
# -----------------------------------------------------

import logging
import os
import pathlib
import colorama
import toml

from datetime import datetime
from colorama import Fore, Back, Style
from colorlog import ColoredFormatter

color_log = toml.load(f"{os.getcwd()}/config.toml").get("color_log")
dir_path = os.getcwd() # logs path
filename = "{:%d-%m-%Y}".format(datetime.now()) + ".log"
log_colors={
			"DEBUG":"white",
			"INFO":"cyan",
			"OK":"green",
			"WARNING":"yellow",
			"ERROR":"red",
			"CRITICAL":"MAGENTA",
		}

# Example:
# log.debug("A quirky message only developers care about")
# log.info("Curious users might want to know this")
# log.warning("Something is wrong and any user should be informed")
# log.error("Serious stuff, this is red for a reason")
# log.critical("OH NO everything is on fire")

# ---------------* main *---------------
def add_logging_level(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present 

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # credit: http://stackoverflow.com/q/2183233/2988730, especially
    # credit: http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

def create_logger(logFolder = ""):
	# config
    logging.captureWarnings(True) # catch py waring message
    formatter_file = logging.Formatter("%(asctime)s   |  %(levelname)-8s | %(message)s",
        datefmt="%d-%m-%Y %I:%M:%S %p%z")
    formatter_console_color = ColoredFormatter(" %(asctime)s   |  %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s",
        datefmt="%d-%m-%Y %I:%M:%S %p%z",
        log_colors=log_colors)
    formatter_console = logging.Formatter("%(asctime)s   |  %(levelname)-8s | %(message)s",
        datefmt="%d-%m-%Y %I:%M:%S %p%z")
    logger = logging.getLogger("py.warnings") # catch py waring message
    logger.setLevel(level=logging.DEBUG)

	# create new folder if not exist
    if logFolder != "" and not os.path.exists(dir_path+logFolder):
        os.makedirs(dir_path+logFolder)

	# file handler
    fileHandler = logging.FileHandler(dir_path+logFolder+"/"+filename, "a", "utf-8")
    fileHandler.setFormatter(formatter_file)
    logger.addHandler(fileHandler)

	# console handler
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)
    if color_log:
        consoleHandler.setFormatter(formatter_console_color)
    else:
        consoleHandler.setFormatter(formatter_console)
    logger.addHandler(consoleHandler)

    return logger

# ---------------* initialization *---------------
colorama.init()
add_logging_level("OK", logging.INFO+1)
log = create_logger("\logs")
