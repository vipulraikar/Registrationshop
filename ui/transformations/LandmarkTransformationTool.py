"""
LandmarkTransformationTool (TransformationTool)

:Authors:
	Berend Klein Haneveld
"""
from Landmark import Landmark
from TransformationTool import TransformationTool
from ui.widgets.PointsWidget import PointsWidget
from ui.widgets.StatusWidget import StatusWidget
from ui.transformations import TwoStepPicker as Picker
from ui.transformations import Transformation
from core.decorators import overrides
from core.vtkDrawing import TransformWithMatrix
from vtk import vtkPoints
from vtk import vtkLandmarkTransform
from vtk import vtkTransform
from vtk import vtkMatrix4x4
from PySide.QtGui import QWidget
from PySide.QtGui import QGridLayout
from PySide.QtGui import QComboBox
from PySide.QtGui import QLabel
from PySide.QtCore import Signal
from PySide.QtCore import Slot
from PySide.QtCore import Qt


class LandmarkTransformationTool(TransformationTool):
	"""
	LandmarkTransformationTool
	"""
	updatedLandmarks = Signal(list)

	def __init__(self):
		super(LandmarkTransformationTool, self).__init__()

		self.fixedPicker = Picker()
		self.movingPicker = Picker()

		self.landmarkPointSets = []  # Sets of points
		self.landmarkIndicators = []  # All the landmark indicator objects

		self.originalTransform = None
		self.originalScalingTransform = None

		self.activeIndex = 0
		self.landmarkTransformType = 0  # Rigid, Similarity or Affine

	@overrides(TransformationTool)
	def getParameterWidget(self):
		self.pointsWidget = PointsWidget()

		self.landmarkComboBox = QComboBox()
		self.landmarkComboBox.addItem("Rigid body")
		self.landmarkComboBox.addItem("Similarity")
		self.landmarkComboBox.addItem("Affine")

		layout = QGridLayout()
		layout.setAlignment(Qt.AlignTop)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(QLabel("Transform type"), 0, 0)
		layout.addWidget(self.landmarkComboBox, 0, 1)
		layout.addWidget(self.pointsWidget, 1, 0, 1, 2)
		
		self.updatedLandmarks.connect(self.pointsWidget.setPoints)
		self.landmarkComboBox.currentIndexChanged.connect(self.landmarkTypeChanged)
		self.pointsWidget.activeLandmarkChanged.connect(self.setActiveLandmark)

		widget = QWidget()
		widget.setLayout(layout)
		return widget

	@overrides(TransformationTool)
	def setRenderWidgets(self, fixed=None, moving=None, multi=None):
		self.fixedWidget = fixed
		self.movingWidget = moving
		self.multiWidget = multi

		self.fixedPicker.setWidget(self.fixedWidget)
		self.movingPicker.setWidget(self.movingWidget)

		self.fixedPicker.pickedLocation.connect(self.pickedFixedLocation)
		self.movingPicker.pickedLocation.connect(self.pickedMovingLocation)

		# Save the original complete transform
		self.originalTransform = self.multiWidget.transformations.completeTransform()
		self.originalScalingTransform = self.multiWidget.transformations.scalingTransform()

		# Add a new transform on top of the others
		transform = Transformation(vtkTransform(), Transformation.TypeLandmark)
		self.multiWidget.transformations.append(transform)

		statusWidget = StatusWidget.Instance()
		statusWidget.setText("Place landmarks in both volumes to create a landmark transform. Hold your " +
			"mouse over a volume and press 'A'. Turn the volume, move your mouse and press 'A' again to set a " +
			"landmark.")

	def setLandmarkWidgets(self, fixed, moving):
		self.fixedLandmarkWidget = fixed
		self.movingLandmarkWidget = moving

		self.fixedPicker.setPropertiesWidget(self.fixedLandmarkWidget)
		self.movingPicker.setPropertiesWidget(self.movingLandmarkWidget)

	@overrides(TransformationTool)
	def cancelTransform(self):
		del self.multiWidget.transformations[-1]

	@overrides(TransformationTool)
	def applyTransform(self):
		pass

	@overrides(TransformationTool)
	def cleanUp(self):
		self.fixedPicker.cleanUp()
		self.movingPicker.cleanUp()

		for landmarkIndicator in self.landmarkIndicators:
			landmarkIndicator.cleanUp()

		self.landmarkPointSets = []

		self.fixedPicker = Picker()
		self.movingPicker = Picker()

		self.fixedWidget.render()
		self.movingWidget.render()
		self.multiWidget.render()

		self.fixedLandmarkWidget.setVisible(False)
		self.movingLandmarkWidget.setVisible(False)

		self.toolFinished.emit()

	@Slot(int)
	def setActiveLandmark(self, index):
		self.activeIndex = index
		self._update()
		self.fixedWidget.render()
		self.movingWidget.render()
		self.multiWidget.render()

	@Slot(int)
	def landmarkTypeChanged(self, value):
		"""
		Called when the transformation type is changed
		from the combo box. Rigid, Similarity or Affine.
		"""
		self.landmarkTransformType = value
		self._updateTransform()
		self.multiWidget.render()

	@Slot(list)
	def pickedFixedLocation(self, location):
		"""
		Place spheres in fixed widget and in multi-widget.
		The input location should be in local data coordinates.
		"""
		self._pickedLocation(location, "fixed")

	@Slot(list)
	def pickedMovingLocation(self, location):
		"""
		Place spheres in moving widget and in multi-widget.
		The input location should be in local data coordinates.
		"""
		self._pickedLocation(location, "moving")

	def _pickedLocation(self, location, landmarkType):
		if self.activeIndex < len(self.landmarkPointSets):
			# Just update the landmark
			landmarks = [x for x in self.landmarkIndicators if (x.id == self.activeIndex and x.flag == landmarkType)]
			for landmark in landmarks:
				landmark.position = location

			index = 0 if landmarkType == "fixed" else 1
			if not self.landmarkPointSets[self.activeIndex][index]:
				# Add another landmark indicator if there was no landmark
				self._addLandmarkIndicator(location, landmarkType)

			self.landmarkPointSets[self.activeIndex][index] = location
		else:
			# Add the location to the landmark points as a set
			landmarkSet = [location, None] if (landmarkType == "fixed") else [None, location]
			self.landmarkPointSets.append(landmarkSet)
			self._addLandmarkIndicator(location, landmarkType)

		self._updateTransform()
		self._update()
		self.updatedLandmarks.emit(self.landmarkPointSets)
		self.multiWidget.render()
		self.movingWidget.render()

	def _updateTransform(self):
		"""
		Update the landmark transform
		"""
		if PointsSetsIsEmpty(self.landmarkPointSets):
			return

		numberOfSets = NumberOfSets(self.landmarkPointSets)
		fixedPoints = vtkPoints()
		movingPoints = vtkPoints()
		fixedPoints.SetNumberOfPoints(numberOfSets)
		movingPoints.SetNumberOfPoints(numberOfSets)

		pointsetIndex = 0
		for index in range(len(self.landmarkPointSets)):
			pointset = self.landmarkPointSets[index]
			if pointset[0] and pointset[1]:
				fixedPoint = pointset[0]
				movingPoint = pointset[1]
				# Transform the point from the moving landmark with the original transform
				transPoint = self.originalTransform.TransformPoint(movingPoint)
				fixedPoints.SetPoint(pointsetIndex, fixedPoint)
				movingPoints.SetPoint(pointsetIndex, transPoint)
				pointsetIndex += 1

		landmarkTransform = vtkLandmarkTransform()
		if self.landmarkTransformType == 0:
			landmarkTransform.SetModeToRigidBody()
		elif self.landmarkTransformType == 1:
			landmarkTransform.SetModeToSimilarity()
		elif self.landmarkTransformType == 2:
			landmarkTransform.SetModeToAffine()
		landmarkTransform.SetSourceLandmarks(fixedPoints)
		landmarkTransform.SetTargetLandmarks(movingPoints)
		landmarkTransform.Update()

		transform = TransformWithMatrix(landmarkTransform.GetMatrix())
		transform.Inverse()
		
		self.multiWidget.transformations[-1] = Transformation(transform, Transformation.TypeLandmark)
		self._updateLandmarkTransforms()

	def _update(self):
		for landmark in self.landmarkIndicators:
			landmark.active = landmark.id == self.activeIndex
			landmark.update()
		self._updateLandmarkTransforms()

	def _updateLandmarkTransforms(self):
		# Update the transforms
		for landmarkIndicator in self.landmarkIndicators:
			if landmarkIndicator.flag == "moving" and landmarkIndicator.renderer == self.movingWidget.renderer:
				landmarkIndicator.transform = self.multiWidget.transformations.scalingTransform()
				landmarkIndicator.update()
			elif landmarkIndicator.flag == "moving" and landmarkIndicator.renderer == self.multiWidget.renderer:
				landmarkIndicator.transform = self.multiWidget.transformations.completeTransform()
				landmarkIndicator.update()

	def _addLandmarkIndicator(self, location, landmarkType):
		imageData = self.fixedWidget.imageData if landmarkType == "fixed" else self.movingWidget.imageData
		bounds = imageData.GetBounds()
		mean = reduce(lambda x, y: x + y, bounds) / 3.0
		scale = mean / 50.0

		# Create landmark for the correct widget
		widget = self.fixedWidget if landmarkType == "fixed" else self.movingWidget
		landmark = self._landmarkForWidget(widget, landmarkType)
		landmark.id = self.activeIndex
		landmark.position = location
		landmark.scale = scale

		# Create landmark for multi widget
		landmarkMulti = self._landmarkForWidget(self.multiWidget, landmarkType)
		landmarkMulti.id = self.activeIndex
		landmarkMulti.position = location
		landmarkMulti.scale = scale

		self.landmarkIndicators.append(landmark)
		self.landmarkIndicators.append(landmarkMulti)

	def _landmarkForWidget(self, widget, landmarkType):
		return Landmark(index=self.activeIndex,
			renderer=widget.renderer,
			overlay=widget.rendererOverlay,
			flag=landmarkType)


def PointsSetsIsEmpty(points):
	"""
	Returns whether there are actual point sets in the
	given collection for which both landmarks are set.
	"""
	return NumberOfSets(points) == 0


def NumberOfSets(points):
	"""
	Returns the total number of landmark sets in the
	given collection of pointsets.
	"""
	count = 0
	for pointset in points:
		if pointset[0] is not None and pointset[1] is not None:
			count += 1

	return count
