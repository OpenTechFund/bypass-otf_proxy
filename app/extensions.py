from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap5

db = SQLAlchemy()
migrate = Migrate()
bootstrap = Bootstrap5()