from beershop import create_app
from beershop.utils.config import Config


# read configuration file
config = Config.load()

# create server
server = create_app(config)
