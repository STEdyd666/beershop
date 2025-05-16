import pytest
import pymongo
from beershop import create_app
from beershop.utils.config import Config


@pytest.fixture()
def app():
    config = Config.load()

    # append "test" to db name
    testdbname = f"{config.database['name']}-test" 
    config.database['name'] = testdbname
    app = create_app(config)
    app.config.update({
        'TESTING': True,
        'CONFIG': config
    })
    
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
