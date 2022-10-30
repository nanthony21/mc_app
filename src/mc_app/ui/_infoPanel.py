import bokeh.plotting.figure
from bokeh.models import Paragraph, PreText, Button, Column, ColumnDataSource, CustomJS
import typing as t_


class InfoPanel:
    def __init__(self):

        self.idLabel = Paragraph(text='ID = ')
        self.speciesLabel = Paragraph(text='Species = ')
        self.typeLabel = Paragraph(text='Type = ')
        self.birthDateLabel = Paragraph(text='Birth Date = ')
        self.notesLabel = PreText(text='Notes = ', width=500, sizing_mode="stretch_height", style={"white-space": "pre-line"})
        self.addNoteButton = Button(label='Add Note', button_type='success')
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

        self.uploadfileSource = ColumnDataSource({'fileContents': [], 'fileName': []})
        self.loadImageButton.js_on_click(CustomJS(args=dict(file_source=self.uploadfileSource), code="""
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

        dis = objectref is None
        self.deleteButton.disabled = dis
        self.addNoteButton.disabled = dis
        self.loadImageButton.disabled = dis

