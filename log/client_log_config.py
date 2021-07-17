import logging
 
logging.basicConfig(
    filename = "client_app.log",
    format = "%(asctime)s   %(levelname)s %(module)s :   %(message)s",
    level = logging.INFO
)
