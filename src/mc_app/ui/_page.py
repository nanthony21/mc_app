import base64
import glob
import io
import os
import pathlib as pl
import typing as t_
import bokeh
from PIL import ExifTags
from PIL import Image
from bokeh.models import ColumnDataSource, CustomJS, DataTable, TableColumn, Tabs, Panel, Row

from ._graph import MyGraph
from ._infoPanel import InfoPanel
from ._imagePanel import ImagePanel
from ._newSamplePanel import NewSamplePanel
from ..sample import Sample
from ._dialog import openDialog, DialogType


class Page:
    def __init__(self, sqlsession):
        self.resourcePath = pl.Path('static')
        self.sqlsession = sqlsession
        self.graph = MyGraph()
        self.infoPanel = InfoPanel()
        self.newSamplePanel = NewSamplePanel()
        self.imagePanel = ImagePanel()
        self.uploadfileSource = ColumnDataSource({'fileContents': [], 'fileName': []})
        self.infoPanel.loadImageButton.js_on_click(CustomJS(args=dict(file_source=self.uploadfileSource), code="""
            function read_file(filename) {
                var reader = new FileReader();
                reader.onload = load_handler;
                reader.onerror = error_handler;
                // readAsDataURL represents the file's data as a base64 encoded string
                reader.readAsDataURL(filename);
            }

            function load_handler(event) {
                var b64string = event.target.result;
                file_source.data = {'file_contents' : [b64string], 'file_name':[input.files[0].name]};
                file_source.change.emit();
            }

            function error_handler(evt) {
                console.log('error')
                if(evt.target.error.name == "NotReadableError") {
                    console.log("Can't read file!")
                }
            }
            function timed_check(){
                console.log('timer');
                console.log(input.files);
                if (input.files.length != 0){
                    readfile();
                }
                else{
                    setTimeout(timed_check,500);
                }
            }
            function readfile(){
                if (window.FileReader) {
                    read_file(input.files[0]);
                } else {
                    console.log('FileReader is not supported in this browser');
                }
            }
            var input = document.createElement('input');
            input.setAttribute('type', 'file');
            input.setAttribute("accept","image/*","capture=camera");
            input.onclick = function(){
                input.setAttribute('value','""'); //clear the filelist
                setTimeout(timed_check,500);
            }
            input.click();

            """))
        self.uploadfileSource.on_change('data', self.uploadCallback)
        self.plotInfoRow = Row(self.graph.widget, self.infoPanel.widget)
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

        self.tabs = Tabs(tabs=[self.tab1, self.tab2, self.newSamplePanel.widget, self.imagePanel.widget])

    def loadData(self):
        self.graph.getFromDB(self.sqlsession)
        # reregister select callback
        self.graph.renderer.node_renderer.data_source.selected.on_change('indices', self.nodeSelectCallback)
        self.graph.renderer.node_renderer.data_source.selected.trigger('indices', [],
                                                              self.graph.renderer.node_renderer.data_source.selected.indices)
        '''Data Table'''
        col = self.graph.renderer.node_renderer.data_source
        colnames = [TableColumn(field=k, title=k) for k in col.data.keys()]
        self.dTable = DataTable(source=col, columns=colnames)

    '''Callbacks!!!!!!!!!!!!'''

    def nodeSelectCallback(self, attr: str, old, newIndices: t_.List[int]):
        print('node call')
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

    def uploadCallback(self, attr, old, new):
        print('filename:', self.uploadfileSource.data['file_name'])
        raw_contents = self.uploadfileSource.data['file_contents'][0]
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
            raise TypeError("Failed to upload file")
        imgs = list(self.resourcePath.glob(".png"))
        if len(imgs) == 0:
            newfname = '1'
        else:
            newfname = str(max([int(i.split(os.sep)[-1][:-4]) for i in imgs]) + 1)
        self.infoPanel.object.addImage(newfname)
        image.save(str(self.resourcePath / f"{newfname}.png"))
        self.sqlsession.commit()
        self.loadData()
        openDialog(self.graph.plot, DialogType.ALERT, 'Image successfully added.')

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
        if choice is None:
            openDialog(self.graph.plot, DialogType.CONFIRM, "Are you sure you want to delete?", self.deleteSampleCallback)
        elif choice:
            if not self.infoPanel.object:
                print("No object selected")
                return
            if len(self.infoPanel.object.children) == 0:
                imFiles = [i.text for i in self.infoPanel.object.images]
                for i in imFiles:
                    (self.resourcePath / f"{i}.png").unlink()
                self.sqlsession.delete(self.infoPanel.object)
                self.sqlsession.commit()
                self.loadData()
            else:
                openDialog(self.graph.plot, DialogType.ALERT, 'Cannot delete a sample that has child samples')
        else:
            print("Cancelled deletion")
