import requests


# define username
username = 'user'

# define new order
order = {
    "id": "0068",
    "quantity": 4
}

# define payload
payload = {'order': order}

# make post request
r = requests.post('https://beershop.fastsolutions.top/order/user/new', json=payload)

print(r.text)
