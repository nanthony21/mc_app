import datetime
import typing as t_
import bokeh
from bokeh.models import Slider, Range1d, RadioButtonGroup, TapTool, WheelZoomTool, PanTool, ResetTool, Column, CustomJS
import networkx as nx
from mc_app.sample import Sample

def side_pos(G, root=None, height=1, center=(0, 0), pos=None, xgap: float = 1.0):
    import pdb
    # pdb.set_trace()
    if root is None:  # first iteration. find all origins
        roots = [node for node, degree in G.in_degree() if degree == 0]
        for num, i in enumerate(roots):
            pos = side_pos(G, root=i, height=1 / (len(roots) + 1), center=(0, (num + 1) / (len(roots) + 1)),
                                pos=pos)
        return pos
    if pos is None:
        pos = {}
    pos[root] = center
    neighbors = list(G.neighbors(root))
    if len(neighbors) != 0:
        dy = height / (len(neighbors))
        nexty = center[1] - height / 2 - dy / 2
        for neighbor in neighbors:
            nexty += dy
            pos = side_pos(G, root=neighbor, height=dy, center=(center[0] + xgap, nexty), pos=pos)
    return pos


def date_pos(G, root=None, height=1, center=(0, 0), pos=None, orig_date=None):
    if root is None:  # first iteration. find all origins
        roots = [node for node, degree in G.in_degree() if degree == 0]  # list of nodes with no parents (root nodes)
        dates = [datetime.datetime.strptime(G.nodes(data=True)[i]['birthDate'], '%d-%m-%Y') for i in
                 roots]  # a list of the birthdates for each  of the root samples
        import pdb
        # pdb.set_trace()
        orig_date = min(dates)  # The earliest of the dates
        for num, i in enumerate(roots):
            pos = date_pos(G, root=i, height=1 / (len(roots) + 1), center=(0, (num + 1) / (len(roots) + 1)),
                                pos=pos, orig_date=orig_date)
        return pos
    if pos is None:
        pos = {}
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


def tree_pos(G, root: int = 1, width: float = 1., vert_gap: float = 0.2, vert_loc: float = 0,
             xcenter: float = 0.0, pos: t_.Dict[int, t_.Tuple[float, float]] = None):
    """
    If there is a cycle that is reachable from root, then this will see infinite recursion.

    Args:
       G: the graph must be of a directed type
       root: node id of the root of the current branch
       width: horizontal space allocated for this branch - avoids overlap with other branches
       vert_gap: gap between levels of hierarchy
       vert_loc: vertical location of root
       xcenter: horizontal location of root
       pos: a dict keyed by node id with values of (x,y) coordinates of node positions
   """
    if pos is None:
        pos = {}
    pos[root] = (xcenter, vert_loc)
    neighbors = list(G.neighbors(root))  # Neighbor nodes of the root
    if len(neighbors) != 0:
        dx = width / len(neighbors)
        nextx = xcenter - width / 2 - dx / 2
        for neighbor in neighbors:
            nextx += dx
            pos = tree_pos(G, neighbor, width=dx, vert_gap=vert_gap,
                                vert_loc=vert_loc - vert_gap, xcenter=nextx, pos=pos)
    return pos


class MyGraph:
    def __init__(self):
        self._graph_layout = side_pos
        self.slider = Slider(start=1, end=60, value=7, step=1, title="X Zoom")
        self.plot = bokeh.plotting.figure(plot_width=400, plot_height=400,
                                          x_range=Range1d(-1, -1 + self.slider.value, bounds=(-2, 4e6)),
                                          y_range=Range1d(0, 1, bounds=(-0.5, 1.5)),
                                          tools='')

        self.slider.js_on_change(
            'value',
            CustomJS(
                args=dict(slider=self.slider, plot=self.plot),
                code='''
                   var days = slider.value;
                   plot.x_range.end=plot.x_range.start + days;
                   plot.x_range.change.emit();
                ''')
        )
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

    def setLayoutByDate(self, byDate: bool):
        if byDate:
            self._graph_layout = date_pos
            self.plot.xaxis[0].axis_label = 'Days'
        else:
            self._graph_layout = side_pos
            self.plot.xaxis[0].axis_label = 'Generations'

    def getFromDB(self, sqlsession):
        self._graph = nx.DiGraph()
        self.nodelist = [(i.id, i.toJSON()) for i in sqlsession.query(Sample).all()]
        '''Generate Networkx graph'''
        self._graph.add_nodes_from(self.nodelist)
        edges = [(i[0], j) for i in self.nodelist for j in i[1]['children']]
        self._graph.add_edges_from(edges)
        '''Load nx graph to bokeh renderer'''
        self.renderer: bokeh.models.GraphRenderer = bokeh.plotting.from_networkx(self._graph, self._graph_layout)

        # use the first item in the nodelist to generate the possible data sources for the hover tool
        for k, v in self.nodelist[0][1].items():
            self.renderer.node_renderer.data_source.add([i[1][k] for i in self.nodelist], name=k)
        self.renderer.node_renderer.data_source.add(  # Set color based on sampletype
            [self.colors[Sample.Type[nodeData['type']].value - 1] for nodeId, nodeData in self.nodelist],
            'color')
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
            self.renderer.node_renderer.data_source.selected.indices = oldsel.indices