import flask
from flask import Blueprint, current_app, jsonify, request
from datetime import datetime, timezone
import pymongo
import logging
logger = logging.getLogger()

from beershop.utils.db import get_db


# Blueprint Configuration
api_bp = Blueprint(
    'api_bp', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/beershop.api.static'
)

# get list of items
@api_bp.route('/items', methods=['GET'])
def getitems() -> flask.Response:
    """Returns list of all items"""
    # parse request
    style = request.args.get('style')
    name = request.args.get('name')
    
    # get db client
    dbclient = get_db()
    
    # get config
    config = current_app.config.get('CONFIG')

    # get database
    db = dbclient[config.database['name']]

    # set filter on name and style
    if name is not None and style is not None:
        filt = {
            '$text': {'$search': name},
            '$text': {'$search': style},
        }
    elif name is not None:
        filt = {
            '$text': {'$search': name},
        }
    elif style is not None:
        filt = {
            '$text': {'$search': style},
        }
    else:
        filt = {}

    # get documents matching filters
    docs_stylesearch = db['items'].find(
        filt, 
        {'_id': False}
    )

    # conver to list
    docs_stylesearch = list(docs_stylesearch)

    return jsonify(list(docs_stylesearch))

# get single item providing an id
@api_bp.route('/item/<iditem>', methods=['GET'])
def getitem(iditem: str) -> flask.Response:
    """Returns a single item giving an ID"""    
    # get db client
    dbclient = get_db()
    
    # get config
    config = current_app.config.get('CONFIG')

    # get database
    db = dbclient[config.database['name']]

    # get documents matching filters
    doc = db['items'].find_one(
        {'id': iditem},
        {'_id': False}
    )
    
    return jsonify(doc)

# create a new order
@api_bp.route('/order/<username>/new', methods=['POST'])
def neworder(username: str) -> flask.Response:
    """Create a new order"""    
    # get db client
    dbclient = get_db()
    
    # get config
    config = current_app.config.get('CONFIG')

    # get database
    db = dbclient[config.database['name']]

    # get collection
    collection_orders = db['orders']
    
    # get post json data
    data = request.json
    
    # check availability in stock
    order = data.get('order')
    if order is None:
        message = "Wrong order format. Expected 'order' key"
        logger.error(message)
        return message

    iditem = order.get('id')
    if iditem is None:
        message = "Wrong order format. Expected 'id' key"
        logger.error(message)
        return jsonify({'message': message})

    quantity = order.get('quantity')
    if iditem is None:
        message = "Wrong order format. Expected 'quantity' key"
        logger.error(message)
        return jsonify({'message': message})

    # get collection of items
    collection_items = db['items']

    # check stock availability
    item = collection_items.find_one(
        {'id': iditem}
    )

    if item is None:
        return jsonify({'message': f'{iditem} not found.'})

    if item['instock'] == 0:
        return jsonify({'message': "Out of stock"})

    if item['instock'] < quantity:
        return jsonify({'message': f'Items in stock not sufficient for the requested order. Available: {item['instock']}.'})

    # create new order id starting from the latest order
    orders = collection_orders.find(
        {}, 
        {'_id': False}
    ).sort('id', pymongo.DESCENDING).limit(1)
    
    # convert cursor to list
    orders = list(orders)

    if not orders:
        idorder = f'{1:06d}'
    else:
        lastorderid = orders[0]['id']
        idorder = f'{int(lastorderid) + 1:06d}'

    # create a new order
    order = {
        'type': 'new',
        'id': idorder,
        'order': data['order'],
        'user': username,
        'creationtime': datetime.now(timezone.utc),
        'nmodified': 0,
        'lastmodified': None,
        'status': 'processing',
        'laststatuschange': datetime.now(timezone.utc)
    }

    # add new order to orders
    collection_orders.insert_one(order)

    # add new order to queue 
    collection_queue = db['orderqueue']
    collection_queue.insert_one(order)

    return jsonify({'message': idorder})

# delete an order
@api_bp.route('/order/<username>/<idorder>/delete', methods=['GET'])
def deleteorder(username: str, idorder: str) -> flask.Response:
    """Delete an order"""    
    # get db client
    dbclient = get_db()
    
    # get config
    config = current_app.config.get('CONFIG')

    # get database
    db = dbclient[config.database['name']]

    # get collection
    collection_orders = db['orders']
    collection_items = db['items']

    # check the existence of the order
    order = collection_orders.find_one(
        {
            'id': idorder,
            'user': username
        },
        {'_id': False}
    )

    if not order:
        message = f'Order {idorder} not found'
        logger.info(message)
        return jsonify({'message': message})

    if order['status'] == 'deleted':
        message = f'Order {idorder} already cancelled'
        logger.info(message)
        return jsonify({'message': message})

    # create a new order for the queue
    deleteorder = {
        'type': 'delete',
        'id': idorder,
        'order': order['order'],
        'user': username,
        'creationtime': order['creationtime'],
        'nmodified': order['nmodified'] + 1,
        'lastmodified': datetime.now(timezone.utc),
        'status': 'processing',
        'laststatuschange': datetime.now(timezone.utc)
    }
    
    # add new order to queue 
    collection_queue = db['orderqueue']
    collection_queue.insert_one(deleteorder)

    message = f'Order {idorder} deleted'
    logger.info(message)

    return jsonify({'message': message})

# modify order
@api_bp.route('/order/<username>/<idorder>/modify', methods=['POST'])
def modifyorder(username:str, idorder: str) -> flask.Response:
    """Modify order
    
    An order can be modified only when status is either 'processing' or 'confirmed'. It cannot be
    modified when the status is 'paid', 'delivered', 'deleted'.

    The only possibile modification is a reduction of the item quantity.

    Args:
        username: username associated to the order. 
        idorder: id of the order. Example: 000001.

    Returns:
        flask jsonified response with the status of the modification request

    """    
    # get db client
    dbclient = get_db()
    
    # get config
    config = current_app.config.get('CONFIG')

    # get database
    db = dbclient[config.database['name']]

    # get collection
    collection_orders = db['orders']

    # get post json data
    data = request.json
    
    # check availability in stock
    order = data.get('order')
    if order is None:
        message = "Wrong order format. Expected 'order' key"
        logger.error(message)
        return jsonify({'message': message})

    iditem = order.get('id')
    if iditem is None:
        message = "Wrong order format. Expected 'id' key"
        logger.error(message)
        return jsonify({'message': message})

    quantity = order.get('quantity')
    if iditem is None:
        message = "Wrong order format. Expected 'quantity' key"
        logger.error(message)
        return jsonify({'message': message})

    # check the status of the order
    order = collection_orders.find_one(
        {
            'id': idorder,
            'user': username
        },
        {'_id': False}
    )

    if not order:
        message = f'Order {idorder} not found'
        logger.info(message)
        return jsonify({'message': message})

    if order['status'] not in ['processing', 'confirmed']:
        message = (
            f"The order {idorder} cannot be modified. An order can be modified only when status is"
            f"either 'processing' or 'confirmed'. Current status {order['status']}"
        )
        logger.info(message)
        return jsonify({'message': message})

    if iditem != order['order']['id']:
        message = f"The id item differs from the initial order. You can only modify the quantity."
        logger.info(message)
        return jsonify({'message': message})

    if quantity >= order['order']['quantity']:
        message = f"The new quantity can only be reduced from the initial order. Initial order quantity ({order['order']['quantity']}. Request: {quantity})"
        logger.info(message)
        return jsonify({'message': message})

    # get collection of items
    collection_items = db['items']

    # check stock availability
    item = collection_items.find_one(
        {'id': iditem}
    )

    if item['instock'] == 0:
        return {'message': f"Item {iditem} out of stock"}

    if item['instock'] < quantity:
        return {'message': f'Items in stock not sufficient for the requested order ({quantity}). Available: {item['instock']}.'}
    
    # create a new order for the queue
    modifiedorder = {
        'type': 'modify',
        'id': idorder,
        'order': data['order'],
        'user': username,
        'creationtime': order['creationtime'],
        'nmodified': order['nmodified'] + 1,
        'lastmodified': datetime.now(timezone.utc),
        'status': 'processing',
        'laststatuschange': datetime.now(timezone.utc)
    }

    # add modify order to queue 
    collection_queue = db['orderqueue']
    collection_queue.insert_one(modifiedorder)
    
    message = f'Order {idorder} modified'
    logger.info(message)

    return jsonify({'message': message})

# get an order by id
@api_bp.route('/order/<username>/<idorder>/get', methods=['GET'])
def getorderbyid(username: str, idorder: str) -> flask.Response:
    """Get order by id"""    
    # get db client
    dbclient = get_db()
    
    # get config
    config = current_app.config.get('CONFIG')

    # get database
    db = dbclient[config.database['name']]

    # get collection
    collection_orders = db['orders']

    # get order
    order = collection_orders.find_one(
        {
            'id': idorder,
            'user': username
        },
        {'_id': False}
    )

    if not order:
        message = f'Order {idorder} not found'
        logger.info(message)
        return jsonify({'message': message})

    return jsonify({'message': order})
    
# get orders with filters
@api_bp.route('/orders/<username>', methods=['GET'])
def getorders(username: str) -> flask.Response:
    """Get all orders"""    
    # get db client
    dbclient = get_db()
    
    # get config
    config = current_app.config.get('CONFIG')

    # get database
    db = dbclient[config.database['name']]

    # get collection
    collection_orders = db['orders']

    # get request search parameters
    start = request.args.get('start')
    end = request.args.get('end')
    status = request.args.get('status')

    # convert start and end to datetime
    if start is not None:
        try:
            starttime = datetime.fromisoformat(start)
        except (TypeError, ValueError):
            message = f'Wrong format passed to start. The only supported format is ISOFORMAT. Provided {start}'
            logger.error(message)
            return jsonify({'message': message})
    else:
        starttime = None

    if end is not None:
        try:
            endtime = datetime.fromisoformat(end)
        except (TypeError, ValueError):
            message = f'Wrong format passed to start. The only supported format is ISOFORMAT. Provided {end}'
            logger.error(message)
            return jsonify({'message': message})
    else:
        endtime = None

    # set up filter on date
    if starttime is not None and endtime is not None:        
        filterdatetime = {
            'creationtime': {'$gte': starttime, '$lt': endtime}
        }
    elif start is not None:
        filterdatetime = {
            'creationtime': {'$gte': starttime}
        }
    elif end is not None:
        filterdatetime = {
            'creationtime': {'$lt': endtime}
        }
    else:
        filterdatetime = {}

    # set up filter on status
    if status is not None:
        filterstatus = {'status': status}
    else:
        filterstatus = {}

    # filter user
    filteruser = {'user': username}

    # merge filters
    filters = {
        **filterdatetime,
        **filterstatus,
        **filteruser
    }

    # get order
    orders = collection_orders.find(
        filters,
        {'_id': False}
    )

    return jsonify(list(orders))