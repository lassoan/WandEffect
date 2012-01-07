import os
from __main__ import vtk, qt, ctk, slicer
import EditorLib
from EditorLib.EditOptions import HelpButton
from EditorLib.EditOptions import EditOptions
from EditorLib import EditUtil
from EditorLib import LabelEffect

#
# The Editor Extension itself.
# 
# This needs to define the hooks to be come an editor effect.
#

#
# WandEffectOptions - see LabelEffect, EditOptions and Effect for superclasses
#

class WandEffectOptions(EditorLib.LabelEffectOptions):
  """ WandEffect-specfic gui
  """

  def __init__(self, parent=0):
    super(WandEffectOptions,self).__init__(parent)

    # self.attributes should be tuple of options:
    # 'MouseTool' - grabs the cursor
    # 'Nonmodal' - can be applied while another is active
    # 'Disabled' - not available
    self.attributes = ('MouseTool')
    self.displayName = 'Wand Effect'

  def __del__(self):
    super(WandEffectOptions,self).__del__()

  def create(self):
    super(WandEffectOptions,self).create()

    self.toleranceFrame = qt.QFrame(self.frame)
    self.toleranceFrame.setLayout(qt.QHBoxLayout())
    self.frame.layout().addWidget(self.toleranceFrame)
    self.widgets.append(self.toleranceFrame)
    self.toleranceLabel = qt.QLabel("Tolerance:", self.toleranceFrame)
    self.toleranceLabel.setToolTip("Set the tolerance of the wand in terms of background pixel values")
    self.toleranceFrame.layout().addWidget(self.toleranceLabel)
    self.widgets.append(self.toleranceLabel)
    self.toleranceSpinBox = qt.QDoubleSpinBox(self.toleranceFrame)
    self.toleranceSpinBox.setToolTip("Set the tolerance of the wand in terms of background pixel values")
    self.toleranceSpinBox.minimum = 0
    self.toleranceSpinBox.maximum = 1000
    self.toleranceSpinBox.suffix = ""
    self.toleranceFrame.layout().addWidget(self.toleranceSpinBox)
    self.widgets.append(self.toleranceSpinBox)

    self.maxPixelsFrame = qt.QFrame(self.frame)
    self.maxPixelsFrame.setLayout(qt.QHBoxLayout())
    self.frame.layout().addWidget(self.maxPixelsFrame)
    self.widgets.append(self.maxPixelsFrame)
    self.maxPixelsLabel = qt.QLabel("Max Pixels per click:", self.maxPixelsFrame)
    self.maxPixelsLabel.setToolTip("Set the maxPixels for each click")
    self.maxPixelsFrame.layout().addWidget(self.maxPixelsLabel)
    self.widgets.append(self.maxPixelsLabel)
    self.maxPixelsSpinBox = qt.QDoubleSpinBox(self.maxPixelsFrame)
    self.maxPixelsSpinBox.setToolTip("Set the maxPixels for each click")
    self.maxPixelsSpinBox.minimum = 1
    self.maxPixelsSpinBox.maximum = 1000
    self.maxPixelsSpinBox.suffix = ""
    self.maxPixelsFrame.layout().addWidget(self.maxPixelsSpinBox)
    self.widgets.append(self.maxPixelsSpinBox)

    HelpButton(self.frame, "Use this tool to label all voxels that are within a tolerance of where you click")

    self.toleranceSpinBox.connect('valueChanged(double)', self.onToleranceSpinBoxChanged)
    self.maxPixelsSpinBox.connect('valueChanged(double)', self.onMaxPixelsSpinBoxChanged)

    # Add vertical spacer
    self.frame.layout().addStretch(1)

  def destroy(self):
    super(WandEffectOptions,self).destroy()

  # note: this method needs to be implemented exactly as-is
  # in each leaf subclass so that "self" in the observer
  # is of the correct type 
  def updateParameterNode(self, caller, event):
    node = EditUtil.EditUtil().getParameterNode()
    if node != self.parameterNode:
      if self.parameterNode:
        node.RemoveObserver(self.parameterNodeTag)
      self.parameterNode = node
      self.parameterNodeTag = node.AddObserver("ModifiedEvent", self.updateGUIFromMRML)

  def setMRMLDefaults(self):
    super(WandEffectOptions,self).setMRMLDefaults()
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    defaults = (
      ("tolerance", "20"),
      ("maxPixels", "200"),
    )
    for d in defaults:
      param = "Wand,"+d[0]
      pvalue = self.parameterNode.GetParameter(param)
      if pvalue == '':
        self.parameterNode.SetParameter(param, d[1])
    self.parameterNode.SetDisableModifiedEvent(disableState)

  def updateGUIFromMRML(self,caller,event):
    if self.updatingGUI:
      return
    params = ("tolerance",)
    params = ("maxPixels",)
    for p in params:
      if self.parameterNode.GetParameter("Wand,"+p) == '':
        # don't update if the parameter node has not got all values yet
        return
    self.updatingGUI = True
    super(WandEffectOptions,self).updateGUIFromMRML(caller,event)
    self.toleranceSpinBox.setValue( float(self.parameterNode.GetParameter("Wand,tolerance")) )
    self.maxPixelsSpinBox.setValue( float(self.parameterNode.GetParameter("Wand,maxPixels")) )
    self.updatingGUI = False

  def onToleranceSpinBoxChanged(self,value):
    if self.updatingGUI:
      return
    self.updateMRMLFromGUI()

  def onMaxPixelsSpinBoxChanged(self,value):
    if self.updatingGUI:
      return
    self.updateMRMLFromGUI()

  def updateMRMLFromGUI(self):
    if self.updatingGUI:
      return
    disableState = self.parameterNode.GetDisableModifiedEvent()
    self.parameterNode.SetDisableModifiedEvent(1)
    super(WandEffectOptions,self).updateMRMLFromGUI()
    self.parameterNode.SetParameter( "Wand,tolerance", str(self.toleranceSpinBox.value) )
    self.parameterNode.SetParameter( "Wand,maxPixels", str(self.maxPixelsSpinBox.value) )
    self.parameterNode.SetDisableModifiedEvent(disableState)
    if not disableState:
      self.parameterNode.InvokePendingModifiedEvent()


#
# WandEffectTool
#
 
class WandEffectTool(LabelEffect.LabelEffectTool):
  """
  One instance of this will be created per-view when the effect
  is selected.  It is responsible for implementing feedback and
  label map changes in response to user input.
  This class observes the editor parameter node to configure itself
  and queries the current view for background and label volume
  nodes to operate on.
  """

  def __init__(self, sliceWidget):
    super(WandEffectTool,self).__init__(sliceWidget)

  def cleanup(self):
    super(WandEffectTool,self).cleanup()

  def processEvent(self, caller=None, event=None):
    """
    handle events from the render window interactor
    """
    if event == "LeftButtonPressEvent":
      xy = self.interactor.GetEventPosition()
      sliceLogic = self.sliceWidget.sliceLogic()
      logic = WandEffectLogic(sliceLogic)
      logic.apply(xy)
      self.abortEvent(event)
    else:
      pass
      #print(caller,event,self.sliceWidget.sliceLogic().GetSliceNode().GetName())


#
# WandEffectLogic
#
 
class WandEffectLogic(LabelEffect.LabelEffectLogic):
  """
  This class contains helper methods for a given effect
  type.  It can be instanced as needed by an WandEffectTool
  or WandEffectOptions instance in order to compute intermediate
  results (say, for user feedback) or to implement the final 
  segmentation editing operation.  This class is split
  from the WandEffectTool so that the operations can be used
  by other code without the need for a view context.
  """

  def __init__(self,sliceLogic):
    self.sliceLogic = sliceLogic

  def apply(self,xy):
    # TODO: save the undo state - not yet available for extensions
    # EditorStoreCheckPoint $_layers(label,node)
    
    #
    # get the parameters from MRML
    #
    node = EditUtil.EditUtil().getParameterNode()
    tolerance = float(node.GetParameter("Wand,tolerance"))
    maxPixels = float(node.GetParameter("Wand,maxPixels"))


    #
    # get the label and background volume nodes
    #
    labelLogic = self.sliceLogic.GetLabelLayer()
    labelNode = labelLogic.GetVolumeNode()
    labelNode.SetModifiedSinceRead(1)
    backgroundLogic = self.sliceLogic.GetBackgroundLayer()
    backgroundNode = backgroundLogic.GetVolumeNode()

    #
    # get the ijk location of the clicked point
    # by projecting through patient space back into index
    # space of the volume.  Result is sub-pixel, so round it
    # (note: bg and lb will be the same for volumes created
    # by the editor, but can be different if the use selected
    # different bg nodes, but that is not handled here).
    # 
    xyToIJK = labelLogic.GetXYToIJKTransform().GetMatrix()
    ijkFloat = xyToIJK.MultiplyPoint(xy+(0,1))[:3]
    ijk = []
    for element in ijkFloat:
      try:
        intElement = int(round(element))
      except ValueError:
        intElement = 0
      ijk.append(intElement)
    ijk.reverse()
    ijk = tuple(ijk)

    #
    # Get the numpy array for the bg and label
    #
    import vtk.util.numpy_support
    backgroundImage = backgroundNode.GetImageData()
    labelImage = labelNode.GetImageData()
    shape = list(backgroundImage.GetDimensions())
    shape.reverse()
    backgroundArray = vtk.util.numpy_support.vtk_to_numpy(backgroundImage.GetPointData().GetScalars()).reshape(shape)
    labelArray = vtk.util.numpy_support.vtk_to_numpy(labelImage.GetPointData().GetScalars()).reshape(shape)

    #
    # do a re
    value = backgroundArray[ijk]
    label = EditUtil.EditUtil().getLabel()
    lo = value - tolerance
    hi = value + tolerance
    pixelsSet = 0
    toVisit = [ijk,]
    while toVisit != []:
      location = toVisit.pop()
      try:
        l = labelArray[location]
        b = backgroundArray[location]
      except IndexError:
        continue
      if l != 0 or b < lo or b > hi:
        continue
      labelArray[location] = label
      pixelsSet += 1
      if pixelsSet > maxPixels:
        toVisit = []
      else:
        # add the 6 neighbors to the stack
        toVisit.append((location[0] - 1, location[1]    , location[2]    ))
        toVisit.append((location[0] + 1, location[1]    , location[2]    ))
        toVisit.append((location[0]    , location[1] - 1, location[2]    ))
        toVisit.append((location[0]    , location[1] + 1, location[2]    ))
        toVisit.append((location[0]    , location[1]    , location[2] - 1))
        toVisit.append((location[0]    , location[1]    , location[2] + 1))




    # TODO: workaround for new pipeline in slicer4
    # - editing image data of the calling modified on the node
    #   does not pull the pipeline chain
    # - so we trick it by changing the image data first
    workaround = 1
    if workaround:
      if not hasattr(self,"tempImageData"):
        self.tempImageData = vtk.vtkImageData()
      imageData = labelNode.GetImageData()
      labelNode.SetAndObserveImageData(self.tempImageData)
      labelNode.SetAndObserveImageData(imageData)
    else:
      labelNode.Modified()



#
# The WandEffectExtension class definition 
#

class WandEffectExtension(LabelEffect.LabelEffect):
  """Organizes the Options, Tool, and Logic classes into a single instance
  that can be managed by the EditBox
  """

  def __init__(self):
    # name is used to define the name of the icon image resource (e.g. WandEffect.png)
    self.name = "WandEffect"
    # tool tip is displayed on mouse hover
    self.toolTip = "Paint: circular paint brush for label map editing"

    self.options = WandEffectOptions
    self.tool = WandEffectTool
    self.logic = WandEffectLogic

""" Test:

sw = slicer.app.layoutManager().sliceWidget('Red')
import EditorLib
pet = EditorLib.WandEffectTool(sw)

"""

#
# WandEffect
#

class WandEffect:
  """
  This class is the 'hook' for slicer to detect and recognize the extension
  as a loadable scripted module
  """
  def __init__(self, parent):
    parent.title = "Editor Wand Effect"
    parent.category = "Developer Tools.Editor Extensions"
    parent.contributor = "Steve Pieper"
    parent.helpText = """
    Example of an editor extension.  No module interface here, only in the Editor module
    """
    parent.acknowledgementText = """
    This editor extension was developed by 
    <Author>, <Institution>
    based on work by:
    Steve Pieper, Isomics, Inc.
    based on work by:
    Jean-Christophe Fillion-Robin, Kitware Inc.
    and was partially funded by NIH grant 3P41RR013218.
    """

    # TODO:
    # don't show this module - it only appears in the Editor module
    #parent.hidden = True

    # Add this extension to the editor's list for discovery when the module
    # is created.  Since this module may be discovered before the Editor itself,
    # create the list if it doesn't already exist.
    try:
      slicer.modules.editorExtensions
    except AttributeError:
      slicer.modules.editorExtensions = {}
    slicer.modules.editorExtensions['WandEffect'] = WandEffectExtension

#
# WandEffectWidget
#

class WandEffectWidget:
  def __init__(self, parent = None):
    self.parent = parent
    
  def setup(self):
    # don't display anything for this widget - it will be hidden anyway
    pass

  def enter(self):
    pass
    
  def exit(self):
    pass

