import logging
import logging.handlers

logger = logging.getLogger('server_app')

formatter = logging.Formatter('%(asctime)s   %(levelname)s %(module)s :   %(message)s')

fh = logging.handlers.TimedRotatingFileHandler('server_app.log', 'midnight', backupCount=7, encoding='utf-8')
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)

logger.addHandler(fh)
logger.setLevel(logging.INFO)
