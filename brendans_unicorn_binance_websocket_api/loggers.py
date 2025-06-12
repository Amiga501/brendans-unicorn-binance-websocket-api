# -*- coding: utf-8 -*-
"""
Created on Mon Dec 11 10:31:05 2023

@author: brendans1020

"""
# %% Global modules
from collections.abc import Callable
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import logging
import logging.config

import structlog
import sys



# %% Module level config

# Only used in LoggerOld
FORMATTER = logging.Formatter(
    "%(asctime)s thread:%(threadName)s level:%(levelname)s "
    "in %(module)s @line:%(lineno)-4d: %(message)s")


# %% Classes

# -----------------------------------------------------------------------------
class Logger():
    """
    Wrapper around the logging class with a few more useful methods
    """

    # -------------------------------------------------------------------------
    def __init__(self, *,
                 logger_name: str = None,
                 log_file: str = None,
                 log_level: str = "DEBUG",
                 ):
        """!
        Start a new logger instance

        @param [in] logger_name [str] The name of the logger
        @param [in] log_file [str] The name of the log file, leave empty for
            stream only
        @param [in] log_level [str] One of "DEBUG", "INFO", "WARNING", "ERROR"

        """
        log_levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
            }
        log_level_= log_levels.get(log_level) or logging.DEBUG

        timestamper = structlog.processors.TimeStamper(fmt="iso")

        dict_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "default": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                },
            }
        }
        handlers_ = ["default"]
        self.log_file_failure_msg = None
        if log_file:
            log_file = self.__create_log_file(log_file)

        if log_file:
            dict_config["handlers"]["file"] = {
                "level": "DEBUG",
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": log_file,
            }
            handlers_.append("file")

        dict_config["loggers"] = {
            "": {
                "handlers": handlers_,
                "level": "DEBUG",
                "propagate": True,
            },
        }

        logging.config.dictConfig(dict_config)

        structlog.configure(
            processors=[
                # Add callsite parameters.
                structlog.processors.CallsiteParameterAdder([
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    ],
                ),
                structlog.contextvars.merge_contextvars,
                structlog.dev.set_exc_info,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                timestamper,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            #wrapper_class=structlog.stdlib.BoundLogger,
            wrapper_class=structlog.make_filtering_bound_logger(log_level_),
            cache_logger_on_first_use=True,
        )

        # better to have too much log than not enough
        # May be changed later in get_logger()
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
            )
        self.logger = structlog.get_logger(logger_name)

        # with this pattern, it's rarely necessary to propagate the error up to
        # parent
        self.logger.propagate = False

        if self.log_file_failure_msg:
            self.logger.error(self.log_file_failure_msg)

    # -------------------------------------------------------------------------
    def __create_log_file(self, log_file: str) -> str:
        """!
        **Create a log file**

        @param [in] log_file [str] The proposed full file path of log file

        @return [str] the path of the actual log file, not necessarily the
            requested one!

        """
        if not Path(log_file).parent.is_dir():
            print("Invalid folder path specified for log file, will "
                  "attempt to create")
            if not Path(Path(log_file).drive).exists():
                self.log_file_failure_msg = (
                    "Unable to create log file at requested location, "
                    f"{log_file}, as drive doesn't exist', won't create log "
                    "file"
                    )
                log_file = None

            else:
                try:
                    Path(log_file.parent).mkdir(parents=True, exist_ok=True)
                except Exception as exception:
                    self.log_file_failure_msg = (
                        "Unable to create log file at requested location, "
                        f"{log_file}, due to {exception}, won't create log"
                        )
                    log_file = None

                try:
                    with open(log_file, "w") as f:
                        f.writelines(["\n"])
                        ...
                except Exception as exception:
                    self.log_file_failure_msg = (
                        "Unable to create log file at requested location, "
                        f"{log_file}, due to {exception}, won't create log"
                        )
                    log_file = None

        return log_file

    # -------------------------------------------------------------------------
    def __get_console_handler(self) -> Callable:
        """
        From: https://www.toptal.com/python/in-depth-python-logging

        @return [Callable]

        """
        console_handler = logging.StreamHandler(sys.stdout)

        return console_handler

    # -------------------------------------------------------------------------
    def __get_file_handler(self, log_file: str):
        """
        From: https://www.toptal.com/python/in-depth-python-logging

        @param [in] log_file [str] Full file path to the intended log file

        @return [Callable]

        """
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when='midnight')

        return file_handler

    # -------------------------------------------------------------------------
    def get_logger(self, *,
                   log_level: str = None,
                   ) -> Callable:
        """
        **Get handle to the logger instance**

        @param [in] log_level [str] Currently ignored

        """
        return self.logger

    # -------------------------------------------------------------------------
    def set_log_file(self, log_file: str):
        """
        Set the log file for the logger

        @param [in] log_file [str] Full file path to the intended log file

        """
        self.logger.addHandler(self.__get_file_handler(log_file))


# -----------------------------------------------------------------------------
class LoggerOld():
    """
    Wrapper around the logging class with a few more useful methods
    """

    # -------------------------------------------------------------------------
    def __init__(self, *,
                 logger_name=None,
                 log_file=None,
                 additional_levels=[]):
        """
        Start a new logger instance

        Params
        ------
        logger_name: <str> The name of the logger
        log_file: <str> The name of the log file, leave empty for stream only
        additional_Levels: <list> of <dict> {"name": <MUST BE CAPITALS>,
                                             "num": <int>}

        """
        # Add additional levels first so they are part of the parent logging
        # module
        if additional_levels:
            for level in additional_levels:
                self.__add_logging_level(level["name"], level["num"])

        self.logger = logging.getLogger(logger_name)
        # better to have too much log than not enough
        # May be changed later in get_logger()
        self.logger.setLevel("DEBUG")
        self.logger.addHandler(self.__get_console_handler())
        if log_file:
            self.logger.addHandler(self.__get_file_handler(log_file))

        # with this pattern, it's rarely necessary to propagate the error up to parent
        self.logger.propagate = False

    # -------------------------------------------------------------------------
    def __add_logging_level(self, levelName, levelNum, methodName=None):
        """
        From:
            https://stackoverflow.com/a/35804945/8722421

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
            #raise AttributeError('{} already defined in logging module'.format(methodName))
            # Already defined, ignore
            return
        if hasattr(logging, methodName):
            #raise AttributeError('{} already defined in logging module'.format(methodName))
            # Already defined, ignore
            return
        if hasattr(logging.getLoggerClass(), methodName):
            #raise AttributeError('{} already defined in logger class'.format(methodName))
            # Already defined, ignore
            return

        # This method was inspired by the answers to Stack Overflow post
        # http://stackoverflow.com/q/2183233/2988730, especially
        # http://stackoverflow.com/a/13638084/2988730
        def logForLevel(self, message, *args, **kwargs):
            if self.isEnabledFor(levelNum):
                self._log(levelNum, message, args, **kwargs)

        def logToRoot(message, *args, **kwargs):
            logging.log(levelNum, message, *args, **kwargs)

        logging.addLevelName(levelNum, levelName)
        setattr(logging, levelName, levelNum)
        setattr(logging.getLoggerClass(), methodName, logForLevel)
        setattr(logging, methodName, logToRoot)

    # -------------------------------------------------------------------------
    def __get_console_handler(self):
        """
        From: https://www.toptal.com/python/in-depth-python-logging
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMATTER)
        return console_handler

    # -------------------------------------------------------------------------
    def __get_file_handler(self, log_file):
        """
        From: https://www.toptal.com/python/in-depth-python-logging
        """
        file_handler = TimedRotatingFileHandler(log_file, when='midnight')
        file_handler.setFormatter(FORMATTER)
        return file_handler

    # -------------------------------------------------------------------------
    def get_logger(self):
        """
        From: https://www.toptal.com/python/in-depth-python-logging
        """
        return self.logger

    # -------------------------------------------------------------------------
    def set_log_file(self, log_file):
        """
        Set the log file for the logger
        """
        self.logger.addHandler(self.__get_file_handler(log_file))

    # -------------------------------------------------------------------------
    def set_log_level(self, log_level):
        """
        Set the level for the logger
        """
        if not hasattr(logging, log_level):
            print(f"{log_level} does not exist in logging module")
            return

        log_level_ = getattr(logging, log_level)
        try:
            self.logger.setLevel(log_level_)
        except:
            print(f"{log_level} could not be set in logger")


# -----------------------------------------------------------------------------
class UnicornHandlerLogger:
    """!
    **Create instance for cache logger**

    """

    # -------------------------------------------------------------------------
    def __init__(self):
        """!
        **Instance**
        """
        logger_ = Logger(
            logger_name="unicorn.handlers",
            log_level="WARNING",
            )
        self.logger = logger_.get_logger()