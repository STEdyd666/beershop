def test_items_type(client):
    response = client.get("/items")
    data = response.json
    
    # check that items must be a list
    assert isinstance(data, list), f"'items' json response must be a list, found {type(data)}"

def test_insert_neworder(client):
    # define new order
    order = {
        "id": "0001",
        "quantity": 3
    }

    # define payload
    payload = {'order': order}

    # make post request
    response = client.post('/order/user/new', json=payload)
    data = response.json
    
    # check len of order id
    assert len(data['message']) == 6