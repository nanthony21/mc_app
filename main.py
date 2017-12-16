# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 20:11:56 2017

@author: Nick
"""
import random

import matplotlib.pyplot as plt
import sys

from SampleClass import Sample
from visual import Page
import sqlalchemy as sq
import bokeh.io
import bokeh.plotting

useRealDB=True

if useRealDB:
    """For the real database"""
    engine=sq.create_engine('sqlite:///static/data.db',echo=False)
    SessionMaker=sq.orm.sessionmaker(bind=engine)
    session=SessionMaker()
else:
    import datetime
    '''For testing temporary stuff in memory'''
    engine=sq.create_engine('sqlite:///:memory:',echo=False)
    SessionMaker=sq.orm.sessionmaker(bind=engine)
    session=SessionMaker()
    
    Sample.metadata.create_all(engine) #register the tables with the db
    
    '''Create random database'''
    numNodes=100
    startDate=datetime.datetime.now()
    _=[]
    _.append(Sample('blahblahshroom','fruit'))
    _.append(Sample('blahblahshroom','fruit'))
    for i in range(numNodes):
        _.append(Sample([random.choice(_)],Sample.Type(random.choice([1,2,3,4])).name,birthdate=startDate+datetime.timedelta(i)))
    _.append(Sample([_[2],_[4],_[3]],'bulk',birthdate=startDate+datetime.timedelta(11)))
    _.append(Sample([_[-1],_[-2]],'bulk',birthdate=startDate+datetime.timedelta(12)))
    _[3].addNote('Pork for di')
    _[3].addNote('chicken too')
    session.add_all(_)
    '''*****************************************************'''



page=Page(session)

bokeh.io.output_file("interactive_graphs.html")
bokeh.io.show(page.tabs)
bokeh.plotting.curdoc().add_root(page.tabs)