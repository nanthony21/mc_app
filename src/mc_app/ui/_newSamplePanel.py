# -*- coding: utf-8 -*-
"""
Created on Sun Oct 22 15:36:35 2017

@author: Nick
"""
from mc_app.sample import Sample
from bokeh.models import Select, Panel, RadioButtonGroup, Button, TextInput
import bokeh.plotting
import bokeh.palettes
import datetime

class NewSamplePanel:
    def __init__(self):
        self.parentText = TextInput(title='Parent ID (enter species name here if sample is original)')
        self.typeButtons = RadioButtonGroup(labels=[i.name for i in Sample.Type], active=0)
        self.noteText = TextInput(title='Note')
        self.dateText = TextInput(title="Creation Date (format 'Day-Month-Year' UTC)",
                                  value=datetime.datetime.strftime(datetime.datetime.now(datetime.timezone.utc),
                                                                   '%d-%m-%Y'))
        self.button = Button(label='Create!', button_type='success')
        self.copiesSelector = Select(title='Number of Copies', value=str(1), options=[str(i) for i in range(1, 10)])
        self.layout = bokeh.layouts.layout([
            [self.parentText],
            [self.typeButtons],
            [self.noteText],
            [self.dateText],
            [self.copiesSelector],
            [self.button]
        ])









