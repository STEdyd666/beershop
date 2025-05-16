def test_items(mongodb):
    assert 'items' in mongodb.list_collection_names()
    item = mongodb.items.find_one(
        {'id': '0002'}
    )
    assert item['content']['Style'] == 'altbier'

def test_orders(mongodb):
    assert 'orders' in mongodb.list_collection_names()
    order = mongodb.orders.find_one(
        {'id': '000002'}
    )
    assert order['status'] == 'confirmed'