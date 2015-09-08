'''
This module contains the helper functions required for queres the plugin needs
to make.
This function will have should have no dependencies on other modules, except the
mayas default.
'''
#--------------------------------------------
# Name:         matteWorker.py
# Purpose:      Making the actual calls to the maya scene.
# Author:       Talha Ahmed and Qurban Ali
# License:      GPL v3
# Created       15/09/2012
# Copyright:    (c) ICE Animations. All rights reserved
# Python Version:   2.6
#--------------------------------------------
import pymel.core as pc
import maya.cmds as mc
def undoChunk(func):
    ''' This is a decorator for all functions that cause a change in a maya
    scene. It wraps all changes of the decorated function in a single undo
    chunk
    '''
    def _wrapper(*args, **dargs):
        res = None
        try:
            undoChunk = dargs.pop('chunkOpen')
        except KeyError:
            undoChunk = None
        if undoChunk is True:
            pc.undoInfo(openChunk=True)
        try:
            res = func(*args, **dargs)
        finally:
            if undoChunk is False:
                pc.undoInfo(closeChunk=True)
            return res
    return _wrapper

def materials( meshes = [] ):
    '''
        This function returns all the shaders/materials and material
        ids (if set) applied on meshes from a scene.

        Arguments:
            @param meshes: The list of meshes (pymel.core.mesh) whose
            materials are needed

        Return Type:
        A Dictionary --- {mesh:{ Id: ['Material Name', '...', ...]}}
        if material id Attribute is not set, id is None
    '''
    mesh_materials = {}
    for mesh in meshes:
        material = materials_helper(mesh)
        mesh_materials[mesh] = material
    return mesh_materials

def materials_helper( meshNode ):
    '''
        This function returns all the shaders/materials and material
        ids (if set) applied on a single mesh from a scene.

        Arguments:
            @param mesh: mesh (pymel.core.mesh) whose
            materials are needed

        Return Type:
        A Dictionary --- {Id: ['Material Name', '...', ...]}
        if material id Attribute is not set, id is None
    '''
    matls = {}

    instNo = meshNode.instanceNumber()
    shadingEngines = set()
    try:
        validIndices = meshNode.iog[instNo].og.get(mi=True)
        if validIndices:
            for index in validIndices:
                newSet = set(meshNode.iog[instNo].og[index].outputs(
                                                        type='shadingEngine'))
                shadingEngines.update(newSet)
        shadingEngines.update(meshNode.iog[instNo].outputs(
                                                        type='shadingEngine'))
    except IndexError:
        pass

    for x in shadingEngines:
        shaders = x.surfaceShader.inputs()
        if not shaders: continue
        try:
            material_id = pc.getAttr(shaders[0].vrayMaterialId)
        except AttributeError:
            material_id = None
        material = shaders[0]

        if not matls.has_key(material_id):
            matls[material_id] = [material]
        else:
            if material not in matls[material_id]:
                matls[material_id].append(material)
    return matls

def mtlToMatte(materials = []):
    '''
    This function is used to get the multimattes in accordance with the objects
    or materials provided.

    @param materials: Takes the output of the materials function
    @param objects: Take the list of objectIDs (not a necessary implementation
                    at this stage)
    @return: a dictionary of multimattes {name: [mtlID]}
    '''
    multimattes_list = getAllMultiMattes()
    used_multimattes = {}

    for matte in multimattes_list:
        #check if the "use material id" checkBox is checked
        use_material_id = pc.getAttr(matte + ".vray_usematid_multimatte")
        if use_material_id:
            greenid = pc.getAttr(matte + ".vray_greenid_multimatte")
            redid = pc.getAttr(matte + ".vray_redid_multimatte")
            blueid = pc.getAttr(matte + ".vray_blueid_multimatte")
            multimatte_name = pc.getAttr(matte + ".vray_name_multimatte")

            for mat_id in materials:
                if mat_id == greenid or mat_id == redid or mat_id == blueid:
                    if not used_multimattes.has_key(multimatte_name):
                        used_multimattes[multimatte_name] = [mat_id]
                    else:
                        if mat_id not in used_multimattes[multimatte_name]:
                            used_multimattes[multimatte_name].append(mat_id)
    return used_multimattes

def matteToMtlID(matte = []):
    '''
    Query the given list of matte and return the list of materials it contains
    @param matte: list of matte names
    @return: {matte:[mtlID(R,G,B)], matte:None}
             None of the passed mattename is object based
    '''
    mattes = {}
    for m in matte:
        redid = pc.getAttr(m+ ".vray_redid_multimatte")
        greenid = pc.getAttr(m+ ".vray_greenid_multimatte")
        blueid = pc.getAttr(m+ ".vray_blueid_multimatte")

        if pc.getAttr(m.vray_usematid_multimatte) == True:
            mattes[m] = [redid, greenid, blueid]
        else:
            mattes[m] = None
    return mattes

def mtlNameFromId(mtlID = []):
    '''
    Queries materials containing the following IDs
    @param mtID: list of mtlID
    @return: {mtlID:[mtlNames], mtlID:None}
    This fuction uses the services of "materials()"
    '''
    #If the given mtlID doesn't exist return empty list
    mat_names = {}
    meshes = pc.ls(type = 'mesh')
    for mesh in meshes:
        all_materials = materials_helper(mesh)
        for mat_id in mtlID:
            if mat_id in all_materials:
                mat_names[mat_id] = all_materials[mat_id]
            else:
                mat_names[mat_id] = None
    return mat_names

@undoChunk
def createMatte(red = 0, green = 0, blue = 0):
    '''
    Create matte with the given ID
    @param red: materialID
    @param green:
    This function uses the services of "getAllMattes()" and
    "getNewlyCreatedMultiMattes"
    '''

    # create the new multimatte
    prevList = getAllMultiMattes()
    pc.Mel.eval("vrayAddRenderElement MultiMatteElement")
    newList = getAllMultiMattes()
    matte = getNewlyCreatedMultiMattes(prevList, newList)[0]

    pc.setAttr(matte+ ".vray_redid_multimatte", int(red))
    pc.setAttr(matte+ ".vray_greenid_multimatte", int(green))
    pc.setAttr(matte+ ".vray_blueid_multimatte", int(blue))

def mtlExists(mtlID=[]):
    '''
    Queries if the given list of material IDs exist
    @param mtlID: list of material Id
    @return: {mtlID: False|True}
    This function uses the services of "materials()"
    '''
    mat_exist = {}
    meshes = pc.ls(type = 'mesh')
    for mesh in meshes:
        all_materials = materials_helper(mesh)
        for mat_id in mtlID:
            if mat_id in all_materials:
                mat_exist[mat_id] = True
            else:
                mat_exist[mat_id] = False
    return mat_exist

def getLowestUniqueID(includeZero=False):
    ''' fetches all the material ids from the parent materials in the scene and
    find the smallest id integer that has not been used

    @param includeZero if True 0 is considered a valid unique id, by default
    this value is false since vray considers 0 as a 'non-ID' and does not
    render materials having to any matte
    '''
    ses=pc.ls(type='shadingEngine')
    mtlIDs = set()
    for se in ses:
        try:
            sn = se.surfaceShader.inputs()[0]
            mtlIDs.add(sn.vrayMaterialId.get())
        except IndexError:
            continue
        except AttributeError:
            continue

    start = int(not includeZero)
    allids = set(range(start, max(mtlIDs)+2))
    unused = allids.difference(mtlIDs)
    return unused.pop()

@undoChunk
def makeMtlMatte(mtlNames = []):
    ''' This function takes a list of materials and creates multimattes from
    them taking care that none of the material IDs are repeated
    '''
    mtlID_dict = {}
    mtlIDs = []  # list is here so we can know the original order passed
    # collect all the provided materials with same ids to dictionary
    for mtlName in mtlNames:
        mtl = mayaMaterial( mtlName )
        if mtl is None:
            continue

        i = getMaterialID(mtl, createNewID=True)
        if not i:
            i = getLowestUniqueID()
            _setMaterialID(mtlName, i)
        if i in mtlIDs:
            mtlID_dict[i].append(mtlName)
        else:
            mtlIDs.append(i)
            mtlID_dict[i] = [mtlName]

    # print 'mtlIDs=', mtlIDs, 'mtlID_dict=', mtlID_dict

    # call the helper as many times as required providing
    # one material for one id
    # providing three materials for each matte
    numMtlIDs = len(mtlIDs)
    newmattes = []

    for matteOffset in range(0, numMtlIDs, 3):
        mat3 = []
        for index in range(matteOffset, min(matteOffset+3, numMtlIDs)):
            mat3.append(mtlID_dict[mtlIDs[index]][0])
        newmattes.append(_makeMtlMatte(mat3))

    return newmattes

@undoChunk
def _makeMtlMatte(mtlNames = []):
    '''
    if any material doesn't have an ID assigned to it.
    Assign a lowest unique material
    ID to it. And of course make the material matte.
    @param mtlNames: [R[[, G[, B]]]
    '''

    # create a New material matte and give the ids of the first three
    # materials, make sure the useMaterial IDs are checked

    if not mtlNames: pc.error('No material names were passed')

    mtlShortNames = []
    mtlIDs = []
    for mtlName in mtlNames:

        # check if there are valid materials in input
        mtl = mayaMaterial( mtlName )
        if mtl is None:
            pc.error("Provided object %s is not a valid material" % mtlName)

        shortName = mtl.split(':')[-1].split('_')[0]
        mtlShortNames.append( shortName )

        # see if materials have material ids attached to them
        # else give lowest unique id
        mtlIDs.append(getMaterialID(mtl, createNewID=True))
    # print 'mtlIDs inner', mtlIDs

    sel = pc.ls(sl=1)
    # create the new multimatte
    prevList = getAllMultiMattes()
    pc.Mel.eval("vrayAddRenderElement MultiMatteElement")
    newList = getAllMultiMattes()
    newMatte = getNewlyCreatedMultiMattes(prevList, newList)[0]
    pc.select(sel)

    # give good materials IDs to the matte
    newMatte.vray_usematid_multimatte.set(True)
    newMatte.vray_redid_multimatte.set(mtlIDs[0])
    if len(mtlIDs) > 1:
        newMatte.vray_greenid_multimatte.set(mtlIDs[1])
    if len(mtlIDs) > 2:
        newMatte.vray_blueid_multimatte.set(mtlIDs[2])

    # give appropriate name to matte (by extracting from material name)
    newMatteName = '_'.join(mtlShortNames) + '_matte'
    newMatteName = pc.rename( newMatte,  newMatteName )
    newMatte.vray_name_multimatte.set(str(newMatteName))

    return newMatte

def getNewlyCreatedMultiMattes(prevList, newList):
    ''' returns the difference newList - prevList

    newMMs = []
    for j in newList:
        if j not in prevList:
            newMMs.append(j)
    return newMMs
    '''
    return [j for j in newList if j not in prevList]

def getAllMaterialMultiMattes():
    ''' returns the list of Pynode objects of all multimatte
    (vrayRenderElementNodes) nodes which use material ids i.e. there attribute
    vray_usematid_multimatte has been set to a True value

    multimattes = getAllMultiMattes()
    matmultimattes = []
    for mm in multimattes:
        if mm.vray_usematid_multimatte.get():
            matmultimattes.append(mm)
    return matmultimattes
    '''
    return [mm for mm in getAllMultiMattes()
            if mm.vray_usematid_multimatte.get()]

def getAllMultiMattes():
    '''
    @return: the list of pynode objects of all multimatte
    (vrayRenderElementNodes) nodes
    '''
    vrayres = pc.ls(type = 'VRayRenderElement')
    multimattes = []
    for node in vrayres:
        try:
            if node.vrayClassType.get() == 'MultiMatteElement':
                multimattes.append(node)
        except AttributeError:
            pass
    return multimattes

def mayaMaterial(mtl):
    ''' if the argument is a valid maya material it returns a PyNode else it
    returns None
    '''
    try:
        mtl = pc.PyNode(mtl)
        if callable(mtl.outColor.get):
            return mtl
    except pc.MayaNodeError:
        pass
    except AttributeError:
        pass
    return None

@undoChunk
def setMaterialID(mtls, newid):
    ''' @material
    '''
    for mtl in mtls:
        try:
            _setMaterialID(mtl, newid)
        except RuntimeError:
            pc.warning('%s is not a valid maya material' % mtl)

@undoChunk
def _setMaterialID(mtl, newid):
    ''' set material ID on the material specified create one if necessary

    @param mtl MayaName or PyNode for the material on which the ID is to be set
    @param newid integer id that is to be set on the material
    '''
    try:
        newid = int( newid )
    except ValueError:
        newid = 0
    mtlNode = mayaMaterial(mtl)

    if mtlNode is None:
        pc.error("Provided object %s is not a valid material" % mtl)

    try:
        mtlNode.vrayMaterialId.set(newid)
    except AttributeError:
        pc.addAttr(mtlNode, ln='vrayMaterialId', at='long', keyable=False,
                min=0, smx=10, readable=True,
                storable=True, writable=True, dv=0)
        mtlNode.vrayMaterialId.set(newid)

@undoChunk
def getMaterialID(mtl, createNewID=False):
    ''' Get the vray material ID of the material, if it doesnt exist create
    one and assign the lowest unique ID value if required

    @param mtl material object
    @param createNewID if True a new unique id is created if one is not found
    already
    '''

    mtlNode = mayaMaterial(mtl)
    mtlID = None
    if mtlNode is None:
        pc.error("Provided object %s is not a valid material" % mtl)
    try:
        mtlID = mtlNode.vrayMaterialId.get()
        # print 'getting id ', mtlID
    except AttributeError:

        if createNewID:
            pc.addAttr(mtlNode, ln='vrayMaterialId', at='long', keyable=False,
            min=0, smx=10, readable=True, storable=True, writable=True, dv=0)
            mtlID = getLowestUniqueID()
            pc.warning('Creating and assigning new unique id = %d' % mtlID)
            mtlNode.vrayMaterialId.set(mtlID)

    return mtlID

@undoChunk
def setMatteMaterialID(matte, mtlID=[]):
    ''' sets the materials ids for the given multimatte
    '''
    if mtlID:
        pc.setAttr(matte+ ".vray_redid_multimatte", int(mtlID[0]))
        pc.setAttr(matte+ ".vray_greenid_multimatte", int(mtlID[1]))
        pc.setAttr(matte+ ".vray_blueid_multimatte", int(mtlID[2]))

@undoChunk
def renameMatte(oldName, newName):
    '''
    This function reanmes an existing multimatte
    @param oldName: old name of the multimatte (as an object of vray)
    @params newName of the multimatte (as a string)
    returns the newName
    '''
    try:
        newName = pc.rename (oldName, newName)
    except RuntimeError:
        return oldName
    pc.setAttr(oldName+".vray_name_multimatte",newName)
    return newName

@undoChunk
def deleteMattes(mattes = []):
    pc.delete(mattes)

def undo():
    pc.undo()

def getAllMaterials():
    '''
    @return: the list of all materials
    all_materials = []
    meshes = pc.ls(type = 'mesh')
    for mesh in meshes:
        material = materials_helper(mesh)
        for key in material:
            all_materials += material[key]
    #remove the duplications in the list of materials
    all_materials_set = set(all_materials)
    all_materials = list(all_materials_set)
    return all_materials
    '''
    allse = pc.ls(type='shadingEngine')
    allmtls = set()
    for se in allse:
        ssList = se.surfaceShader.inputs()
        for ss in ssList:
            allmtls.add(ss)
    return list(allmtls)

def materialExists(mtlName):
    return mayaMaterial(mtlName)
