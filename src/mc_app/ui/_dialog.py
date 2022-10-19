from bokeh.models import ColumnDataSource, CustomJS
import bokeh
import typing as t_
import enum

class DialogType(enum.Enum):
    CONFIRM = enum.auto()
    ALERT = enum.auto()
    PROMPT = enum.auto()

def openDialog(plot: bokeh.plotting.figure, typ: DialogType, msg: str, callback: t_.Optional[t_.Callable] = None):
    """

    Args:
        plot: Just used as something to add an invisible item to.
         typ: Indicates the type of dialog to open. options are "confirm", "alert", and "prompt". This is passed to custom JS.
        msg: The message to display in the dialog
        func: optional function to pass dialog output to
    """
    trig = plot.circle([-2], [-2], alpha=0).glyph  # Hack: draw an invisible circle on the plot and set a callback on its size. Change the size to open the dialog. There must be a better way.

    if typ == DialogType.ALERT:
        typeStr = "alert"
    elif typ == DialogType.CONFIRM:
        typeStr = "confirm"
    elif typ == DialogType.PROMPT:
        typeStr = "prompt"
    else:
        raise Exception("Unhandled case")

    dataIn = ColumnDataSource({'type': [typeStr], 'msg': [msg]})  # The type and message for the dialog
    dataOut = ColumnDataSource({'ret': []})  # Gets the return value from js
    trig.js_on_change('size', CustomJS(args=dict(datain=dataIn, dataout=dataOut),
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

    def processOutput(attr: str, old, new):
        if new['ret'] != []:
            # dataOut.remove_on_change('data', _process)
            if callback:
                callback(new['ret'][0])
            # dataOut.data['ret'] = []

    dataOut.on_change('data', processOutput)  # When dataout is updated from JS pass the data to `func`
    trig.size += 1  # Trigger the dialog js callback

