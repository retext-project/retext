#!/usr/bin/env python3
# vim: ts=8:sts=8:sw=8:noexpandtab

# ReText
# Copyright 2011-2017 Dmitry Shachnev
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

import multiprocessing as mp
import sys
import signal
import markups
from os import devnull
from os.path import join
from ReText import datadirs, settings, globalSettings, app_version
from ReText import initializeDataDirs
from ReText.window import ReTextWindow

from PyQt5.QtCore import QFile, QFileInfo, QIODevice, QLibraryInfo, \
 QTextStream, QTranslator, Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtNetwork import QNetworkProxyFactory

def canonicalize(option):
	if option in ('--preview', '-'):
		return option
	return QFileInfo(option).canonicalFilePath()

def main():
	if markups.__version_tuple__ < (2, ):
		sys.exit('Error: ReText needs PyMarkups 2.0 or newer to run.')

	# If we're running on Windows without a console, then discard stdout
	# and save stderr to a file to facilitate debugging in case of crashes.
	if sys.executable.endswith('pythonw.exe'):
		sys.stdout = open(devnull, 'w')
		sys.stderr = open('stderr.log', 'w')

	if hasattr(Qt, 'AA_ShareOpenGLContexts'):
		# Needed for Qt WebEngine on Windows
		QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	app.setApplicationDisplayName("ReText")
	app.setApplicationVersion(app_version)
	app.setOrganizationDomain('mitya57.me')
	if hasattr(app, 'setDesktopFileName'): # available since Qt 5.7
		app.setDesktopFileName('me.mitya57.ReText.desktop')
	QNetworkProxyFactory.setUseSystemConfiguration(True)
	initializeDataDirs()
	RtTranslator = QTranslator()
	for path in datadirs:
		if RtTranslator.load('retext_' + globalSettings.uiLanguage,
		                     join(path, 'locale')):
			break
	QtTranslator = QTranslator()
	QtTranslator.load("qtbase_" + globalSettings.uiLanguage,
		QLibraryInfo.location(QLibraryInfo.TranslationsPath))
	app.installTranslator(RtTranslator)
	app.installTranslator(QtTranslator)
	print('Using configuration file:', settings.fileName())
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
	readStdIn = False
	if globalSettings.openLastFilesOnStartup:
		window.restoreLastOpenedFiles()
	for fileName in fileNames:
		if QFile.exists(fileName):
			window.openFileWrapper(fileName)
			if previewMode:
				window.actionPreview.setChecked(True)
				window.preview(True)
		elif fileName == '--preview':
			previewMode = True
		elif fileName == '-':
			readStdIn = True

	inputData = ''
	if readStdIn and sys.stdin is not None:
		if sys.stdin.isatty():
			print('Reading stdin, press ^D to end...')
		inputData = sys.stdin.read()
	if inputData or not window.tabWidget.count():
		window.createNew(inputData)
	signal.signal(signal.SIGINT, lambda sig, frame: window.close())
	sys.exit(app.exec())

if __name__ == '__main__':
	mp.set_start_method('spawn')
	main()
