# -*- coding: utf-8 -*-
"""
Created on Mon Oct 23 20:03:48 2017

@author: Nick
"""
import enum
import datetime
import sqlalchemy as sq
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableList

SqlBase=declarative_base()

association_table = sq.Table('association',SqlBase.metadata,
                          sq.Column('left_node_id',sq.Integer,sq.ForeignKey('sample.id'),primary_key=True),
                          sq.Column('right_node_id',sq.Integer,sq.ForeignKey('sample.id'),primary_key=True)
                          )


class Sample(SqlBase):
    __tablename__='sample'
    id=sq.Column(sq.Integer,primary_key=True)
    children = sq.orm.relationship("Sample",
                        secondary=association_table,
                        primaryjoin=id==association_table.c.left_node_id,
                        secondaryjoin=id==association_table.c.right_node_id,
                        backref="parent")
    
    type=sq.Column(sq.Integer)
    species=sq.Column(sq.String)
    birthDate=sq.Column(sq.String)
    notes=sq.Column(MutableList.as_mutable(sq.PickleType))
    images=sq.Column(MutableList.as_mutable(sq.PickleType))
    @enum.unique
    class Type(enum.Enum):
        agar=1
        grain=2
        brfcake=3
        fruit=4
        syringe=5
        bulk=6

    class Note(object):
        def __init__(self,text):
            self.text=text
            self.date=datetime.datetime.now(datetime.timezone.utc)
            
    def __init__(self,parent,stypename,birthdate=None):
        #If it is an original sample then sample should be set to the species name
        try:
            stype=Sample.Type[stypename]
        except KeyError:
            raise KeyError('Sample type, {0}, is not valid'.format(stypename))
        self.type=stype.value
        if (isinstance(parent,list) and isinstance(parent[0],Sample)):
            self.parent=parent
            self.species=parent[0].species
        elif isinstance(parent,str):
            self.parent=[]
            self.species=parent
        else:
            raise TypeError("Type of parent, {0}, is not valid".format(type(parent)))
        self.notes=MutableList()
        self.images=MutableList()
        if birthdate:
            if isinstance(birthdate,str):
                self.birthDate=datetime.datetime.strftime(datetime.datetime.strptime(birthdate,'%d-%m-%Y'),'%d-%m-%Y')
            elif isinstance(birthdate,datetime.datetime):
                self.birthDate=datetime.datetime.strftime(birthdate,'%d-%m-%Y')
            else:
                raise TypeError('birthdate is not of a valid type')
        else:
            self.birthDate=datetime.datetime.strftime(datetime.datetime.now(datetime.timezone.utc),'%d-%m-%Y')
    #def __repr__(self):
    #    return "Sample: ID:{0}\tType:{1}\tNotes:{2}\tImages:{3}\tParentID:{4}\t#Children:{5}".format(self.id,self.type.name,len(self.notes),len(self.images),self.parent,len(self.children))
    def addNote(self,text):
        self.notes.append(Sample.Note(text))  
    def addImage(self,fileName):
        self.images.append(Sample.Note(fileName))
    def toJSON(self):
        _={}
        _['id']=self.id
        if self.parent:
            _['parent']=[i.id for i in self.parent]
        else:
            _['parent']='null'
        _['children']=[i.id for i in self.children]
        _['type']=Sample.Type(self.type).name
        _['notes']=[{'text':i.text,'date':datetime.datetime.strftime(i.date,'%d-%m-%Y')} for i in self.notes]
        _['images']=[{'fname':i.text,'date':datetime.datetime.strftime(i.date,'%d-%m-%Y')} for i in self.images]
        _['birthDate']=self.birthDate
        _['species']=self.species
        return _

if __name__=='__main__':
    a=Sample('qq','fruit')