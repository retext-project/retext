#!/usr/bin/env python3

# ReText
# Copyright 2011-2015 Dmitry Shachnev
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
import signal
import logging
import os
from os.path import join
import markdown
import markups.mdx_mathjax
import markups
from ReText import datadirs, globalSettings, app_version
from ReText.window import ReTextWindow

from PyQt5.QtCore import QFile, QFileInfo, QIODevice, QLibraryInfo, \
 QTextStream, QTranslator
from PyQt5.QtWidgets import QApplication
from PyQt5.QtNetwork import QNetworkProxyFactory

logging.basicConfig(filename=os.path.dirname(os.path.realpath(__file__)) + os.sep + 'retext.log',
                    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

def canonicalize(option):
	if option == '--preview':
		return option
	return QFileInfo(option).canonicalFilePath()

def main():
	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	app.setApplicationDisplayName("ReText")
	app.setApplicationVersion(app_version)
	app.setOrganizationDomain('mitya57.me')
	if hasattr(app, 'setDesktopFileName'): # available since Qt 5.7
		app.setDesktopFileName('me.mitya57.ReText.desktop')
	QNetworkProxyFactory.setUseSystemConfiguration(True)
	RtTranslator = QTranslator()
	for path in datadirs:
		if RtTranslator.load('retext_' + globalSettings.uiLanguage,
		                     join(path, 'locale')):
			break
	QtTranslator = QTranslator()
	QtTranslator.load("qt_" + globalSettings.uiLanguage,
		QLibraryInfo.location(QLibraryInfo.TranslationsPath))
	app.installTranslator(RtTranslator)
	app.installTranslator(QtTranslator)
	if globalSettings.appStyleSheet:
		sheetfile = QFile(globalSettings.appStyleSheet)
		sheetfile.open(QIODevice.ReadOnly)
		app.setStyleSheet(QTextStream(sheetfile).readAll())
		sheetfile.close()
	window = ReTextWindow()
	window.show()
	# ReText can change directory when loading files, so we
	# need to have a list of canonical names before loading
	fileNames = list(map(canonicalize, sys.argv[1:]))
	previewMode = False
	for fileName in fileNames:
		if QFile.exists(fileName):
			window.openFileWrapper(fileName)
			if previewMode:
				window.actionPreview.trigger()
		elif fileName == '--preview':
			previewMode = True
	if sys.stdin:
		inputData = '' if sys.stdin.isatty() else sys.stdin.read()
		if inputData or not window.tabWidget.count():
			window.createNew(inputData)
	signal.signal(signal.SIGINT, lambda sig, frame: window.close())
	sys.exit(app.exec())

if __name__ == '__main__':
	try:
		main()
	except Exception as e:
		logger.exception(e)
