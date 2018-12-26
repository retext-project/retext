from ReText import globalSettings
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTabWidget, \
	QDialogButtonBox, QWidget, QGridLayout, QLabel, QSpinBox


class ClickableLabel(QLabel):
	clicked = pyqtSignal()

	def mousePressEvent(self, event):
		self.clicked.emit()
		super().mousePressEvent(event)


class TableWizardDialog(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.parent = parent
		self.initTableWizardOptions()
		self.layout = QVBoxLayout(self)
		self.tabWidget = QTabWidget(self)
		self.layout.addWidget(self.tabWidget)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Ok | 
			QDialogButtonBox.Cancel)
		buttonBox.accepted.connect(self.makeTable)
		buttonBox.rejected.connect(self.close)
		self.initWidgets()
		self.layout.addWidget(buttonBox)

	def initTableWizardOptions(self):
		self.tabs = (
			(self.tr('Table'), (
				(self.tr('Row'), 'rowCount'),
				(self.tr('Column'), 'columnCount')
			))
		)

	def initWidgets(self):
		self.configurators = {}
		tabTitle = self.tabs[0]
		options = self.tabs[1]

		page = self.getPageWidget(options)
		self.tabWidget.addTab(page, tabTitle)
	
	def getPageWidget(self, options):
		page = QWidget(self)
		layout = QGridLayout(page)
		for index, option in enumerate(options):
			displayname, name = option[:2]
			
			if displayname:
				label = ClickableLabel(displayname + ':', self)
			
			value = getattr(globalSettings, name)
			self.configurators[name] = QSpinBox(self)
			if (name == 'rowCount') or (name == 'columnCount'):
				self.configurators[name].setRange(1,10)
				
			self.configurators[name].setValue(value)
			layout.addWidget(label, index, 0)
			layout.addWidget(self.configurators[name], index, 1, Qt.AlignRight)
		return page

	def makeTable(self):
		rowCount = self.configurators['rowCount'].value()
		columnCount = self.configurators['columnCount'].value()
	

		# Table column's name section (table Header)
		tableHeader = ''
		for column in range(columnCount):
			tableHeader += '|    '
		tableHeader += '|\n'

		for column in range(columnCount):
			tableHeader += '|----'
		tableHeader += '|\n'
		self.parent.currentTab.editBox.insertPlainText(tableHeader)


		# Table Content section (table body)		
		for row in range(rowCount):
			tableBody = ''
			for column in range(columnCount):
				tableBody += '|    '
			tableBody += '|\n'
			self.parent.currentTab.editBox.insertPlainText(tableBody)
		self.close()

