from queue import SimpleQueue
import asyncio
import logging
import logging.handlers


is_logger_setup = set()

def create_logger(logger_name: str = __name__):
    logger = logging.getLogger(logger_name)
    if logger_name not in is_logger_setup:
        logger.setLevel(logging.INFO)  # Log messages at INFO level and above
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
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