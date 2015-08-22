"""
The module contains all the necessary Qt based classes to draw the plugin UI
and contains the logic behind it's working.
The plugin is designed to display, edit and make Multi(material)Mattes easily
"""
#--------------------------------------------
# Name:         matteWorker.py
# Purpose:      Managing and drawing multiple instances of the MatteWork
#               plugin
# Author:       Hussain Parsaiyan
# License:      GPL v3
# Created       15/09/2012
# Copyright:    (c) ICE Animations. All rights reserved
# Python Version:   2.6
#--------------------------------------------
from uiContainer import uic
import qtify_maya_window as qtfy
from PyQt4 import QtGui, QtCore
import pymel.core as pc
import time, itertools as it
import maya.OpenMaya as om
import random, string
import model_item as mi
import utilities as matte_util
reload(mi)
reload(matte_util)
Qt = QtCore.Qt
import os
import qutil




class Material(object):
    """
    This layer does all the querying, editing and creation in the Maya scene.
    Basically a layer which does (almost) all the communication with the maya
    scene using the matte_util's module.
    """
    def __init__(self, fpnMtl, container):
        self.fpnMtl = fpnMtl
        self.container = container
        self.mtlItem = []
        #self.refresh()

    def refresh(self):
        """syncs itself with the maya
        """
        if self.exists():
            self.mtlID = matte_util.getMaterialID(self.fpnMtl)
            self.updateMaterialItems()
        else:
            self.hide()

    def changeID(self, mtlID, chunkOpen = False , looping = True):
        if self.exists():
            if looping:
                matte_util.setMaterialID([self.fpnMtl], mtlID,
                                                        chunkOpen = chunkOpen)
                self.mtlID = matte_util.getMaterialID(self.fpnMtl)
                for x in self.mtlItem:
                    x.textChanged(mtlID, False, False)
        else:
            self.hide()

    def updateMaterialItems(self):
        tmp = self.mtlItem[:]
        for mtlItem in tmp:
            try:
                text = mtlItem.text()
                mtlItem.setText(text)
            except:
                self.mtlItem.pop(self.mtlItem.index(mtlItem))
        map(lambda x: x.textChanged(self.mtlID, looping = False), self.mtlItem)

    def exists(self):
        return True
        return matte_util.materialExists(self.fpnMtl)
    def hide(self):
        #hide the corresponding materialName and materialID items
        #and pop off self of the dict materials
        map(lambda x:x.hide(), self.mtlItem)
        self.container.pop(self.fpnMtl)

    def addToMtlItemList(self, mtlItem):
        """Add item to self.mtlItem
        """
        self.mtlItem.append(mtlItem)

Form, Base = uic.loadUiType(os.path.join(qutil.dirname(__file__, 2), 'ui', 'ui.ui'))
class GUI(Form, Base):

    def __init__(self, parent = qtfy.getMayaWindow()):

        super(GUI, self).__init__()
        self.setupUi(self)
        parent.addDockWidget(Qt.DockWidgetArea(0x2), self)

        #self.pluginDir = arg[0]
        pc.loadPlugin("vrayformaya.mll", qt = True)

        self.createMaterialModel(True)
        self.updateMatteModel(True)
        self.turnMeshItemVisible()
        self.makeMatteButton.clicked.connect(self.makeMatte)
        self.refreshButton.clicked.connect(self.refresh)
        self.matteView.doubleClicked.connect(self.sceneMatteSelect)
        self.materialView.doubleClicked.connect(self.sceneMaterialSelect)
        map(self.clearSelectionButton.clicked.connect,
                                                [self.clearSelection])
        map(self.addSelectionButton.clicked.connect, [self.addSelection])
        map(self.removeSelectionButton.clicked.connect,
                                                [self.removeSelection])
        map(self.undoButton.clicked.connect,
                                    [matte_util.undo, self.refresh])
        map(self.deleteMatteButton.clicked.connect,
                        [self.deleteSelectedMatte, self.updateMatteModel])
        self.expandAllButton.clicked.connect(self.materialView.expandAll)
        self.collapseAllButton.clicked.connect(
                                              self.materialView.collapseAll)

    def sceneMaterialSelect(self, index):
        item = self.materialModel.itemFromIndex(index)
        if hasattr(item, "fpn"):
            pc.select(item.fpn())

    def sceneMatteSelect(self, index):

        item = self.matteModel.itemFromIndex(index)
        if hasattr(item, "name"):
            pc.select(item.name())

    def clearSelection(self):
        self.materialView.selectAll()
        self.removeSelection()

    def addSelection(self):
        """get the mesh name, search for it through the """
        meshItems = {}
        meshToMtlID = {}
        for mesh in self.selection():
            if not self.meshItems.get(mesh):
                meshToMtlID = dict(meshToMtlID,
                                    **matte_util.materials([mesh]))
        self.populateMaterials()
        for mesh in meshToMtlID:
            meshItems[mesh] = mi.MeshItem(None, {mesh: meshToMtlID[mesh]},
                                                        self.materials)
        map(self.materialModel.appendRow, meshItems.values())
        self.meshItems = dict(self.meshItems, **meshItems)
        self.meshToMtlID = dict(self.meshToMtlID, **meshToMtlID)

    def removeSelection(self):
        self.refresh()
        selection = self.materialView.selectionModel()
        map(lambda y: map(lambda z : y(z),
                        [self.materialModel.itemFromIndex(x).mesh.keys()[0]
                        for x in self.materialView.selectedIndexes()
                        if isinstance(self.materialModel.itemFromIndex(x),
                                            mi.MeshItem)]),
                        [self.meshItems.pop, self.meshToMtlID.pop])
        checker = lambda : map(lambda y : y.row(),
                            [x for x in self.materialView.selectedIndexes()
                            if isinstance(
                                self.materialModel.itemFromIndex(x),
                                mi.MeshItem)
                            ]
                            )

        while checker():
            self.materialModel.removeRow(checker()[0])
        self.refresh()

    def deleteSelectedMatte(self):
        matte_util.deleteMattes([x.text()
                            for x in map(self.matteModel.itemFromIndex,
                                self.matteView.selectedIndexes())
                                if not x.text().isdigit()])

    def redraw(self):
        self.updateMaterialModel()
        self.updateMatteModel()

    def refresh(self):
        """
        Now you have to do the following:
        1. Mesh extant. i.e. is the mesh in our list of mesh
            extant on the scene
        2. Material extant. i.e. is the material in our list of material
            still available
        3. Recheck the ID of all the materials
        4. Check the materials associativitity.
            i.e. is the material known to be attached to a particular
            mesh still attached to it.
        5. Check matte changes.
        6. To be found :P
        """
        selectionModel = self.materialView.selectionModel()
        items = selectionModel.selection()
        self.materialView.clearSelection()
        #1:
        #3:
        map(lambda x: x.refresh(), self.materials.values())
        #5:
        self.updateMatteModel()
        #4:
        #to be implemented
        #for blah in selectionModel.selectedIndexes()
        selectionModel.select(items, selectionModel.SelectionFlag(2))

    def makeMatte(self):
        self.refresh()
        listOfMtl = [x.mtlName
                        for x in map(self.materialModel.itemFromIndex,
                                    self.materialView.selectedIndexes())
                                    if hasattr(x, "mtlName")]
        matte_util.makeMtlMatte(listOfMtl)
        self.refresh()
        self.updateMatteModel()

    def updateMatteModel(self, first = False):
        if not first: del self.matteModel

        self.matteModel  = mi.MatteModel(self)
        self.matteList = matte_util.getAllMaterialMultiMattes()
        self.mattes = [mi.MatteItem(x) for x in self.matteList]
        self.matteModel.appendColumn([x for x in self.mattes])
        self.matteModel.appendColumn([x.red for x in self.mattes])
        self.matteModel.appendColumn([x.green for x in self.mattes])
        self.matteModel.appendColumn([x.blue for x in self.mattes])
        self.matteView.setModel(self.matteModel)
        self.matteView.setColumnWidth(0, 150)
        self.matteModel.setHorizontalHeaderLabels(["MultiMatte Name",
                                                "Red", "Green", "Blue"])

    def createMaterialModel(self, first = False):
        if first: self.materialModel = mi.MtlModel(self)
        self.meshToMtlID={} #{mesh:{mtlID:[name],None:[name]}}
        for mesh in self.selection():
            #this redundant loop is being reused in addSelection.
            #DRY it out, and rethink it
            try:
                self.meshToMtlID = dict(self.meshToMtlID,
                                        **matte_util.materials([mesh]))
            except:
                continue

        self.populateMaterials()
        self.populateMeshItems()
        self.materialModel.appendColumn(self.meshItems.values())
        self.materialModel.setHorizontalHeaderLabels(["Material Name",
                                                        "Material ID"])
        self.materialView.setModel(self.materialModel)

    def turnMeshItemVisible(self):
        for mesh in self.selection():
            #self.meshItems[mesh].show()
            pass

    def turnMeshItemInvisible(self):
        for mesh in self.selection():
            self.meshItems[mesh].hide()

    def selection(self):
        return pc.ls(sl = True, type = "mesh", dag = True, ni = True)

    def populateMaterials(self):
        try:
            self.materials
        except:
            self.materials = {}
        for material in matte_util.getAllMaterials():
            if not self.materials.get(material.name()):
                self.materials[material.name()] = Material(material.name(),
                                                            self.materials)

    def populateMeshItems(self):
        self.meshItems = {}
        for mesh in self.meshToMtlID:
            self.meshItems[mesh] = mi.MeshItem(None,
                                            {mesh: self.meshToMtlID[mesh]},
                                                self.materials)