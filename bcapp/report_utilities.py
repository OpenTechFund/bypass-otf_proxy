import datetime
import os
import sqlalchemy as db
import pandas as import pd


def report(**kwargs):

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    reports = db.Table('reports', metadata, autoload=True, autoload_with=engine)
    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)
    mirrors = db.Table('mirrors', metadata, autoload=True, autoload_with=engine)

    # First, get domains and mirrors for fuzzy matching

    domains_list = []
    query = db.select([domains])
    result = connection.execute(query).fetchall()

    for line in result:
        domains_list.append({'id' : line[0], 'name' : line[1]})

    mirrors_list = []
    query = db.select([mirrors])
    result = connection.execute(query).fetchall()
    for line in result:
        mirrors_list.append({'id' : line[0], 'mirror_url' : line[1], 'domain_id' : line[2]})
 
    # Match domains with what's being asked for