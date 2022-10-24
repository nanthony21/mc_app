
import pathlib as pl
import typing as t_
import bokeh
from PIL import ExifTags, Image
from bokeh.models import ColumnDataSource, CustomJS, DataTable, TableColumn, Tabs, Panel, Row

from ._graph import MyGraph
from ._infoPanel import InfoPanel
from ._imagePanel import ImagePanel
from ._newSamplePanel import NewSamplePanel
from ..sample import Sample
from ._dialog import openDialog, DialogType
from mc_app import resourcePath

class Page:
    def __init__(self, sqlsession):
        self.sqlsession = sqlsession
        self.graph = MyGraph()

        def updateDataCB():
            self.sqlsession.commit()
            self.loadData()

        self.infoPanel = InfoPanel(updateDataCB, self.graph.plot)
        self.newSamplePanel = NewSamplePanel()
        self.imagePanel = ImagePanel()

        self.plotInfoRow = Row(self.graph.widget, self.infoPanel.widget, sizing_mode="scale_width")
        self.loadData()
        '''Callbacks!!!!!!'''
        self.newSamplePanel.button.on_click(self.newSampleCallback)
        self.graph.renderer.node_renderer.data_source.selected.on_change('indices', self.nodeSelectCallback)
        self.graph.xSelectSwitch.on_change('active', self.xSelectCallback)
        self.infoPanel.addNoteButton.on_click(self.addNoteCallback)
        self.imagePanel.imgSelectDropDown.on_click(self.selectImageCallback)
        self.infoPanel.deleteButton.on_click(self.deleteSampleCallback)

        ''''''
        self.tab1 = Panel(child=self.plotInfoRow, title='Plot')
        self.tab2 = Panel(child=self.dTable, title='Data')

        self.tabs = Tabs(tabs=[self.tab1, self.tab2, self.newSamplePanel.widget, self.imagePanel.widget], sizing_mode="scale_width")

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
            images = datasource.data['images'][index]
            objectRef = self.sqlsession.query(Sample).filter_by(id=int(ID)).first()
        except IndexError:  # nothing is selected
            ID, species, Type, birthDate, notes, images, objectRef = (None, None, None, None, [], [], None)
        self.infoPanel.updateText(ID, species, Type, birthDate, notes, images, objectRef)
        self.newSamplePanel.parentText.value = str(ID)
        if objectRef:
            self.imagePanel.imgSelectDropDown.menu = [(str(i + 1), v.text) for i, v in enumerate(objectRef.images)]
        self.imagePanel.reset()

    def newSampleCallback(self):
        print('new sample')
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
            self.infoPanel.object.addNote(note)
            self.sqlsession.commit()
            self.loadData()
        else:
            print('type not valid', type(note))

    def selectImageCallback(self, event: bokeh.events.ButtonClick):
        new = event.item
        if new is not None:
            self.imagePanel.reset()
            fName = pl.Path('static') / f"{new}.png"
            imgurl = str((fName).absolute())
            img_source = ColumnDataSource(dict(url=[imgurl]))
            if len(self.imagePanel.plot.renderers) > 0:
                self.imagePanel.plot.renderers.pop(-1)
            width, height = Image.open(str(fName)).size
            newWidth = width / max((width, height))
            newHeight = height / max((width, height))
            self.imagePanel.plot.image_url(url='url', x=0, y=1, w=newWidth, h=newHeight, source=img_source)

    def xSelectCallback(self, attr, old, new):
        if new == 1:
            self.graph.setLayoutByDate(True)
        elif new == 0:
            self.graph.setLayoutByDate(False)
        else:
            raise Exception("Selection not valid")
        self.loadData()

    def deleteSampleCallback(self, choice: bool = None):
        if not self.infoPanel.object:
            print("No object selected")
            return
        if len(self.infoPanel.object.children) > 0:
            openDialog(self.graph.plot, DialogType.ALERT, 'Cannot delete a sample that has child samples')
            return

        if choice is None:
            openDialog(self.graph.plot, DialogType.CONFIRM, "Are you sure you want to delete?",
                       self.deleteSampleCallback)
        elif choice:
            imFiles = [i.text for i in self.infoPanel.object.images]
            for i in imFiles:
                (resourcePath / f"{i}.png").unlink()
            self.sqlsession.delete(self.infoPanel.object)
            self.sqlsession.commit()
            self.loadData()
        else:
            print("Cancelled deletion")