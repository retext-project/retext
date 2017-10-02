# This file is part of ReText
# Copyright: 2013-2017 Dmitry Shachnev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from ReText import globalSettings, getBundledIcon, getSettingsFilePath
from ReText.icontheme import get_icon_theme
from markups.common import CONFIGURATION_DIR
from os.path import join

from PyQt5.QtCore import QFile, QFileInfo, QUrl, Qt
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, \
 QFileDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox

MKD_EXTS_FILE = join(CONFIGURATION_DIR, 'markdown-extensions.txt')

class FileSelectButton(QPushButton):
	def __init__(self, parent, fileName):
		QPushButton.__init__(self, parent)
		self.fileName = fileName
		self.defaultText = self.tr('(none)')
		self.updateButtonText()
		self.clicked.connect(self.processClick)

	def processClick(self):
		startDir = (QFileInfo(self.fileName).absolutePath()
		            if self.fileName else '')
		self.fileName = QFileDialog.getOpenFileName(
			self, self.tr('Select file to open'), startDir)[0]
		self.updateButtonText()

	def updateButtonText(self):
		if self.fileName:
			self.setText(QFileInfo(self.fileName).fileName())
		else:
			self.setText(self.defaultText)

class ConfigDialog(QDialog):
	def __init__(self, parent):
		QDialog.__init__(self, parent)
		self.parent = parent
		self.initConfigOptions()
		self.layout = QGridLayout(self)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Ok |
			QDialogButtonBox.Cancel)
		buttonBox.accepted.connect(self.saveSettings)
		buttonBox.rejected.connect(self.close)
		self.initWidgets()
		self.configurators['rightMargin'].valueChanged.connect(self.handleRightMarginSet)
		self.layout.addWidget(buttonBox, len(self.options)+1, 0, 1, 2)

	def initConfigOptions(self):
		# options is a tuple containing (displayname, name) tuples
		self.options = (
			(self.tr('Behavior'), None),
			(self.tr('Automatically save documents'), 'autoSave'),
			(self.tr('Automatically open last documents on startup'), 'openLastFilesOnStartup'),
			(self.tr('Restore window geometry'), 'saveWindowGeometry'),
			(self.tr('Use live preview by default'), 'livePreviewByDefault'),
			(self.tr('Open external links in ReText window'), 'handleWebLinks'),
			(self.tr('Markdown syntax extensions (comma-separated)'), 'markdownExtensions'),
			(None, 'markdownExtensions'),
			(self.tr('Enable synchronized scrolling for Markdown'), 'syncScroll'),
		#	(self.tr('Default Markdown file extension'), 'markdownDefaultFileExtension'),
		#	(self.tr('Default reStructuredText file extension'), 'restDefaultFileExtension'),
			(self.tr('Editor'), None),
			(self.tr('Highlight current line'), 'highlightCurrentLine'),
			(self.tr('Show line numbers'), 'lineNumbersEnabled'),
			(self.tr('Line numbers are relative to current line'), 'relativeLineNumbers'),
			(self.tr('Tab key inserts spaces'), 'tabInsertsSpaces'),
			(self.tr('Tabulation width'), 'tabWidth'),
			(self.tr('Draw vertical line at column'), 'rightMargin'),
			(self.tr('Enable soft wrap'), 'rightMarginWrap'),
			(self.tr('Show document stats'), 'documentStatsEnabled'),
			(self.tr('Interface'), None),
			(self.tr('Icon theme name'), 'iconTheme'),
			(self.tr('Stylesheet file'), 'styleSheet', True),
		)

	def initWidgets(self):
		self.configurators = {}
		for index, option in enumerate(self.options):
			displayname, name = option[:2]
			fileselector = option[2] if len(option) > 2 else False
			if name is None:
				header = QLabel('<h3>%s</h3>' % displayname, self)
				self.layout.addWidget(header, index, 0, 1, 2, Qt.AlignHCenter)
				continue
			if displayname:
				label = QLabel(displayname + ':', self)
			if name == 'markdownExtensions':
				if displayname:
					url = QUrl('https://github.com/retext-project/retext/wiki/Markdown-extensions')
					helpButton = QPushButton(self.tr('Help'), self)
					helpButton.clicked.connect(lambda: QDesktopServices.openUrl(url))
					self.layout.addWidget(label, index, 0)
					self.layout.addWidget(helpButton, index, 1)
					continue
				try:
					extsFile = open(MKD_EXTS_FILE)
					value = extsFile.read().rstrip().replace(extsFile.newlines, ', ')
					extsFile.close()
				except Exception:
					value = ''
				self.configurators[name] = QLineEdit(self)
				self.configurators[name].setText(value)
				self.layout.addWidget(self.configurators[name], index, 0, 1, 2)
				continue
			value = getattr(globalSettings, name)
			if isinstance(value, bool):
				self.configurators[name] = QCheckBox(self)
				self.configurators[name].setChecked(value)
				if name == 'rightMarginWrap' and (globalSettings.rightMargin == 0):
					self.configurators[name].setEnabled(False)
			elif isinstance(value, int):
				self.configurators[name] = QSpinBox(self)
				if name == 'tabWidth':
					self.configurators[name].setRange(1, 10)
				else:
					self.configurators[name].setMaximum(200)
				self.configurators[name].setValue(value)
			elif isinstance(value, str) and fileselector:
				self.configurators[name] = FileSelectButton(self, value)
			elif isinstance(value, str):
				self.configurators[name] = QLineEdit(self)
				self.configurators[name].setText(value)
			self.layout.addWidget(label, index, 0)
			self.layout.addWidget(self.configurators[name], index, 1, Qt.AlignRight)
		# Display the current config file
		label = QLabel(self.tr('Using configuration file at:'), self)
		self.layout.addWidget(label, len(self.options), 0)
		path = getSettingsFilePath()
		pathLabel = QLabel('<a href="file://'+path+'">'+path+'</a>', self)
		pathLabel.linkActivated.connect(self.openLink)
		self.layout.addWidget(pathLabel, len(self.options), 1)

	def handleRightMarginSet(self, value):
		if value > 0:
			self.configurators['rightMarginWrap'].setEnabled(True)
			self.configurators['rightMarginWrap'].setChecked(globalSettings.rightMarginWrap)
		else:
			self.configurators['rightMarginWrap'].setChecked(False)
			self.configurators['rightMarginWrap'].setEnabled(False)

	def saveSettings(self):
		for option in self.options:
			name = option[1]
			if name is None or name == 'markdownExtensions':
				continue
			configurator = self.configurators[name]
			if isinstance(configurator, QCheckBox):
				value = configurator.isChecked()
			elif isinstance(configurator, QSpinBox):
				value = configurator.value()
			elif isinstance(configurator, QLineEdit):
				value = configurator.text()
			elif isinstance(configurator, FileSelectButton):
				value = configurator.fileName
			setattr(globalSettings, name, value)
		self.applySettings()
		self.close()

	def applySettings(self):
		QIcon.setThemeName(globalSettings.iconTheme)
		if QIcon.themeName() in ('hicolor', ''):
			if not QFile.exists(getBundledIcon('document-new')):
				QIcon.setThemeName(get_icon_theme())
		try:
			extsFile = open(MKD_EXTS_FILE, 'w')
			for ext in self.configurators['markdownExtensions'].text().split(','):
				if ext.strip():
					extsFile.write(ext.strip() + '\n')
			extsFile.close()
		except Exception as e:
			print(e, file=sys.stderr)
		for tab in self.parent.iterateTabs():
			tab.editBox.updateFont()
			tab.editBox.setWrapModeAndWidth()
			tab.editBox.viewport().update()
		self.parent.updateStyleSheet()

	def openLink(self, link):
		QDesktopServices.openUrl(QUrl(link))
