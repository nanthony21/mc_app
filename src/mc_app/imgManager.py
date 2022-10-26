import typing as t_
import pathlib as pl
from .sample import Sample
import PIL.Image

class ImageManager:
    def __init__(self, imagePath: pl.Path):
        self._imPath = imagePath
        if not self._imPath.exists():
            self._imPath.mkdir()

    def hasImage(self, sample: Sample, imgNum: int) -> bool:
        fDir = self._imPath / f"{sample.id}"
        if not fDir.exists():
            return False
        fname = f"{imgNum}.png"
        return (fDir / fname).exists()

    def deleteImage(self, sample: Sample, imgNum: int):
        fPath = self._imPath / f"{sample.id}"
        (fPath/ f"{imgNum}.png").unlink()
        if len(fPath.glob("*")) == 0:  # empty
            fPath.unlink()


    def saveImage(self, sample: Sample, imgNum: int, img: PIL.Image.Image):
        fname = f"{imgNum}.png"
        fPath = self._imPath / f"{sample.id}" / fname
        if not fPath.parent.exists():
            fPath.parent.mkdir()
        if fPath.exists():
            raise Exception()
        img.save(str(fPath))
        sample.addImage(fname)

    def getImageNums(self, sample: Sample) -> t_.List[int]:
        numsInDb = [int(note.text.split('.')[0]) for note in sample.images]
        return [i for i in numsInDb if self.hasImage(sample, i)]

    def loadImage(self, sample: Sample, imgNum: int) -> PIL.Image.Image:
        fPath = self._imPath / f"{sample.id}" / f"{imgNum}.png"
        return PIL.Image.open(fPath)
