# vim: noexpandtab:ts=4:sw=4
# This file is part of ReText
# Copyright: Dmitry Shachnev 2012-2014
# License: GNU GPL v2 or higher

import markups
import sys
from subprocess import Popen
from markups.common import MODULE_HOME_PAGE
from ReText import icon_path, DOCTYPE_MARKDOWN, DOCTYPE_REST, app_name, \
 app_version, globalSettings, settings, readListFromSettings, \
 writeListToSettings, writeToSettings, datadirs, enchant, enchant_available
from ReText.webpages import wpInit, wpUpdateAll
from ReText.dialogs import HtmlDialog, LocaleDialog
from ReText.config import ConfigDialog
from ReText.highlighter import ReTextHighlighter
from ReText.editor import ReTextEdit

from PyQt5.QtCore import QDir, QFile, QFileInfo, QIODevice, QLocale, QRect, \
 QTextCodec, QTextStream, QTimer, QUrl, Qt
from PyQt5.QtGui import QColor, QDesktopServices, QFont, QFontMetrics, QIcon, \
 QKeySequence, QPalette, QTextCursor, QTextDocument, QTextDocumentWriter
from PyQt5.QtWidgets import QAction, QActionGroup, QApplication, QCheckBox, \
 QComboBox, QDesktopWidget, QDialog, QFileDialog, QFontDialog, QInputDialog, \
 QLineEdit, QMainWindow, QMenuBar, QMessageBox, QSplitter, QTabWidget, \
 QTextBrowser, QTextEdit, QToolBar
from PyQt5.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtWebKitWidgets import QWebPage, QWebView

class ReTextWindow(QMainWindow):
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		self.initConfig()
		self.resize(800, 600)
		if globalSettings.windowGeometry:
			self.restoreGeometry(globalSettings.windowGeometry)
		else:
			screen = QDesktopWidget().screenGeometry()
			size = self.geometry()
			self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
		if globalSettings.iconTheme:
			QIcon.setThemeName(globalSettings.iconTheme)
		if QFile.exists(icon_path+'retext.png'):
			self.setWindowIcon(QIcon(icon_path+'retext.png'))
		elif QFile.exists('/usr/share/pixmaps/retext.png'):
			self.setWindowIcon(QIcon('/usr/share/pixmaps/retext.png'))
		else:
			self.setWindowIcon(QIcon.fromTheme('retext', QIcon.fromTheme('accessories-text-editor')))
		self.editBoxes = []
		self.previewBoxes = []
		self.highlighters = []
		self.markups = []
		self.fileNames = []
		self.actionPreviewChecked = []
		self.actionLivePreviewChecked = []
		self.actionPlainTextChecked = []
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
		self.actionReload = self.act(self.tr('Reload'), 'view-refresh', trig=self.openFileMain)
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
		self.actionChangeFont = self.act(self.tr('Change default font'), trig=self.changeFont)
		self.actionSearch = self.act(self.tr('Find text'), 'edit-find', shct=QKeySequence.Find)
		self.actionSearch.setCheckable(True)
		self.actionSearch.triggered[bool].connect(self.searchBar.setVisible)
		self.searchBar.visibilityChanged.connect(self.searchBarVisibilityChanged)
		self.actionPreview = self.act(self.tr('Preview'), shct=Qt.CTRL+Qt.Key_E, trigbool=self.preview)
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
		self.actionTableMode = self.act(self.tr('Table mode'), shct=Qt.CTRL+Qt.Key_T,
			trigbool=lambda x: self.editBoxes[self.ind].enableTableMode(x))
		self.actionFullScreen = self.act(self.tr('Fullscreen mode'), 'view-fullscreen',
			shct=Qt.Key_F11, trigbool=self.enableFullScreen)
		self.actionConfig = self.act(self.tr('Preferences'), icon='preferences-system',
			trig=self.openConfigDialog)
		self.actionSaveHtml = self.act('HTML', 'text-html', self.saveFileHtml)
		self.actionPdf = self.act('PDF', 'application-pdf', self.savePdf)
		self.actionOdf = self.act('ODT', 'x-office-document', self.saveOdf)
		self.getExportExtensionsList()
		self.actionQuit = self.act(self.tr('Quit'), 'application-exit', shct=QKeySequence.Quit)
		self.actionQuit.setMenuRole(QAction.QuitRole)
		self.actionQuit.triggered.connect(self.close)
		self.actionUndo = self.act(self.tr('Undo'), 'edit-undo',
			lambda: self.editBoxes[self.ind].undo(), shct=QKeySequence.Undo)
		self.actionRedo = self.act(self.tr('Redo'), 'edit-redo',
			lambda: self.editBoxes[self.ind].redo(), shct=QKeySequence.Redo)
		self.actionCopy = self.act(self.tr('Copy'), 'edit-copy',
			lambda: self.editBoxes[self.ind].copy(), shct=QKeySequence.Copy)
		self.actionCut = self.act(self.tr('Cut'), 'edit-cut',
			lambda: self.editBoxes[self.ind].cut(), shct=QKeySequence.Cut)
		self.actionPaste = self.act(self.tr('Paste'), 'edit-paste',
			lambda: self.editBoxes[self.ind].paste(), shct=QKeySequence.Paste)
		self.actionUndo.setEnabled(False)
		self.actionRedo.setEnabled(False)
		self.actionCopy.setEnabled(False)
		self.actionCut.setEnabled(False)
		qApp = QApplication.instance()
		qApp.clipboard().dataChanged.connect(self.clipboardDataChanged)
		self.clipboardDataChanged()
		if enchant_available:
			self.actionEnableSC = self.act(self.tr('Enable'), trigbool=self.enableSC)
			self.actionSetLocale = self.act(self.tr('Set locale'), trig=self.changeLocale)
		self.actionPlainText = self.act(self.tr('Plain text'), trigbool=self.enablePlainText)
		self.actionWebKit = self.act(self.tr('Use WebKit renderer'), trigbool=self.enableWebKit)
		self.actionWebKit.setChecked(globalSettings.useWebKit)
		self.actionWpgen = self.act(self.tr('Generate webpages'), trig=self.startWpgen)
		self.actionShow = self.act(self.tr('Show'), 'system-file-manager', self.showInDir)
		self.actionFind = self.act(self.tr('Next'), 'go-next', self.find,
			shct=QKeySequence.FindNext)
		self.actionFindPrev = self.act(self.tr('Previous'), 'go-previous',
			lambda: self.find(back=True), shct=QKeySequence.FindPrevious)
		self.actionHelp = self.act(self.tr('Get help online'), 'help-contents', self.openHelp)
		self.aboutWindowTitle = self.tr('About %s', 'Example of final string: About ReText')
		self.aboutWindowTitle = self.aboutWindowTitle % app_name
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
		if globalSettings.styleSheet:
			sheetfile = QFile(globalSettings.styleSheet)
			sheetfile.open(QIODevice.ReadOnly)
			self.ss = QTextStream(sheetfile).readAll()
			sheetfile.close()
		else:
			self.ss = ''
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
		self.menuDir = menuFile.addMenu(self.tr('Directory'))
		self.menuDir.addAction(self.actionShow)
		self.menuDir.addAction(self.actionWpgen)
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
		menuEdit.addAction(self.actionPlainText)
		menuEdit.addAction(self.actionChangeFont)
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
		menuEdit.addAction(self.actionLivePreview)
		menuEdit.addAction(self.actionPreview)
		menuEdit.addAction(self.actionTableMode)
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
				self.enableSC(True)

	def initConfig(self):
		self.font = None
		if globalSettings.font:
			self.font = QFont(globalSettings.font)
		if self.font and globalSettings.fontSize:
			self.font.setPointSize(globalSettings.fontSize)

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

	def getSplitter(self, index):
		splitter = QSplitter(Qt.Horizontal)
		# Give both boxes a minimum size so the minimumSizeHint will be
		# ignored when splitter.setSizes is called below
		for widget in self.editBoxes[index], self.previewBoxes[index]:
			widget.setMinimumWidth(125)
			splitter.addWidget(widget)
		splitter.setSizes((50, 50))
		splitter.setChildrenCollapsible(False)
		return splitter

	def getWebView(self):
		webView = QWebView()
		if not globalSettings.handleWebLinks:
			webView.page().setLinkDelegationPolicy(QWebPage.DelegateExternalLinks)
			webView.page().linkClicked.connect(QDesktopServices.openUrl)
		webView.settings().setAttribute(QWebSettings.LocalContentCanAccessFileUrls, False)
		return webView

	def createTab(self, fileName):
		self.previewBlocked = False
		self.editBoxes.append(ReTextEdit(self))
		self.highlighters.append(ReTextHighlighter(self.editBoxes[-1].document()))
		if enchant_available and self.actionEnableSC.isChecked():
			self.highlighters[-1].dictionary = \
			enchant.Dict(self.sl) if self.sl else enchant.Dict()
			self.highlighters[-1].rehighlight()
		if globalSettings.useWebKit:
			self.previewBoxes.append(self.getWebView())
		else:
			self.previewBoxes.append(QTextBrowser())
			self.previewBoxes[-1].setOpenExternalLinks(True)
		self.previewBoxes[-1].setVisible(False)
		self.fileNames.append(fileName)
		markupClass = self.getMarkupClass(fileName)
		self.markups.append(self.getMarkup(fileName))
		self.highlighters[-1].docType = (markupClass.name if markupClass else '')
		liveMode = globalSettings.restorePreviewState and globalSettings.previewState
		self.actionPreviewChecked.append(liveMode)
		self.actionLivePreviewChecked.append(liveMode)
		self.actionPlainTextChecked.append(False)
		metrics = QFontMetrics(self.editBoxes[-1].font())
		self.editBoxes[-1].setTabStopWidth(globalSettings.tabWidth * metrics.width(' '))
		self.editBoxes[-1].textChanged.connect(self.updateLivePreviewBox)
		self.editBoxes[-1].undoAvailable.connect(self.actionUndo.setEnabled)
		self.editBoxes[-1].redoAvailable.connect(self.actionRedo.setEnabled)
		self.editBoxes[-1].copyAvailable.connect(self.enableCopy)
		self.editBoxes[-1].document().modificationChanged.connect(self.modificationChanged)
		return self.getSplitter(-1)

	def closeTab(self, ind):
		if self.maybeSave(ind):
			if self.tabWidget.count() == 1:
				self.tabWidget.addTab(self.createTab(""), self.tr("New document"))
			del self.editBoxes[ind]
			del self.previewBoxes[ind]
			del self.highlighters[ind]
			del self.markups[ind]
			del self.fileNames[ind]
			del self.actionPreviewChecked[ind]
			del self.actionLivePreviewChecked[ind]
			del self.actionPlainTextChecked[ind]
			self.tabWidget.removeTab(ind)

	def getMarkupClass(self, fileName=None):
		if fileName is None:
			fileName = self.fileNames[self.ind]
		if self.actionPlainText.isChecked():
			return
		if fileName:
			markupClass = markups.get_markup_for_file_name(
				fileName, return_class=True)
			if markupClass:
				return markupClass
		return self.defaultMarkup

	def getMarkup(self, fileName=None):
		if fileName is None:
			fileName = self.fileNames[self.ind]
		markupClass = self.getMarkupClass(fileName=fileName)
		if markupClass and markupClass.available():
			return markupClass(filename=fileName)

	def docTypeChanged(self):
		oldType = self.highlighters[self.ind].docType
		markupClass = self.getMarkupClass()
		newType = markupClass.name if markupClass else ''
		if oldType != newType:
			self.markups[self.ind] = self.getMarkup()
			self.updatePreviewBox()
			self.highlighters[self.ind].docType = newType
			self.highlighters[self.ind].rehighlight()
		dtMarkdown = (newType == DOCTYPE_MARKDOWN)
		dtMkdOrReST = (newType in (DOCTYPE_MARKDOWN, DOCTYPE_REST))
		self.tagsBox.setEnabled(dtMarkdown)
		self.symbolBox.setEnabled(dtMarkdown)
		self.actionUnderline.setEnabled(dtMarkdown)
		self.actionBold.setEnabled(dtMkdOrReST)
		self.actionItalic.setEnabled(dtMkdOrReST)
		canReload = bool(self.fileNames[self.ind]) and not self.autoSaveActive()
		self.actionSetEncoding.setEnabled(canReload)
		self.actionReload.setEnabled(canReload)

	def changeIndex(self, ind):
		if ind > -1:
			self.actionPlainText.setChecked(self.actionPlainTextChecked[ind])
			self.actionSaveHtml.setDisabled(self.actionPlainTextChecked[ind])
			self.actionViewHtml.setDisabled(self.actionPlainTextChecked[ind])
			self.actionUndo.setEnabled(self.editBoxes[ind].document().isUndoAvailable())
			self.actionRedo.setEnabled(self.editBoxes[ind].document().isRedoAvailable())
			self.actionCopy.setEnabled(self.editBoxes[ind].textCursor().hasSelection())
			self.actionCut.setEnabled(self.editBoxes[ind].textCursor().hasSelection())
			self.actionPreview.setChecked(self.actionPreviewChecked[ind])
			self.actionLivePreview.setChecked(self.actionLivePreviewChecked[ind])
			self.actionTableMode.setChecked(self.editBoxes[ind].tableModeEnabled)
			self.editBar.setDisabled(self.actionPreviewChecked[ind])
		self.ind = ind
		if self.fileNames[ind]:
			self.setCurrentFile()
		else:
			self.setWindowTitle(self.tr('New document') + '[*]')
			self.docTypeChanged()
		self.modificationChanged(self.editBoxes[ind].document().isModified())
		if globalSettings.restorePreviewState:
			globalSettings.previewState = self.actionLivePreviewChecked[ind]
		if self.actionLivePreviewChecked[ind]:
			self.enableLivePreview(True)
		self.editBoxes[self.ind].setFocus(Qt.OtherFocusReason)

	def changeFont(self):
		if not self.font:
			self.font = QFont()
		fd = QFontDialog.getFont(self.font, self)
		if fd[1]:
			self.font = QFont()
			self.font.setFamily(fd[0].family())
			settings.setValue('font', fd[0].family())
			self.font.setPointSize(fd[0].pointSize())
			settings.setValue('fontSize', fd[0].pointSize())
			self.updatePreviewBox()

	def preview(self, viewmode):
		self.actionPreviewChecked[self.ind] = viewmode
		if self.actionLivePreview.isChecked():
			self.actionLivePreview.setChecked(False)
			return self.enableLivePreview(False)
		self.editBar.setDisabled(viewmode)
		self.editBoxes[self.ind].setVisible(not viewmode)
		self.previewBoxes[self.ind].setVisible(viewmode)
		if viewmode:
			self.updatePreviewBox()

	def enableLivePreview(self, livemode):
		if globalSettings.restorePreviewState:
			globalSettings.previewState = livemode
		self.actionLivePreviewChecked[self.ind] = livemode
		self.actionPreviewChecked[self.ind] = livemode
		self.actionPreview.setChecked(livemode)
		self.editBar.setEnabled(True)
		self.previewBoxes[self.ind].setVisible(livemode)
		self.editBoxes[self.ind].setVisible(True)
		if livemode:
			self.updatePreviewBox()

	def enableWebKit(self, enable):
		globalSettings.useWebKit = enable
		oldind = self.ind
		self.tabWidget.clear()
		for self.ind in range(len(self.editBoxes)):
			if enable:
				self.previewBoxes[self.ind] = self.getWebView()
			else:
				self.previewBoxes[self.ind] = QTextBrowser()
				self.previewBoxes[self.ind].setOpenExternalLinks(True)
			splitter = self.getSplitter(self.ind)
			self.tabWidget.addTab(splitter, self.getDocumentTitle(baseName=True))
			self.updatePreviewBox()
			self.previewBoxes[self.ind].setVisible(self.actionPreviewChecked[self.ind])
		self.ind = oldind
		self.tabWidget.setCurrentIndex(self.ind)

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

	def enableSC(self, yes):
		if yes:
			if self.sl:
				self.setAllDictionaries(enchant.Dict(self.sl))
			else:
				self.setAllDictionaries(enchant.Dict())
		else:
			self.setAllDictionaries(None)
		globalSettings.spellCheck = yes

	def setAllDictionaries(self, dictionary):
		for hl in self.highlighters:
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
				self.enableSC(self.actionEnableSC.isChecked())
		else:
			self.sl = None
			self.enableSC(self.actionEnableSC.isChecked())
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
		editBox = self.editBoxes[self.ind]
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

	def getHtml(self, includeStyleSheet=True, includeTitle=True,
	            includeMeta=False, styleForWebKit=False, webenv=False):
		if self.markups[self.ind] is None:
			markupClass = self.getMarkupClass()
			errMsg = self.tr('Could not parse file contents, check if '
			'you have the <a href="%s">necessary module</a> installed!')
			try:
				errMsg %= markupClass.attributes[MODULE_HOME_PAGE]
			except (AttributeError, KeyError):
				# Remove the link if markupClass doesn't have the needed attribute
				errMsg = errMsg.replace('<a href="%s">', '')
				errMsg = errMsg.replace('</a>', '')
			return '<p style="color: red">%s</p>' % errMsg
		text = self.editBoxes[self.ind].toPlainText()
		# WpGen directives
		text = text.replace('%HTMLDIR%', 'html')
		text = text.replace('%\\HTMLDIR%', '%HTMLDIR%')
		headers = ''
		if includeStyleSheet:
			fontline = ''
			if styleForWebKit:
				fontname = self.font.family() if self.font else 'Sans'
				fontsize = (self.font if self.font else QFont()).pointSize()
				fontline = 'body { font-family: %s; font-size: %spt }\n' % \
					(fontname, fontsize)
			headers += '<style type="text/css">\n' + fontline + self.ss + '</style>\n'
		cssFileName = self.getDocumentTitle(baseName=True)+'.css'
		if QFile(cssFileName).exists():
			headers += '<link rel="stylesheet" type="text/css" href="%s">\n' \
			% cssFileName
		if includeMeta:
			headers += '<meta name="generator" content="%s %s">\n' % \
			(app_name, app_version)
		fallbackTitle = self.getDocumentTitle() if includeTitle else ''
		return self.markups[self.ind].get_whole_html(text,
			custom_headers=headers, include_stylesheet=includeStyleSheet,
			fallback_title=fallbackTitle, webenv=webenv)

	def updatePreviewBox(self):
		self.previewBlocked = False
		pb = self.previewBoxes[self.ind]
		textedit = isinstance(pb, QTextEdit)
		if textedit:
			scrollbar = pb.verticalScrollBar()
			disttobottom = scrollbar.maximum() - scrollbar.value()
		else:
			frame = pb.page().mainFrame()
			scrollpos = frame.scrollPosition()
		if self.actionPlainText.isChecked():
			if textedit:
				pb.setPlainText(self.editBoxes[self.ind].toPlainText())
			else:
				td = QTextDocument()
				td.setPlainText(self.editBoxes[self.ind].toPlainText())
				pb.setHtml(td.toHtml())
		else:
			try:
				html = self.getHtml(styleForWebKit=(not textedit))
			except Exception:
				return self.printError()
			if textedit:
				pb.setHtml(html)
			else:
				pb.setHtml(html, QUrl.fromLocalFile(self.fileNames[self.ind]))
		if self.font and textedit:
			pb.document().setDefaultFont(self.font)
		if textedit:
			scrollbar.setValue(scrollbar.maximum() - disttobottom)
		else:
			frame.setScrollPosition(scrollpos)

	def updateLivePreviewBox(self):
		if self.actionLivePreview.isChecked() and self.previewBlocked == False:
			self.previewBlocked = True
			QTimer.singleShot(1000, self.updatePreviewBox)

	def startWpgen(self):
		if not self.fileNames[self.ind]:
			return QMessageBox.warning(self, '', self.tr("Please, save the file somewhere."))
		if not QFile.exists("template.html"):
			try:
				wpInit()
			except IOError as e:
				e = str(e)
				return QMessageBox.warning(self, '', self.tr(
				'Failed to copy default template, please create template.html manually.')
				+ '\n\n' + e)
		wpUpdateAll()
		msgBox = QMessageBox(QMessageBox.Information, '',
		self.tr("Webpages saved in <code>html</code> directory."), QMessageBox.Ok)
		showButton = msgBox.addButton(self.tr("Show directory"), QMessageBox.AcceptRole)
		msgBox.exec()
		if msgBox.clickedButton() == showButton:
			QDesktopServices.openUrl(QUrl.fromLocalFile(QDir('html').absolutePath()))

	def showInDir(self):
		if self.fileNames[self.ind]:
			QDesktopServices.openUrl(QUrl.fromLocalFile(QFileInfo(self.fileNames[self.ind]).path()))
		else:
			QMessageBox.warning(self, '', self.tr("Please, save the file somewhere."))

	def setCurrentFile(self):
		self.setWindowTitle("")
		self.tabWidget.setTabText(self.ind, self.getDocumentTitle(baseName=True))
		self.setWindowFilePath(self.fileNames[self.ind])
		files = readListFromSettings("recentFileList")
		while self.fileNames[self.ind] in files:
			files.remove(self.fileNames[self.ind])
		files.insert(0, self.fileNames[self.ind])
		if len(files) > 10:
			del files[10:]
		writeListToSettings("recentFileList", files)
		QDir.setCurrent(QFileInfo(self.fileNames[self.ind]).dir().path())
		self.docTypeChanged()

	def createNew(self, text=None):
		self.tabWidget.addTab(self.createTab(""), self.tr("New document"))
		self.ind = self.tabWidget.count()-1
		self.tabWidget.setCurrentIndex(self.ind)
		if text:
			self.editBoxes[self.ind].textCursor().insertText(text)

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

	def extensionFuntion(self, data):
		return lambda: \
		self.runExtensionCommand(data['Exec'], data['FileFilter'], data['DefaultExtension'])

	def getExportExtensionsList(self):
		extensions = []
		for extsprefix in datadirs:
			extsdir = QDir(extsprefix+'/export-extensions/')
			if extsdir.exists():
				for fileInfo in extsdir.entryInfoList(['*.desktop', '*.ini'], QDir.Files | QDir.Readable):
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
				action = self.act(name, trig=self.extensionFuntion(data))
				if 'Icon' in extension:
					action.setIcon(self.actIcon(extension['Icon']))
				mimetype = extension['MimeType'] if 'MimeType' in extension else None
			except KeyError:
				print('Failed to parse extension: Name is required', file=sys.stderr)
			else:
				self.extensionActions.append((action, mimetype))

	def updateExtensionsVisibility(self):
		markupClass = self.getMarkupClass()
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
		fileNames = QFileDialog.getOpenFileNames(self, self.tr("Select one or several files to open"), "",
			self.tr("Supported files") + fileFilter + self.tr("All files (*)"))
		for fileName in fileNames[0]:
			self.openFileWrapper(fileName)

	def openFileWrapper(self, fileName):
		if not fileName:
			return
		fileName = QFileInfo(fileName).canonicalFilePath()
		exists = False
		for i in range(self.tabWidget.count()):
			if self.fileNames[i] == fileName:
				exists = True
				ex = i
		if exists:
			self.tabWidget.setCurrentIndex(ex)
		elif QFile.exists(fileName):
			noEmptyTab = (
				(self.ind is None) or
				self.fileNames[self.ind] or
				self.editBoxes[self.ind].toPlainText() or
				self.editBoxes[self.ind].document().isModified()
			)
			if noEmptyTab:
				self.tabWidget.addTab(self.createTab(fileName), "")
				self.ind = self.tabWidget.count()-1
				self.tabWidget.setCurrentIndex(self.ind)
			self.fileNames[self.ind] = fileName
			self.openFileMain()

	def openFileMain(self, encoding=None):
		openfile = QFile(self.fileNames[self.ind])
		openfile.open(QIODevice.ReadOnly)
		stream = QTextStream(openfile)
		if encoding:
			stream.setCodec(encoding)
		text = stream.readAll()
		openfile.close()
		markupClass = markups.get_markup_for_file_name(
			self.fileNames[self.ind], return_class=True)
		self.highlighters[self.ind].docType = (markupClass.name if markupClass else '')
		self.markups[self.ind] = self.getMarkup()
		pt = not markupClass
		if not globalSettings.autoPlainText:
			pt = False
			if self.defaultMarkup:
				self.highlighters[self.ind].docType = self.defaultMarkup.name
		editBox = self.editBoxes[self.ind]
		modified = bool(encoding) and (editBox.toPlainText() != text)
		editBox.setPlainText(text)
		self.actionPlainText.setChecked(pt)
		self.enablePlainText(pt)
		self.setCurrentFile()
		editBox.document().setModified(modified)
		self.setWindowModified(modified)

	def showEncodingDialog(self):
		if not self.maybeSave(self.ind):
			return
		encoding, ok = QInputDialog.getItem(self, '',
			self.tr('Select file encoding from the list:'),
			[bytes(b).decode() for b in QTextCodec.availableCodecs()],
			0, False)
		if ok:
			self.openFileMain(encoding)

	def saveFile(self):
		self.saveFileMain(dlg=False)

	def saveFileAs(self):
		self.saveFileMain(dlg=True)

	def saveAll(self):
		oldind = self.ind
		for self.ind in range(self.tabWidget.count()):
			if self.fileNames[self.ind] and QFileInfo(self.fileNames[self.ind]).isWritable():
				self.saveFileCore(self.fileNames[self.ind])
				self.editBoxes[self.ind].document().setModified(False)
		self.ind = oldind

	def saveFileMain(self, dlg):
		if (not self.fileNames[self.ind]) or dlg:
			markupClass = self.getMarkupClass()
			if (markupClass is None) or not hasattr(markupClass, 'default_extension'):
				defaultExt = self.tr("Plain text (*.txt)")
				ext = ".txt"
			else:
				defaultExt = self.tr('%s files',
					'Example of final string: Markdown files') \
					% markupClass.name + ' (' + str.join(' ',
					('*'+extension for extension in markupClass.file_extensions)) + ')'
				ext = markupClass.default_extension
			newFileName = QFileDialog.getSaveFileName(self,
				self.tr("Save file"), "", defaultExt)[0]
			if newFileName:
				if not QFileInfo(newFileName).suffix():
					newFileName += ext
				self.fileNames[self.ind] = newFileName
				self.actionSetEncoding.setDisabled(self.autoSaveActive())
		if self.fileNames[self.ind]:
			result = self.saveFileCore(self.fileNames[self.ind])
			if result:
				self.setCurrentFile()
				self.editBoxes[self.ind].document().setModified(False)
				self.setWindowModified(False)
				return True
			else:
				QMessageBox.warning(self, '',
				self.tr("Cannot save to file because it is read-only!"))
		return False

	def saveFileCore(self, fn):
		savefile = QFile(fn)
		result = savefile.open(QIODevice.WriteOnly)
		if result:
			savestream = QTextStream(savefile)
			savestream << self.editBoxes[self.ind].toPlainText()
			savefile.close()
		return result

	def saveHtml(self, fileName):
		if not QFileInfo(fileName).suffix():
			fileName += ".html"
		try:
			htmltext = self.getHtml(includeStyleSheet=False, includeMeta=True,
			webenv=True)
		except Exception:
			return self.printError()
		htmlFile = QFile(fileName)
		htmlFile.open(QIODevice.WriteOnly)
		html = QTextStream(htmlFile)
		html << htmltext
		htmlFile.close()

	def textDocument(self):
		td = QTextDocument()
		td.setMetaInformation(QTextDocument.DocumentTitle, self.getDocumentTitle())
		if self.ss:
			td.setDefaultStyleSheet(self.ss)
		if self.actionPlainText.isChecked():
			td.setPlainText(self.editBoxes[self.ind].toPlainText())
		else:
			td.setHtml(self.getHtml())
		if self.font:
			td.setDefaultFont(self.font)
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
		writer.setFormat("odf")
		writer.write(document)

	def saveFileHtml(self):
		fileName = QFileDialog.getSaveFileName(self,
			self.tr("Save file"), "",
			self.tr("HTML files (*.html *.htm)"))[0]
		if fileName:
			self.saveHtml(fileName)

	def getDocumentForPrint(self):
		if globalSettings.useWebKit:
			return self.previewBoxes[self.ind]
		try:
			return self.textDocument()
		except Exception:
			self.printError()

	def standardPrinter(self):
		printer = QPrinter(QPrinter.HighResolution)
		printer.setDocName(self.getDocumentTitle())
		printer.setCreator(app_name+" "+app_version)
		return printer

	def savePdf(self):
		self.updatePreviewBox()
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
		self.updatePreviewBox()
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
		basename = '.%s.retext-temp' % self.getDocumentTitle(baseName=True)
		if html:
			tmpname = basename+'.html'
			self.saveHtml(tmpname)
		else:
			tmpname = basename+self.getMarkupClass().default_extension
			self.saveFileCore(tmpname)
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

	def getDocumentTitle(self, baseName=False):
		markup = self.markups[self.ind]
		realTitle = ''
		if markup and not baseName:
			text = self.editBoxes[self.ind].toPlainText()
			try:
				realTitle = markup.get_document_title(text)
			except Exception:
				self.printError()
		if realTitle:
			return realTitle
		elif self.fileNames[self.ind]:
			fileinfo = QFileInfo(self.fileNames[self.ind])
			basename = fileinfo.completeBaseName()
			return (basename if basename else fileinfo.fileName())
		return self.tr("New document")

	def autoSaveActive(self):
		return self.autoSaveEnabled and self.fileNames[self.ind] and \
		QFileInfo(self.fileNames[self.ind]).isWritable()

	def modificationChanged(self, changed):
		if self.autoSaveActive():
			changed = False
		self.actionSave.setEnabled(changed)
		self.setWindowModified(changed)

	def clipboardDataChanged(self):
		self.actionPaste.setEnabled(QApplication.instance().clipboard().mimeData().hasText())

	def insertChars(self, chars):
		tc = self.editBoxes[self.ind].textCursor()
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
		tc = self.editBoxes[self.ind].textCursor()
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
			self.editBoxes[self.ind].insertPlainText('&'+self.usefulChars[num-1]+';')
		self.symbolBox.setCurrentIndex(0)

	def maybeSave(self, ind):
		if self.autoSaveActive():
			self.saveFileCore(self.fileNames[self.ind])
			return True
		if not self.editBoxes[ind].document().isModified():
			return True
		self.tabWidget.setCurrentIndex(ind)
		ret = QMessageBox.warning(self, '',
			self.tr("The document has been modified.\nDo you want to save your changes?"),
			QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
		if ret == QMessageBox.Save:
			return self.saveFileMain(False)
		elif ret == QMessageBox.Cancel:
			return False
		return True

	def closeEvent(self, closeevent):
		for self.ind in range(self.tabWidget.count()):
			if not self.maybeSave(self.ind):
				return closeevent.ignore()
		if globalSettings.saveWindowGeometry and not self.isMaximized():
			globalSettings.windowGeometry = self.saveGeometry()
		closeevent.accept()

	def viewHtml(self):
		htmlDlg = HtmlDialog(self)
		try:
			htmltext = self.getHtml(includeStyleSheet=False, includeTitle=False)
		except Exception:
			return self.printError()
		winTitle = self.getDocumentTitle(baseName=True)
		htmlDlg.setWindowTitle(winTitle+" ("+self.tr("HTML code")+")")
		htmlDlg.textEdit.setPlainText(htmltext.rstrip())
		htmlDlg.hl.rehighlight()
		htmlDlg.show()
		htmlDlg.raise_()
		htmlDlg.activateWindow()

	def openHelp(self):
		QDesktopServices.openUrl(QUrl('http://sourceforge.net/p/retext/home/Help and Support'))

	def aboutDialog(self):
		QMessageBox.about(self, self.aboutWindowTitle,
		'<p><b>'+app_name+' '+app_version+'</b><br>'+self.tr('Simple but powerful editor'
		' for Markdown and reStructuredText')
		+'</p><p>'+self.tr('Author: Dmitry Shachnev, 2011')
		+'<br><a href="http://sourceforge.net/p/retext/">'+self.tr('Website')
		+'</a> | <a href="http://daringfireball.net/projects/markdown/syntax">'+self.tr('Markdown syntax')
		+'</a> | <a href="http://docutils.sourceforge.net/docs/user/rst/quickref.html">'
		+self.tr('reStructuredText syntax')+'</a></p>')

	def enablePlainText(self, value):
		self.actionPlainTextChecked[self.ind] = value
		self.actionSaveHtml.setDisabled(value)
		self.actionViewHtml.setDisabled(value)
		self.docTypeChanged()

	def setDefaultMarkup(self, markup):
		self.defaultMarkup = markup
		defaultName = markups.get_available_markups()[0].name
		writeToSettings('defaultMarkup', markup.name, defaultName)
		oldind = self.ind
		for self.ind in range(len(self.previewBoxes)):
			self.docTypeChanged()
		self.ind = oldind
