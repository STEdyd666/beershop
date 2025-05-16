import flask
from flask import Blueprint


# Blueprint Configuration
home_bp = Blueprint(
    'home_bp', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/beershop.home.static'
)

# render home
@home_bp.route('/home', methods=['GET', 'POST'])
def home():
    """Home page"""
    return flask.render_template('index.html')
