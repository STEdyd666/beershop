from __future__ import annotations
from flask import Flask, g
import flask

from typing import Dict, Any


__version__='0.1.0'

def create_app(config: Config) -> Flask:
    """Create Flask server.
    
    Args:
        config: configuration data to be binded to the flask instance

    """
    app = Flask(__name__)
    
    # add config file to flask instance
    app.config['CONFIG'] = config

    # necessary for login
    app.secret_key = "pit379u25872aa9034t8aayuw0976b"

    # handle database in g object
    @app.teardown_appcontext
    def teardown_db(exception):
        db = g.pop('db', None)

        if db is not None:
            db.close()

    # redirect root to home
    @app.route("/")
    def redirectroot():
        return flask.redirect('/home')

    # import application parts
    from .api.routes import api_bp
    from .home.routes import home_bp
    
    # register Blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(home_bp)
    
    if __name__ == '__main__':
        app.run(debug=True)

    return app