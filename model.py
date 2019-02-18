"""Models and database functions"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from random import randint

##############################################################################
# Model definitions

class Guest(db.Model):
    """Guests of the event"""
    __tablename__ = "guests"

    guest_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    splash_that_id = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        """Provide helpful representation when printed."""
        return "<Guest guest_id=%s name=%s>" % (self.guest_id, self.name)


##############################################################################
# Helper functions
def connect_to_db(app, db_uri='postgresql:///hellotwilio'):
    """Connect the database to our Flask app."""

    # Configure to use our PstgreSQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.app = app
    db.init_app(app)


if __name__ == "__main__":
   # As a convenience, if we run this module interactively, it will leave
   # you in a state of being able to work with the database directly.

   from main import app
   connect_to_db(app)
   db.drop_all()
   db.create_all()
   print("Connected to DB.")

