# vim: ts=8:sts=8:sw=8:noexpandtab
#
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

import markups
import sys
from subprocess import Popen
import warnings

from ReText import (getBundledIcon, app_version, globalSettings,
                    readListFromSettings, writeListToSettings, datadirs)
from ReText.tab import (ReTextTab, ReTextWebKitPreview, ReTextWebEnginePreview,
                        PreviewNormal, PreviewLive)
from ReText.dialogs import HtmlDialog, LocaleDialog
from ReText.config import ConfigDialog
from ReText.icontheme import get_icon_theme

try:
	from ReText.fakevimeditor import ReTextFakeVimHandler, FakeVimMode
except ImportError:
	ReTextFakeVimHandler = None

try:
	import enchant
except ImportError:
	enchant = None

from PyQt5.QtCore import QDir, QFile, QFileInfo, QFileSystemWatcher, \
 QIODevice, QLocale, QTextCodec, QTextStream, QTimer, QUrl, Qt
from PyQt5.QtGui import QColor, QDesktopServices, QIcon, \
 QKeySequence, QPalette, QTextDocument, QTextDocumentWriter
from PyQt5.QtWidgets import QAction, QActionGroup, QApplication, QCheckBox, \
 QComboBox, QDesktopWidget, QDialog, QFileDialog, QFontDialog, QInputDialog, \
 QLineEdit, QMainWindow, QMenu, QMessageBox, QTabWidget, QToolBar
from PyQt5.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter

class ReTextWindow(QMainWindow):
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		self.resize(950, 700)
		screenRect = QDesktopWidget().screenGeometry()
		if globalSettings.windowGeometry:
			self.restoreGeometry(globalSettings.windowGeometry)
		else:
			self.move((screenRect.width()-self.width())/2, (screenRect.height()-self.height())/2)
			if not screenRect.contains(self.geometry()):
				self.showMaximized()
		if sys.platform.startswith('darwin'):
			# https://github.com/retext-project/retext/issues/198
			searchPaths = QIcon.themeSearchPaths()
			searchPaths.append('/opt/local/share/icons')
			searchPaths.append('/usr/local/share/icons')
			QIcon.setThemeSearchPaths(searchPaths)
		if globalSettings.iconTheme:
			QIcon.setThemeName(globalSettings.iconTheme)
		if QIcon.themeName() in ('hicolor', ''):
			if not QFile.exists(getBundledIcon('document-new')):
				QIcon.setThemeName(get_icon_theme())
		if QFile.exists(getBundledIcon('retext')):
			self.setWindowIcon(QIcon(getBundledIcon('retext')))
		elif QFile.exists('/usr/share/pixmaps/retext.png'):
			self.setWindowIcon(QIcon('/usr/share/pixmaps/retext.png'))
		else:
			self.setWindowIcon(QIcon.fromTheme('retext',
				QIcon.fromTheme('accessories-text-editor')))
		self.tabWidget = QTabWidget(self)
		self.initTabWidget()
		self.setCentralWidget(self.tabWidget)
		self.tabWidget.currentChanged.connect(self.changeIndex)
		self.tabWidget.tabCloseRequested.connect(self.closeTab)
		toolBar = QToolBar(self.tr('File toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, toolBar)
		self.editBar = QToolBar(self.tr('Edit toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, self.editBar)
		self.searchBar = QToolBar(self.tr('Search toolbar'), self)
		self.addToolBar(Qt.BottomToolBarArea, self.searchBar)
		toolBar.setVisible(not globalSettings.hideToolBar)
		self.editBar.setVisible(not globalSettings.hideToolBar)
		self.actionNew = self.act(self.tr('New'), 'document-new',
			self.createNew, shct=QKeySequence.New)
		self.actionNew.setPriority(QAction.LowPriority)
		self.actionOpen = self.act(self.tr('Open'), 'document-open',
			self.openFile, shct=QKeySequence.Open)
		self.actionOpen.setPriority(QAction.LowPriority)
		self.actionSetEncoding = self.act(self.tr('Set encoding'),
			trig=self.showEncodingDialog)
		self.actionSetEncoding.setEnabled(False)
		self.actionReload = self.act(self.tr('Reload'), 'view-refresh',
			lambda: self.currentTab.readTextFromFile())
		self.actionReload.setEnabled(False)
		self.actionSave = self.act(self.tr('Save'), 'document-save',
			self.saveFile, shct=QKeySequence.Save)
		self.actionSave.setEnabled(False)
		self.actionSave.setPriority(QAction.LowPriority)
		self.actionSaveAs = self.act(self.tr('Save as'), 'document-save-as',
			self.saveFileAs, shct=QKeySequence.SaveAs)
		self.actionNextTab = self.act(self.tr('Next tab'), 'go-next',
			lambda: self.switchTab(1), shct=Qt.CTRL+Qt.Key_PageDown)
		self.actionPrevTab = self.act(self.tr('Previous tab'), 'go-previous',
			lambda: self.switchTab(-1), shct=Qt.CTRL+Qt.Key_PageUp)
		self.actionPrint = self.act(self.tr('Print'), 'document-print',
			self.printFile, shct=QKeySequence.Print)
		self.actionPrint.setPriority(QAction.LowPriority)
		self.actionPrintPreview = self.act(self.tr('Print preview'), 'document-print-preview',
			self.printPreview)
		self.actionViewHtml = self.act(self.tr('View HTML code'), 'text-html', self.viewHtml)
		self.actionChangeEditorFont = self.act(self.tr('Change editor font'),
			trig=self.changeEditorFont)
		self.actionChangePreviewFont = self.act(self.tr('Change preview font'),
			trig=self.changePreviewFont)
		self.actionSearch = self.act(self.tr('Find text'), 'edit-find', shct=QKeySequence.Find)
		self.actionSearch.setCheckable(True)
		self.actionSearch.triggered[bool].connect(self.searchBar.setVisible)
		self.searchBar.visibilityChanged.connect(self.searchBarVisibilityChanged)
		self.actionPreview = self.act(self.tr('Preview'), shct=Qt.CTRL+Qt.Key_E,
			trigbool=self.preview)
		if QIcon.hasThemeIcon('document-preview'):
			self.actionPreview.setIcon(QIcon.fromTheme('document-preview'))
		elif QIcon.hasThemeIcon('preview-file'):
			self.actionPreview.setIcon(QIcon.fromTheme('preview-file'))
		elif QIcon.hasThemeIcon('x-office-document'):
			self.actionPreview.setIcon(QIcon.fromTheme('x-office-document'))
		else:
			self.actionPreview.setIcon(QIcon(getBundledIcon('document-preview')))
		self.actionLivePreview = self.act(self.tr('Live preview'), shct=Qt.CTRL+Qt.Key_L,
		trigbool=self.enableLivePreview)
		menuPreview = QMenu()
		menuPreview.addAction(self.actionLivePreview)
		self.actionPreview.setMenu(menuPreview)
		self.actionTableMode = self.act(self.tr('Table editing mode'),
			shct=Qt.CTRL+Qt.Key_T,
			trigbool=lambda x: self.currentTab.editBox.enableTableMode(x))
		if ReTextFakeVimHandler:
			self.actionFakeVimMode = self.act(self.tr('FakeVim mode'),
				shct=Qt.CTRL+Qt.ALT+Qt.Key_V, trigbool=self.enableFakeVimMode)
			if globalSettings.useFakeVim:
				self.actionFakeVimMode.setChecked(True)
				self.enableFakeVimMode(True)
		self.actionFullScreen = self.act(self.tr('Fullscreen mode'), 'view-fullscreen',
			shct=Qt.Key_F11, trigbool=self.enableFullScreen)
		self.actionFullScreen.setPriority(QAction.LowPriority)
		self.actionConfig = self.act(self.tr('Preferences'), icon='preferences-system',
			trig=self.openConfigDialog)
		self.actionConfig.setMenuRole(QAction.PreferencesRole)
		self.actionSaveHtml = self.act('HTML', 'text-html', self.saveFileHtml)
		self.actionPdf = self.act('PDF', 'application-pdf', self.savePdf)
		self.actionOdf = self.act('ODT', 'x-office-document', self.saveOdf)
		self.getExportExtensionsList()
		self.actionQuit = self.act(self.tr('Quit'), 'application-exit', shct=QKeySequence.Quit)
		self.actionQuit.setMenuRole(QAction.QuitRole)
		self.actionQuit.triggered.connect(self.close)
		self.actionUndo = self.act(self.tr('Undo'), 'edit-undo',
			lambda: self.currentTab.editBox.undo(), shct=QKeySequence.Undo)
		self.actionRedo = self.act(self.tr('Redo'), 'edit-redo',
			lambda: self.currentTab.editBox.redo(), shct=QKeySequence.Redo)
		self.actionCopy = self.act(self.tr('Copy'), 'edit-copy',
			lambda: self.currentTab.editBox.copy(), shct=QKeySequence.Copy)
		self.actionCut = self.act(self.tr('Cut'), 'edit-cut',
			lambda: self.currentTab.editBox.cut(), shct=QKeySequence.Cut)
		self.actionPaste = self.act(self.tr('Paste'), 'edit-paste',
			lambda: self.currentTab.editBox.paste(), shct=QKeySequence.Paste)
		self.actionUndo.setEnabled(False)
		self.actionRedo.setEnabled(False)
		self.actionCopy.setEnabled(False)
		self.actionCut.setEnabled(False)
		qApp = QApplication.instance()
		qApp.clipboard().dataChanged.connect(self.clipboardDataChanged)
		self.clipboardDataChanged()
		if enchant is not None:
			self.actionEnableSC = self.act(self.tr('Enable'), trigbool=self.enableSpellCheck)
			self.actionSetLocale = self.act(self.tr('Set locale'), trig=self.changeLocale)
		self.actionWebKit = self.act(self.tr('Use WebKit renderer'), trigbool=self.enableWebKit)
		if ReTextWebKitPreview is None:
			globalSettings.useWebKit = False
			self.actionWebKit.setEnabled(False)
		self.actionWebKit.setChecked(globalSettings.useWebKit)
		self.actionWebEngine = self.act(self.tr('Use WebEngine (Chromium) renderer'),
			trigbool=self.enableWebEngine)
		if ReTextWebEnginePreview is None:
			globalSettings.useWebEngine = False
		self.actionWebEngine.setChecked(globalSettings.useWebEngine)
		self.actionShow = self.act(self.tr('Show directory'), 'system-file-manager', self.showInDir)
		self.actionFind = self.act(self.tr('Next'), 'go-next', self.find,
			shct=QKeySequence.FindNext)
		self.actionFindPrev = self.act(self.tr('Previous'), 'go-previous',
			lambda: self.find(back=True), shct=QKeySequence.FindPrevious)
		self.actionReplace = self.act(self.tr('Replace'), 'edit-find-replace',
			lambda: self.find(replace=True))
		self.actionReplaceAll = self.act(self.tr('Replace all'), trig=self.replaceAll)
		menuReplace = QMenu()
		menuReplace.addAction(self.actionReplaceAll)
		self.actionReplace.setMenu(menuReplace)
		self.actionCloseSearch = self.act(self.tr('Close'), 'window-close',
			lambda: self.searchBar.setVisible(False))
		self.actionCloseSearch.setPriority(QAction.LowPriority)
		self.actionHelp = self.act(self.tr('Get help online'), 'help-contents', self.openHelp)
		self.aboutWindowTitle = self.tr('About ReText')
		self.actionAbout = self.act(self.aboutWindowTitle, 'help-about', self.aboutDialog)
		self.actionAbout.setMenuRole(QAction.AboutRole)
		self.actionAboutQt = self.act(self.tr('About Qt'))
		self.actionAboutQt.setMenuRole(QAction.AboutQtRole)
		self.actionAboutQt.triggered.connect(qApp.aboutQt)
		availableMarkups = markups.get_available_markups()
		if not availableMarkups:
			print('Warning: no markups are available!')
		if len(availableMarkups) > 1:
			self.chooseGroup = QActionGroup(self)
			markupActions = []
			for markup in availableMarkups:
				markupAction = self.act(markup.name, trigbool=self.markupFunction(markup))
				if markup.name == globalSettings.defaultMarkup:
					markupAction.setChecked(True)
				self.chooseGroup.addAction(markupAction)
				markupActions.append(markupAction)
		self.actionBold = self.act(self.tr('Bold'), shct=QKeySequence.Bold,
			trig=lambda: self.insertFormatting('bold'))
		self.actionItalic = self.act(self.tr('Italic'), shct=QKeySequence.Italic,
			trig=lambda: self.insertFormatting('italic'))
		self.actionUnderline = self.act(self.tr('Underline'), shct=QKeySequence.Underline,
			trig=lambda: self.insertFormatting('underline'))
		self.usefulTags = ('header', 'italic', 'bold', 'underline', 'numbering',
			'bullets', 'image', 'link', 'inline code', 'code block', 'blockquote')
		self.usefulChars = ('deg', 'divide', 'dollar', 'hellip', 'laquo', 'larr',
			'lsquo', 'mdash', 'middot', 'minus', 'nbsp', 'ndash', 'raquo',
			'rarr', 'rsquo', 'times')
		self.formattingBox = QComboBox(self.editBar)
		self.formattingBox.addItem(self.tr('Formatting'))
		self.formattingBox.addItems(self.usefulTags)
		self.formattingBox.activated[str].connect(self.insertFormatting)
		self.symbolBox = QComboBox(self.editBar)
		self.symbolBox.addItem(self.tr('Symbols'))
		self.symbolBox.addItems(self.usefulChars)
		self.symbolBox.activated.connect(self.insertSymbol)
		self.updateStyleSheet()
		menubar = self.menuBar()
		menuFile = menubar.addMenu(self.tr('File'))
		menuEdit = menubar.addMenu(self.tr('Edit'))
		menuHelp = menubar.addMenu(self.tr('Help'))
		menuFile.addAction(self.actionNew)
		menuFile.addAction(self.actionOpen)
		self.menuRecentFiles = menuFile.addMenu(self.tr('Open recent'))
		self.menuRecentFiles.aboutToShow.connect(self.updateRecentFiles)
		menuFile.addAction(self.actionShow)
		menuFile.addAction(self.actionSetEncoding)
		menuFile.addAction(self.actionReload)
		menuFile.addSeparator()
		menuFile.addAction(self.actionSave)
		menuFile.addAction(self.actionSaveAs)
		menuFile.addSeparator()
		menuFile.addAction(self.actionNextTab)
		menuFile.addAction(self.actionPrevTab)
		menuFile.addSeparator()
		menuExport = menuFile.addMenu(self.tr('Export'))
		menuExport.addAction(self.actionSaveHtml)
		menuExport.addAction(self.actionOdf)
		menuExport.addAction(self.actionPdf)
		if self.extensionActions:
			menuExport.addSeparator()
			for action, mimetype in self.extensionActions:
				menuExport.addAction(action)
			menuExport.aboutToShow.connect(self.updateExtensionsVisibility)
		menuFile.addAction(self.actionPrint)
		menuFile.addAction(self.actionPrintPreview)
		menuFile.addSeparator()
		menuFile.addAction(self.actionQuit)
		menuEdit.addAction(self.actionUndo)
		menuEdit.addAction(self.actionRedo)
		menuEdit.addSeparator()
		menuEdit.addAction(self.actionCut)
		menuEdit.addAction(self.actionCopy)
		menuEdit.addAction(self.actionPaste)
		menuEdit.addSeparator()
		if enchant is not None:
			menuSC = menuEdit.addMenu(self.tr('Spell check'))
			menuSC.addAction(self.actionEnableSC)
			menuSC.addAction(self.actionSetLocale)
		menuEdit.addAction(self.actionSearch)
		menuEdit.addAction(self.actionChangeEditorFont)
		menuEdit.addAction(self.actionChangePreviewFont)
		menuEdit.addSeparator()
		if len(availableMarkups) > 1:
			self.menuMode = menuEdit.addMenu(self.tr('Default markup'))
			for markupAction in markupActions:
				self.menuMode.addAction(markupAction)
		menuFormat = menuEdit.addMenu(self.tr('Formatting'))
		menuFormat.addAction(self.actionBold)
		menuFormat.addAction(self.actionItalic)
		menuFormat.addAction(self.actionUnderline)
		if ReTextWebKitPreview is not None or ReTextWebEnginePreview is None:
			menuEdit.addAction(self.actionWebKit)
		else:
			menuEdit.addAction(self.actionWebEngine)
		menuEdit.addSeparator()
		menuEdit.addAction(self.actionViewHtml)
		menuEdit.addAction(self.actionPreview)
		menuEdit.addAction(self.actionTableMode)
		if ReTextFakeVimHandler:
			menuEdit.addAction(self.actionFakeVimMode)
		menuEdit.addSeparator()
		menuEdit.addAction(self.actionFullScreen)
		menuEdit.addAction(self.actionConfig)
		menuHelp.addAction(self.actionHelp)
		menuHelp.addSeparator()
		menuHelp.addAction(self.actionAbout)
		menuHelp.addAction(self.actionAboutQt)
		toolBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		toolBar.addAction(self.actionNew)
		toolBar.addSeparator()
		toolBar.addAction(self.actionOpen)
		toolBar.addAction(self.actionSave)
		toolBar.addAction(self.actionPrint)
		toolBar.addSeparator()
		toolBar.addAction(self.actionPreview)
		toolBar.addAction(self.actionFullScreen)
		self.editBar.addAction(self.actionUndo)
		self.editBar.addAction(self.actionRedo)
		self.editBar.addSeparator()
		self.editBar.addAction(self.actionCut)
		self.editBar.addAction(self.actionCopy)
		self.editBar.addAction(self.actionPaste)
		self.editBar.addSeparator()
		self.editBar.addWidget(self.formattingBox)
		self.editBar.addWidget(self.symbolBox)
		self.searchEdit = QLineEdit(self.searchBar)
		self.searchEdit.setPlaceholderText(self.tr('Search'))
		self.searchEdit.returnPressed.connect(self.find)
		self.replaceEdit = QLineEdit(self.searchBar)
		self.replaceEdit.setPlaceholderText(self.tr('Replace with'))
		self.replaceEdit.returnPressed.connect(self.find)
		self.csBox = QCheckBox(self.tr('Case sensitively'), self.searchBar)
		self.searchBar.addWidget(self.searchEdit)
		self.searchBar.addWidget(self.replaceEdit)
		self.searchBar.addSeparator()
		self.searchBar.addWidget(self.csBox)
		self.searchBar.addAction(self.actionFindPrev)
		self.searchBar.addAction(self.actionFind)
		self.searchBar.addAction(self.actionReplace)
		self.searchBar.addAction(self.actionCloseSearch)
		self.searchBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		self.searchBar.setVisible(False)
		self.autoSaveEnabled = globalSettings.autoSave
		if self.autoSaveEnabled:
			timer = QTimer(self)
			timer.start(60000)
			timer.timeout.connect(self.saveAll)
		self.ind = None
		if enchant is not None:
			self.sl = globalSettings.spellCheckLocale
			try:
				enchant.Dict(self.sl or None)
			except enchant.errors.Error as e:
				warnings.warn(str(e), RuntimeWarning)
				globalSettings.spellCheck = False
			if globalSettings.spellCheck:
				self.actionEnableSC.setChecked(True)
		self.fileSystemWatcher = QFileSystemWatcher()
		self.fileSystemWatcher.fileChanged.connect(self.fileChanged)

	def restoreLastOpenedFiles(self):
		for file in readListFromSettings("lastFileList"):
			self.openFileWrapper(file)

		# Show the tab of last opened file
		lastTabIndex = globalSettings.lastTabIndex
		if lastTabIndex >= 0 and lastTabIndex < self.tabWidget.count():
			self.tabWidget.setCurrentIndex(lastTabIndex)

	def iterateTabs(self):
		for i in range(self.tabWidget.count()):
			yield self.tabWidget.widget(i)

	def updateStyleSheet(self):
		if globalSettings.styleSheet:
			sheetfile = QFile(globalSettings.styleSheet)
			sheetfile.open(QIODevice.ReadOnly)
			self.ss = QTextStream(sheetfile).readAll()
			sheetfile.close()
		else:
			palette = QApplication.palette()
			self.ss = 'html { color: %s; }\n' % palette.color(QPalette.WindowText).name()
			self.ss += 'td, th { border: 1px solid #c3c3c3; padding: 0 3px 0 3px; }\n'
			self.ss += 'table { border-collapse: collapse; }\n'

	def initTabWidget(self):
		def dragEnterEvent(e):
			e.acceptProposedAction()
		def dropEvent(e):
			fn = bytes(e.mimeData().data('text/plain')).decode().rstrip()
			if fn.startswith('file:'):
				fn = QUrl(fn).toLocalFile()
			self.openFileWrapper(fn)
		self.tabWidget.setTabsClosable(True)
		self.tabWidget.setAcceptDrops(True)
		self.tabWidget.setMovable(True)
		self.tabWidget.dragEnterEvent = dragEnterEvent
		self.tabWidget.dropEvent = dropEvent
		if hasattr(self.tabWidget, 'setTabBarAutoHide'):
			self.tabWidget.setTabBarAutoHide(globalSettings.tabBarAutoHide)

	def act(self, name, icon=None, trig=None, trigbool=None, shct=None):
		if not isinstance(shct, QKeySequence):
			shct = QKeySequence(shct)
		if icon:
			action = QAction(self.actIcon(icon), name, self)
		else:
			action = QAction(name, self)
		if trig:
			action.triggered.connect(trig)
		elif trigbool:
			action.setCheckable(True)
			action.triggered[bool].connect(trigbool)
		if shct:
			action.setShortcut(shct)
		return action

	def actIcon(self, name):
		return QIcon.fromTheme(name, QIcon(getBundledIcon(name)))

	def printError(self):
		import traceback
		print('Exception occurred while parsing document:', file=sys.stderr)
		traceback.print_exc()


	def tabFileNameChanged(self, tab):
		'''
		Perform all UI state changes that need to be done when the
		filename of the current tab has changed.
		'''
		if tab == self.currentTab:
			if tab.fileName:
				self.setWindowTitle("")
				self.setWindowFilePath(tab.fileName)
				self.tabWidget.setTabText(self.ind, tab.getBaseName())
				self.tabWidget.setTabToolTip(self.ind, tab.fileName)
				QDir.setCurrent(QFileInfo(tab.fileName).dir().path())
			else:
				self.setWindowFilePath('')
				self.setWindowTitle(self.tr('New document') + '[*]')

			canReload = bool(tab.fileName) and not self.autoSaveActive(tab)
			self.actionSetEncoding.setEnabled(canReload)
			self.actionReload.setEnabled(canReload)

	def tabActiveMarkupChanged(self, tab):
		'''
		Perform all UI state changes that need to be done when the
		active markup class of the current tab has changed.
		'''
		if tab == self.currentTab:
			markupClass = tab.getActiveMarkupClass()
			dtMarkdown = (markupClass == markups.MarkdownMarkup)
			dtMkdOrReST = dtMarkdown or (markupClass == markups.ReStructuredTextMarkup)
			self.formattingBox.setEnabled(dtMarkdown)
			self.symbolBox.setEnabled(dtMarkdown)
			self.actionUnderline.setEnabled(dtMarkdown)
			self.actionBold.setEnabled(dtMkdOrReST)
			self.actionItalic.setEnabled(dtMkdOrReST)

	def tabModificationStateChanged(self, tab):
		'''
		Perform all UI state changes that need to be done when the
		modification state of the current tab has changed.
		'''
		if tab == self.currentTab:
			changed = tab.editBox.document().isModified()
			if self.autoSaveActive(tab):
				changed = False
			self.actionSave.setEnabled(changed)
			self.setWindowModified(changed)

	def createTab(self, fileName):
		self.currentTab = ReTextTab(self, fileName,
			previewState=int(globalSettings.livePreviewByDefault))
		self.currentTab.fileNameChanged.connect(lambda: self.tabFileNameChanged(self.currentTab))
		self.currentTab.modificationStateChanged.connect(lambda: self.tabModificationStateChanged(self.currentTab))
		self.currentTab.activeMarkupChanged.connect(lambda: self.tabActiveMarkupChanged(self.currentTab))
		self.tabWidget.addTab(self.currentTab, self.tr("New document"))
		self.currentTab.updateBoxesVisibility()

	def closeTab(self, ind):
		if self.maybeSave(ind):
			if self.tabWidget.count() == 1:
				self.createTab("")
			closedTab = self.tabWidget.widget(ind)
			if closedTab.fileName:
				self.fileSystemWatcher.removePath(closedTab.fileName)
			self.tabWidget.removeTab(ind)
			closedTab.deleteLater()

	def changeIndex(self, ind):
		'''
		This function is called when a different tab is selected.
		It changes the state of the window to mirror the current state
		of the newly selected tab. Future changes to this state will be
		done in response to signals emitted by the tab, to which the
		window was subscribed when the tab was created. The window is
		subscribed to all tabs like this, but only the active tab will
		logically generate these signals.
		Aside from the above this function also calls the handlers for
		the other changes that are implied by a tab switch: filename
		change, modification state change and active markup change.
		'''
		self.currentTab = self.tabWidget.currentWidget()
		editBox = self.currentTab.editBox
		previewState = self.currentTab.previewState
		self.actionUndo.setEnabled(editBox.document().isUndoAvailable())
		self.actionRedo.setEnabled(editBox.document().isRedoAvailable())
		self.actionCopy.setEnabled(editBox.textCursor().hasSelection())
		self.actionCut.setEnabled(editBox.textCursor().hasSelection())
		self.actionPreview.setChecked(previewState >= PreviewLive)
		self.actionLivePreview.setChecked(previewState == PreviewLive)
		self.actionTableMode.setChecked(editBox.tableModeEnabled)
		self.editBar.setEnabled(previewState < PreviewNormal)
		self.ind = ind
		editBox.setFocus(Qt.OtherFocusReason)

		self.tabFileNameChanged(self.currentTab)
		self.tabModificationStateChanged(self.currentTab)
		self.tabActiveMarkupChanged(self.currentTab)

	def changeEditorFont(self):
		font, ok = QFontDialog.getFont(globalSettings.editorFont, self)
		if ok:
			globalSettings.editorFont = font
			for tab in self.iterateTabs():
				tab.editBox.updateFont()

	def changePreviewFont(self):
		font, ok = QFontDialog.getFont(globalSettings.font, self)
		if ok:
			globalSettings.font = font
			for tab in self.iterateTabs():
				tab.triggerPreviewUpdate()

	def preview(self, viewmode):
		self.currentTab.previewState = viewmode * 2
		self.actionLivePreview.setChecked(False)
		self.editBar.setDisabled(viewmode)
		self.currentTab.updateBoxesVisibility()
		self.currentTab.triggerPreviewUpdate()

	def enableLivePreview(self, livemode):
		self.currentTab.previewState = int(livemode)
		self.actionPreview.setChecked(livemode)
		self.editBar.setEnabled(True)
		self.currentTab.updateBoxesVisibility()
		self.currentTab.triggerPreviewUpdate()

	def enableWebKit(self, enable):
		globalSettings.useWebKit = enable
		globalSettings.useWebEngine = False
		for tab in self.iterateTabs():
			tab.rebuildPreviewBox()

	def enableWebEngine(self, enable):
		globalSettings.useWebKit = False
		globalSettings.useWebEngine = enable
		for tab in self.iterateTabs():
			tab.rebuildPreviewBox()

	def enableCopy(self, copymode):
		self.actionCopy.setEnabled(copymode)
		self.actionCut.setEnabled(copymode)

	def enableFullScreen(self, yes):
		if yes:
			self.showFullScreen()
		else:
			self.showNormal()

	def openConfigDialog(self):
		dlg = ConfigDialog(self)
		dlg.setWindowTitle(self.tr('Preferences'))
		dlg.show()

	def enableFakeVimMode(self, yes):
		globalSettings.useFakeVim = yes
		if yes:
			FakeVimMode.init(self)
			for tab in self.iterateTabs():
				tab.editBox.installFakeVimHandler()
		else:
			FakeVimMode.exit(self)

	def enableSpellCheck(self, yes):
		try:
			dict = enchant.Dict(self.sl or None)
		except enchant.errors.Error as e:
			QMessageBox.warning(self, '', str(e))
			self.actionEnableSC.setChecked(False)
			yes = False
		self.setAllDictionaries(dict if yes else None)
		globalSettings.spellCheck = yes

	def setAllDictionaries(self, dictionary):
		for tab in self.iterateTabs():
			hl = tab.highlighter
			hl.dictionary = dictionary
			hl.rehighlight()

	def changeLocale(self):
		localedlg = LocaleDialog(self, defaultText=self.sl)
		if localedlg.exec() != QDialog.Accepted:
			return
		sl = localedlg.localeEdit.text()
		try:
			enchant.Dict(sl or None)
		except enchant.errors.Error as e:
			QMessageBox.warning(self, '', str(e))
		else:
			self.sl = sl or None
			self.enableSpellCheck(self.actionEnableSC.isChecked())
			if localedlg.checkBox.isChecked():
				globalSettings.spellCheckLocale = sl

	def searchBarVisibilityChanged(self, visible):
		self.actionSearch.setChecked(visible)
		if visible:
			self.searchEdit.setFocus(Qt.ShortcutFocusReason)

	def find(self, back=False, replace=False):
		flags = QTextDocument.FindFlags()
		if back:
			flags |= QTextDocument.FindBackward
		if self.csBox.isChecked():
			flags |= QTextDocument.FindCaseSensitively
		text = self.searchEdit.text()
		replaceText = self.replaceEdit.text() if replace else None
		found = self.currentTab.find(text, flags, replaceText=replaceText)
		self.setSearchEditColor(found)

	def replaceAll(self):
		text = self.searchEdit.text()
		replaceText = self.replaceEdit.text()
		found = self.currentTab.replaceAll(text, replaceText)
		self.setSearchEditColor(found)

	def setSearchEditColor(self, found):
		palette = self.searchEdit.palette()
		palette.setColor(QPalette.Active, QPalette.Base,
		                 Qt.white if found else QColor(255, 102, 102))
		self.searchEdit.setPalette(palette)

	def showInDir(self):
		if self.currentTab.fileName:
			path = QFileInfo(self.currentTab.fileName).path()
			QDesktopServices.openUrl(QUrl.fromLocalFile(path))
		else:
			QMessageBox.warning(self, '', self.tr("Please, save the file somewhere."))

	def moveToTopOfRecentFileList(self, fileName):
		if fileName:
			files = readListFromSettings("recentFileList")
			if fileName in files:
				files.remove(fileName)
			files.insert(0, fileName)
			if len(files) > 10:
				del files[10:]
			writeListToSettings("recentFileList", files)

	def createNew(self, text=None):
		self.createTab("")
		self.ind = self.tabWidget.count()-1
		self.tabWidget.setCurrentIndex(self.ind)
		if text:
			self.currentTab.editBox.textCursor().insertText(text)

	def switchTab(self, shift=1):
		self.tabWidget.setCurrentIndex((self.ind + shift) % self.tabWidget.count())

	def updateRecentFiles(self):
		self.menuRecentFiles.clear()
		self.recentFilesActions = []
		filesOld = readListFromSettings("recentFileList")
		files = []
		for f in filesOld:
			if QFile.exists(f):
				files.append(f)
				self.recentFilesActions.append(self.act(f, trig=self.openFunction(f)))
		writeListToSettings("recentFileList", files)
		for action in self.recentFilesActions:
			self.menuRecentFiles.addAction(action)

	def markupFunction(self, markup):
		return lambda: self.setDefaultMarkup(markup)

	def openFunction(self, fileName):
		return lambda: self.openFileWrapper(fileName)

	def extensionFunction(self, data):
		return lambda: \
		self.runExtensionCommand(data['Exec'], data['FileFilter'], data['DefaultExtension'])

	def getExportExtensionsList(self):
		extensions = []
		for extsprefix in datadirs:
			extsdir = QDir(extsprefix+'/export-extensions/')
			if extsdir.exists():
				for fileInfo in extsdir.entryInfoList(['*.desktop', '*.ini'],
				QDir.Files | QDir.Readable):
					extensions.append(self.readExtension(fileInfo.filePath()))
		locale = QLocale.system().name()
		self.extensionActions = []
		for extension in extensions:
			try:
				if ('Name[%s]' % locale) in extension:
					name = extension['Name[%s]' % locale]
				elif ('Name[%s]' % locale.split('_')[0]) in extension:
					name = extension['Name[%s]' % locale.split('_')[0]]
				else:
					name = extension['Name']
				data = {}
				for prop in ('FileFilter', 'DefaultExtension', 'Exec'):
					if 'X-ReText-'+prop in extension:
						data[prop] = extension['X-ReText-'+prop]
					elif prop in extension:
						data[prop] = extension[prop]
					else:
						data[prop] = ''
				action = self.act(name, trig=self.extensionFunction(data))
				if 'Icon' in extension:
					action.setIcon(self.actIcon(extension['Icon']))
				mimetype = extension['MimeType'] if 'MimeType' in extension else None
			except KeyError:
				print('Failed to parse extension: Name is required', file=sys.stderr)
			else:
				self.extensionActions.append((action, mimetype))

	def updateExtensionsVisibility(self):
		markupClass = self.currentTab.getActiveMarkupClass()
		for action in self.extensionActions:
			if markupClass is None:
				action[0].setEnabled(False)
				continue
			mimetype = action[1]
			if mimetype is None:
				enabled = True
			elif markupClass == markups.MarkdownMarkup:
				enabled = (mimetype in ("text/x-retext-markdown", "text/x-markdown", "text/markdown"))
			elif markupClass == markups.ReStructuredTextMarkup:
				enabled = (mimetype in ("text/x-retext-rst", "text/x-rst"))
			else:
				enabled = False
			action[0].setEnabled(enabled)

	def readExtension(self, fileName):
		extFile = QFile(fileName)
		extFile.open(QIODevice.ReadOnly)
		extension = {}
		stream = QTextStream(extFile)
		while not stream.atEnd():
			line = stream.readLine()
			if '=' in line:
				index = line.index('=')
				extension[line[:index].rstrip()] = line[index+1:].lstrip()
		extFile.close()
		return extension

	def openFile(self):
		supportedExtensions = ['.txt']
		for markup in markups.get_all_markups():
			supportedExtensions += markup.file_extensions
		fileFilter = ' (' + str.join(' ', ['*'+ext for ext in supportedExtensions]) + ');;'
		fileNames = QFileDialog.getOpenFileNames(self,
			self.tr("Select one or several files to open"), QDir.currentPath(),
			self.tr("Supported files") + fileFilter + self.tr("All files (*)"))
		for fileName in fileNames[0]:
			self.openFileWrapper(fileName)

	def openFileWrapper(self, fileName):
		if not fileName:
			return
		fileName = QFileInfo(fileName).canonicalFilePath()
		exists = False
		for i, tab in enumerate(self.iterateTabs()):
			if tab.fileName == fileName:
				exists = True
				ex = i
		if exists:
			self.tabWidget.setCurrentIndex(ex)
		elif QFile.exists(fileName):
			noEmptyTab = (
				(self.ind is None) or
				self.currentTab.fileName or
				self.currentTab.editBox.toPlainText() or
				self.currentTab.editBox.document().isModified()
			)
			if noEmptyTab:
				self.createTab(fileName)
				self.ind = self.tabWidget.count()-1
				self.tabWidget.setCurrentIndex(self.ind)
			if fileName:
				self.fileSystemWatcher.addPath(fileName)
			self.currentTab.readTextFromFile(fileName)
			self.moveToTopOfRecentFileList(self.currentTab.fileName)

	def showEncodingDialog(self):
		if not self.maybeSave(self.ind):
			return
		codecsSet = set(bytes(QTextCodec.codecForName(alias).name())
		                for alias in QTextCodec.availableCodecs())
		encoding, ok = QInputDialog.getItem(self, '',
			self.tr('Select file encoding from the list:'),
			[bytes(b).decode() for b in sorted(codecsSet)],
			0, False)
		if ok:
			self.currentTab.readTextFromFile(None, encoding)

	def saveFileAs(self):
		self.saveFile(dlg=True)

	def saveAll(self):
		for tab in self.iterateTabs():
			if tab.fileName and QFileInfo(tab.fileName).isWritable():
				tab.saveTextToFile()

	def saveFile(self, dlg=False):
		fileNameToSave = self.currentTab.fileName

		if (not fileNameToSave) or dlg:
			markupClass = self.currentTab.getActiveMarkupClass()
			if (markupClass is None) or not hasattr(markupClass, 'default_extension'):
				defaultExt = self.tr("Plain text (*.txt)")
				ext = ".txt"
			else:
				defaultExt = self.tr('%s files',
					'Example of final string: Markdown files') \
					% markupClass.name + ' (' + str.join(' ',
					('*'+extension for extension in markupClass.file_extensions)) + ')'
				if markupClass == markups.MarkdownMarkup:
					ext = globalSettings.markdownDefaultFileExtension
				elif markupClass == markups.ReStructuredTextMarkup:
					ext = globalSettings.restDefaultFileExtension
				else:
					ext = markupClass.default_extension
			fileNameToSave = QFileDialog.getSaveFileName(self,
				self.tr("Save file"), "", defaultExt)[0]
			if fileNameToSave:
				if not QFileInfo(fileNameToSave).suffix():
					fileNameToSave += ext
				# Make sure we don't overwrite a file opened in other tab
				for tab in self.iterateTabs():
					if tab is not self.currentTab and tab.fileName == fileNameToSave:
						QMessageBox.warning(self, "",
							self.tr("Cannot save to file which is open in another tab!"))
						return False
				self.actionSetEncoding.setDisabled(self.autoSaveActive())
		if fileNameToSave:
			if self.currentTab.saveTextToFile(fileNameToSave):
				self.moveToTopOfRecentFileList(self.currentTab.fileName)
				return True
			else:
				QMessageBox.warning(self, '',
				self.tr("Cannot save to file because it is read-only!"))
		return False

	def saveHtml(self, fileName):
		if not QFileInfo(fileName).suffix():
			fileName += ".html"
		try:
			_, htmltext, _ = self.currentTab.getDocumentForExport(includeStyleSheet=False,
				                                              webenv=True)
		except Exception:
			return self.printError()
		htmlFile = QFile(fileName)
		result = htmlFile.open(QIODevice.WriteOnly)
		if not result:
			QMessageBox.warning(self, '',
				self.tr("Cannot save to file because it is read-only!"))
			return
		html = QTextStream(htmlFile)
		if globalSettings.defaultCodec:
			html.setCodec(globalSettings.defaultCodec)
		html << htmltext
		htmlFile.close()

	def textDocument(self, title, htmltext):
		td = QTextDocument()
		td.setMetaInformation(QTextDocument.DocumentTitle, title)
		if self.ss:
			td.setDefaultStyleSheet(self.ss)
		td.setHtml(htmltext)
		td.setDefaultFont(globalSettings.font)
		return td

	def saveOdf(self):
		title, htmltext, _ = self.currentTab.getDocumentForExport(includeStyleSheet=True,
		                                                          webenv=False)
		try:
			document = self.textDocument(title, htmltext)
		except Exception:
			return self.printError()
		fileName = QFileDialog.getSaveFileName(self,
			self.tr("Export document to ODT"), "",
			self.tr("OpenDocument text files (*.odt)"))[0]
		if not QFileInfo(fileName).suffix():
			fileName += ".odt"
		writer = QTextDocumentWriter(fileName)
		writer.setFormat(b"odf")
		writer.write(document)

	def saveFileHtml(self):
		fileName = QFileDialog.getSaveFileName(self,
			self.tr("Save file"), "",
			self.tr("HTML files (*.html *.htm)"))[0]
		if fileName:
			self.saveHtml(fileName)

	def getDocumentForPrint(self, title, htmltext, preview):
		if globalSettings.useWebKit:
			return preview
		try:
			return self.textDocument(title, htmltext)
		except Exception:
			self.printError()

	def standardPrinter(self, title):
		printer = QPrinter(QPrinter.HighResolution)
		printer.setDocName(title)
		printer.setCreator('ReText %s' % app_version)
		return printer

	def savePdf(self):
		fileName = QFileDialog.getSaveFileName(self,
			self.tr("Export document to PDF"),
			"", self.tr("PDF files (*.pdf)"))[0]
		if fileName:
			if not QFileInfo(fileName).suffix():
				fileName += ".pdf"
			title, htmltext, preview = self.currentTab.getDocumentForExport(includeStyleSheet=True,
										        webenv=False)
			printer = self.standardPrinter(title)
			printer.setOutputFormat(QPrinter.PdfFormat)
			printer.setOutputFileName(fileName)
			document = self.getDocumentForPrint(title, htmltext, preview)
			if document != None:
				document.print(printer)

	def printFile(self):
		title, htmltext, preview = self.currentTab.getDocumentForExport(includeStyleSheet=True,
										webenv=False)
		printer = self.standardPrinter(title)
		dlg = QPrintDialog(printer, self)
		dlg.setWindowTitle(self.tr("Print document"))
		if (dlg.exec() == QDialog.Accepted):
			document = self.getDocumentForPrint(title, htmltext, preview)
			if document != None:
				document.print(printer)

	def printPreview(self):
		title, htmltext, preview = self.currentTab.getDocumentForExport(includeStyleSheet=True,
										webenv=False)
		document = self.getDocumentForPrint(title, htmltext, preview)
		if document is None:
			return
		printer = self.standardPrinter(title)
		preview = QPrintPreviewDialog(printer, self)
		preview.paintRequested.connect(document.print)
		preview.exec()

	def runExtensionCommand(self, command, filefilter, defaultext):
		import shlex
		of = ('%of' in command)
		html = ('%html' in command)
		if of:
			if defaultext and not filefilter:
				filefilter = '*'+defaultext
			fileName = QFileDialog.getSaveFileName(self,
				self.tr('Export document'), '', filefilter)[0]
			if not fileName:
				return
			if defaultext and not QFileInfo(fileName).suffix():
				fileName += defaultext
		else:
			fileName = 'out' + defaultext
		basename = '.%s.retext-temp' % self.currentTab.getBaseName()
		if html:
			tmpname = basename+'.html'
			self.saveHtml(tmpname)
		else:
			tmpname = basename + self.currentTab.getActiveMarkupClass().default_extension
			self.currentTab.writeTextToFile(tmpname)
		command = command.replace('%of', shlex.quote(fileName))
		command = command.replace('%html' if html else '%if', shlex.quote(tmpname))
		try:
			Popen(str(command), shell=True).wait()
		except Exception as error:
			errorstr = str(error)
			QMessageBox.warning(self, '', self.tr('Failed to execute the command:')
			+ '\n' + errorstr)
		QFile(tmpname).remove()

	def autoSaveActive(self, tab=None):
		tab = tab if tab else self.currentTab
		return bool(self.autoSaveEnabled and tab.fileName and
			    QFileInfo(tab.fileName).isWritable())

	def clipboardDataChanged(self):
		mimeData = QApplication.instance().clipboard().mimeData()
		if mimeData is not None:
			self.actionPaste.setEnabled(mimeData.hasText() or mimeData.hasImage())

	def insertFormatting(self, formatting):
		cursor = self.currentTab.editBox.textCursor()
		text = cursor.selectedText()
		moveCursorTo = None

		def c(cursor):
			nonlocal moveCursorTo
			moveCursorTo = cursor.position()

		def ensurenl(cursor):
			if not cursor.atBlockStart():
				cursor.insertText('\n\n')

		toinsert = {
			'header': (ensurenl, '# ', text),
			'italic': ('*', text, c, '*'),
			'bold': ('**', text, c, '**'),
			'underline': ('<u>', text, c, '</u>'),
			'numbering': (ensurenl, ' 1. ', text),
			'bullets': (ensurenl, '  * ', text),
			'image': ('![', text or self.tr('Alt text'), c, '](', self.tr('URL'), ')'),
			'link': ('[', text or self.tr('Link text'), c, '](', self.tr('URL'), ')'),
			'inline code': ('`', text, c, '`'),
			'code block': (ensurenl, '    ', text),
			'blockquote': (ensurenl, '> ', text),
		}

		if formatting not in toinsert:
			return

		cursor.beginEditBlock()
		for token in toinsert[formatting]:
			if callable(token):
				token(cursor)
			else:
				cursor.insertText(token)
		cursor.endEditBlock()

		self.formattingBox.setCurrentIndex(0)
		# Bring back the focus on the editor
		self.currentTab.editBox.setFocus(Qt.OtherFocusReason)

		if moveCursorTo:
			cursor.setPosition(moveCursorTo)
			self.currentTab.editBox.setTextCursor(cursor)

	def insertSymbol(self, num):
		if num:
			self.currentTab.editBox.insertPlainText('&'+self.usefulChars[num-1]+';')
		self.symbolBox.setCurrentIndex(0)

	def fileChanged(self, fileName):
		ind = None
		for testind, tab in enumerate(self.iterateTabs()):
			if tab.fileName == fileName:
				ind = testind
		if ind is None:
			self.fileSystemWatcher.removePath(fileName)
		self.tabWidget.setCurrentIndex(ind)
		if not QFile.exists(fileName):
			self.currentTab.editBox.document().setModified(True)
			QMessageBox.warning(self, '', self.tr(
				'This file has been deleted by other application.\n'
				'Please make sure you save the file before exit.'))
		elif not self.currentTab.editBox.document().isModified():
			# File was not modified in ReText, reload silently
			self.currentTab.readTextFromFile()
		else:
			text = self.tr(
				'This document has been modified by other application.\n'
				'Do you want to reload the file (this will discard all '
				'your changes)?\n')
			if self.autoSaveEnabled:
				text += self.tr(
					'If you choose to not reload the file, auto save mode will '
					'be disabled for this session to prevent data loss.')
			messageBox = QMessageBox(QMessageBox.Warning, '', text)
			reloadButton = messageBox.addButton(self.tr('Reload'), QMessageBox.YesRole)
			messageBox.addButton(QMessageBox.Cancel)
			messageBox.exec()
			if messageBox.clickedButton() is reloadButton:
				self.currentTab.readTextFromFile()
			else:
				self.autoSaveEnabled = False
				self.currentTab.editBox.document().setModified(True)
		if fileName not in self.fileSystemWatcher.files():
			# https://github.com/retext-project/retext/issues/137
			self.fileSystemWatcher.addPath(fileName)

	def maybeSave(self, ind):
		tab = self.tabWidget.widget(ind)
		if self.autoSaveActive(tab):
			tab.saveTextToFile()
			return True
		if not tab.editBox.document().isModified():
			return True
		self.tabWidget.setCurrentIndex(ind)
		ret = QMessageBox.warning(self, '',
			self.tr("The document has been modified.\nDo you want to save your changes?"),
			QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
		if ret == QMessageBox.Save:
			return self.saveFile(False)
		elif ret == QMessageBox.Cancel:
			return False
		return True

	def closeEvent(self, closeevent):
		for ind in range(self.tabWidget.count()):
			if not self.maybeSave(ind):
				return closeevent.ignore()
		if globalSettings.saveWindowGeometry:
			globalSettings.windowGeometry = self.saveGeometry()
		if globalSettings.openLastFilesOnStartup:
			files = [tab.fileName for tab in self.iterateTabs()]
			writeListToSettings("lastFileList", files)
			globalSettings.lastTabIndex = self.tabWidget.currentIndex()
		closeevent.accept()

	def viewHtml(self):
		htmlDlg = HtmlDialog(self)
		try:
			_, htmltext, _ = self.currentTab.getDocumentForExport(includeStyleSheet=False,
			                                                      webenv=False)
		except Exception:
			return self.printError()
		winTitle = self.currentTab.getBaseName()
		htmlDlg.setWindowTitle(winTitle+" ("+self.tr("HTML code")+")")
		htmlDlg.textEdit.setPlainText(htmltext.rstrip())
		htmlDlg.hl.rehighlight()
		htmlDlg.show()
		htmlDlg.raise_()
		htmlDlg.activateWindow()

	def openHelp(self):
		QDesktopServices.openUrl(QUrl('https://github.com/retext-project/retext/wiki'))

	def aboutDialog(self):
		QMessageBox.about(self, self.aboutWindowTitle,
		'<p><b>' + (self.tr('ReText %s (using PyMarkups %s)') % (app_version, markups.__version__))
		+'</b></p>' + self.tr('Simple but powerful editor'
		' for Markdown and reStructuredText')
		+'</p><p>'+self.tr('Author: Dmitry Shachnev, 2011').replace('2011', '2011–2017')
		+'<br><a href="https://github.com/retext-project/retext">'+self.tr('Website')
		+'</a> | <a href="http://daringfireball.net/projects/markdown/syntax">'
		+self.tr('Markdown syntax')
		+'</a> | <a href="http://docutils.sourceforge.net/docs/user/rst/quickref.html">'
		+self.tr('reStructuredText syntax')+'</a></p>')

	def setDefaultMarkup(self, markupClass):
		globalSettings.defaultMarkup = markupClass.name
		for tab in self.iterateTabs():
			if not tab.fileName:
				tab.updateActiveMarkupClass()
