"""
This module contains all the helper classes (models and items) required to
construct the model and the view items, implement its interaction with the
Material layer.
"""
#--------------------------------------------
# Name:         matteWorker.py
# Purpose:      Customized QStandardItemModel and QStandardItem classes
# Author:       Hussain Parsaiyan
# License:      GPL v3
# Created       15/09/2012
# Copyright:    (c) ICE Animations. All rights reserved
# Python Version:   2.6
#--------------------------------------------
import qtify_maya_window as qtfy
from PyQt4 import QtGui, QtCore
import utilities as matte_util
reload(matte_util)

Qt = QtCore.Qt

class MatteModel(QtGui.QStandardItemModel):
    def __init__(self, parent = None):
        super(MatteModel, self).__init__(parent)
        self.itemChanged.connect(self.changeMatteID)

    def changeMatteID(self, matte):
        matte_util.setMatteMaterialID(matte.parent.text(),
                                    [matte.parent.red.text(),
                                     matte.parent.green.text(),
                                     matte.parent.blue.text()])

class MtlModel(QtGui.QStandardItemModel):

    def __init__(self, parent = None):
        super(MtlModel, self).__init__(parent)
        self.itemChanged.connect(self.changeMtlID)

    def changeMtlID(self, mtl):
        selectIDItems = [x
                        for x in map(self.itemFromIndex,
                                self.parent().materialView.selectedIndexes())
                                if hasattr(x, "mtlName")]+[mtl]\
                                if hasattr(mtl, "mtlName")\
                                else []
        #selectIDItems = [x for x in set(selectIDItems)]
        self.itemChanged.disconnect(self.changeMtlID)
        mtlToEdit = [x.mtlName for x in selectIDItems]
        #matte_util.setMaterialID(mtlToEdit, mtl.text())
        #mtlToEdit.pop(mtlToEdit.index(mtl))
        for x in selectIDItems:
            x.textChanged(mtl.text(), True)\
            if selectIDItems.index(x) < len(selectIDItems) -1\
            else x.textChanged(mtl.text())
        if not hasattr(mtl, "mtlName"): mtl.setText("")
        self.itemChanged.connect(self.changeMtlID)


    def setMakeMatteButtonState(self):
        #not functional right now
        self.parent().makeMatteButton.setEnabled(True
                    if len(self.parent().materialView.selectedIndexes()) > 0
                    else True)

    def hide(self, index):
        pass

class MatteItem(QtGui.QStandardItem):

    def __init__(self,matte = None, parent = None):
        """
        @param text: The name of the item/mesh
        @param parent: The parent Item of this QStandardItem
        """
        super(MatteItem, self).__init__(matte.name() if hasattr(matte, "name")
                                                    else matte)
        self.parent = parent
        self.setEditable(False)
        if hasattr(matte, "name"):
            self.red = MatteItem(str(matte.vray_redid_multimatte.get()), self)
            self.green = MatteItem(str(matte.vray_greenid_multimatte.get()),
                                                                        self)
            self.blue = MatteItem(str(matte.vray_blueid_multimatte.get()), self)
            [x.setEditable(True) for x in [self.red, self.green, self.blue]]
            self.matteName = matte.name()
            self.name = lambda : self.matteName


class MeshItem(QtGui.QStandardItem):

    def __init__(self, *arg ):
        self.parent,self.mesh, self.materials = arg
        #mesh = {meshnode : {1:[mtlName], None:[mtlName]}}
        super(MeshItem,self).__init__(self.mesh.keys()[0].name().split(":")[-1])
        self.fpnMesh = self.mesh.keys()[0].name()
        self.mtlNameToID = {} #{materialName: ID}
        for xMtlID in self.mesh.values():
            for x in xMtlID:
                for y in xMtlID[x]:
                    self.mtlNameToID[y.name()] = x
            self.setEditable(False)
        #self.hide()
        self.giveChild()

    def hide(self):
        model.hide(model.indexFromItem(self))

    def giveChild(self):
        #appends a child, *item*, to self and sets self to tristate
        mtlItems = [MtlNameItem(self, mtlName) for mtlName in self.mtlNameToID]
        self.appendColumn(mtlItems)
        [x.setEditable(False) for x in mtlItems]
        self.appendColumn([MtlIDItem(self, mtlName,
                        self.mtlNameToID[mtlName.fpnMtl],
                        self.materials[mtlName.fpnMtl])
                        for mtlName in mtlItems])

    def fpn(self):
        return self.fpnMesh

class MtlNameItem(QtGui.QStandardItem):
    def __init__(self, parent = None, mtl = None):
        super(MtlNameItem, self).__init__(mtl.split(":")[-1])
        self.fpnMtl = mtl

    def hide(self):
        model.hide(model.indexFromItem(self))

    def fpn(self):
        return self.fpnMtl

class MtlIDItem(QtGui.QStandardItem):

    def __init__(self, parent = None, *arg):
        mtl, mtlID, material = arg
        self.mtlNameItem = mtl
        self.mtlName = mtl.fpnMtl
        super(MtlIDItem, self).__init__(self.processMtlID(mtlID))
        self.material = material
        self.material.addToMtlItemList(self)

    def processMtlID(self, mtlID):
        return str(mtlID) if isinstance(mtlID, int) and mtlID else ""

    def textChanged(self, text, chunkOpen = False, looping = True):

        if isinstance(text, int) or text == None:
            text = self.processMtlID(text)
        val = text.isdigit() and int(text)
        self.setText(text if val else "")
        if looping:
            self.material.changeID(self.text(), chunkOpen, looping )

    def hide(self):
        model.hide(model.indexFromItem(self))