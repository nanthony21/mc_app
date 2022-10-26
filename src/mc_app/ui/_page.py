
import pathlib as pl
import typing as t_
import bokeh
from PIL import ExifTags, Image
from bokeh.models import ColumnDataSource, DataTable, TableColumn, Tabs, Panel, Row
from bokeh.layouts import column
from ._graph import MyGraph
from ._infoPanel import InfoPanel
from ._imagePanel import ImagePanel
from ._newSamplePanel import NewSamplePanel
from ..sample import Sample
from ._dialog import openDialog, DialogType
from mc_app import resourcePath
import numpy as np
import base64
import io
import os
from PIL import ExifTags, Image
from ._dialog import openDialog, DialogType
from mc_app import resourcePath
from mc_app.imgManager import ImageManager

class Page:
    def __init__(self, sqlsession):
        self.sqlsession = sqlsession
        self.imgManager = ImageManager(resourcePath / "images")
        self.graph = MyGraph()

        self.infoPanel = InfoPanel()
        self.newSamplePanel = NewSamplePanel()
        self.imagePanel = ImagePanel()

        plotInfoRow = Row(self.graph.widget, self.infoPanel.widget, sizing_mode="scale_width")
        self.loadData()
        '''Callbacks!!!!!!'''
        self.newSamplePanel.button.on_click(self.newSampleCallback)
        self.graph.renderer.node_renderer.data_source.selected.on_change('indices', self.nodeSelectCallback)
        self.graph.xSelectSwitch.on_change('active', self.xSelectCallback)
        self.infoPanel.addNoteButton.on_click(self.addNoteCallback)
        self.imagePanel.imgSelectDropDown.on_click(self.selectImageCallback)
        self.infoPanel.deleteButton.on_click(self.deleteSampleCallback)
        self.infoPanel.uploadfileSource.on_change('data', self.uploadCallback)

        ''''''
        plotCol = column(plotInfoRow, self.newSamplePanel.layout)
        tab1 = Panel(child=plotCol, title='Plot')
        tab2 = Panel(child=self.dTable, title='Data')

        self.tabs = Tabs(tabs=[tab1, tab2, self.imagePanel.widget], sizing_mode="scale_width")

    def loadData(self):
        self.graph.getFromDB(self.sqlsession)
        # reregister select callback
        self.graph.renderer.node_renderer.data_source.selected.on_change('indices', self.nodeSelectCallback)
        self.graph.renderer.node_renderer.data_source.selected.trigger('indices', [],
                                                              self.graph.renderer.node_renderer.data_source.selected.indices)
        '''Data Table'''
        col = self.graph.renderer.node_renderer.data_source
        colnames = [TableColumn(field=k, title=k) for k in col.data.keys()]
        self.dTable = DataTable(source=col, columns=colnames, sizing_mode="scale_width")

    '''Callbacks!!!!!!!!!!!!'''

    def nodeSelectCallback(self, attr: str, old, newIndices: t_.List[int]):
        print('node call')
        if len(newIndices) > 1:  # don't allow more than one selection
            self.graph.renderer.node_renderer.data_source.selected.indices = [newIndices[0]] # This will re-trigger this callback.
            return
        try:
            index = newIndices[0]
            datasource = self.graph.renderer.node_renderer.data_source
            ID = datasource.data['id'][index]
            species = datasource.data['species'][index]
            Type = datasource.data['type'][index]
            birthDate = datasource.data['birthDate'][index]
            notes = datasource.data['notes'][index]
            objectRef = self.sqlsession.query(Sample).filter_by(id=int(ID)).first()
            images = self.imgManager.getImageNums(objectRef)
        except IndexError:  # nothing is selected
            ID, species, Type, birthDate, notes, images, objectRef = (None, None, None, None, [], [], None)
        self.selectedSample = objectRef
        self.infoPanel.updateText(ID, species, Type, birthDate, notes, images, objectRef)
        self.newSamplePanel.parentText.value = str(ID)
        if objectRef:
            self.imagePanel.imgSelectDropDown.menu = [str(i) for i in self.imgManager.getImageNums(objectRef)]
        self.imagePanel.reset()

    def newSampleCallback(self):
        panel = self.newSamplePanel
        try:
            ID = list(map(int, panel.parentText.value.split(',')))
            parent = self.sqlsession.query(Sample).filter(Sample.id.in_(ID)).all()
        except ValueError:
            parent = panel.parentText.value  # for if its a new sample and the species was entered instead
        samples = []
        for i in range(int(self.newSamplePanel.copiesSelector.value)):
            sample = Sample(parent, panel.typeButtons.labels[panel.typeButtons.active], birthdate=panel.dateText.value)
            if panel.noteText.value:
                sample.addNote(panel.noteText.value)
            self.sqlsession.add(sample)
            samples.append(sample)

        self.sqlsession.commit()
        self.loadData()
        ids = [sample.id for sample in samples]  # this only works if it comes after the commit
        idstring = ','.join(map(str, ids))
        openDialog(self.graph.plot, DialogType.ALERT, "Successfully added new sample: {}".format(idstring))

    def addNoteCallback(self, note=None):
        if note is None:
            print('note added')
            openDialog(self.graph.plot, DialogType.PROMPT, 'Note', self.addNoteCallback)
        elif type(note) == str:
            self.selectedSample.addNote(note)
            self.sqlsession.commit()
            self.loadData()
        else:
            print('type not valid', type(note))

    def selectImageCallback(self, event: bokeh.events.ButtonClick):
        imgNum: str = event.item
        if imgNum is not None:
            imgNum: int = int(imgNum)
            self.imagePanel.reset()
            if len(self.imagePanel.plot.renderers) > 0:
                self.imagePanel.plot.renderers.pop(-1)
            im = self.imgManager.loadImage(self.selectedSample, imgNum)
            im = im.convert("RGBA")
            width, height = im.size
            img = np.empty((height, width), dtype=np.uint32)
            view = img.view(dtype=np.uint8).reshape((height, width, 4))
            # Copy the RGBA image into view, flipping it so it comes right-side up
            # with a lower-left origin
            view[:, :, :] = np.flipud(np.asarray(im))
            newWidth = width / max((width, height))
            newHeight = height / max((width, height))
            self.imagePanel.plot.image_rgba(image=[img], x=0, y=0, dw=newWidth, dh=newHeight)

    def xSelectCallback(self, attr, old, new):
        if new == 1:
            self.graph.setLayoutByDate(True)
        elif new == 0:
            self.graph.setLayoutByDate(False)
        else:
            raise Exception("Selection not valid")
        self.loadData()

    def deleteSampleCallback(self, choice: bool = None):
        if not self.selectedSample:
            print("No object selected")
            return
        if len(self.selectedSample.children) > 0:
            openDialog(self.graph.plot, DialogType.ALERT, 'Cannot delete a sample that has child samples')
            return

        if choice is None:
            openDialog(self.graph.plot, DialogType.CONFIRM, "Are you sure you want to delete?",
                       self.deleteSampleCallback)
        elif choice:
            imgs = self.imgManager.getImageNums(self.selectedSample)
            for i in imgs:
                self.imgManager.deleteImage(self.selectedSample, i)
            self.sqlsession.delete(self.selectedSample)
            self.sqlsession.commit()
            self.loadData()
        else:
            print("Cancelled deletion")

    def uploadCallback(self, attr, old, new):
        print('filename:', self.infoPanel.uploadfileSource.data['file_name'])
        raw_contents = self.infoPanel.uploadfileSource.data['file_contents'][0]
        # remove the prefix that JS adds
        prefix, b64_contents = raw_contents.split(",", 1)
        file_contents = base64.b64decode(b64_contents)
        file_io = io.BytesIO(file_contents)

        try:
            image = Image.open(file_io)
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            if image._getexif() is not None:
                if orientation in image._getexif().keys():
                    print('rotate')
                    exif = dict(image._getexif().items())
                    if exif[orientation] == 3:
                        image = image.rotate(180, expand=True)
                    elif exif[orientation] == 6:
                        image = image.rotate(270, expand=True)
                    elif exif[orientation] == 8:
                        image = image.rotate(90, expand=True)
                    elif exif[orientation] == 1:
                        print('no rotation needed')
                    else:
                        print('no valid rotation found')
                    print('orientation value = ', exif[orientation])
        except:
            openDialog(self.graph.plot, DialogType.ALERT, 'Failed to upload file.')
            return
        imgs = self.imgManager.getImageNums(self.selectedSample)
        if len(imgs) == 0:
            newNum = 0
        else:
            newNum = max(imgs) + 1
        self.imgManager.saveImage(self.selectedSample, newNum, image)
        self.sqlsession.commit()
        self.loadData()
        openDialog(self.graph.plot, DialogType.ALERT, 'Image successfully added.')
