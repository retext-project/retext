#!/usr/bin/env python3
# vim: ts=8:sts=8:sw=8:noexpandtab

# ReText
# Copyright 2011-2022 Dmitry Shachnev
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

import ctypes
import multiprocessing
import sys
import signal
import markups
from os import devnull
from os.path import join
from ReText import packageDir, settings, globalSettings, app_version
from ReText.window import ReTextWindow

from PyQt6.QtCore import QCommandLineOption, QCommandLineParser, QFile, \
 QFileInfo, QIODevice, QLibraryInfo, QTextStream, QTranslator, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QNetworkProxyFactory
from PyQt6.QtDBus import QDBusConnection, QDBusInterface

def canonicalize(option):
	if option == '-':
		return option
	return QFileInfo(option).canonicalFilePath()

def main():
	multiprocessing.set_start_method('spawn')

	if markups.__version_tuple__ < (2, ):
		sys.exit('Error: ReText needs PyMarkups 2.0 or newer to run.')

	# If we're running on Windows without a console, then discard stdout
	# and save stderr to a file to facilitate debugging in case of crashes.
	if sys.executable.endswith('pythonw.exe'):
		sys.stdout = open(devnull, 'w')
		sys.stderr = open('stderr.log', 'w')

	try:
		# See https://github.com/retext-project/retext/issues/399
		# and https://launchpad.net/bugs/941826
		ctypes.CDLL('libGL.so.1', ctypes.RTLD_GLOBAL)
	except OSError:
		pass

	# Needed for Qt WebEngine on Windows
	QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	app.setApplicationDisplayName("ReText")
	app.setApplicationVersion(app_version)
	app.setOrganizationDomain('mitya57.me')
	app.setDesktopFileName('me.mitya57.ReText.desktop')
	QNetworkProxyFactory.setUseSystemConfiguration(True)

	RtTranslator = QTranslator()
	RtTranslator.load('retext_' + globalSettings.uiLanguage,
	                  join(packageDir, 'locale'))
	QtTranslator = QTranslator()
	translationsPath = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
	QtTranslator.load("qtbase_" + globalSettings.uiLanguage, translationsPath)
	app.installTranslator(RtTranslator)
	app.installTranslator(QtTranslator)

	parser = QCommandLineParser()
	parser.addHelpOption()
	parser.addVersionOption()
	previewOption = QCommandLineOption('preview',
		QApplication.translate('main', 'Open the files in preview mode'))
	newWindowOption = QCommandLineOption('new-window',
		QApplication.translate('main', 'Create a new window even if there is an existing one'))
	parser.addOption(previewOption)
	parser.addOption(newWindowOption)
	parser.addPositionalArgument('files',
		QApplication.translate('main', 'List of files to open'),
		'[files...]')

	parser.process(app)
	filesToOpen = parser.positionalArguments()

	print('Using configuration file:', settings.fileName())
	if globalSettings.appStyleSheet:
		sheetfile = QFile(globalSettings.appStyleSheet)
		sheetfile.open(QIODevice.OpenModeFlag.ReadOnly)
		app.setStyleSheet(QTextStream(sheetfile).readAll())
		sheetfile.close()
	window = ReTextWindow()

	openInExistingWindow = (globalSettings.openFilesInExistingWindow
		and not parser.isSet(newWindowOption))
	connection = QDBusConnection.sessionBus()
	if connection.isConnected() and openInExistingWindow:
		connection.registerObject('/', window, QDBusConnection.RegisterOption.ExportAllSlots)
		serviceName = 'me.mitya57.ReText'
		if not connection.registerService(serviceName) and filesToOpen:
			print('Opening the file(s) in the existing window of ReText.')
			iface = QDBusInterface(serviceName, '/', '', connection)
			for fileName in filesToOpen:
				iface.call('openFileWrapper', fileName)
			qWidgetIface = QDBusInterface(serviceName, '/', 'org.qtproject.Qt.QWidget', connection)
			qWidgetIface.call('raise')
			sys.exit(0)

	window.show()
	# ReText can change directory when loading files, so we
	# need to have a list of canonical names before loading
	fileNames = list(map(canonicalize, filesToOpen))
	readStdIn = False

	if globalSettings.openLastFilesOnStartup:
		window.restoreLastOpenedFiles()
	for fileName in fileNames:
		if QFile.exists(fileName):
			window.openFileWrapper(fileName)
			if parser.isSet(previewOption):
				window.actionPreview.setChecked(True)
				window.preview(True)
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
	main()
