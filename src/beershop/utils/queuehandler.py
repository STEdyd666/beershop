from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time
from datetime import datetime, timezone
from pymongo import MongoClient
import pymongo
import sys
import logging
logger = logging.getLogger()


@dataclass
class QueueHandler:
    """Class to manage the queue of orders
    
    Args:
        database: configuration of the database
        polling: time in seconds between every check on queue for new documents

    """
    _QUEUE_COLLECTION = 'orderqueue'
    _ORDERS_COLLECTION = 'orders'
    _ITEMS_COLLECTION = 'items'

    database: DatabaseConfig
    polling: int

    def listen(self, starttime: Optional[datetime] = None):
        """Listen to new documents
        
        Args:
            starttime: whether to start processing orders from a specific datetime.

        """
        # connect to db
        client = MongoClient(
            host=self.database['host'],
            port=self.database['port'], 
            serverSelectionTimeoutMS=self.database['timeout']
        )

        # test connection
        try:
            client.is_mongos
        except errors.ServerSelectionTimeoutError as err:
            logger.error(f'Failed to connect to database. \n({err})')
            sys.exit(1)

        # get collection of queued orders
        db = client[self.database['name']]
        collection_queue = db[self._QUEUE_COLLECTION]

        # filter by starttime
        if starttime is not None:
            filterstarttime = {'creationtime': {'$gt': starttime}}
        else:
            filterstarttime = {'creationtime': {'$gt': datetime.now(timezone.utc)}}
        
        # get collection of orders and items
        collection_orders = db[self._ORDERS_COLLECTION]
        collection_items = db[self._ITEMS_COLLECTION]

        # get tailable cursor
        cursor = collection_queue.find(
            filterstarttime,
            cursor_type=pymongo.CursorType.TAILABLE_AWAIT
        )

        # listen to changes
        logging.info('Listening to orders...')
        while cursor.alive:
            try:
                order = cursor.next()

                # check stock availability
                item = collection_items.find_one(
                    {
                        'id': order['order']['id'],
                    },
                    {'id': False}
                )
                
                match order['type']:
                    case 'new':
                        if item['instock'] == 0:
                            # set status of order as cancelled
                            collection_orders.update_one(
                                {
                                    'id': order['id'],
                                    'user': order['user']
                                },
                                {'$set': 
                                    {
                                        'status': 'canceled',
                                        'laststatuschange': datetime.now(timezone.utc)
                                    },
                                }
                            )
                            logger.info(f"Order {order['id']} canceled because item out of stock.")

                        if item['instock'] < order['order']['quantity']:
                            # set status of order as cancelled
                            collection_orders.update_one(
                                {
                                    'id': order['id'],
                                    'user': order['user']
                                },
                                {'$set': 
                                    {
                                        'status': 'canceled',
                                        'laststatuschange': datetime.now(timezone.utc)
                                    },
                                }
                            )
                            logger.info(f"Order {order['id']} canceled because items in stock are not sufficient for the requested order.")

                        # confim order if the quantity is sufficient
                        collection_orders.update_one(
                            {
                                'id': order['id'],
                                'user': order['user']
                            },
                            {'$set': 
                                {
                                    'status': 'confirmed',
                                    'laststatuschange': datetime.now(timezone.utc)
                                }
                            }
                        )
                        logger.info(f"Order {order['id']} confirmed.")

                        # change stock quantity
                        newstockquantity = item['instock'] - order['order']['quantity']
                        collection_items.update_one(
                            {
                                'id': order['order']['id'],
                            },
                            {'$set': {'instock':newstockquantity}}
                        )
                        logger.info(f"Stock of item {order['order']['id']} updated after order {order['id']} from {item['instock']} to {newstockquantity}.")

                    case 'modify':
                        # get initial order
                        initialorder = collection_orders.find_one(
                            {
                                'id': order['id'],
                                'user': order['user']
                            },
                            {'_id': False}
                        )

                        # update order
                        collection_orders.update_one(
                            {
                                'id': order['id'],
                                'user': order['user']
                            },
                            {'$set': 
                                {
                                    'type': 'modify',
                                    'status': 'confirmed',
                                    'laststatuschange': datetime.now(timezone.utc),
                                    'nmodified': order['nmodified'] + 1,
                                    'lastmodified': datetime.now(timezone.utc),
                                    'order': order['order']                                  
                                }
                            }
                        )

                        logger.info(f"Order {order['id']} modified.")

                        # update stock quantity
                        increasestock = initialorder['order']['quantity'] - order['order']['quantity']
                        newstockquantity = item['instock'] + increasestock
                        collection_items.update_one(
                            {
                                'id': order['order']['id'],
                            },
                            {'$set': {'instock': newstockquantity}}
                        )
                        logger.info(f"Stock of item {order['order']['id']} updated after order {order['id']} modification from {item['instock']} to {newstockquantity}.")
                    
                    case 'delete':
                        # set order status as delete
                        collection_orders.update_one(
                            {
                                'id': order['id'],
                                'user': order['user']
                            },
                            {'$set': 
                                {
                                    'type': 'delete',
                                    'status': 'deleted',
                                    'laststatuschange': datetime.now(timezone.utc),
                                    'nmodified': order['nmodified'] + 1,
                                    'lastmodified': datetime.now(timezone.utc),
                                    'order': order['order']                                  
                                }
                            }
                        )

                        # restore quantity in stock
                        newstockquantity = item['instock'] + order['order']['quantity']
                    
                        collection_items.update_one(
                            {
                                'id': order['order']['id'],
                            },
                            {'$set': {'instock': newstockquantity}}
                        )
                        logger.info(f"Stock of item {order['order']['id']} updated after order {order['id']} cancellation from {item['instock']} to {newstockquantity}.")
            except StopIteration:
                try:
                    time.sleep(self.polling)
                except KeyboardInterrupt:
                    logger.info('Queue handler stopped by the user.')
                    sys.exit()
            except KeyboardInterrupt:
                logger.info('Queue handler stopped by the user.')
                sys.exit()
            
