# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 20:11:56 2017

@author: Nick

"""
import random
from sample import Sample
from mc_app.ui import Page
import sqlalchemy as sq
import bokeh.document
import logging
import sys
import datetime


#### User input
useRealDB = False  # If true then a database will be loaded from file. else a fake database will be generated


def configureLogger():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    return root

def generateDB(numNodes: int):
    startDate = datetime.datetime.now()
    _ = []
    _.append(Sample('MySample', Sample.Type.Fruit.name))
    _.append(Sample('MyOtherSample', Sample.Type.Fruit.name))
    for i in range(numNodes):
        _.append(Sample([random.choice(_)], Sample.Type(random.choice([1, 2, 3, 4])).name,
                        birthdate=startDate + datetime.timedelta(i)))
    _.append(Sample([_[2], _[4], _[3]], Sample.Type.Bulk.name, birthdate=startDate + datetime.timedelta(11)))
    _.append(Sample([_[-1], _[-2]], Sample.Type.Bulk.name, birthdate=startDate + datetime.timedelta(12)))
    _[3].addNote('This happened.')
    _[3].addNote('That happened.')
    return _

logger = configureLogger()

if useRealDB:
    """For the real database"""
    logger.info("Using real database")
    engine = sq.create_engine('sqlite:///static/data.db', echo=False)
    session = sq.orm.sessionmaker(bind=engine)()
    Sample.metadata.create_all(engine)  # register the tables with the db

    # The below snippet can be used to generate a new file (Since the app won't launch on an empty database.
    # db = generateDB(5)
    # session.add_all(db)

else:

    '''For testing temporary stuff in memory'''
    logger.info("Faking database")
    engine = sq.create_engine('sqlite:///:memory:', echo=False)
    session = sq.orm.sessionmaker(bind=engine)()

    Sample.metadata.create_all(engine)  # register the tables with the db

    '''Create random database'''
    _ = generateDB(100)
    session.add_all(_)



'''*****************************************************'''
from bokeh.server.server import Server

def bkapp(doc: bokeh.document.Document):
    page = Page(session)
    doc.add_root(page.tabs)
    doc.title = "Myco Tracker"

server = Server(
    {"/": bkapp},
    numProcs=4,
    allow_websocket_origin=["*"],
    port=6004
)

# start timers and services and immediately return
server.start()

if __name__ == '__main__':
    print('Opening Bokeh application on http://localhost:5006/')

    server.io_loop.add_callback(server.show, "/")
    server.io_loop.start()


