# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

import markups
from subprocess import Popen, PIPE

try:
	from PyQt4.QtCore import *
	from PyQt4.QtGui import *
except ImportError:
	from PySide.QtCore import *
	from PySide.QtGui import *
	use_pyside = True
else:
	use_pyside = False

app_name = "ReText"
app_version = "4.0.0"

settings = QSettings('ReText project', 'ReText')

if not str(settings.fileName()).endswith('.conf'):
	# We are on Windows probably
	settings = QSettings(QSettings.IniFormat, QSettings.UserScope, 
		'ReText project', 'ReText')

try:
	import enchant
	enchant.Dict()
except:
	enchant_available = False
else:
	enchant_available = True

icon_path = "icons/"

DOCTYPE_NONE = ''
DOCTYPE_MARKDOWN = markups.MarkdownMarkup.name
DOCTYPE_REST = markups.ReStructuredTextMarkup.name
DOCTYPE_HTML = 'html'

try:
	if use_pyside:
		from PySide.QtWebKit import QWebView, QWebPage
	else:
		from PyQt4.QtWebKit import QWebView, QWebPage
except ImportError:
	webkit_available = False
else:
	webkit_available = True

def readFromSettings(key, keytype, settings=settings, default=None):
	if not settings.contains(key):
		return default
	try:
		return settings.value(key, type=keytype)
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

monofont = QFont()
monofont.setFamily(readFromSettings('editorFont', str, default='monospace'))
if settings.contains('editorFontSize'):
	monofont.setPointSize(readFromSettings('editorFontSize', int))

datadirs = (
	'.',
	'/usr/share/retext',
	'/usr/local/share/retext',
	QDir.homePath()+'/.local/share/retext'
)
