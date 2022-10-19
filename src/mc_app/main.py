# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 20:11:56 2017

@author: Nick


run this with the scripts/runit script to start the server.
Do not add a __main__ guard
"""
import random
from sample import Sample
from mc_app.ui import Page
import sqlalchemy as sq
import bokeh.plotting
import logging
import sys

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

logger = configureLogger()

if useRealDB:
    """For the real database"""
    logger.info("Using real database")
    engine = sq.create_engine('sqlite:///static/data.db', echo=False)
    SessionMaker = sq.orm.sessionmaker(bind=engine)
    session = SessionMaker()
else:
    import datetime

    '''For testing temporary stuff in memory'''
    logger.info("Faking database")
    engine = sq.create_engine('sqlite:///:memory:', echo=False)
    SessionMaker = sq.orm.sessionmaker(bind=engine)
    session = SessionMaker()

    Sample.metadata.create_all(engine)  # register the tables with the db

    '''Create random database'''
    numNodes = 100
    startDate = datetime.datetime.now()
    _ = []
    _.append(Sample('MySample', 'fruit'))
    _.append(Sample('MyOtherSample', 'fruit'))
    for i in range(numNodes):
        _.append(Sample([random.choice(_)], Sample.Type(random.choice([1, 2, 3, 4])).name,
                        birthdate=startDate + datetime.timedelta(i)))
    _.append(Sample([_[2], _[4], _[3]], 'bulk', birthdate=startDate + datetime.timedelta(11)))
    _.append(Sample([_[-1], _[-2]], 'bulk', birthdate=startDate + datetime.timedelta(12)))
    _[3].addNote('This happened.')
    _[3].addNote('That happened.')
    session.add_all(_)
    '''*****************************************************'''

page = Page(session)

# bokeh.io.output_file("interactive_graphs.html")
# bokeh.io.show(page.tabs)
bokeh.plotting.curdoc().add_root(page.tabs)

