from ReText import *

class ConfigDialog(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.initConfigOptions()
		self.layout = QGridLayout(self)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Ok |
			QDialogButtonBox.Cancel)
		self.connect(buttonBox, SIGNAL('accepted()'), self.saveSettings)
		self.connect(buttonBox, SIGNAL('rejected()'), self.close)
		self.initWidgets()
		self.layout.addWidget(buttonBox, len(self.options), 0, 1, 2)
	
	def initConfigOptions(self):
		# options is a tuple containing (displayname, name, default) tuples
		self.options = (
			(self.tr('Behavior'), None, None),
			(self.tr('Automatically save documents'), 'autoSave', False),
			(self.tr('Restore window geometry'), 'saveWindowGeometry', False),
			(self.tr('Restore live preview state'), 'restorePreviewState', False),
			(self.tr('Open external links in ReText window'), 'handleWebLinks', False),
			(self.tr('Open unknown files in plain text mode'), 'autoPlainText', True),
			(self.tr('Editor'), None, None),
			(self.tr('Highlight current line'), 'highlightCurrentLine', True),
			(self.tr('Show line numbers'), 'lineNumbersEnabled', False),
			(self.tr('Tab key inserts spaces'), 'tabInsertsSpaces', True),
			(self.tr('Tabulation width'), 'tabWidth', 4),
			(self.tr('Display right margin at column'), 'rightMargin', 0),
			(self.tr('Interface'), None, None),
			(self.tr('Icon theme name'), 'iconTheme', '')
			# Ideas for future: styleSheet, editorFont
		)
	
	def initWidgets(self):
		self.configurators = {}
		for index in range(len(self.options)):
			displayname, name, default = self.options[index]
			if name is None:
				header = QLabel('<h3>%s</h3>' % displayname, self)
				self.layout.addWidget(header, index, 0, 1, 2, Qt.AlignHCenter)
				continue
			value = readFromSettings(name, type(default), default=default)
			label = QLabel(displayname, self)
			if isinstance(default, bool):
				self.configurators[name] = QCheckBox(self)
				self.configurators[name].setChecked(value)
			elif isinstance(default, int):
				self.configurators[name] = QSpinBox(self)
				if name == 'tabWidth':
					self.configurators[name].setRange(1, 10)
				else:
					self.configurators[name].setMaximum(100)
				self.configurators[name].setValue(value)
			elif isinstance(default, str):
				self.configurators[name] = QLineEdit(self)
				self.configurators[name].setText(value)
			self.layout.addWidget(label, index, 0)
			self.layout.addWidget(self.configurators[name], index, 1, Qt.AlignRight)

	def saveSettings(self):
		for displayname, name, default in self.options:
			if name is None:
				continue
			configurator = self.configurators[name]
			if isinstance(default, bool):
				value = configurator.isChecked()
			elif isinstance(default, int):
				value = configurator.value()
			elif isinstance(default, str):
				value = configurator.text()
			writeToSettings(name, value, default)
		self.close()
