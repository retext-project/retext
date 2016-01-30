# This file is part of ReText
# Copyright: 2012-2015 Dmitry Shachnev
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
from ReText import icon_path, app_version, globalSettings, readListFromSettings, \
 writeListToSettings, writeToSettings, datadirs, enchant, enchant_available
from ReText.tab import ReTextTab, PreviewNormal, PreviewLive
from ReText.dialogs import HtmlDialog, LocaleDialog
from ReText.config import ConfigDialog
from ReText.icontheme import get_icon_theme

try:
	from ReText.fakevimeditor import ReTextFakeVimHandler, FakeVimMode
except ImportError:
	ReTextFakeVimHandler = None

from PyQt5.QtCore import QDir, QFile, QFileInfo, QFileSystemWatcher, \
 QIODevice, QLocale, QRect, QTextCodec, QTextStream, QTimer, QUrl, Qt
from PyQt5.QtGui import QColor, QDesktopServices, QIcon, \
 QKeySequence, QPalette, QTextCursor, QTextDocument, QTextDocumentWriter
from PyQt5.QtWidgets import QAction, QActionGroup, QApplication, QCheckBox, \
 QComboBox, QDesktopWidget, QDialog, QFileDialog, QFontDialog, QInputDialog, \
 QLineEdit, QMainWindow, QMenu, QMenuBar, QMessageBox, QTabWidget, QToolBar
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
		if globalSettings.iconTheme:
			QIcon.setThemeName(globalSettings.iconTheme)
		if QIcon.themeName() in ('hicolor', ''):
			if not QFile.exists(icon_path + 'document-new.png'):
				QIcon.setThemeName(get_icon_theme())
		if QFile.exists(icon_path+'retext.png'):
			self.setWindowIcon(QIcon(icon_path+'retext.png'))
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
			self.actionPreview.setIcon(QIcon(icon_path+'document-preview.png'))
		self.actionLivePreview = self.act(self.tr('Live preview'), shct=Qt.CTRL+Qt.Key_L,
		trigbool=self.enableLivePreview)
		menuPreview = QMenu()
		menuPreview.addAction(self.actionLivePreview)
		self.actionPreview.setMenu(menuPreview)
		self.actionTableMode = self.act(self.tr('Table mode'), shct=Qt.CTRL+Qt.Key_T,
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
		if enchant_available:
			self.actionEnableSC = self.act(self.tr('Enable'), trigbool=self.enableSpellCheck)
			self.actionSetLocale = self.act(self.tr('Set locale'), trig=self.changeLocale)
		self.actionWebKit = self.act(self.tr('Use WebKit renderer'), trigbool=self.enableWebKit)
		self.actionWebKit.setChecked(globalSettings.useWebKit)
		self.actionShow = self.act(self.tr('Show directory'), 'system-file-manager', self.showInDir)
		self.actionFind = self.act(self.tr('Next'), 'go-next', self.find,
			shct=QKeySequence.FindNext)
		self.actionFindPrev = self.act(self.tr('Previous'), 'go-previous',
			lambda: self.find(back=True), shct=QKeySequence.FindPrevious)
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
		self.defaultMarkup = availableMarkups[0] if availableMarkups else None
		if globalSettings.defaultMarkup:
			mc = markups.find_markup_class_by_name(globalSettings.defaultMarkup)
			if mc and mc.available():
				self.defaultMarkup = mc
		if len(availableMarkups) > 1:
			self.chooseGroup = QActionGroup(self)
			markupActions = []
			for markup in availableMarkups:
				markupAction = self.act(markup.name, trigbool=self.markupFunction(markup))
				if markup == self.defaultMarkup:
					markupAction.setChecked(True)
				self.chooseGroup.addAction(markupAction)
				markupActions.append(markupAction)
		self.actionBold = self.act(self.tr('Bold'), shct=QKeySequence.Bold,
			trig=lambda: self.insertChars('**'))
		self.actionItalic = self.act(self.tr('Italic'), shct=QKeySequence.Italic,
			trig=lambda: self.insertChars('*'))
		self.actionUnderline = self.act(self.tr('Underline'), shct=QKeySequence.Underline,
			trig=lambda: self.insertTag('u'))
		self.usefulTags = ('a', 'big', 'center', 'img', 's', 'small', 'span',
			'table', 'td', 'tr', 'u')
		self.usefulChars = ('deg', 'divide', 'dollar', 'hellip', 'laquo', 'larr',
			'lsquo', 'mdash', 'middot', 'minus', 'nbsp', 'ndash', 'raquo',
			'rarr', 'rsquo', 'times')
		self.tagsBox = QComboBox(self.editBar)
		self.tagsBox.addItem(self.tr('Tags'))
		self.tagsBox.addItems(self.usefulTags)
		self.tagsBox.activated.connect(self.insertTag)
		self.symbolBox = QComboBox(self.editBar)
		self.symbolBox.addItem(self.tr('Symbols'))
		self.symbolBox.addItems(self.usefulChars)
		self.symbolBox.activated.connect(self.insertSymbol)
		self.updateStyleSheet()
		menubar = QMenuBar(self)
		menubar.setGeometry(QRect(0, 0, 800, 25))
		self.setMenuBar(menubar)
		menuFile = menubar.addMenu(self.tr('File'))
		menuEdit = menubar.addMenu(self.tr('Edit'))
		menuHelp = menubar.addMenu(self.tr('Help'))
		menuFile.addAction(self.actionNew)
		menuFile.addAction(self.actionOpen)
		self.menuRecentFiles = menuFile.addMenu(self.tr('Open recent'))
		self.menuRecentFiles.aboutToShow.connect(self.updateRecentFiles)
		menuFile.addMenu(self.menuRecentFiles)
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
		if enchant_available:
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
		menuEdit.addAction(self.actionWebKit)
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
		menubar.addMenu(menuFile)
		menubar.addMenu(menuEdit)
		menubar.addMenu(menuHelp)
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
		self.editBar.addWidget(self.tagsBox)
		self.editBar.addWidget(self.symbolBox)
		self.searchEdit = QLineEdit(self.searchBar)
		self.searchEdit.setPlaceholderText(self.tr('Search'))
		self.searchEdit.returnPressed.connect(self.find)
		self.csBox = QCheckBox(self.tr('Case sensitively'), self.searchBar)
		self.searchBar.addWidget(self.searchEdit)
		self.searchBar.addSeparator()
		self.searchBar.addWidget(self.csBox)
		self.searchBar.addAction(self.actionFindPrev)
		self.searchBar.addAction(self.actionFind)
		self.searchBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		self.searchBar.setVisible(False)
		self.autoSaveEnabled = globalSettings.autoSave
		if self.autoSaveEnabled:
			timer = QTimer(self)
			timer.start(60000)
			timer.timeout.connect(self.saveAll)
		self.ind = None
		if enchant_available:
			self.sl = globalSettings.spellCheckLocale
			if self.sl:
				try:
					enchant.Dict(self.sl)
				except Exception as e:
					print(e, file=sys.stderr)
					self.sl = None
			if globalSettings.spellCheck:
				self.actionEnableSC.setChecked(True)
				self.enableSpellCheck(True)
		self.fileSystemWatcher = QFileSystemWatcher()
		self.fileSystemWatcher.fileChanged.connect(self.fileChanged)

	def iterateTabs(self):
		for i in range(self.tabWidget.count()):
			yield self.tabWidget.widget(i).tab

	def updateStyleSheet(self):
		if globalSettings.styleSheet:
			sheetfile = QFile(globalSettings.styleSheet)
			sheetfile.open(QIODevice.ReadOnly)
			self.ss = QTextStream(sheetfile).readAll()
			sheetfile.close()
		else:
			self.ss = ''

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
		return QIcon.fromTheme(name, QIcon(icon_path+name+'.png'))

	def printError(self):
		import traceback
		print('Exception occured while parsing document:', file=sys.stderr)
		traceback.print_exc()

	def createTab(self, fileName):
		self.currentTab = ReTextTab(self, fileName,
			previewState=int(globalSettings.livePreviewByDefault))
		self.tabWidget.addTab(self.currentTab.getSplitter(), self.tr("New document"))

	def closeTab(self, ind):
		if self.maybeSave(ind):
			if self.tabWidget.count() == 1:
				self.createTab("")
			currentWidget = self.tabWidget.widget(ind)
			if currentWidget.tab.fileName:
				self.fileSystemWatcher.removePath(currentWidget.tab.fileName)
			del currentWidget.tab
			self.tabWidget.removeTab(ind)

	def docTypeChanged(self):
		markupClass = self.currentTab.getMarkupClass()
		if type(self.currentTab.markup) != markupClass:
			self.currentTab.setMarkupClass(markupClass)
			self.currentTab.updatePreviewBox()
		dtMarkdown = (markupClass == markups.MarkdownMarkup)
		dtMkdOrReST = dtMarkdown or (markupClass == markups.ReStructuredTextMarkup)
		self.tagsBox.setEnabled(dtMarkdown)
		self.symbolBox.setEnabled(dtMarkdown)
		self.actionUnderline.setEnabled(dtMarkdown)
		self.actionBold.setEnabled(dtMkdOrReST)
		self.actionItalic.setEnabled(dtMkdOrReST)
		canReload = bool(self.currentTab.fileName) and not self.autoSaveActive()
		self.actionSetEncoding.setEnabled(canReload)
		self.actionReload.setEnabled(canReload)

	def changeIndex(self, ind):
		self.currentTab = self.tabWidget.currentWidget().tab
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
		if self.currentTab.fileName:
			self.setCurrentFile()
		else:
			self.setWindowTitle(self.tr('New document') + '[*]')
			self.docTypeChanged()
		self.modificationChanged(editBox.document().isModified())
		editBox.setFocus(Qt.OtherFocusReason)

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
				tab.updatePreviewBox()

	def preview(self, viewmode):
		self.currentTab.previewState = viewmode * 2
		self.actionLivePreview.setChecked(False)
		self.editBar.setDisabled(viewmode)
		self.currentTab.updateBoxesVisibility()
		if viewmode:
			self.currentTab.updatePreviewBox()

	def enableLivePreview(self, livemode):
		self.currentTab.previewState = int(livemode)
		self.actionPreview.setChecked(livemode)
		self.editBar.setEnabled(True)
		self.currentTab.updateBoxesVisibility()
		if livemode:
			self.currentTab.updatePreviewBox()

	def enableWebKit(self, enable):
		globalSettings.useWebKit = enable
		for i in range(self.tabWidget.count()):
			splitter = self.tabWidget.widget(i)
			tab = splitter.tab
			tab.previewBox.setParent(None)
			tab.previewBox.deleteLater()
			tab.previewBox = tab.createPreviewBox()
			tab.previewBox.setMinimumWidth(125)
			splitter.addWidget(tab.previewBox)
			splitter.setSizes((50, 50))
			tab.updatePreviewBox()
			tab.updateBoxesVisibility()

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
				tab.installFakeVimHandler()
		else:
			FakeVimMode.exit(self)

	def enableSpellCheck(self, yes):
		if yes:
			if self.sl:
				self.setAllDictionaries(enchant.Dict(self.sl))
			else:
				self.setAllDictionaries(enchant.Dict())
		else:
			self.setAllDictionaries(None)
		globalSettings.spellCheck = yes

	def setAllDictionaries(self, dictionary):
		for tab in self.iterateTabs():
			hl = tab.highlighter
			hl.dictionary = dictionary
			hl.rehighlight()

	def changeLocale(self):
		if self.sl:
			localedlg = LocaleDialog(self, defaultText=self.sl)
		else:
			localedlg = LocaleDialog(self)
		if localedlg.exec() != QDialog.Accepted:
			return
		sl = localedlg.localeEdit.text()
		setdefault = localedlg.checkBox.isChecked()
		if sl:
			try:
				sl = str(sl)
				enchant.Dict(sl)
			except Exception as e:
				QMessageBox.warning(self, '', str(e))
			else:
				self.sl = sl
				self.enableSpellCheck(self.actionEnableSC.isChecked())
		else:
			self.sl = None
			self.enableSpellCheck(self.actionEnableSC.isChecked())
		if setdefault:
			globalSettings.spellCheckLocale = sl

	def searchBarVisibilityChanged(self, visible):
		self.actionSearch.setChecked(visible)
		if visible:
			self.searchEdit.setFocus(Qt.ShortcutFocusReason)

	def find(self, back=False):
		flags = QTextDocument.FindFlags()
		if back:
			flags |= QTextDocument.FindBackward
		if self.csBox.isChecked():
			flags |= QTextDocument.FindCaseSensitively
		text = self.searchEdit.text()
		editBox = self.currentTab.editBox
		cursor = editBox.textCursor()
		newCursor = editBox.document().find(text, cursor, flags)
		if not newCursor.isNull():
			editBox.setTextCursor(newCursor)
			return self.setSearchEditColor(True)
		cursor.movePosition(QTextCursor.End if back else QTextCursor.Start)
		newCursor = editBox.document().find(text, cursor, flags)
		if not newCursor.isNull():
			editBox.setTextCursor(newCursor)
			return self.setSearchEditColor(True)
		self.setSearchEditColor(False)

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

	def setCurrentFile(self):
		self.setWindowTitle("")
		self.tabWidget.setTabText(self.ind, self.currentTab.getDocumentTitle(baseName=True))
		self.setWindowFilePath(self.currentTab.fileName)
		files = readListFromSettings("recentFileList")
		while self.currentTab.fileName in files:
			files.remove(self.currentTab.fileName)
		files.insert(0, self.currentTab.fileName)
		if len(files) > 10:
			del files[10:]
		writeListToSettings("recentFileList", files)
		QDir.setCurrent(QFileInfo(self.currentTab.fileName).dir().path())
		self.docTypeChanged()

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
		markupClass = self.currentTab.getMarkupClass()
		for action in self.extensionActions:
			if markupClass is None:
				action[0].setEnabled(False)
				continue
			mimetype = action[1]
			if mimetype == None:
				enabled = True
			elif markupClass == markups.MarkdownMarkup:
				enabled = (mimetype in ("text/x-retext-markdown", "text/x-markdown"))
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
			self.tr("Select one or several files to open"), "",
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
			self.currentTab.fileName = fileName
			self.currentTab.readTextFromFile()
			editBox = self.currentTab.editBox
			self.setCurrentFile()
			self.setWindowModified(editBox.document().isModified())

	def showEncodingDialog(self):
		if not self.maybeSave(self.ind):
			return
		encoding, ok = QInputDialog.getItem(self, '',
			self.tr('Select file encoding from the list:'),
			[bytes(b).decode() for b in QTextCodec.availableCodecs()],
			0, False)
		if ok:
			self.currentTab.readTextFromFile(encoding)

	def saveFileAs(self):
		self.saveFile(dlg=True)

	def saveAll(self):
		for tab in self.iterateTabs():
			if tab.fileName and QFileInfo(tab.fileName).isWritable():
				tab.saveTextToFile()
				tab.editBox.document().setModified(False)

	def saveFile(self, dlg=False):
		if (not self.currentTab.fileName) or dlg:
			markupClass = self.currentTab.getMarkupClass()
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
			newFileName = QFileDialog.getSaveFileName(self,
				self.tr("Save file"), "", defaultExt)[0]
			if newFileName:
				if not QFileInfo(newFileName).suffix():
					newFileName += ext
				if self.currentTab.fileName:
					self.fileSystemWatcher.removePath(self.currentTab.fileName)
				self.currentTab.fileName = newFileName
				self.actionSetEncoding.setDisabled(self.autoSaveActive())
		if self.currentTab.fileName:
			if self.currentTab.saveTextToFile():
				self.setCurrentFile()
				self.currentTab.editBox.document().setModified(False)
				self.setWindowModified(False)
				return True
			else:
				QMessageBox.warning(self, '',
				self.tr("Cannot save to file because it is read-only!"))
		return False

	def saveHtml(self, fileName):
		if not QFileInfo(fileName).suffix():
			fileName += ".html"
		try:
			htmltext = self.currentTab.getHtml(includeStyleSheet=False,
				includeMeta=True, webenv=True)
		except Exception:
			return self.printError()
		htmlFile = QFile(fileName)
		htmlFile.open(QIODevice.WriteOnly)
		html = QTextStream(htmlFile)
		if globalSettings.defaultCodec:
			html.setCodec(globalSettings.defaultCodec)
		html << htmltext
		htmlFile.close()

	def textDocument(self):
		td = QTextDocument()
		td.setMetaInformation(QTextDocument.DocumentTitle,
		                      self.currentTab.getDocumentTitle())
		if self.ss:
			td.setDefaultStyleSheet(self.ss)
		td.setHtml(self.currentTab.getHtml())
		td.setDefaultFont(globalSettings.font)
		return td

	def saveOdf(self):
		try:
			document = self.textDocument()
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

	def getDocumentForPrint(self):
		if globalSettings.useWebKit:
			return self.currentTab.previewBox
		try:
			return self.textDocument()
		except Exception:
			self.printError()

	def standardPrinter(self):
		printer = QPrinter(QPrinter.HighResolution)
		printer.setDocName(self.currentTab.getDocumentTitle())
		printer.setCreator('ReText %s' % app_version)
		return printer

	def savePdf(self):
		self.currentTab.updatePreviewBox()
		fileName = QFileDialog.getSaveFileName(self,
			self.tr("Export document to PDF"),
			"", self.tr("PDF files (*.pdf)"))[0]
		if fileName:
			if not QFileInfo(fileName).suffix():
				fileName += ".pdf"
			printer = self.standardPrinter()
			printer.setOutputFormat(QPrinter.PdfFormat)
			printer.setOutputFileName(fileName)
			document = self.getDocumentForPrint()
			if document != None:
				document.print(printer)

	def printFile(self):
		self.currentTab.updatePreviewBox()
		printer = self.standardPrinter()
		dlg = QPrintDialog(printer, self)
		dlg.setWindowTitle(self.tr("Print document"))
		if (dlg.exec() == QDialog.Accepted):
			document = self.getDocumentForPrint()
			if document != None:
				document.print(printer)

	def printPreview(self):
		document = self.getDocumentForPrint()
		if document == None:
			return
		printer = self.standardPrinter()
		preview = QPrintPreviewDialog(printer, self)
		preview.paintRequested.connect(document.print)
		preview.exec()

	def runExtensionCommand(self, command, filefilter, defaultext):
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
		basename = '.%s.retext-temp' % self.currentTab.getDocumentTitle(baseName=True)
		if html:
			tmpname = basename+'.html'
			self.saveHtml(tmpname)
		else:
			tmpname = basename + self.currentTab.getMarkupClass().default_extension
			self.currentTab.saveTextToFile(fileName=tmpname, addToWatcher=False)
		command = command.replace('%of', '"out'+defaultext+'"')
		command = command.replace('%html' if html else '%if', '"'+tmpname+'"')
		try:
			Popen(str(command), shell=True).wait()
		except Exception as error:
			errorstr = str(error)
			QMessageBox.warning(self, '', self.tr('Failed to execute the command:')
			+ '\n' + errorstr)
		QFile(tmpname).remove()
		if of:
			QFile('out'+defaultext).rename(fileName)

	def autoSaveActive(self, ind=None):
		tab = self.currentTab if ind is None else self.tabWidget.widget(ind).tab
		return (self.autoSaveEnabled and tab.fileName and
			QFileInfo(tab.fileName).isWritable())

	def modificationChanged(self, changed):
		if self.autoSaveActive():
			changed = False
		self.actionSave.setEnabled(changed)
		self.setWindowModified(changed)

	def clipboardDataChanged(self):
		mimeData = QApplication.instance().clipboard().mimeData()
		if mimeData is not None:
			self.actionPaste.setEnabled(mimeData.hasText())

	def insertChars(self, chars):
		tc = self.currentTab.editBox.textCursor()
		if tc.hasSelection():
			selection = tc.selectedText()
			if selection.startswith(chars) and selection.endswith(chars):
				if len(selection) > 2*len(chars):
					selection = selection[len(chars):-len(chars)]
					tc.insertText(selection)
			else:
				tc.insertText(chars+tc.selectedText()+chars)
		else:
			tc.insertText(chars)

	def insertTag(self, ut):
		if not ut:
			return
		if isinstance(ut, int):
			ut = self.usefulTags[ut - 1]
		arg = ' style=""' if ut == 'span' else ''
		tc = self.currentTab.editBox.textCursor()
		if ut == 'img':
			toinsert = ('<a href="' + tc.selectedText() +
			'" target="_blank"><img src="' + tc.selectedText() + '"/></a>')
		elif ut == 'a':
			toinsert = ('<a href="' + tc.selectedText() +
			'" target="_blank">' + tc.selectedText() + '</a>')
		else:
			toinsert = '<'+ut+arg+'>'+tc.selectedText()+'</'+ut+'>'
		tc.insertText(toinsert)
		self.tagsBox.setCurrentIndex(0)

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
			self.currentTab.updatePreviewBox()
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
				self.currentTab.updatePreviewBox()
			else:
				self.autoSaveEnabled = False
				self.currentTab.editBox.document().setModified(True)
		if fileName not in self.fileSystemWatcher.files():
			# https://github.com/retext-project/retext/issues/137
			self.fileSystemWatcher.addPath(fileName)

	def maybeSave(self, ind):
		tab = self.tabWidget.widget(ind).tab
		if self.autoSaveActive(ind):
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
		if globalSettings.saveWindowGeometry and not self.isMaximized():
			globalSettings.windowGeometry = self.saveGeometry()
		closeevent.accept()

	def viewHtml(self):
		htmlDlg = HtmlDialog(self)
		try:
			htmltext = self.currentTab.getHtml(includeStyleSheet=False,
				includeTitle=False)
		except Exception:
			return self.printError()
		winTitle = self.currentTab.getDocumentTitle(baseName=True)
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
		+'</p><p>'+self.tr('Author: Dmitry Shachnev, 2011').replace('2011', '2011\u2013' '2015')
		+'<br><a href="https://github.com/retext-project/retext">'+self.tr('Website')
		+'</a> | <a href="http://daringfireball.net/projects/markdown/syntax">'
		+self.tr('Markdown syntax')
		+'</a> | <a href="http://docutils.sourceforge.net/docs/user/rst/quickref.html">'
		+self.tr('reStructuredText syntax')+'</a></p>')

	def setDefaultMarkup(self, markupClass):
		self.defaultMarkup = markupClass
		defaultName = markups.get_available_markups()[0].name
		writeToSettings('defaultMarkup', markupClass.name, defaultName)
		for tab in self.iterateTabs():
			if not tab.fileName:
				tab.setMarkupClass(markupClass)
				tab.updatePreviewBox()
		self.docTypeChanged()
