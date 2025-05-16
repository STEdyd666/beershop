from flask import g, current_app
from pymongo import MongoClient, errors
import sys
import logging
logger = logging.getLogger()


def connect_to_database():
    # get config
    config = current_app.config.get('CONFIG')

    # connect to db
    client = MongoClient(
        host=config.database['host'],
        port=config.database['port'], 
        serverSelectionTimeoutMS=config.database['timeout']
    )

    # test connection
    try:
        client.is_mongos
    except errors.ServerSelectionTimeoutError as err:
        logger.error(f"Failed to connect to database. \n({err})")
        sys.exit(1)
    
    return client

def get_db():
    if 'db' not in g:
        g.db = connect_to_database()

    return g.db