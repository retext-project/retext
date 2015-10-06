# This file is part of ReText
# Copyright: 2012-2014 Dmitry Shachnev
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

import markups
import markups.common
from os.path import join, abspath

from PyQt5.QtCore import QByteArray, QLocale, QSettings, QStandardPaths
from PyQt5.QtGui import QFont

app_version = "5.2.1"

settings = QSettings('ReText project', 'ReText')
print('Using configuration file:', settings.fileName())

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
	'autoSave': False,
	'colorSchemeFile': '',
	'defaultCodec': '',
	'defaultMarkup': '',
	'editorFont': QFont('monospace'),
	'font': QFont(),
	'handleWebLinks': False,
	'hideToolBar': False,
	'highlightCurrentLine': False,
	'iconTheme': '',
	'lineNumbersEnabled': False,
	'markdownDefaultFileExtension': '.mkd',
	'previewState': False,
	'pygmentsStyle': 'default',
	'restDefaultFileExtension': '.rst',
	'restorePreviewState': False,
	'rightMargin': 0,
	'saveWindowGeometry': False,
	'spellCheck': False,
	'spellCheckLocale': '',
	'styleSheet': '',
	'tabInsertsSpaces': True,
	'tabWidth': 4,
	'uiLanguage': QLocale.system().name(),
	'useFakeVim': False,
	'useWebKit': False,
	'windowGeometry': QByteArray(),
}

def readFromSettings(key, keytype, settings=settings, default=None):
	if isinstance(default, QFont):
		family = readFromSettings(key, str, settings, default.family())
		size = readFromSettings(key + 'Size', int, settings, 0)
		return QFont(family, size)
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
	if isinstance(value, QFont):
		writeToSettings(key, value.family(), '', settings)
		writeToSettings(key + 'Size', max(value.pointSize(), 0), 0, settings)
	elif value == default:
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

datadirs = QStandardPaths.standardLocations(QStandardPaths.GenericDataLocation)
datadirs = [abspath('.')] + [join(d, 'retext') for d in datadirs]
