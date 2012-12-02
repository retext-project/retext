# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

from ReText import *
from ReText.webpages import wpInit, wpUpdateAll
from ReText.htmldialog import HtmlDialog
from ReText.highlighter import ReTextHighlighter
from ReText.editor import ReTextEdit

class LocaleDialog(QDialog):
	def __init__(self, parent, defaultText=""):
		QDialog.__init__(self, parent)
		self.setWindowTitle(app_name)
		verticalLayout = QVBoxLayout(self)
		self.label = QLabel(self)
		self.label.setText(self.tr('Enter locale name (example: en_US)'))
		verticalLayout.addWidget(self.label)
		self.localeEdit = QLineEdit(self)
		self.localeEdit.setText(defaultText)
		verticalLayout.addWidget(self.localeEdit)
		self.checkBox = QCheckBox(self.tr('Set as default'), self)
		verticalLayout.addWidget(self.checkBox)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
		verticalLayout.addWidget(buttonBox)
		self.connect(buttonBox, SIGNAL('accepted()'), self.accept)
		self.connect(buttonBox, SIGNAL('rejected()'), self.reject)

class ReTextWindow(QMainWindow):
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		self.initConfig()
		self.resize(800, 600)
		if settings.contains('windowGeometry'):
			self.restoreGeometry(readFromSettings('windowGeometry', QByteArray))
		else:
			screen = QDesktopWidget().screenGeometry()
			size = self.geometry()
			self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
		if settings.contains('iconTheme'):
			QIcon.setThemeName(readFromSettings('iconTheme', str))
		if QIcon.themeName() in ('', 'hicolor'):
			try:
				gconf = Popen(['gconftool-2', '--get', '/desktop/gnome/interface/icon_theme'],
				stdout=PIPE)
			except: pass
			else:
				iconTheme = gconf.stdout.read().rstrip()
				if iconTheme:
					iconTheme = iconTheme.decode()
					QIcon.setThemeName(iconTheme)
					settings.setValue('iconTheme', iconTheme)
		if QFile.exists(icon_path+'retext.png'):
			self.setWindowIcon(QIcon(icon_path+'retext.png'))
		else:
			self.setWindowIcon(QIcon.fromTheme('retext', QIcon.fromTheme('accessories-text-editor')))
		self.editBoxes = []
		self.previewBoxes = []
		self.highlighters = []
		self.markups = []
		self.fileNames = []
		self.apc = []
		self.alpc = []
		self.aptc = []
		self.tabWidget = QTabWidget(self)
		self.tabWidget.setTabsClosable(True)
		self.setCentralWidget(self.tabWidget)
		self.connect(self.tabWidget, SIGNAL('currentChanged(int)'), self.changeIndex)
		self.connect(self.tabWidget, SIGNAL('tabCloseRequested(int)'), self.closeTab)
		toolBar = QToolBar(self.tr('File toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, toolBar)
		self.editBar = QToolBar(self.tr('Edit toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, self.editBar)
		self.searchBar = QToolBar(self.tr('Search toolbar'), self)
		self.addToolBar(Qt.BottomToolBarArea, self.searchBar)
		if readFromSettings('hideToolBar', bool, default=False):
			toolBar.setVisible(False)
			self.editBar.setVisible(False)
		self.actionNew = self.act(self.tr('New'), icon='document-new', shct=QKeySequence.New,
			trig=self.createNew)
		self.actionNew.setPriority(QAction.LowPriority)
		self.actionOpen = self.act(self.tr('Open'), icon='document-open', shct=QKeySequence.Open,
			trig=self.openFile)
		self.actionOpen.setPriority(QAction.LowPriority)
		self.actionSave = self.act(self.tr('Save'), icon='document-save', shct=QKeySequence.Save,
			trig=self.saveFile)
		self.actionSave.setEnabled(False)
		self.actionSave.setPriority(QAction.LowPriority)
		self.actionSaveAs = self.act(self.tr('Save as'), icon='document-save-as',
			shct=QKeySequence.SaveAs, trig=self.saveFileAs)
		self.actionPrint = self.act(self.tr('Print'), icon='document-print', shct=QKeySequence.Print,
			trig=self.printFile)
		self.actionPrint.setPriority(QAction.LowPriority)
		self.actionPrintPreview = self.act(self.tr('Print preview'), icon='document-print-preview',
			trig=self.printPreview)
		self.actionViewHtml = self.act(self.tr('View HTML code'), icon='text-html', trig=self.viewHtml)
		self.actionChangeFont = self.act(self.tr('Change default font'), trig=self.changeFont)
		self.actionSearch = self.act(self.tr('Find text'), icon='edit-find', shct=QKeySequence.Find)
		self.actionSearch.setCheckable(True)
		self.connect(self.actionSearch, SIGNAL('triggered(bool)'), self.searchBar,
			SLOT('setVisible(bool)'))
		self.connect(self.searchBar, SIGNAL('visibilityChanged(bool)'), self.searchBarVisibilityChanged)
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
		self.actionFullScreen = self.act(self.tr('Fullscreen mode'), icon='view-fullscreen',
			shct=Qt.Key_F11, trigbool=self.enableFullScreen)
		self.actionPerfectHtml = self.act('HTML', icon='text-html', trig=self.saveFilePerfect)
		self.actionPdf = self.act('PDF', icon='application-pdf', trig=self.savePdf)
		self.actionOdf = self.act('ODT', icon='x-office-document', trig=self.saveOdf)
		self.getExportExtensionsList()
		self.actionQuit = self.act(self.tr('Quit'), icon='application-exit', shct=QKeySequence.Quit)
		self.actionQuit.setMenuRole(QAction.QuitRole)
		self.connect(self.actionQuit, SIGNAL('triggered()'), self.close)
		self.actionUndo = self.act(self.tr('Undo'), icon='edit-undo', shct=QKeySequence.Undo,
			trig=lambda: self.editBoxes[self.ind].undo())
		self.actionRedo = self.act(self.tr('Redo'), icon='edit-redo', shct=QKeySequence.Redo,
			trig=lambda: self.editBoxes[self.ind].redo())
		self.actionCopy = self.act(self.tr('Copy'), icon='edit-copy', shct=QKeySequence.Copy,
			trig=lambda: self.editBoxes[self.ind].copy())
		self.actionCut = self.act(self.tr('Cut'), icon='edit-cut', shct=QKeySequence.Cut,
			trig=lambda: self.editBoxes[self.ind].cut())
		self.actionPaste = self.act(self.tr('Paste'), icon='edit-paste', shct=QKeySequence.Paste,
			trig=lambda: self.editBoxes[self.ind].paste())
		self.actionUndo.setEnabled(False)
		self.actionRedo.setEnabled(False)
		self.actionCopy.setEnabled(False)
		self.actionCut.setEnabled(False)
		self.connect(qApp.clipboard(), SIGNAL('dataChanged()'), self.clipboardDataChanged)
		self.clipboardDataChanged()
		if enchant_available:
			self.actionEnableSC = self.act(self.tr('Enable'), trigbool=self.enableSC)
			self.actionSetLocale = self.act(self.tr('Set locale'), trig=self.changeLocale)
		self.actionPlainText = self.act(self.tr('Plain text'), trigbool=self.enablePlainText)
		if webkit_available:
			self.actionWebKit = self.act(self.tr('Use WebKit renderer'), trigbool=self.enableWebKit)
			self.useWebKit = readFromSettings('useWebKit', bool, default=False)
			if self.useWebKit:
				self.actionWebKit.setChecked(True)
		self.actionWpgen = self.act(self.tr('Generate webpages'), trig=self.startWpgen)
		self.actionShow = self.act(self.tr('Show'), icon='system-file-manager', trig=self.showInDir)
		self.actionFind = self.act(self.tr('Next'), icon='go-next', shct=QKeySequence.FindNext,
			trig=self.find)
		self.actionFindPrev = self.act(self.tr('Previous'), icon='go-previous',
			shct=QKeySequence.FindPrevious, trig=lambda: self.find(back=True))
		self.actionHelp = self.act(self.tr('Get help online'), icon='help-contents', trig=self.openHelp)
		self.aboutWindowTitle = self.tr('About %s', 'Example of final string: About ReText')
		try:
			self.aboutWindowTitle =  self.aboutWindowTitle % app_name
		except:
			# For Python 2
			self.aboutWindowTitle = self.aboutWindowTitle.replace('%s', '%1').arg(app_name)
		self.actionAbout = self.act(self.aboutWindowTitle, icon='help-about', trig=self.aboutDialog)
		self.actionAbout.setMenuRole(QAction.AboutRole)
		self.actionAboutQt = self.act(self.tr('About Qt'))
		self.actionAboutQt.setMenuRole(QAction.AboutQtRole)
		self.connect(self.actionAboutQt, SIGNAL('triggered()'), qApp, SLOT('aboutQt()'))
		availableMarkups = markups.get_available_markups()
		if not availableMarkups:
			print('Warning: no markups are available!')
		self.defaultMarkup = availableMarkups[0] if availableMarkups else None
		if settings.contains('defaultMarkup'):
			dm = str(readFromSettings('defaultMarkup', str))
			mc = markups.find_markup_class_by_name(dm)
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
			trig=lambda: self.insertTag(9)) # <u>...</u>
		self.usefulTags = ('a', 'big', 'center', 'img', 's', 'small', 'span',
			'table', 'td', 'tr', 'u')
		self.usefulChars = ('deg', 'divide', 'dollar', 'hellip', 'laquo', 'larr',
			'lsquo', 'mdash', 'middot', 'minus', 'nbsp', 'ndash', 'raquo',
			'rarr', 'rsquo', 'times')
		self.tagsBox = QComboBox(self.editBar)
		self.tagsBox.addItem(self.tr('Tags'))
		self.tagsBox.addItems(self.usefulTags)
		self.connect(self.tagsBox, SIGNAL('activated(int)'), self.insertTag)
		self.symbolBox = QComboBox(self.editBar)
		self.symbolBox.addItem(self.tr('Symbols'))
		self.symbolBox.addItems(self.usefulChars)
		self.connect(self.symbolBox, SIGNAL('activated(int)'), self.insertSymbol)
		if settings.contains('styleSheet'):
			ssname = readFromSettings('styleSheet', str)
			sheetfile = QFile(ssname)
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
		self.connect(self.menuRecentFiles, SIGNAL('aboutToShow()'), self.updateRecentFiles)
		menuFile.addMenu(self.menuRecentFiles)
		self.menuDir = menuFile.addMenu(self.tr('Directory'))
		self.menuDir.addAction(self.actionShow)
		self.menuDir.addAction(self.actionWpgen)
		menuFile.addSeparator()
		menuFile.addAction(self.actionSave)
		menuFile.addAction(self.actionSaveAs)
		menuFile.addSeparator()
		menuExport = menuFile.addMenu(self.tr('Export'))
		menuExport.addAction(self.actionPerfectHtml)
		menuExport.addAction(self.actionOdf)
		menuExport.addAction(self.actionPdf)
		if self.extensionActions:
			menuExport.addSeparator()
			for action, mimetype in self.extensionActions:
				menuExport.addAction(action)
			self.connect(self.menuRecentFiles, SIGNAL('aboutToShow()'), self.updateExtensionsVisibility)
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
			self.menuMode = menuEdit.addMenu(self.tr('Default editing mode'))
			for markupAction in markupActions:
				self.menuMode.addAction(markupAction)
		menuFormat = menuEdit.addMenu(self.tr('Formatting'))
		menuFormat.addAction(self.actionBold)
		menuFormat.addAction(self.actionItalic)
		menuFormat.addAction(self.actionUnderline)
		if webkit_available:
			menuEdit.addAction(self.actionWebKit)
		menuEdit.addSeparator()
		menuEdit.addAction(self.actionViewHtml)
		menuEdit.addAction(self.actionLivePreview)
		menuEdit.addAction(self.actionPreview)
		menuEdit.addSeparator()
		menuEdit.addAction(self.actionFullScreen)
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
		try:
			self.searchEdit.setPlaceholderText(self.tr('Search'))
		except: pass
		self.connect(self.searchEdit, SIGNAL('returnPressed()'), self.find)
		self.csBox = QCheckBox(self.tr('Case sensitively'), self.searchBar)
		self.searchBar.addWidget(self.searchEdit)
		self.searchBar.addWidget(self.csBox)
		self.searchBar.addAction(self.actionFindPrev)
		self.searchBar.addAction(self.actionFind)
		self.searchBar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
		self.searchBar.setVisible(False)
		if self.autoSave:
			timer = QTimer(self)
			timer.start(60000)
			self.connect(timer, SIGNAL('timeout()'), self.saveAll)
		self.ind = 0
		self.tabWidget.addTab(self.createTab(""), self.tr('New document'))
		if enchant_available:
			self.sl = None
			if settings.contains('spellCheckLocale'):
				try:
					self.sl = str(readFromSettings('spellCheckLocale', str))
					enchant.Dict(self.sl)
				except Exception as e:
					print(e)
					self.sl = None
			if readFromSettings('spellCheck', bool, default=False):
				self.actionEnableSC.setChecked(True)
				self.enableSC(True)
	
	def initConfig(self):
		self.font = None
		if settings.contains('font'):
			self.font = QFont(readFromSettings('font', str))
		if self.font and settings.contains('fontSize'):
			self.font.setPointSize(readFromSettings('fontSize', int))
		self.tabWidth = readFromSettings('tabWidth', int, default=4)
		self.tabInsertsSpaces = readFromSettings('tabInsertsSpaces', bool,
			default=True)
		self.rightMargin = readFromSettings('rightMargin', int, default=0)
		self.saveWindowGeometry = readFromSettings('saveWindowGeometry', bool,
			default=False)
		self.handleLinks = readFromSettings('handleWebLinks', bool, default=False)
		self.autoSave = readFromSettings('autoSave', bool, default=False)
		self.restorePreviewState = readFromSettings('restorePreviewState', bool,
			default=False)
		self.livePreviewEnabled = readFromSettings('previewState', bool,
			default=False)
	
	def act(self, name, icon=None, trig=None, trigbool=None, shct=None):
		if icon:
			action = QAction(self.actIcon(icon), name, self)
		else:
			action = QAction(name, self)
		if trig:
			self.connect(action, SIGNAL('triggered()'), trig)
		elif trigbool:
			action.setCheckable(True)
			self.connect(action, SIGNAL('triggered(bool)'), trigbool)
		if shct:
			action.setShortcut(shct)
		return action
	
	def actIcon(self, name):
		return QIcon.fromTheme(name, QIcon(icon_path+name+'.png'))
	
	def printError(self):
		import traceback
		print('Exception occured while parsing document:')
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
		if not self.handleLinks:
			webView.page().setLinkDelegationPolicy(QWebPage.DelegateExternalLinks)
			self.connect(webView.page(), SIGNAL("linkClicked(const QUrl&)"), self.linkClicked)
		return webView
	
	def linkClicked(self, url):
		urlstr = convertToUnicode(url.toString())
		if urlstr.startswith('file://') or not (':/' in urlstr):
			self.previewBoxes[self.ind].load(url)
		elif urlstr.startswith('about:blank#'):
			self.previewBoxes[self.ind].page().mainFrame().scrollToAnchor(urlstr[12:])
		else:
			QDesktopServices.openUrl(url)
	
	def createTab(self, fileName):
		self.previewBlocked = False
		self.editBoxes.append(ReTextEdit(self))
		self.highlighters.append(ReTextHighlighter(self.editBoxes[-1].document()))
		if enchant_available and self.actionEnableSC.isChecked():
			self.highlighters[-1].dictionary = \
			enchant.Dict(self.sl) if self.sl else enchant.Dict()
			self.highlighters[-1].rehighlight()
		if self.useWebKit:
			self.previewBoxes.append(self.getWebView())
		else:
			self.previewBoxes.append(QTextBrowser())
			self.previewBoxes[-1].setOpenExternalLinks(True)
		self.previewBoxes[-1].setVisible(False)
		self.fileNames.append(fileName)
		markupClass = self.getMarkupClass(fileName)
		self.markups.append(self.getMarkup(fileName))
		self.highlighters[-1].docType = (markupClass.name if markupClass else '')
		liveMode = self.restorePreviewState and self.livePreviewEnabled
		self.apc.append(liveMode)
		self.alpc.append(liveMode)
		self.aptc.append(False)
		metrics = QFontMetrics(self.editBoxes[-1].font())
		self.editBoxes[-1].setTabStopWidth(self.tabWidth*metrics.width(' '))
		self.connect(self.editBoxes[-1], SIGNAL('textChanged()'), self.updateLivePreviewBox)
		self.connect(self.editBoxes[-1], SIGNAL('undoAvailable(bool)'), self.actionUndo,
			SLOT('setEnabled(bool)'))
		self.connect(self.editBoxes[-1], SIGNAL('redoAvailable(bool)'), self.actionRedo,
			SLOT('setEnabled(bool)'))
		self.connect(self.editBoxes[-1], SIGNAL('copyAvailable(bool)'), self.enableCopy)
		self.connect(self.editBoxes[-1].document(), SIGNAL('modificationChanged(bool)'),
			self.modificationChanged)
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
			del self.apc[ind]
			del self.alpc[ind]
			del self.aptc[ind]
			self.tabWidget.removeTab(ind)
	
	def getMarkupClass(self, fileName=None):
		if fileName is None:
			fileName = self.fileNames[self.ind]
		fileName = convertToUnicode(fileName)
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
		fileName = convertToUnicode(fileName)
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
	
	def changeIndex(self, ind):
		if ind > -1:
			self.actionPlainText.setChecked(self.aptc[ind])
			self.actionPerfectHtml.setDisabled(self.aptc[ind])
			self.actionViewHtml.setDisabled(self.aptc[ind])
			self.actionUndo.setEnabled(self.editBoxes[ind].document().isUndoAvailable())
			self.actionRedo.setEnabled(self.editBoxes[ind].document().isRedoAvailable())
			self.actionCopy.setEnabled(self.editBoxes[ind].textCursor().hasSelection())
			self.actionCut.setEnabled(self.editBoxes[ind].textCursor().hasSelection())
			self.actionPreview.setChecked(self.apc[ind])
			self.actionLivePreview.setChecked(self.alpc[ind])
			self.editBar.setDisabled(self.apc[ind])
		self.ind = ind
		if self.fileNames[ind]:
			self.setCurrentFile()
		else:
			try:
				self.setWindowTitle(self.tr('New document') + '[*] ' + QChar(0x2014) + ' ' + app_name)
			except:
				# For Python 3
				self.setWindowTitle(self.tr('New document') + '[*] \u2014 ' + app_name)
			self.docTypeChanged()
		self.modificationChanged(self.editBoxes[ind].document().isModified())
		self.livePreviewEnabled = self.alpc[ind]
		if self.alpc[ind]:
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
		self.apc[self.ind] = viewmode
		if self.actionLivePreview.isChecked():
			self.actionLivePreview.setChecked(False)
			return self.enableLivePreview(False)
		self.editBar.setDisabled(viewmode)
		self.editBoxes[self.ind].setVisible(not viewmode)
		self.previewBoxes[self.ind].setVisible(viewmode)
		if viewmode:
			self.updatePreviewBox()
	
	def enableLivePreview(self, livemode):
		self.livePreviewEnabled = livemode
		self.alpc[self.ind] = livemode
		self.apc[self.ind] = livemode
		self.actionPreview.setChecked(livemode)
		self.editBar.setEnabled(True)
		self.previewBoxes[self.ind].setVisible(livemode)
		self.editBoxes[self.ind].setVisible(True)
		if livemode:
			self.updatePreviewBox()
	
	def enableWebKit(self, enable):
		self.useWebKit = enable
		if enable:
			settings.setValue('useWebKit', True)
		else:
			settings.remove('useWebKit')
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
			self.previewBoxes[self.ind].setVisible(self.apc[self.ind])
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
	
	def enableSC(self, yes):
		if yes:
			if self.sl:
				self.setAllDictionaries(enchant.Dict(self.sl))
			else:
				self.setAllDictionaries(enchant.Dict())
			settings.setValue('spellCheck', True)
		else:
			self.setAllDictionaries(None)
			settings.remove('spellCheck')
	
	def setAllDictionaries(self, dictionary):
		for hl in self.highlighters:
			hl.dictionary = dictionary
			hl.rehighlight()
	
	def changeLocale(self):
		if self.sl:
			localedlg = LocaleDialog(self, defaultText=self.sl)
		else:
			localedlg = LocaleDialog(self)
		if localedlg.exec_() != QDialog.Accepted:
			return
		sl = localedlg.localeEdit.text()
		setdefault = localedlg.checkBox.isChecked()
		if sl:
			try:
				sl = str(sl)
				enchant.Dict(sl)
			except Exception as e:
				QMessageBox.warning(self, app_name, str(e))
			else:
				self.sl = sl
				self.enableSC(self.actionEnableSC.isChecked())
				if setdefault:
					settings.setValue('spellCheckLocale', sl)
		else:
			self.sl = None
			self.enableSC(self.actionEnableSC.isChecked())
			if setdefault:
				settings.remove('spellCheckLocale')
	
	def searchBarVisibilityChanged(self, visible):
		self.actionSearch.setChecked(visible)
		if visible:
			self.searchEdit.setFocus(Qt.ShortcutFocusReason)
	
	def find(self, back=False):
		flags = 0
		if back:
			flags = QTextDocument.FindBackward
		if self.csBox.isChecked():
			flags = flags | QTextDocument.FindCaseSensitively
		text = self.searchEdit.text()
		if not self.findMain(text, flags):
			if text in self.editBoxes[self.ind].toPlainText():
				cursor = self.editBoxes[self.ind].textCursor()
				if back:
					cursor.movePosition(QTextCursor.End)
				else:
					cursor.movePosition(QTextCursor.Start)
				self.editBoxes[self.ind].setTextCursor(cursor)
				self.findMain(text, flags)
	
	def findMain(self, text, flags):
		if flags:
			return self.editBoxes[self.ind].find(text, flags)
		else:
			return self.editBoxes[self.ind].find(text)
	
	def getHtml(self, includeStyleSheet=True, includeTitle=True,
	            includeMeta=False, styleForWebKit=False, webenv=False):
		if self.markups[self.ind] is None:
			markupClass = self.getMarkupClass()
			errMsg = self.tr('Could not parse file contents, check if '
			'you have the <a href="%s">necessary module</a> installed!')
			try:
				errMsg %= markupClass.attributes[markups.MODULE_HOME_PAGE]
			except:
				# Remove the link if markupClass doesn't have the needed attribute
				errMsg = errMsg.replace('<a href="%s">', '')
				errMsg = errMsg.replace('</a>', '')
			return '<p style="color: red">%s</p>' % errMsg
		text = convertToUnicode(self.editBoxes[self.ind].toPlainText())
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
			% QUrl.fromLocalFile(QFileInfo(cssFileName).absoluteFilePath()).toString()
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
			scrollpos = scrollbar.value()
			maximum = (scrollpos == scrollbar.maximum()
				and scrollpos != scrollbar.minimum())
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
			except:
				return self.printError()
			if not textedit and ('<script ' in html):
				# Work-around a bug in QtWebKit
				# by saving the html locally
				tempFile = QTemporaryFile('retext-XXXXXX.html')
				tempFile.setAutoRemove(False)
				tempFile.open(QIODevice.WriteOnly)
				stream = QTextStream(tempFile)
				stream << html
				tempFile.close()
				self.connect(pb, SIGNAL('loadFinished(bool)'),
					lambda ok: tempFile.remove())
				pb.load(QUrl.fromLocalFile(tempFile.fileName()))
			else:
				pb.setHtml(html)
		if self.font and textedit:
			pb.document().setDefaultFont(self.font)
		if textedit:
			if maximum:
				scrollbar.triggerAction(QScrollBar.SliderToMaximum)
			else:
				scrollbar.setValue(scrollpos)
		else:
			frame.setScrollPosition(scrollpos)
	
	def updateLivePreviewBox(self):
		if self.actionLivePreview.isChecked() and self.previewBlocked == False:
			self.previewBlocked = True
			QTimer.singleShot(1000, self.updatePreviewBox)
	
	def startWpgen(self):
		if not self.fileNames[self.ind]:
			return QMessageBox.warning(self, app_name, self.tr("Please, save the file somewhere."))
		if not QFile.exists("template.html"):
			try:
				wpInit()
			except IOError as e:
				try:
					e = unicode(str(e), 'utf-8')
				except NameError:
					# For Python 3
					e = str(e)
				return QMessageBox.warning(self, app_name, self.tr(
				'Failed to copy default template, please create template.html manually.')
				+ '\n\n' + e)
		wpUpdateAll()
		msgBox = QMessageBox(QMessageBox.Information, app_name,
		self.tr("Webpages saved in <code>html</code> directory."), QMessageBox.Ok)
		showButton = msgBox.addButton(self.tr("Show directory"), QMessageBox.AcceptRole)
		msgBox.exec_()
		if msgBox.clickedButton() == showButton:
			QDesktopServices.openUrl(QUrl.fromLocalFile(QDir('html').absolutePath()))
	
	def showInDir(self):
		if self.fileNames[self.ind]:
			QDesktopServices.openUrl(QUrl.fromLocalFile(QFileInfo(self.fileNames[self.ind]).path()))
		else:
			QMessageBox.warning(self, app_name, self.tr("Please, save the file somewhere."))
	
	def setCurrentFile(self):
		self.setWindowTitle("")
		self.tabWidget.setTabText(self.ind, self.getDocumentTitle(baseName=True))
		self.setWindowFilePath(self.fileNames[self.ind])
		files = readListFromSettings("recentFileList")
		try:
			files.prepend(self.fileNames[self.ind])
			files.removeDuplicates()
		except:
			# For Python 3
			while self.fileNames[self.ind] in files:
				files.remove(self.fileNames[self.ind])
			files.insert(0, self.fileNames[self.ind])
		if len(files) > 10:
			del files[10:]
		writeListToSettings("recentFileList", files)
		QDir.setCurrent(QFileInfo(self.fileNames[self.ind]).dir().path())
		self.docTypeChanged()
	
	def createNew(self):
		self.tabWidget.addTab(self.createTab(""), self.tr("New document"))
		self.ind = self.tabWidget.count()-1
		self.tabWidget.setCurrentIndex(self.ind)
	
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
		for extsprefix in ('/usr', QDir.homePath()+'/.local'):
			extsdir = QDir(extsprefix+'/share/retext/export-extensions/')
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
				print('Failed to parse extension: Name is required')
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
			line = convertToUnicode(stream.readLine())
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
		for fileName in fileNames:
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
			if self.fileNames[self.ind] or self.editBoxes[self.ind].toPlainText() \
			or self.editBoxes[self.ind].document().isModified():
				self.tabWidget.addTab(self.createTab(fileName), "")
				self.ind = self.tabWidget.count()-1
				self.tabWidget.setCurrentIndex(self.ind)
			self.fileNames[self.ind] = fileName
			self.openFileMain()
	
	def openFileMain(self):
		openfile = QFile(self.fileNames[self.ind])
		openfile.open(QIODevice.ReadOnly)
		html = QTextStream(openfile).readAll()
		openfile.close()
		markupClass = markups.get_markup_for_file_name(
			convertToUnicode(self.fileNames[self.ind]), return_class=True)
		self.highlighters[self.ind].docType = (markupClass.name if markupClass else '')
		self.markups[self.ind] = self.getMarkup()
		pt = not markupClass
		if not readFromSettings('autoPlainText', bool, default=True):
			pt = False
			if self.defaultMarkup:
				self.highlighters[self.ind].docType = self.defaultMarkup.name
		self.editBoxes[self.ind].setPlainText(html)
		self.actionPlainText.setChecked(pt)
		self.enablePlainText(pt)
		self.setCurrentFile()
		self.setWindowModified(False)
	
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
				defaultExt = convertToUnicode(self.tr('%s files',
					'Example of final string: Markdown files')) \
					% markupClass.name + ' (' + str.join(' ',
					['*'+ext for ext in markupClass.file_extensions]) + ')'
				ext = markupClass.default_extension
			newFileName = QFileDialog.getSaveFileName(self, self.tr("Save file"), "", defaultExt)
			if newFileName:
				if not QFileInfo(newFileName).suffix():
					newFileName += ext
				self.fileNames[self.ind] = newFileName
		if self.fileNames[self.ind]:
			result = self.saveFileCore(self.fileNames[self.ind])
			if result:
				self.setCurrentFile()
				self.editBoxes[self.ind].document().setModified(False)
				self.setWindowModified(False)
				return True
			else:
				QMessageBox.warning(self, app_name,
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
		except:
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
		except:
			return self.printError()
		fileName = QFileDialog.getSaveFileName(self, self.tr("Export document to ODT"), "",
			self.tr("OpenDocument text files (*.odt)"))
		if not QFileInfo(fileName).suffix():
			fileName += ".odt"
		writer = QTextDocumentWriter(fileName)
		writer.setFormat("odf")
		writer.write(document)
	
	def saveFilePerfect(self):
		fileName = None
		fileName = QFileDialog.getSaveFileName(self, self.tr("Save file"), "",
			self.tr("HTML files (*.html *.htm)"))
		if fileName:
			self.saveHtml(fileName)
	
	def getDocumentForPrint(self):
		if self.useWebKit:
			return self.previewBoxes[self.ind]
		try:
			return self.textDocument()
		except:
			self.printError()
	
	def standardPrinter(self):
		printer = QPrinter(QPrinter.HighResolution)
		printer.setDocName(self.getDocumentTitle())
		printer.setCreator(app_name+" "+app_version)
		return printer
	
	def savePdf(self):
		self.updatePreviewBox()
		fileName = QFileDialog.getSaveFileName(self, self.tr("Export document to PDF"),
			"", self.tr("PDF files (*.pdf)"))
		if fileName:
			if not QFileInfo(fileName).suffix():
				fileName += ".pdf"
			printer = self.standardPrinter()
			printer.setOutputFormat(QPrinter.PdfFormat)
			printer.setOutputFileName(fileName)
			document = self.getDocumentForPrint()
			if document != None:
				document.print_(printer)
	
	def printFile(self):
		self.updatePreviewBox()
		printer = self.standardPrinter()
		dlg = QPrintDialog(printer, self)
		dlg.setWindowTitle(self.tr("Print document"))
		if (dlg.exec_() == QDialog.Accepted):
			document = self.getDocumentForPrint()
			if document != None:
				document.print_(printer)
	
	def printPreview(self):
		document = self.getDocumentForPrint()
		if document == None:
			return
		printer = self.standardPrinter()
		preview = QPrintPreviewDialog(printer, self)
		self.connect(preview, SIGNAL("paintRequested(QPrinter*)"), document.print_)
		preview.exec_()
	
	def runExtensionCommand(self, command, filefilter, defaultext):
		of = ('%of' in command)
		html = ('%html' in command)
		if of:
			if defaultext and not filefilter:
				filefilter = '*'+defaultext
			fileName = QFileDialog.getSaveFileName(self, self.tr('Export document'), '', filefilter)
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
		command = command.replace('%of', 'out'+defaultext)
		command = command.replace('%html' if html else '%if', tmpname)
		try:
			Popen(str(command), shell=True).wait()
		except Exception as error:
			errorstr = str(error)
			try:
				errorstr = QString.fromUtf8(errorstr)
			except:
				# Not needed for Python 3
				pass
			QMessageBox.warning(self, app_name, self.tr('Failed to execute the command:')
			+ '\n' + errorstr)
		QFile(tmpname).remove()
		if of:
			QFile('out'+defaultext).rename(fileName)
	
	def getDocumentTitle(self, baseName=False):
		markup = self.markups[self.ind]
		realTitle = ''
		if markup and not baseName:
			text = convertToUnicode(self.editBoxes[self.ind].toPlainText())
			try:
				realTitle = markup.get_document_title(text)
			except:
				self.printError()
		if realTitle:
			return realTitle
		elif self.fileNames[self.ind]:
			fileinfo = QFileInfo(self.fileNames[self.ind])
			basename = fileinfo.completeBaseName()
			return (basename if basename else fileinfo.fileName())
		return self.tr("New document")
	
	def autoSaveActive(self):
		return self.autoSave and self.fileNames[self.ind] and \
		QFileInfo(self.fileNames[self.ind]).isWritable()
	
	def modificationChanged(self, changed):
		if self.autoSaveActive():
			changed = False
		self.actionSave.setEnabled(changed)
		self.setWindowModified(changed)
	
	def clipboardDataChanged(self):
		self.actionPaste.setEnabled(qApp.clipboard().mimeData().hasText())
	
	def insertChars(self, chars):
		tc = self.editBoxes[self.ind].textCursor()
		if tc.hasSelection():
			selection = convertToUnicode(tc.selectedText())
			if selection.startswith(chars) and selection.endswith(chars):
				if len(selection) > 2*len(chars):
					selection = selection[len(chars):-len(chars)]
					tc.insertText(selection)
			else:
				tc.insertText(chars+tc.selectedText()+chars)
		else:
			tc.insertText(chars)
	
	def insertTag(self, num):
		if num:
			ut = self.usefulTags[num-1]
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
		ret = QMessageBox.warning(self, app_name,
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
		if self.restorePreviewState:
			if self.livePreviewEnabled:
				settings.setValue('previewState', True)
			else:
				settings.remove('previewState')
		if self.saveWindowGeometry and not self.isMaximized():
			settings.setValue('windowGeometry', self.saveGeometry())
		closeevent.accept()
	
	def viewHtml(self):
		HtmlDlg = HtmlDialog(self)
		try:
			htmltext = self.getHtml(includeStyleSheet=False, includeTitle=False)
		except:
			return self.printError()
		winTitle = self.getDocumentTitle(baseName=True)
		try:
			HtmlDlg.setWindowTitle(winTitle+" ("+self.tr("HTML code")+") "+QChar(0x2014)+" "+app_name)
		except:
			# For Python 3
			HtmlDlg.setWindowTitle(winTitle+" ("+self.tr("HTML code")+") \u2014 "+app_name)
		HtmlDlg.textEdit.setPlainText(htmltext.rstrip())
		HtmlDlg.show()
		HtmlDlg.raise_()
		HtmlDlg.activateWindow()
	
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
		self.aptc[self.ind] = value
		self.actionPerfectHtml.setDisabled(value)
		self.actionViewHtml.setDisabled(value)
		self.docTypeChanged()
	
	def setDefaultMarkup(self, markup):
		self.defaultMarkup = markup
		if markup == markups.get_available_markups()[0]:
			settings.remove('defaultMarkup')
		else:
			settings.setValue('defaultMarkup', markup.name)
		oldind = self.ind
		for self.ind in range(len(self.previewBoxes)):
			self.docTypeChanged()
		self.ind = oldind
