import logging

logger = logging.getLogger('bgm')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | [%(module)s.%(funcName)s] %(message)s')

log_file = 'bgm.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
