# Beershop

This project is a proof of concept of an API designed to handle orders, focused on keeping consistency of stock levels in the warehouse.

The dataset is a list of 200 beers, which includes details about name, style, description and can be found [here](https://www.kaggle.com/datasets/ruthgn/beer-profile-and-ratings-data-set) (the dataset has been reduced from 3197 to 200 for sake of simplicity, and the reduced version can be found in folder `example`).

The API can be tested at the following address: [beershop.fastsolutions.top/home](https://beershop.fastsolutions.top/home) or installed locally using the instructions reported below.

## Architecture

The backend is written in python using the Flask framework and uses MongoDB to store the data.

The architecture is based on three components:
- Flask server to serve the API.
- MongoDB to store the data.
- A deamon to handle orders.

The deamon is designed to handle all the orders sequentially, to avoid the case of multiple concurrent request that may break the consistency of stock levels of items.

The deamon is based on the combined use of a `capped` collection and a `tailable` cursor of MongoDB:
- A `capped` collection is a collection where documents are stored sequentially and they can only be inserted.
- A `tailable` cursor is a cursor that can be listened to like the `tail -f` utility command usually available on linux.

Every order is added in the queue of orders and processed one by one.

## Features

- Retrieval of list of items (beers) with search based on name, style and description.
- Possibility to create, modify, and delete orders.
- Automatic management of stock levels.
- Visualization of orders with search based on id and creation time.
- Possibility to order a flexible quantity of an item.
- Indication of the status of the order (`processing`, `confirmed`, etc)

## Current limitations

- No user management. (a login layer is necessary to implement this functionality).
- Possibility to include only one item for order.
- The only modification of an order is a reduction of the quantity of an item.
- The only supported status of orders is:
    - `processing`: state of the order before the final check on stock level.
    - `confirmed`: state of the order when the stock level has been checked and the availability of the item confirmed (ideally before the payment).
- No payment step. (this include the case of a failed payment).
- The search is limited on a text search based on exact name, style that may be present on name, style and description field.

## Enhancements

- Include efficient search algorithms (e.g ElasticSearch, Meilisearch).
- Allow multiple items in orders.
- Allow modification of items and full support on quantity variations.

# Getting started

## Prerequisite

Prerequisite:
- MongoDB .
- Python >= 3.10.

## Installation

Clone the repository and run inside the main package folder:
```bash
pip install .
```

**Remarks** It is suggested to use a virtual environment to install the package, to avoid possible conflicts of packages.

## Configuration

The application is configured throught a configuration file written in yaml format, that must be provided in the following way:
- Through the flag `-config` when starting the application from CMD or the enviroment variable `BEERSHOP_CONFIG`. (the priority is the command line argument first, than the environment variable).
- Through the environment variable only when deployed with an WSGI HTTP server (e.g `gunicorn`).

The configuration file includes up to now only the settings of the database:
```yaml
database:
  host: 127.0.0.1
  port: 27017
  name: beershop
  timeout: 5000
```

where:
- `host`: is the host/ip of the MongoDB instance.
- `port`: the port of the MongoDB instance (`27017` is the default).
- `name`: name of the database.
- `timeout`: time in milliseconds before raising an exception if the connection cannot be established.

## Before starting

The package provides two CMD entry points that are mandatory to be executed to run the application:
- `beershop-configure`: configure the collection necessary for the queue handler deamon to process orders.
- `beershop-initializetestdb`: initialized the DB with the dataset.

These two commands are available once the package is installed:

```bash
beershop-configure -h
```

```bash
usage: beershop-configure [-h] [-nmax NMAX] [-size SIZE] [-config CONFIG] [-j]

Configure the Beershop app. This method initializes the database collection to handle the order queue.

options:
  -h, --help      show this help message and exit
  -nmax NMAX      Maximum number of orders (Default: 10000).
  -size SIZE      Mazimum size of collection in bytes. (Default: 1MB)
  -config CONFIG  Configuration file in yaml format.
  -j              show program's version number and exit
```

```bash
beershop-initializetestdb -h
```

```bash
usage: beershop-initializetestdb [-h] [-seed SEED] [-config CONFIG] [-j] filename

Initialize the DB with the test data.

positional arguments:
  filename        Path to the input file in csv format. See the documentation on how to write this file.

options:
  -h, --help      show this help message and exit
  -seed SEED      Seed to be used when generating random numbers.
  -config CONFIG  Configuration file in yaml format.
  -j              show program's version number and exit
```

## How to run the app

The backend and the queue handler deamon must be run independently:
- `beershop-start -h` to start the backend.
- `beershop-start-queuehandler -h` to start the queue handler.

## Dataset

### Items

Each item in the dataset has this format:

```json
{
  "id": "0001",
  "last_update": {
    "$date": "2025-05-15T21:35:55.347Z"
  },
  "creation_time": {
    "$date": "2025-05-15T21:35:55.347Z"
  },
  "instock": 13,
  "limitoutofstock": 3,
  "content": {
    "Name": "Amber",
    "Style": "altbier",
    "Brewery": "Alaskan Brewing Co.",
    "Beer Name (Full)": "Alaskan Brewing Co. Alaskan Amber",
    "Description": "Notes:Richly malty and long on the palate, with just enough hop backing to make this beautiful amber colored \"alt\" style beer notably well balanced.\\t",
    "ABV": 5.3,
    "Min IBU": 25,
    "Max IBU": 50,
    "Astringency": 13,
    "Body": 32,
    "Alcohol": 9,
    "Bitter": 47,
    "Sweet": 74,
    "Sour": 33,
    "Salty": 0,
    "Fruits": 33,
    "Hoppy": 57,
    "Spices": 8,
    "Malty": 111,
    "review_aroma": 3.498994,
    "review_appearance": 3.636821,
    "review_palate": 3.556338,
    "review_taste": 3.643863,
    "review_overall": 3.847082,
    "number_of_reviews": 497
  },
  "unitprice": 3
}
```

Where:
- `id`: the id of the item defined as an incremental number codified as a four character string with padding zeros.
- `instock`: quantity of the item available in stock.
- `content`: info about the item like `name`, `style` and `description`. 

### Orders

Each order has this format:

```json
{
  "type": "new",
  "id": "000001",
  "order": {
    "id": "0006",
    "quantity": 1
  },
  "user": "user",
  "creationtime": {
    "$date": "2025-05-15T21:39:14.453Z"
  },
  "nmodified": 4,
  "lastmodified": {
    "$date": "2025-05-15T21:40:01.322Z"
  },
  "status": "deleted",
  "laststatuschange": {
    "$date": "2025-05-15T21:40:01.322Z"
  }
}
```

Where:
- `type`: is the order type. Either `new`, `modify`, `delete`. This keyword is used by the queue handler to process correctly the request.
- `id`: the id of the order defined as an incremental number codified as a six character string with padding zeros.
- `content`: content of the order with the id of the item and the quantity.
- `nmodified`: number that represent how many time the order has been modified.
- `lastmodified`: utc datetime in last modification.
- `status`: status of the order. Either `processing`, `confirmed`, `deleted`. Gives indications on how is going the purchase process.
- `laststatuschange`: utc datatime of last change in status.

## API description

Here are listed the full set of APIs exposed by the backend:
- `/items` [`GET`]: get the list of items. It supports the search keys `name` and `style` to filter on item `name`, `style` and `description`.
- `/item/<iditem>` [`GET`]: get a specific item giving the id of the item `iditem`.
- `/order/<username>/new` [`POST`]: create a new order for a specific user `username`. The data must be provided as json with the structure:
    ```json
    {
        "id": "0004",
        "quantity": 5
    }
    ```
    Where `id` is the id of an item and `quantity` is the requested quantity of the item.
- `/order/<username>/<idorder>/delete` [`GET`]: delete the order of the user `username` and the order id `idorder`.
- `/order/<username>/<idorder>/modify` ['POST']: modify an order of the user `username` and the order id `idorder`. 
    The data must be provided as json with the structure:
    ```json
    {
        "id": "0004",
        "quantity": 3
    }
    ```
- `/order/<username>/<idorder>/get` [`GET`]: get a specific order giving the user `username` and an id order `idorder`.
- `/orders/<username>` [`GET`]: get a list of order for the specific user `username`. It supports the search keys `start` and `end` to filter on the creation time of the order and the key `status` to filter by the order status.

## Examples

Here are listed some examples of the API. 

The `GET` requests are directly written as url, while `POST` requests are written as python scripts.

### How to get a list of items filtering by name and style

Request:

```
http://127.0.0.1:9666/items?name=imperial&style=ipa
```

Retrive all the items that have the keyword `imperial` and `ipa` in the name, style and description attribute.

Response:

```json
[
  {
    "content": {
      "ABV": 8.1,
      "Alcohol": 14,
      "Astringency": 19,
      "Beer Name (Full)": "Green Flash Brewing Co. Green Flash West Coast I.P.A.",
      "Bitter": 97,
      "Body": 31,
      "Brewery": "Green Flash Brewing Co.",
      "Description": "Notes:As craft beer pioneers, we embarked on an expedition to brew the benchmark West Coast IPA. We ventured into the unknown and struck gold, discovering a tantalizing menagerie of hops. Simcoe for tropical and grapefruit zest, Columbus for hop pungency, Centennial for pine notes, Citra for citrus zest and Cascade for floral aroma are layered throughout the brewing process. West Coast IPA\u00ae exemplifies the Green Flash spirit of adventure and discovery.95 IBUPrior to 2014 7.3% ABV2014 and later 8.1% ABV\\t",
      "Fruits": 76,
      "Hoppy": 139,
      "Malty": 45,
      "Max IBU": 100,
      "Min IBU": 65,
      "Name": "West Coast IPA",
      "Salty": 0,
      "Sour": 65,
      "Spices": 9,
      "Style": "ipa - imperial",
      "Sweet": 44,
      "number_of_reviews": 1286,
      "review_appearance": 4.110031,
      "review_aroma": 4.256998,
      "review_overall": 4.107698,
      "review_palate": 4.0521,
      "review_taste": 4.197512
    },
    "creation_time": "Mon, 12 May 2025 14:37:48 GMT",
    "id": "0059",
    "instock": 31,
    "last_update": "Mon, 12 May 2025 14:37:48 GMT",
    "limitoutofstock": 3,
    "unitprice": 7
  },
  {
    "content": {
      "ABV": 10.25,
      "Alcohol": 14,
      "Astringency": 23,
      "Beer Name (Full)": "Russian River Brewing Company Pliny The Younger",
      "Bitter": 73,
      "Body": 46,
      "Brewery": "Russian River Brewing Company",
      "Description": "Notes:Pliny the Younger, the man, was Pliny the Elder\u2019s nephew and adopted son. They lived nearly 2,000 years ago! Pliny the Elder is our Double IPA, so we felt it was fitting to name our Triple IPA after his son. It is almost a true Triple IPA with triple the amount of hops as a regular I.P.A. That said, it is extremely difficult, time and space consuming, and very expensive to make. And that is why we don\u2019t make it more often! This beer is very full-bodied with tons of hop character in the nose and throughout. It is also deceptively well-balanced and smooth.\\t",
      "Fruits": 49,
      "Hoppy": 106,
      "Malty": 19,
      "Max IBU": 100,
      "Min IBU": 65,
      "Name": "Pliny The Younger",
      "Salty": 0,
      "Sour": 40,
      "Spices": 4,
      "Style": "ipa - imperial",
      "Sweet": 29,
      "number_of_reviews": 610,
      "review_appearance": 4.482787,
      "review_aroma": 4.72377,
      "review_overall": 4.6,
      "review_palate": 4.612295,
      "review_taste": 4.72459
    },
    "creation_time": "Mon, 12 May 2025 14:37:48 GMT",
    "id": "0060",
    "instock": 5,
    "last_update": "Mon, 12 May 2025 14:37:48 GMT",
    "limitoutofstock": 3,
    "unitprice": 7
  }
]
```

### Hot to get a specific item

Request:

```
/item/0001
```

Retrive the item with id `0001`

Response:

```json
{
  "content": {
    "ABV": 5.3,
    "Alcohol": 9,
    "Astringency": 13,
    "Beer Name (Full)": "Alaskan Brewing Co. Alaskan Amber",
    "Bitter": 47,
    "Body": 32,
    "Brewery": "Alaskan Brewing Co.",
    "Description": "Notes:Richly malty and long on the palate, with just enough hop backing to make this beautiful amber colored \"alt\" style beer notably well balanced.\\t",
    "Fruits": 33,
    "Hoppy": 57,
    "Malty": 111,
    "Max IBU": 50,
    "Min IBU": 25,
    "Name": "Amber",
    "Salty": 0,
    "Sour": 33,
    "Spices": 8,
    "Style": "altbier",
    "Sweet": 74,
    "number_of_reviews": 497,
    "review_appearance": 3.636821,
    "review_aroma": 3.498994,
    "review_overall": 3.847082,
    "review_palate": 3.556338,
    "review_taste": 3.643863
  },
  "creation_time": "Mon, 12 May 2025 14:37:48 GMT",
  "id": "0001",
  "instock": 3,
  "last_update": "Mon, 12 May 2025 14:37:48 GMT",
  "limitoutofstock": 3,
  "unitprice": 3
}
```

### How to make a new order

Request:

```python
import requests


# define username
username = 'user'

# define new order
order = {
    "id": "0006",
    "quantity": 3
}

# define payload
payload = {'order': order}

# make post request
r = requests.post('http://127.0.0.1:9666/order/user/new', json=payload)

print(r.text)
```

This request make a new order of `3` items with id `0006`.

Response:

```json
{
  "message": "000013"
}
```

The response is the `id` of the order.

Output from the queue handler:

```bash
INFO:root:Order 000013 confirmed.
INFO:root:Stock of item 0006 updated after order 000013 from 36 to 33.
```

### How to modify an order

Requests:

```python
import requests


# define username
username = 'user'

# define new order
order = {
    "id": "0006",
    "quantity": 2
}

# define payload
payload = {'order': order}

# make post request
r = requests.post('http://127.0.0.1:9666/order/user/000013/modify', json=payload)

print(r.text)
```

This request modifies the quantity of the item `0006` of the order `000013` from 3 to 2.

Response:

```json
{
  "message": "Order 000011 modified"
}
```

Output from the queue handler:

```bash
INFO:root:Order 000013 modified.
INFO:root:Stock of item 0006 updated after order 000013 modification from 33 to 34.
```

### how to get a specific order

Request:

```
/order/user/000013/get
```

Retrive the order with id `000013`

Response:

```json
{
  "creationtime": "Thu, 15 May 2025 20:45:09 GMT",
  "id": "000013",
  "lastmodified": "Thu, 15 May 2025 20:46:24 GMT",
  "laststatuschange": "Thu, 15 May 2025 20:46:24 GMT",
  "nmodified": 2,
  "order": {
    "id": "0006",
    "quantity": 2
  },
  "status": "confirmed",
  "type": "modify",
  "user": "user"
}
```

### How to delete an order

Request:

```
/order/user/000013/delete
```

Delete the order with id `000013`

Response:

```json
{
  "message": "Order 000013 deleted"
}
```

### How to retrieve multiple orders

Request:

```
/orders/user?start=2025-05-15T22:45:00&end=2025-05-15T22:55:00&status=confirmed
```

Retrieve the orders created in the datetime range `[2025-05-15T22:45:00, 2025-05-15T22:55:00]` and status `confirmed`. Datetime are in UTC.

Response:

```json
[
  {
    "creationtime": "Thu, 15 May 2025 20:38:23 GMT",
    "id": "000012",
    "lastmodified": null,
    "laststatuschange": "Thu, 15 May 2025 20:42:07 GMT",
    "nmodified": 0,
    "order": {
      "id": "0005",
      "quantity": 3
    },
    "status": "confirmed",
    "type": "new",
    "user": "user"
  },
  {
    "creationtime": "Thu, 15 May 2025 20:45:09 GMT",
    "id": "000013",
    "lastmodified": "Thu, 15 May 2025 20:51:31 GMT",
    "laststatuschange": "Thu, 15 May 2025 20:51:31 GMT",
    "nmodified": 3,
    "order": {
      "id": "0006",
      "quantity": 2
    },
    "status": "confirmed",
    "type": "modify",
    "user": "user"
  }
]
```
