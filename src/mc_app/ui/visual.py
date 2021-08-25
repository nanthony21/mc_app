# -*- coding: utf-8 -*-
"""
Created on Sun Oct 22 15:36:35 2017

@author: Nick
"""
from mc_app.sample import Sample
import networkx as nx
from bokeh.models import Select, CustomJS, Slider, Panel, ColumnDataSource, PreText, Tabs, Column, RadioButtonGroup, \
    Dropdown, Row, Button, Plot, DataTable, TextInput, TableColumn, Range1d, TapTool, PanTool, HoverTool, WheelZoomTool, \
    Paragraph, ResetTool
import bokeh.plotting
import bokeh.palettes
import bokeh.events
import datetime
from PIL import Image, ExifTags
import base64
import io
import glob
import os


def side_pos(G, root=None, height=1, center=(0, 0), pos=None, xgap=1):
    if root == None:  # first iteration. find all origins
        roots = [i for i in [j for j in G.nodes()] if G.nodes()[i]['parent'] == 'null']
        for num, i in enumerate(roots):
            pos = side_pos(G, root=i, height=1 / (len(roots) + 1), center=(0, (num + 1) / (len(roots) + 1)),
                                pos=pos)
        return pos
    if pos == None:
        pos = {root: center}
    else:
        pos[root] = center
    neighbors = list(G.neighbors(root))
    if len(neighbors) != 0:
        dy = height / (len(neighbors))
        nexty = center[1] - height / 2 - dy / 2
        for neighbor in neighbors:
            nexty += dy
            pos = side_pos(G, root=neighbor, height=dy, center=(center[0] + xgap, nexty), pos=pos)
    return pos


def date_pos(G, root=None, height=1, center=(0, 0), pos=None, xgap=0.2, orig_date=None):
    if root is None:  # first iteration. find all origins
        roots = [i for i in [j for j in G.nodes()] if
                 G.nodes()[i]['parent'] == 'null']  # list of nodes with no parents (root nodes)
        dates = [datetime.datetime.strptime(G.nodes(data=True)[i]['birthDate'], '%d-%m-%Y') for i in
                 roots]  # a list of the birthdates for each  of the root samples
        orig_date = min(dates)  # The earliest of the dates
        for num, i in enumerate(roots):
            pos = date_pos(G, root=i, height=1 / (len(roots) + 1), center=(0, (num + 1) / (len(roots) + 1)),
                                pos=pos, orig_date=orig_date)
        return pos
    if pos is None:
        pos = {root: center}
    else:
        pos[root] = center
    neighbors = list(G.neighbors(root))
    if len(neighbors) != 0:
        dy = height / (len(neighbors))
        nexty = center[1] - height / 2 - dy / 2
        for neighbor in neighbors:
            nexty += dy
            birthDate = datetime.datetime.strptime(G.nodes(data=True)[neighbor]['birthDate'], '%d-%m-%Y')
            nextx = (birthDate - orig_date).days
            pos = date_pos(G, root=neighbor, height=dy, center=(nextx, nexty), pos=pos, orig_date=orig_date)
    return pos


def tree_pos(G, root=1, width=1., vert_gap=0.2, vert_loc=0, xcenter=0, pos=None, parent=None):

    '''If there is a cycle that is reachable from root, then this will see infinite recursion.
       G: the graph must be of a directed type
       root: the root node of current branch
       width: horizontal space allocated for this branch - avoids overlap with other branches
       vert_gap: gap between levels of hierarchy
       vert_loc: vertical location of root
       xcenter: horizontal location of root
       pos: a dict saying where all nodes go if they have been assigned
       parent: parent of this branch.'''
    if pos is None:
        pos = {root: (xcenter, vert_loc)}
    else:
        pos[root] = (xcenter, vert_loc)
    neighbors = list(G.neighbors(root))
    if len(list(neighbors)) != 0:
        dx = width / len(neighbors)
        nextx = xcenter - width / 2 - dx / 2
        for neighbor in neighbors:
            nextx += dx
            pos = tree_pos(G, neighbor, width=dx, vert_gap=vert_gap,
                                vert_loc=vert_loc - vert_gap, xcenter=nextx, pos=pos,
                                parent=root)
    return pos


class MyGraph:

    def __init__(self):
        slidercallback = CustomJS(args=dict(), code='''
           var days = slider.value;
           plot.x_range.end=plot.x_range.start + days;
           plot.x_range.change.emit();
        ''')
        self.pos = tree_pos# side_pos
        self.slider = Slider(start=1, end=60, value=7, step=1, title="X Zoom")
        self.plot = bokeh.plotting.figure(plot_width=400, plot_height=400,
                                          x_range=Range1d(-1, -1 + self.slider.value, bounds=(-2, 4e6)),
                                          y_range=Range1d(0, 1, bounds=(-0.5, 1.5)),
                                          tools='')
        slidercallback.args['slider'] = self.slider
        slidercallback.args['plot'] = self.plot
        self.slider.js_on_change('value', slidercallback)
        self.xSelectSwitch = RadioButtonGroup(labels=['By Generation', 'By Date'], active=0)
        self.plot.toolbar.logo = None
        self.plot.title.text = "Samples"
        self.plot.yaxis.visible = False
        self.plot.ygrid.visible = False
        self.plot.xaxis[0].ticker.min_interval = 1
        self.plot.xaxis[0].ticker.num_minor_ticks = 0
        self.plot.xaxis[0].axis_label = 'Generations'
        self.pallete = bokeh.palettes.Spectral4
        tools = [
            TapTool(),
            WheelZoomTool(),
            PanTool(),
            ResetTool()]
        # HoverTool(tooltips={'ID':"@id",'Type':'@type','Notes':'@notes'})]
        tools[1].dimensions = 'height'  # vertical zoom only
        self.plot.add_tools(*tools)
        self.plot.toolbar.active_scroll = tools[1]  # sets the scroll zoom to be active immediately.
        self.colors = ['red', 'blue', 'green', 'purple', 'cyan', 'yellow']
        self.widget = Column(self.plot, self.slider, self.xSelectSwitch)

    def getFromDB(self, sqlsession):
        self.g = nx.DiGraph()
        self.nodelist = [(i.id, i.toJSON()) for i in sqlsession.query(Sample).all()]
        '''Generate Networkx graph'''
        self.g.add_nodes_from(self.nodelist)
        edges = [(i[0], j) for i in self.nodelist for j in i[1]['children']]
        self.g.add_edges_from(edges)
        '''Load nx graph to bokeh renderer'''
        self.renderer = bokeh.plotting.from_networkx(self.g, self.pos)
        for k, v in self.nodelist[0][
            1].items():  # use the first item in the nodelist to generate the possible data sources for the hover tool
            self.renderer.node_renderer.data_source.add([i[1][k] for i in self.nodelist], name=k)

        self.renderer.node_renderer.data_source.add(
            [self.colors[Sample.Type[j].value - 1] for j in [i[1]['type'] for i in self.nodelist]], 'color')
        self.renderer.node_renderer.glyph = bokeh.models.Circle(size=20, fill_color='color')  # self.pallete[0])
        self.renderer.node_renderer.selection_glyph = bokeh.models.Circle(size=15, fill_color='color')
        self.renderer.node_renderer.hover_glyph = bokeh.models.Circle(size=15, fill_color=self.pallete[1])

        self.renderer.edge_renderer.glyph = bokeh.models.MultiLine(line_color="#CCCCCC", line_alpha=0.8, line_width=5)
        self.renderer.edge_renderer.selection_glyph = bokeh.models.MultiLine(line_color=self.pallete[0], line_width=5)
        self.renderer.edge_renderer.hover_glyph = bokeh.models.MultiLine(line_color=self.pallete[1], line_width=5)

        self.renderer.selection_policy = bokeh.models.graphs.NodesAndLinkedEdges()
        self.renderer.inspection_policy = bokeh.models.graphs.NodesOnly()

        try:
            oldrenderer = \
            [(i, v) for i, v in enumerate(self.plot.renderers) if isinstance(v, bokeh.models.GraphRenderer)][0]
            oldsel = oldrenderer[1].node_renderer.data_source.selected
        except:
            oldsel = None
            oldrenderer = None
        if oldrenderer:
            self.plot.renderers.pop(oldrenderer[0])
        self.plot.renderers.append(self.renderer)
        # If something was previously selected add it reselect it now
        if oldsel:
            self.renderer.node_renderer.data_source.selected = oldsel


class InfoPanel():
    def __init__(self):
        self.idLabel = Paragraph(text='ID = ')
        self.speciesLabel = Paragraph(text='Species = ')
        self.typeLabel = Paragraph(text='Type = ')
        self.birthDateLabel = Paragraph(text='Birth Date = ')
        self.notesLabel = PreText(text='Notes = ')
        self.addNoteButton = Button(label='Add Note')
        self.imagesLabel = Paragraph(text='# of Images = ')
        self.loadImageButton = Button(label='Upload Image', button_type='success')
        self.deleteButton = Button(label='Delete Sample!!', button_type='danger')
        self.widget = Column(
            self.idLabel,
            self.speciesLabel,
            self.typeLabel,
            self.birthDateLabel,
            self.notesLabel,
            self.addNoteButton,
            self.imagesLabel,
            self.loadImageButton,
            self.deleteButton)

    def updateText(self, ID, species, Type, birthDate, notes, images, objectref):
        assert isinstance(notes, list)
        assert isinstance(images, list)
        self.idLabel.text = 'ID = ' + str(ID)
        self.speciesLabel.text = 'Species = ' + str(species)
        self.typeLabel.text = 'Type = ' + str(Type)
        self.birthDateLabel.text = 'Birth Date = ' + str(birthDate)
        self.notesLabel.text = 'Notes = \n' + '\n'.join(
            [str(i + 1) + ': ' + v['text'] + ' | ' + v['date'] for i, v in enumerate(notes)])
        self.imagesLabel.text = '# of Images = ' + str(len(images))
        self.object = objectref


class NewSamplePanel():
    def __init__(self):
        self.parentText = TextInput(title='Parent ID (enter species name here if sample is original)')
        self.typeButtons = RadioButtonGroup(labels=[i.name for i in Sample.Type], active=0)
        self.noteText = TextInput(title='Note')
        self.dateText = TextInput(title="Creation Date (format 'Day-Month-Year' UTC)",
                                  value=datetime.datetime.strftime(datetime.datetime.now(datetime.timezone.utc),
                                                                   '%d-%m-%Y'))
        self.button = Button(label='Create!')
        self.copiesSelector = Select(title='Number of Copies', value=str(1), options=[str(i) for i in range(1, 10)])
        self.widget = Panel(child=bokeh.layouts.layout([
            [self.parentText],
            [self.typeButtons],
            [self.noteText],
            [self.dateText],
            [self.copiesSelector],
            [self.button]
        ]), title='New Sample')


class ImagePanel():
    def __init__(self):
        self.plot = bokeh.plotting.figure(plot_width=500, plot_height=500,
                                          x_range=Range1d(0, 1, bounds=(-0.25, 1.25)),
                                          y_range=Range1d(0, 1, bounds=(-0.25, 1.25)),
                                          )
        self.plot.tools.pop(-1)  # remove help tool
        self.plot.tools.pop(-2)  # remove save tool
        self.plot.toolbar.active_scroll = self.plot.tools[1]  # activate wheel scroll
        self.plot.toolbar.logo = None
        self.plot.xaxis.visible = False
        self.plot.yaxis.visible = False
        self.plot.xgrid.grid_line_color = None
        self.plot.ygrid.grid_line_color = None
        self.plot.outline_line_alpha = 0
        menu = []
        self.imgSelectDropDown: Dropdown = Dropdown(label="SelectImage", button_type="warning", menu=menu)
        self.widget = Panel(child=Row(self.plot, self.imgSelectDropDown), title='Images')

    def reset(self):
        self.plot.x_range.start = 0
        self.plot.x_range.end = 1
        self.plot.y_range.start = 0
        self.plot.y_range.end = 1
        if len(self.plot.renderers) > 0:
            self.plot.renderers.pop(-1)
        # self.imgSelectDropDown.value = None


class Page:
    def __init__(self, sqlsession):
        self.doc = bokeh.plotting.curdoc()
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
        self.dialog = Dialog(self.graph.plot)
        self.loadData()
        '''Callbacks!!!!!!'''
        self.newSamplePanel.button.on_click(self.newSampleCallback)
        self.graph.renderer.node_renderer.data_source.on_change('selected', self.nodeSelectCallback)
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
        self.graph.renderer.node_renderer.data_source.on_change('selected', self.nodeSelectCallback)
        self.graph.renderer.node_renderer.data_source.trigger('selected', [],
                                                              self.graph.renderer.node_renderer.data_source.selected)
        '''Data Table'''
        col = self.graph.renderer.node_renderer.data_source
        colnames = [TableColumn(field=k, title=k) for k in col.data.keys()]
        self.dTable = DataTable(source=col, columns=colnames)

    '''Callbacks!!!!!!!!!!!!'''

    def nodeSelectCallback(self, attr: str, old, new: bokeh.models.Selection):
        print('node call')
        try:
            index = new.indices[0]
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
        self.dialog.open('alert', "Successfully added new sample: {}".format(idstring))

    def addNoteCallback(self, note=None):
        if note is None:
            print('note added')
            self.dialog.open('prompt', 'Note', self.addNoteCallback)
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
            return
        imgs = glob.glob(os.path.join('static', '*.png'))
        if len(imgs) == 0:
            newfname = '1'
        else:
            newfname = str(max([int(i.split(os.sep)[-1][:-4]) for i in imgs]) + 1)
        self.infoPanel.object.addImage(newfname)
        image.save(os.path.join('static', newfname + '.png'))
        self.sqlsession.commit()
        self.loadData()
        self.dialog.open('alert', 'Image successfully added.')

    def selectImageCallback(self, event: bokeh.events.ButtonClick):
        new = event.item
        if new != None:
            self.imagePanel.reset()
            imgurl = os.path.join("myco_app", 'static', new + ".png")
            img_source = ColumnDataSource(dict(url=[imgurl]))
            if len(self.imagePanel.plot.renderers) > 0:
                self.imagePanel.plot.renderers.pop(-1)
            width, height = Image.open(os.path.join('static', new + '.png')).size
            newWidth = width / max((width, height))
            newHeight = height / max((width, height))
            self.imagePanel.plot.image_url(url='url', x=0, y=1, w=newWidth, h=newHeight, source=img_source)

    def xSelectCallback(self, attr, old, new):
        print(new)
        if new == 1:
            self.graph.pos = date_pos
            self.graph.plot.xaxis[0].axis_label = 'Days'
        elif new == 0:
            self.graph.pos = side_pos
            self.graph.plot.xaxis[0].axis_label = 'Generations'
        else:
            print("xSelect buttton choice not valid")
        self.loadData()

    def deleteSampleCallback(self, choice=None):
        if choice == None:
            print('del')
            choice = self.dialog.open('confirm', "Are you sure you want to delete?", self.deleteSampleCallback)
        elif choice == True and self.infoPanel.object:
            if len(self.infoPanel.object.children) == 0:
                imFiles = [i.text for i in self.infoPanel.object.images]
                for i in imFiles:
                    os.remove(os.path.join('static', i + '.png'))
                self.sqlsession.delete(self.infoPanel.object)
                self.sqlsession.commit()
                self.loadData()
            else:
                self.dialog.open('alert', 'Cannot delete a sample that has child samples')
        else:
            print("Cancelled deletion")


class Dialog:
    def __init__(self, plot):
        '''Dialog stuff'''
        self.trig = plot.circle([-2], [-2], alpha=0).glyph
        self.dataIn = ColumnDataSource({'type': [], 'msg': []})
        self.dataOut = ColumnDataSource({'ret': []})
        self.trig.js_on_change('size', CustomJS(args=dict(datain=self.dataIn, dataout=self.dataOut),
                                                code='''
             console.log('dialog');
             var type = datain.data['type'][0];
             var msg = datain.data['msg'][0];
             if (type==['alert']){
                 alert(msg);
                 dataout.data = {'ret':[true]};
                 dataout.change.emit()
             }
             else if (type==['confirm']){
                 var conf=confirm(msg);
                 console.log(conf);
                 dataout.data = {'ret':[conf]};
                 dataout.change.emit();
                 console.log(dataout.data);
             }
             else if (type==['prompt']){
                 dataout.data ={'ret':[prompt(msg)]};
                 dataout.change.emit();
                 console.log(dataout.data)

             }
             else{
                 console.log("No dialog type selected");
             }
             '''))

    def open(self, typ, msg, func=None):
        print('open', typ)
        self.func = func
        self.dataIn.data = {'type': [typ], 'msg': [msg]}
        self.trig.size += 1
        self.dataOut.on_change('data', self.process)

    def process(self, attr, old, new):
        if new['ret'] != []:
            print('proc')
            print(new['ret'])
            self.dataOut.remove_on_change('data', self.process)
            if self.func:
                self.func(new['ret'][0])
            self.dataOut.data['ret'] = []
