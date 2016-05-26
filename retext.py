#!/usr/bin/env python3
# vim: ts=8:sts=8:sw=8:noexpandtab

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

import multiprocessing as mp
import sys
import signal
import markups
import struct
import json
from os import devnull
from os.path import join
from ReText import datadirs, settings, globalSettings, app_version
from ReText.window import ReTextWindow
from ReText.singleapplication import SingleApplication

from PyQt5.QtCore import QFile, QFileInfo, QIODevice, QLibraryInfo, \
 QTextStream, QTranslator, QTimer
from PyQt5.QtWidgets import QApplication, qApp
from PyQt5.QtNetwork import QNetworkProxyFactory

def canonicalize(option):
	if option == '--preview':
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

	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	app.setApplicationDisplayName("ReText")
	app.setApplicationVersion(app_version)
	app.setOrganizationDomain('mitya57.me')
	if hasattr(app, 'setDesktopFileName'): # available since Qt 5.7
		app.setDesktopFileName('me.mitya57.ReText.desktop')

	singleApp = SingleApplication("D1278E7822F011E6802800F1F38F93EF")
	singleApp.start()
	if singleApp.mode == singleApp.Client:
		# When we in client mode, we just send the arguments to existed
		# appliaction and exit
		message = json.dumps(list(map(canonicalize, sys.argv[1:])))
		singleApp.sendMessage(message.encode('utf-8'))
		
		# Exit the application immediately after send message 
		timer = QTimer()
		timer.setSingleShot(True)
		timer.setInterval(0)
		timer.timeout.connect(app.quit)
		timer.start()
		
		# We should clear some messages before exit
		sys.exit(app.exec())
		return
		
	def onReceivedMessage(message):
		for widget in qApp.topLevelWidgets():
			isMainWindow = widget.property("_mainWindow_")
			if isMainWindow is None:
				continue
				
			fileNames = json.loads(message.decode('utf-8'))
			for fileName in fileNames:
				if QFile.exists(fileName):
					widget.openFileWrapper(fileName)
			break
	singleApp.receivedMessage.connect(onReceivedMessage)

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
	print('Using configuration file:', settings.fileName())
	if globalSettings.appStyleSheet:
		sheetfile = QFile(globalSettings.appStyleSheet)
		sheetfile.open(QIODevice.ReadOnly)
		app.setStyleSheet(QTextStream(sheetfile).readAll())
		sheetfile.close()
	window = ReTextWindow()
	# Mark this window so that we could find it while we received message. 
	window.setProperty("_mainWindow_", True)
	window.show()
	# ReText can change directory when loading files, so we
	# need to have a list of canonical names before loading
	fileNames = list(map(canonicalize, sys.argv[1:]))
	previewMode = False
	for fileName in fileNames:
		if QFile.exists(fileName):
			window.openFileWrapper(fileName)
			if previewMode:
				window.actionPreview.setChecked(True)
				window.preview(True)
		elif fileName == '--preview':
			previewMode = True
	inputData = '' if (sys.stdin is None or sys.stdin.isatty()) else sys.stdin.read()
	if inputData or not window.tabWidget.count():
		window.createNew(inputData)
	signal.signal(signal.SIGINT, lambda sig, frame: window.close())
	sys.exit(app.exec())

if __name__ == '__main__':
	mp.set_start_method('spawn')
	main()
