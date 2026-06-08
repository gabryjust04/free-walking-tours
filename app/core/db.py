import sqlite3
from flask import current_app, g


def get_db():

    if 'conn' not in g:
        g.conn = sqlite3.connect(current_app.config["DATABASE"])
        g.conn.row_factory = sqlite3.Row

    return g.conn

def close_db(e=None):

    conn = g.pop('conn',None)

    if conn is not None:
        conn.close()

def init_app(app):
    app.teardown_appcontext(close_db)

