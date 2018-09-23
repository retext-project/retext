# vim: ts=8:sts=8:sw=8:noexpandtab

# This file is part of ReText
# Copyright: 2012-2017 Dmitry Shachnev
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
import markups
import markups.common
from os.path import dirname, exists, join

from PyQt5.QtCore import QByteArray, QLocale, QSettings, QStandardPaths
from PyQt5.QtGui import QFont

app_version = "7.0.4"

settings = QSettings('ReText project', 'ReText')

if not str(settings.fileName()).endswith('.conf'):
	# We are on Windows probably
	settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
		'ReText project', 'ReText')

datadirs = []

def initializeDataDirs():
	assert not datadirs

	if '__file__' in locals():
		datadirs.append(dirname(dirname(__file__)))

	dataLocations = QStandardPaths.standardLocations(QStandardPaths.GenericDataLocation)
	datadirs.extend(join(d, 'retext') for d in dataLocations)

	if sys.platform == "win32":
		# Windows compatibility: Add "PythonXXX\share\" path
		datadirs.append(join(dirname(sys.executable), 'share', 'retext'))

	# For virtualenvs
	datadirs.append(join(dirname(dirname(sys.executable)), 'share', 'retext'))

_iconPath = None

def getBundledIcon(iconName):
	global _iconPath
	if _iconPath is None:
		for dir in ['icons'] + datadirs:
			_iconPath = join(dir, 'icons')
			if exists(_iconPath):
				break
	return join(_iconPath, iconName + '.png')

configOptions = {
	'appStyleSheet': '',
	'autoSave': False,
	'defaultCodec': '',
	'defaultMarkup': markups.MarkdownMarkup.name,
	'detectEncoding': True,
	'editorFont': QFont(),
	'font': QFont(),
	'handleWebLinks': False,
	'hideToolBar': False,
	'highlightCurrentLine': False,
	'iconTheme': '',
	'lastTabIndex': 0,
	'lineNumbersEnabled': False,
	'livePreviewByDefault': False,
	'markdownDefaultFileExtension': '.mkd',
	'openLastFilesOnStartup': False,
	'pygmentsStyle': 'default',
	'restDefaultFileExtension': '.rst',
	'rightMargin': 0,
	'saveWindowGeometry': False,
	'spellCheck': False,
	'spellCheckLocale': '',
	'styleSheet': '',
	'syncScroll': True,
	'tabBarAutoHide': False,
	'tabInsertsSpaces': True,
	'tabWidth': 4,
	'uiLanguage': QLocale.system().name(),
	'useFakeVim': False,
	'useWebEngine': False,
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

def chooseMonospaceFont():
	font = QFont('monospace')
	font.setStyleHint(QFont.TypeWriter)
	return font

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

	def __getattribute__(self, option):
		value = object.__getattribute__(self, option)
		# Choose a font just-in-time, because when the settings are
		# loaded it is too early to work.
		if option == 'font' and not value.family():
			value = QFont()
		if option == 'editorFont' and not value.family():
			value = chooseMonospaceFont()
		return value

globalSettings = ReTextSettings()

markups.common.PYGMENTS_STYLE = globalSettings.pygmentsStyle
