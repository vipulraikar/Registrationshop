
from PySide.QtGui import QWidget
from PySide.QtGui import QVBoxLayout
from PySide.QtGui import QPushButton
from PySide.QtGui import QIcon
from core.AppVars import AppVars
from ui.ButtonContainer import ButtonContainer
from ui.ParameterModel import ParameterModel
from ui.TransformationParametersListView import TransformationParameterListView

class ParameterWidget(QWidget):
	"""
	Widget that displays parameters. Holds buttons for 
	acting on the parameters.
	"""
	def __init__(self):
		super(ParameterWidget, self).__init__()

		self.initUI()
		
	def initUI(self):
		# Create container for action buttons
		self.actionContainer = ButtonContainer()
		self.parameterModel = ParameterModel()

		self.parameterView = TransformationParameterListView()
		self.parameterView.setRootIsDecorated(False)
		self.parameterView.setModel(self.parameterModel)

		# Create a main layout (vertical) for this widget
		self.layout = QVBoxLayout()
		self.layout.setSpacing(0)
		self.layout.setContentsMargins(0, 0, 0, 0)
		self.layout.addWidget(self.parameterView)
		self.layout.addWidget(self.actionContainer)

		self.setLayout(self.layout)

		# Add a button to the container
		addButton = QPushButton()
		addButton.setIcon(QIcon(AppVars.imagePath() + "AddButton.png"))
		addButton.clicked.connect(self.addButtonClicked)
		self.actionContainer.addButton(addButton)

		removeButton = QPushButton()
		removeButton.setIcon(QIcon(AppVars.imagePath() + "RemoveButton.png"))
		removeButton.clicked.connect(self.removeButtonClicked)
		self.actionContainer.addButton(removeButton)
		
	def addButtonClicked(self):
		self.parameterView.addParameter()

	def removeButtonClicked(self):
		self.parameterView.removeSelectedParameter()
		# TODO: disable the add/remove buttons when no tranformation is selected
