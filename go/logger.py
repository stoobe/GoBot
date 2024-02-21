from queue import SimpleQueue
import asyncio
import logging
import logging.handlers

import _config

is_logger_setup = set()

dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('{asctime}.{msecs:03.0f}  {levelname:<8}  {name:<14} -- {message}', dt_fmt, style='{')

def create_logger(logger_name: str = __name__):
    logger = logging.getLogger(logger_name)
    if logger_name not in is_logger_setup:
        logger.setLevel(_config.logging_level)  # Log messages at INFO level and above
        console_handler = logging.StreamHandler()
        # formatter = logging.Formatter(
        #     "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        # )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        is_logger_setup.add(logger_name)
    return logger

    # queue = SimpleQueue()
    # queue_handler = logging.handlers.QueueHandler(queue)
    # listener = logging.handlers.QueueListener(
    #     queue,
    #     logging.StreamHandler(),
    #     # logging.FileHandler('app.log'),
    # )
    # logger = logging.getLogger('main')
    # logger.setLevel(logging.INFO)  # Log messages at INFO level and above
    # logger.addHandler(queue_handler)
    # return logger