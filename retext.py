#!/usr/bin/env python3

# ReText
# Copyright 2011-2013 Dmitry Shachnev

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import sys
import signal
from ReText import QtCore, QtWidgets, QtWebKit, datadirs, globalSettings
from ReText.window import ReTextWindow

(QFile, QFileInfo, QIODevice, QLibraryInfo, QLocale, QTextStream,
 QTranslator) = (QtCore.QFile, QtCore.QFileInfo, QtCore.QIODevice,
 QtCore.QLibraryInfo, QtCore.QLocale, QtCore.QTextStream, QtCore.QTranslator)
QApplication = QtWidgets.QApplication
QWebSettings = QtWebKit.QWebSettings

def main():
	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	if hasattr(app, 'setApplicationDisplayName'):
		app.setApplicationDisplayName("ReText")
	RtTranslator = QTranslator()
	for path in datadirs:
		if RtTranslator.load('retext_'+QLocale.system().name(), path+'/locale'):
			break
	QtTranslator = QTranslator()
	QtTranslator.load("qt_"+QLocale.system().name(), QLibraryInfo.location(QLibraryInfo.TranslationsPath))
	app.installTranslator(RtTranslator)
	app.installTranslator(QtTranslator)
	if globalSettings.appStyleSheet:
		sheetfile = QFile(globalSettings.appStyleSheet)
		sheetfile.open(QIODevice.ReadOnly)
		app.setStyleSheet(QTextStream(sheetfile).readAll())
		sheetfile.close()
	# A work-around for https://bugs.webkit.org/show_bug.cgi?id=114618
	webSettings = QWebSettings.globalSettings()
	webSettings.setFontFamily(QWebSettings.FixedFont, 'monospace')
	window = ReTextWindow()
	window.show()
	fileNames = [QFileInfo(arg).canonicalFilePath() for arg in sys.argv[1:]]
	for fileName in fileNames:
		if QFile.exists(fileName):
			window.openFileWrapper(fileName)
	signal.signal(signal.SIGINT, lambda sig, frame: window.close())
	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
