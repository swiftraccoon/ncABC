from flask import Flask
from blueprints.inventory import inventory_bp

app = Flask(__name__)

# Register Blueprints
app.register_blueprint(inventory_bp, url_prefix='/')

if __name__ == '__main__':
    app.run(debug=True)
