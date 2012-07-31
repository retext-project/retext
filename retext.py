#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ReText
# Copyright 2011-2012 Dmitry Shachnev

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
from ReText import *
from ReText.window import ReTextWindow

def main(fileNames):
	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	RtTranslator = QTranslator()
	if not RtTranslator.load("retext_"+QLocale.system().name(), "locale"):
		if not RtTranslator.load("retext_"+QLocale.system().name(), "/usr/share/retext/locale"):
			RtTranslator.load("retext_"+QLocale.system().name(), "/usr/lib/retext")
	QtTranslator = QTranslator()
	QtTranslator.load("qt_"+QLocale.system().name(), QLibraryInfo.location(QLibraryInfo.TranslationsPath))
	app.installTranslator(RtTranslator)
	app.installTranslator(QtTranslator)
	if settings.contains('appStyleSheet'):
		stylename = readFromSettings('appStyleSheet', str)
		sheetfile = QFile(stylename)
		sheetfile.open(QIODevice.ReadOnly)
		app.setStyleSheet(QTextStream(sheetfile).readAll())
		sheetfile.close()
	window = ReTextWindow()
	for fileName in fileNames:
		try:
			fileName = QString.fromUtf8(fileName)
		except:
			# Not needed for Python 3
			pass
		if QFile.exists(fileName):
			window.openFileWrapper(fileName)
	window.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	main(sys.argv[1:])
