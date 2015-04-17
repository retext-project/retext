# This file is part of ReText
# Copyright: Dmitry Shachnev 2012-2014
# License: GNU GPL v2 or higher

import markups
import markups.common
from os.path import join, abspath

from PyQt5.QtCore import QByteArray, QLocale, QSettings, QStandardPaths
from PyQt5.QtGui import QFont

app_name = "ReText"
app_version = "5.0.2"

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
	'colorSchemeFile': '',
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
	'uiLanguage': QLocale.system().name(),
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

datadirs = QStandardPaths.standardLocations(QStandardPaths.GenericDataLocation)
datadirs = [abspath('.')] + [join(d, 'retext') for d in datadirs]
