from bokeh.models import Paragraph, PreText, Button, Column


class InfoPanel:
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
