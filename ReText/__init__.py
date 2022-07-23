# vim: ts=8:sts=8:sw=8:noexpandtab

# This file is part of ReText
# Copyright: 2012-2022 Dmitry Shachnev
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
from os.path import abspath, dirname, join, expanduser

from PyQt6.QtCore import QByteArray, QLocale, QSettings
from PyQt6.QtGui import QFont, QFontDatabase

app_version = "8.0.0"

settings = QSettings('ReText project', 'ReText')

if not str(settings.fileName()).endswith('.conf'):
	# We are on Windows probably
	settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
		'ReText project', 'ReText')


packageDir = abspath(dirname(__file__))

def getBundledIcon(iconName):
	return join(packageDir, 'icons', iconName + '.png')


configOptions = {
	'appStyleSheet': '',
	'autoSave': False,
	'defaultCodec': '',
	'defaultMarkup': markups.MarkdownMarkup.name,
	'defaultPreviewState': 'editor',
	'detectEncoding': True,
	'directoryPath': expanduser("~"),
	'documentStatsEnabled': False,
	'editorFont': '',
	'font': '',
	'handleWebLinks': False,
	'hideToolBar': False,
	'highlightCurrentLine': 'disabled',
	'iconTheme': '',
	'lastTabIndex': 0,
	'lineNumbersEnabled': False,
	'markdownDefaultFileExtension': '.mkd',
	'openFilesInExistingWindow': True,
	'openLastFilesOnStartup': False,
	'orderedListMode': 'increment',
	'paperSize': '',
	'pygmentsStyle': 'default',
	'recentDocumentsCount': 10,
	'relativeLineNumbers': False,
	'restDefaultFileExtension': '.rst',
	'rightMargin': 0,
	'rightMarginWrap': False,
	'saveWindowGeometry': False,
	'showDirectoryTree': False,
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
	'wideCursor': False,
	'windowGeometry': QByteArray(),
	'windowTitleFullPath': False,
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

def getSettingsFilePath(settings=settings):
	return settings.fileName()


class ReTextSettings:
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

	def getPreviewFont(self):
		font = QFont()
		if self.font:
			font.fromString(self.font)
		return font

	def getEditorFont(self):
		font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
		if self.editorFont:
			font.fromString(self.editorFont)
		return font

globalSettings = ReTextSettings()

markups.common.PYGMENTS_STYLE = globalSettings.pygmentsStyle
