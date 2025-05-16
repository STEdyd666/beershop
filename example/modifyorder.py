import requests


# define username
username = 'user'

# define new order
order = {
    "id": "0068",
    "quantity": 3
}

# define payload
payload = {'order': order}

# make post request
r = requests.post('https://beershop.fastsolutions.top/order/user/000001/modify', json=payload)

print(r.text)
