# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

import markups
import markups.common
import sys
from os.path import join, abspath

if '--pyqt4' in sys.argv:
	from PyQt4 import QtCore, QtGui, QtWebKit
elif '--pyside' in sys.argv:
	from PySide import QtCore, QtGui, QtWebKit
else:
	try:
		from PyQt5 import QtCore, QtPrintSupport, QtGui, QtWidgets, QtWebKit, QtWebKitWidgets
	except ImportError:
		try:
			from PyQt4 import QtCore, QtGui, QtWebKit
		except ImportError:
			from PySide import QtCore, QtGui, QtWebKit

if not 'QtWidgets' in locals():
	# PyQt4 or PySide
	QtPrintSupport, QtWidgets, QtWebKitWidgets = QtGui, QtGui, QtWebKit

(QByteArray, QDir, QSettings) = (QtCore.QByteArray, QtCore.QDir, QtCore.QSettings)
QFont = QtGui.QFont

app_name = "ReText"
app_version = "4.1.3"

settings = QSettings('ReText project', 'ReText')

if not str(settings.fileName()).endswith('.conf'):
	# We are on Windows probably
	settings = QSettings(QSettings.IniFormat, QSettings.UserScope, 
		'ReText project', 'ReText')

try:
	import enchant
	import enchant.errors
except ImportError:
	enchant_available = False
	enchant = None
else:
	enchant_available = True
	try:
		enchant.Dict()
	except enchant.errors.Error:
		enchant_available = False

icon_path = "icons/"

DOCTYPE_NONE = ''
DOCTYPE_MARKDOWN = markups.MarkdownMarkup.name
DOCTYPE_REST = markups.ReStructuredTextMarkup.name
DOCTYPE_HTML = 'html'

configOptions = {
	'appStyleSheet': '',
	'autoPlainText': True,
	'autoSave': False,
	'defaultMarkup': '',
	'editorFont': 'monospace',
	'editorFontSize': 0,
	'font': '',
	'fontSize': 0,
	'iconTheme': '',
	'handleWebLinks': False,
	'hideToolBar': False,
	'highlightCurrentLine': False,
	'lineNumbersEnabled': False,
	'previewState': False,
	'pygmentsStyle': 'default',
	'restorePreviewState': False,
	'rightMargin': 0,
	'saveWindowGeometry': False,
	'spellCheck': False,
	'spellCheckLocale': '',
	'styleSheet': '',
	'tabInsertsSpaces': True,
	'tabWidth': 4,
	'useWebKit': False,
	'windowGeometry': QByteArray(),
}

def readFromSettings(key, keytype, settings=settings, default=None):
	if not settings.contains(key):
		return default
	try:
		value = settings.value(key, type=keytype)
		if isinstance(value, keytype):
			return value
		# PySide returns strings instead of ints and bools
		if (isinstance(value, str) and value.lower() == 'false'
		and keytype is bool):
			return False
		return keytype(value)
	except TypeError as error:
		# Type mismatch
		print('Warning: '+str(error))
		# Return an instance of keytype
		return default if (default is not None) else keytype()

def readListFromSettings(key, settings=settings):
	if not settings.contains(key):
		return []
	value = settings.value(key)
	if isinstance(value, str):
		return [value]
	else:
		return value

def writeToSettings(key, value, default, settings=settings):
	if value == default:
		settings.remove(key)
	else:
		settings.setValue(key, value)

def writeListToSettings(key, value, settings=settings):
	if len(value) > 1:
		settings.setValue(key, value)
	elif len(value) == 1:
		settings.setValue(key, value[0])
	else:
		settings.remove(key)

class ReTextSettings(object):
	def __init__(self):
		for option in configOptions:
			value = configOptions[option]
			object.__setattr__(self, option, readFromSettings(
				option, type(value), default=value))
	
	def __setattr__(self, option, value):
		if not option in configOptions:
			raise AttributeError('Unknown attribute')
		object.__setattr__(self, option, value)
		writeToSettings(option, value, configOptions[option])

globalSettings = ReTextSettings()

markups.common.PYGMENTS_STYLE = globalSettings.pygmentsStyle

monofont = QFont()
monofont.setFamily(globalSettings.editorFont)
if globalSettings.editorFontSize:
	monofont.setPointSize(globalSettings.editorFontSize)

currentpath = abspath('.')
if hasattr(QtCore, 'QStandardPaths'):
	datadirs = QtCore.QStandardPaths.standardLocations(
		QtCore.QStandardPaths.GenericDataLocation)
	datadirs = [currentpath] + [join(d, 'retext') for d in datadirs]
else:
	datadirs = (
		currentpath,
		'/usr/share/retext',
		'/usr/local/share/retext',
		QDir.homePath()+'/.local/share/retext'
	)
