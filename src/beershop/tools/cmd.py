import sys
import inspect
import argparse
import subprocess
import pandas as pd
import json
from datetime import datetime, timezone
import random
import os
import pymongo
from pymongo import MongoClient, errors
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from beershop.utils.config import Config
from beershop.utils.queuehandler import QueueHandler
from beershop import create_app
import beershop


def configure():
    """Command line option to configure the Beershop app
    
    This method initializes the database collection to handle the order queue.
    
    """
    parser = argparse.ArgumentParser(
        description=(
            'Configure the Beershop app. '
            'This method initializes the database collection to handle the order queue.'
        )
    )
    parser.add_argument('-nmax', dest='nmax', default=10000, help='Maximum number of orders (Default: 10000).')
    parser.add_argument('-size', dest='size', default=100000, help='Mazimum size of collection in bytes. (Default: 1MB)')
    parser.add_argument('-config', dest='config', help='Configuration file in yaml format.')
    parser.add_argument('-j', action='version')
    
    parser.version = beershop.__version__
    args = parser.parse_args()

    # read configuration file
    config = Config.load(args.config)

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
    
    # get collection of the stocks
    db = client[config.database['name']]
    
    # drop collection if there is any
    db['orderqueue'].drop()

    # create capped collection
    collection = pymongo.collection.Collection(
        db, 
        'orderqueue',
        capped=True, 
        max=args.nmax,
        size=args.size
    )

    # add a dummy order to start tailing the collection
    collection.insert_one(
        {
            'dummy': 'dummy'
        }
    )

    logger.info('Order queue created.')

def start():
    """Command line option for starting the Beershop application using the integrated webserver"""
    parser = argparse.ArgumentParser(description='Start the Beershop application using the integrated web server.')
    parser.add_argument('-config', dest='config', help='Configuration file in yaml format.')
    parser.add_argument('-j', action='version')

    parser.version = beershop.__version__
    args = parser.parse_args()
    
    # read configuration file
    config = Config.load(args.config)
    
    # start server
    app = create_app(config)
    app.run(debug=True, host='0.0.0.0', port=9666)

def initialize_testdb():
    """Command line option to inizialize the test DB for the Beershop application"""
    parser = argparse.ArgumentParser(description='Initialize the DB with the test data.')
    parser.add_argument('filename', help='Path to the input file in csv format. See the documentation on how to write this file.')
    parser.add_argument('-seed', dest='seed', default=1, help='Seed to be used when generating random numbers.')
    parser.add_argument('-config', dest='config', help='Configuration file in yaml format.')
    parser.add_argument('-j', action='version')

    parser.version = beershop.__version__
    args = parser.parse_args()
    
    # read configuration file
    config = Config.load(args.config)

    # read input file
    if not os.path.exists(args.filename):
        logger.error(f'Input file {args.filename} not found.')
        sys.exit(1)
    
    # check filename extension
    if not args.filename.endswith('.csv'):
        logger.error(f"Wrong format of input file. Provided {args.filename.split('.')[-1]}. Supported 'CSV'")
        sys.exit(1)

    # read input file
    df = pd.read_csv(args.filename)

    # set random seed to replicate results
    random.seed(1)
    
    # set the default number of limit out of stock. Evalutate whether to pass this value as argument
    limitoutofstock = 3

    # convert to lower letters style to simply later search
    df['Style'] = df['Style'].str.lower()

    # convert to list of dict and reduce size
    data = df.to_dict(orient='records')
    data = data[::16]

    # set current datetime in utc format
    today = datetime.now(timezone.utc)

    # create stocks
    items = list()
    for count, beer in enumerate(data):
        currentstock = {
            'id': f'{count + 1:04d}',
            'last_update': datetime.now(timezone.utc),
            'creation_time': datetime.now(timezone.utc),
            'instock': random.randrange(5, 50),
            'limitoutofstock': limitoutofstock,
            'content': beer,
            'unitprice': random.randrange(2, 10)
        }
        items.append(currentstock)
    
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
    
    # get collection of the stocks and orders
    collection_items = client[config.database['name']]['items']
    collection_orders = client[config.database['name']]['orders']

    # reset content
    collection_items.drop()
    collection_orders.drop()

    # add test stocks
    results = collection_items.insert_many(items)

    # create index on descriptions to allow mongodb text search
    collection_items.create_index(
        {
            'content.Style': 'text',
            'content.Description': 'text', 
            'content.Name': 'text'
        }
    )

    logger.info('Test database initalized successfully.')

def start_queuehandler():
    """Command line option to start the queue handler to process orders"""
    parser = argparse.ArgumentParser(description='Start the queue handler to process orders. Only order after the start of listener are processed.')
    parser.add_argument('-polling', dest='polling', default=1, help='Polling time in seconds between every check on queue for new documents.')
    parser.add_argument('-starttime', dest='starttime', help='Whether to start processing orders from a specific datetime. Supported format: ISOFORMAT')
    parser.add_argument('-config', dest='config', help='Configuration file in yaml format.')
    parser.add_argument('-j', action='version')

    parser.version = beershop.__version__
    args = parser.parse_args()
    
    # read configuration file
    config = Config.load(args.config)

    # initialize queue handler
    queuehandler = QueueHandler(
        config.database,
        args.polling,
    )

    # convert in python datetime
    if args.starttime is not None:
        starttime = datetime.fromisoformat(args.starttime)
    else:
        starttime = None

    # start listener
    queuehandler.listen(
        starttime
    )