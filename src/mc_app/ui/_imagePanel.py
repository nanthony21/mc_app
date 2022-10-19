import bokeh
from bokeh.models import Range1d, Dropdown, Row, Panel


class ImagePanel:
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