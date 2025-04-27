# vim: ts=4:sw=4:expandtab
#
# This file is part of ReText
# Copyright: 2012-2025 Dmitry Shachnev
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

import configparser
import os
import shlex
import sys
import traceback
import warnings
from subprocess import Popen

import markups

from ReText import app_version, getBundledIcon, globalCache, globalSettings
from ReText.config import ConfigDialog, setIconThemeFromSettings
from ReText.dialogs import EncodingDialog, HtmlDialog, LocaleDialog
from ReText.filesystemmodel import ReTextFileSystemModel
from ReText.tab import (
    PreviewDisabled,
    PreviewLive,
    PreviewNormal,
    ReTextTab,
    ReTextWebEnginePreview,
)
from ReText.tabledialog import InsertTableDialog

try:
    from ReText.fakevimeditor import FakeVimMode, ReTextFakeVimHandler
except ImportError:
    ReTextFakeVimHandler = None

try:
    import enchant
except ImportError:
    enchant = None

from PyQt6.QtCore import (
    QByteArray,
    QDir,
    QFile,
    QFileInfo,
    QFileSystemWatcher,
    QLocale,
    QMarginsF,
    QStandardPaths,
    Qt,
    QTimer,
    QUrl,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QDesktopServices,
    QIcon,
    QKeySequence,
    QPageLayout,
    QPageSize,
    QPalette,
    QTextDocument,
    QTextDocumentWriter,
)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFontDialog,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QTreeView,
)

previewStatesByName = {
    'editor': PreviewDisabled,
    'normal-preview': PreviewNormal,
    'live-preview': PreviewLive,
}


class ReTextWindow(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.resize(950, 700)
        qApp = QApplication.instance()
        screenRect = self.screen().geometry()
        if globalCache.windowGeometry:
            self.restoreGeometry(globalCache.windowGeometry)
        else:
            self.move((screenRect.width() - self.width()) // 2,
                      (screenRect.height() - self.height()) // 2)
            if not screenRect.contains(self.geometry()):
                self.showMaximized()
        if sys.platform.startswith('darwin'):
            # https://github.com/retext-project/retext/issues/198
            searchPaths = QIcon.themeSearchPaths()
            searchPaths.append('/opt/local/share/icons')
            searchPaths.append('/usr/local/share/icons')
            QIcon.setThemeSearchPaths(searchPaths)
        setIconThemeFromSettings()
        if QFile.exists(getBundledIcon('retext')):
            self.setWindowIcon(QIcon(getBundledIcon('retext')))
        elif QFile.exists('/usr/share/pixmaps/retext.png'):
            self.setWindowIcon(QIcon('/usr/share/pixmaps/retext.png'))
        else:
            self.setWindowIcon(QIcon.fromTheme('retext',
                QIcon.fromTheme('accessories-text-editor')))
        self.splitter = QSplitter(self)
        self.treeView = QTreeView(self.splitter)
        self.treeView.doubleClicked.connect(self.treeItemSelected)
        self.initDirectoryTree()
        self.treeView.setVisible(globalSettings.showDirectoryTree)
        self.tabWidget = QTabWidget(self.splitter)
        self.initTabWidget()
        if globalCache.splitterState:
            self.splitter.restoreState(globalCache.splitterState)
        else:
            self.splitter.setSizes([self.width() // 5, self.width() * 4 // 5])
        self.setCentralWidget(self.splitter)
        self.tabWidget.currentChanged.connect(self.changeIndex)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)
        self.toolBar = QToolBar(self.tr('File toolbar'), self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolBar)
        self.editBar = QToolBar(self.tr('Edit toolbar'), self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.editBar)
        self.searchBar = QToolBar(self.tr('Search toolbar'), self)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.searchBar)
        self.toolBar.setVisible(not globalSettings.hideToolBar)
        self.editBar.setVisible(not globalSettings.hideToolBar)
        self.actionNew = self.act(self.tr('New'), 'document-new',
            self.createNew, shct=QKeySequence.StandardKey.New)
        self.actionOpen = self.act(self.tr('Open'), 'document-open',
            self.openFile, shct=QKeySequence.StandardKey.Open)
        self.actionSetEncoding = self.act(self.tr('Set encoding'),
            trig=self.showEncodingDialog)
        self.actionSetEncoding.setEnabled(False)
        self.actionReload = self.act(self.tr('Reload'), 'view-refresh',
            lambda: self.currentTab.readTextFromFile())
        self.actionReload.setEnabled(False)
        self.actionSave = self.act(self.tr('Save'), 'document-save',
            self.saveFile, shct=QKeySequence.StandardKey.Save)
        self.actionSave.setEnabled(False)
        self.actionSaveAs = self.act(self.tr('Save as'), 'document-save-as',
            self.saveFileAs, shct=QKeySequence.StandardKey.SaveAs)
        self.actionNextTab = self.act(self.tr('Next tab'), 'go-next',
            lambda: self.switchTab(1))
        self.actionNextTab.setShortcuts([
            *QKeySequence.keyBindings(QKeySequence.StandardKey.NextChild),
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_PageDown),
        ])
        self.actionPrevTab = self.act(self.tr('Previous tab'), 'go-previous',
            lambda: self.switchTab(-1))
        self.actionPrevTab.setShortcuts([
            *QKeySequence.keyBindings(QKeySequence.StandardKey.PreviousChild),
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_PageUp),
            # https://bugreports.qt.io/browse/QTBUG-15746
            QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Backtab),
        ])
        self.actionCloseCurrentTab = self.act(self.tr('Close tab'), 'window-close',
            lambda: self.closeTab(self.ind), shct=QKeySequence.StandardKey.Close)
        self.actionPrint = self.act(self.tr('Print'), 'document-print',
            self.printFile, shct=QKeySequence.StandardKey.Print)
        self.actionPrintPreview = self.act(self.tr('Print preview'), 'document-print-preview',
            self.printPreview)
        self.actionViewHtml = self.act(
            self.tr('View HTML code'),
            'text-html',
            self.viewHtml,
            shct=Qt.Modifier.CTRL | Qt.Key.Key_H,
        )
        self.actionChangeEditorFont = self.act(self.tr('Change editor font'),
            trig=self.changeEditorFont)
        self.actionChangePreviewFont = self.act(self.tr('Change preview font'),
            trig=self.changePreviewFont)
        self.actionSearch = self.act(self.tr('Find text'), 'edit-find',
            self.search, shct=QKeySequence.StandardKey.Find)
        self.actionGoToLine = self.act(self.tr('Go to line'),
            trig=self.goToLine, shct=Qt.Modifier.CTRL | Qt.Key.Key_G)
        self.searchBar.visibilityChanged.connect(self.searchBarVisibilityChanged)
        self.actionPreview = self.act(self.tr('Preview'), shct=Qt.Modifier.CTRL | Qt.Key.Key_E,
            trigbool=self.preview)
        if QIcon.hasThemeIcon('document-preview'):
            self.actionPreview.setIcon(QIcon.fromTheme('document-preview'))
        elif QIcon.hasThemeIcon('preview-file'):
            self.actionPreview.setIcon(QIcon.fromTheme('preview-file'))
        elif QIcon.hasThemeIcon('x-office-document'):
            self.actionPreview.setIcon(QIcon.fromTheme('x-office-document'))
        else:
            self.actionPreview.setIcon(QIcon(getBundledIcon('document-preview')))
        self.actionLivePreview = self.act(self.tr('Live preview'), shct=Qt.Modifier.CTRL | Qt.Key.Key_L,
        trigbool=self.enableLivePreview)
        menuPreview = QMenu()
        menuPreview.addAction(self.actionLivePreview)
        self.actionInsertTable = self.act(self.tr('Insert table'),
            trig=lambda: self.insertFormatting('table'))
        self.actionTableMode = self.act(self.tr('Table editing mode'),
            shct=Qt.Modifier.CTRL | Qt.Key.Key_T,
            trigbool=lambda x: self.currentTab.editBox.enableTableMode(x))
        self.actionInsertImages = self.act(self.tr('Insert images by file path'),
            trig=lambda: self.insertImages())
        if ReTextFakeVimHandler:
            self.actionFakeVimMode = self.act(self.tr('FakeVim mode'),
                shct=Qt.Modifier.CTRL | Qt.Modifier.ALT | Qt.Key.Key_V, trigbool=self.enableFakeVimMode)
            if globalSettings.useFakeVim:
                self.actionFakeVimMode.setChecked(True)
                self.enableFakeVimMode(True)
        self.actionFullScreen = self.act(self.tr('Fullscreen mode'), 'view-fullscreen',
            shct=QKeySequence.StandardKey.FullScreen, trigbool=self.enableFullScreen)
        self.actionFullScreen.setChecked(self.isFullScreen())
        self.actionConfig = self.act(self.tr('Preferences'), trig=self.openConfigDialog)
        if QIcon.hasThemeIcon('configure'):
            self.actionConfig.setIcon(QIcon.fromTheme('configure'))
        else:
            self.actionConfig.setIcon(QIcon.fromTheme('preferences-system'))
        self.actionConfig.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.actionSaveHtml = self.act('HTML', 'text-html', self.saveFileHtml)
        self.actionPdf = self.act('PDF', 'application-pdf', self.savePdf)
        self.actionOdf = self.act('ODT', 'x-office-document', self.saveOdf)
        self.getExportExtensionsList()
        self.actionQuit = self.act(
            self.tr('Quit'),
            'application-exit',
            shct=QKeySequence.StandardKey.Quit,
        )
        self.actionQuit.setMenuRole(QAction.MenuRole.QuitRole)
        self.actionQuit.triggered.connect(self.close)
        self.actionUndo = self.act(self.tr('Undo'), 'edit-undo',
            lambda: self.currentTab.editBox.undo(), shct=QKeySequence.StandardKey.Undo)
        self.actionRedo = self.act(self.tr('Redo'), 'edit-redo',
            lambda: self.currentTab.editBox.redo(), shct=QKeySequence.StandardKey.Redo)
        self.actionCopy = self.act(self.tr('Copy'), 'edit-copy',
            lambda: self.currentTab.editBox.copy(), shct=QKeySequence.StandardKey.Copy)
        self.actionCut = self.act(self.tr('Cut'), 'edit-cut',
            lambda: self.currentTab.editBox.cut(), shct=QKeySequence.StandardKey.Cut)
        self.actionPaste = self.act(self.tr('Paste'), 'edit-paste',
            lambda: self.currentTab.editBox.paste(), shct=QKeySequence.StandardKey.Paste)
        self.actionPasteImage = self.act(
            self.tr('Paste image'),
            'edit-paste',
            lambda: self.currentTab.editBox.pasteImage(),
            shct=Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_V,
        )
        self.actionMoveUp = self.act(self.tr('Move line up'), 'go-up',
            lambda: self.currentTab.editBox.moveLineUp(), shct=Qt.Modifier.ALT | Qt.Key.Key_Up)
        self.actionMoveDown = self.act(self.tr('Move line down'), 'go-down',
            lambda: self.currentTab.editBox.moveLineDown(), shct=Qt.Modifier.ALT | Qt.Key.Key_Down)
        self.actionUndo.setEnabled(False)
        self.actionRedo.setEnabled(False)
        self.actionCopy.setEnabled(False)
        self.actionCut.setEnabled(False)
        qApp.clipboard().dataChanged.connect(self.clipboardDataChanged)
        self.clipboardDataChanged()
        self.actionEnableSC = self.act(self.tr('Enable'), trigbool=self.enableSpellCheck)
        self.actionSetLocale = self.act(self.tr('Set locale'), trig=self.changeLocale)
        self.actionWebEngine = self.act(self.tr('Use WebEngine (Chromium) renderer'),
            trigbool=self.enableWebEngine)
        if ReTextWebEnginePreview is None:
            globalSettings.useWebEngine = False
            self.actionWebEngine.setEnabled(False)
        self.actionWebEngine.setChecked(globalSettings.useWebEngine)
        self.actionShow = self.act(self.tr('Show directory'), 'document-open-folder', self.showInDir)
        self.actionShowDirectoryTree = self.act(self.tr('Show directory tree'),
            trigbool=self.treeView.setVisible,
            shct=Qt.Key.Key_F9)
        self.actionShowDirectoryTree.setChecked(globalSettings.showDirectoryTree)
        self.actionFind = self.act(self.tr('Next'), 'go-next', self.find,
            shct=QKeySequence.StandardKey.FindNext)
        self.actionFindPrev = self.act(self.tr('Previous'), 'go-previous',
            lambda: self.find(back=True), shct=QKeySequence.StandardKey.FindPrevious)
        self.actionReplace = self.act(self.tr('Replace'), 'edit-find-replace',
            lambda: self.find(replace=True))
        self.actionReplaceAll = self.act(self.tr('Replace all'), trig=self.replaceAll)
        menuReplace = QMenu()
        menuReplace.addAction(self.actionReplaceAll)
        self.actionCloseSearch = self.act(self.tr('Close'), 'window-close',
            lambda: self.searchBar.setVisible(False),
            shct=QKeySequence.StandardKey.Cancel)
        self.actionCloseSearch.setPriority(QAction.Priority.LowPriority)
        self.actionHelp = self.act(self.tr('Get help online'), 'help-contents', self.openHelp)
        self.actionWhatsNew = self.act(self.tr("What's new"), trig=self.openReleases)
        self.aboutWindowTitle = self.tr('About ReText')
        self.actionAbout = self.act(self.aboutWindowTitle, 'help-about', self.aboutDialog)
        self.actionAbout.setMenuRole(QAction.MenuRole.AboutRole)
        self.actionAboutQt = self.act(self.tr('About Qt'))
        self.actionAboutQt.setMenuRole(QAction.MenuRole.AboutQtRole)
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
        self.actionBold = self.act(self.tr('Bold'), shct=QKeySequence.StandardKey.Bold,
            trig=lambda: self.insertFormatting('bold'))
        self.actionItalic = self.act(self.tr('Italic'), shct=QKeySequence.StandardKey.Italic,
            trig=lambda: self.insertFormatting('italic'))
        self.actionUnderline = self.act(self.tr('Underline'), shct=QKeySequence.StandardKey.Underline,
            trig=lambda: self.insertFormatting('underline'))
        self.usefulTags = ('header', 'italic', 'bold', 'underline', 'numbering',
            'bullets', 'image', 'link', 'inline code', 'code block', 'blockquote',
            'table')
        self.usefulChars = ('deg', 'divide', 'euro', 'hellip', 'laquo', 'larr',
            'lsquo', 'mdash', 'middot', 'minus', 'nbsp', 'ndash', 'raquo',
            'rarr', 'rsquo', 'times')
        self.formattingBox = QComboBox(self.editBar)
        self.formattingBox.addItem(self.tr('Formatting'))
        self.formattingBox.addItems(self.usefulTags)
        self.formattingBox.textActivated.connect(self.insertFormatting)
        self.symbolBox = QComboBox(self.editBar)
        self.symbolBox.addItem(self.tr('Symbols'))
        self.symbolBox.addItems(self.usefulChars)
        self.symbolBox.activated.connect(self.insertSymbol)
        self.updateStyleSheet()
        menubar = self.menuBar()
        menuFile = menubar.addMenu(self.tr('&File'))
        menuEdit = menubar.addMenu(self.tr('&Edit'))
        menuHelp = menubar.addMenu(self.tr('&Help'))
        menuFile.addAction(self.actionNew)
        menuFile.addAction(self.actionOpen)
        self.menuRecentFiles = menuFile.addMenu(
            self.actIcon('document-open-recent'),
            self.tr('Open recent'),
        )
        self.menuRecentFiles.aboutToShow.connect(self.updateRecentFiles)
        menuFile.addAction(self.actionShow)
        menuFile.addAction(self.actionShowDirectoryTree)
        menuFile.addAction(self.actionSetEncoding)
        menuFile.addAction(self.actionReload)
        menuFile.addSeparator()
        menuFile.addAction(self.actionSave)
        menuFile.addAction(self.actionSaveAs)
        menuFile.addSeparator()
        menuFile.addAction(self.actionNextTab)
        menuFile.addAction(self.actionPrevTab)
        menuFile.addAction(self.actionCloseCurrentTab)
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
        menuEdit.addAction(self.actionPasteImage)
        menuEdit.addSeparator()
        menuEdit.addAction(self.actionMoveUp)
        menuEdit.addAction(self.actionMoveDown)
        menuEdit.addSeparator()
        if enchant is not None:
            menuSC = menuEdit.addMenu(self.tr('Spell check'))
            menuSC.addAction(self.actionEnableSC)
            menuSC.addAction(self.actionSetLocale)
        menuEdit.addAction(self.actionSearch)
        menuEdit.addAction(self.actionGoToLine)
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
        menuEdit.addAction(self.actionWebEngine)
        menuEdit.addSeparator()
        menuEdit.addAction(self.actionViewHtml)
        menuEdit.addAction(self.actionPreview)
        menuEdit.addAction(self.actionLivePreview)
        menuEdit.addAction(self.actionInsertTable)
        menuEdit.addAction(self.actionTableMode)
        menuEdit.addAction(self.actionInsertImages)
        if ReTextFakeVimHandler:
            menuEdit.addAction(self.actionFakeVimMode)
        menuEdit.addSeparator()
        menuEdit.addAction(self.actionFullScreen)
        menuEdit.addAction(self.actionConfig)
        menuHelp.addAction(self.actionHelp)
        menuHelp.addAction(self.actionWhatsNew)
        menuHelp.addSeparator()
        menuHelp.addAction(self.actionAbout)
        menuHelp.addAction(self.actionAboutQt)
        self.toolBar.addAction(self.actionNew)
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actionOpen)
        self.toolBar.addAction(self.actionSave)
        self.toolBar.addAction(self.actionPrint)
        self.toolBar.addSeparator()
        previewButton = QToolButton(self.toolBar)
        previewButton.setDefaultAction(self.actionPreview)
        previewButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        previewButton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        previewButton.setMenu(menuPreview)
        self.toolBar.addWidget(previewButton)
        self.toolBar.addAction(self.actionFullScreen)
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
        replaceButton = QToolButton(self.searchBar)
        replaceButton.setDefaultAction(self.actionReplace)
        replaceButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        replaceButton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        replaceButton.setMenu(menuReplace)
        self.searchBar.addWidget(replaceButton)
        self.searchBar.addAction(self.actionCloseSearch)
        self.searchBar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.searchBar.setVisible(False)
        self.autoSaveTimer = QTimer(self)
        self.autoSaveTimer.timeout.connect(self.saveAll)
        if globalSettings.autoSave:
            self.autoSaveTimer.start(60000)
        self.ind = None
        if enchant is not None:
            self.spellCheckLanguages = globalSettings.spellCheckLocale
            languages, errors = self.getSpellCheckDictionaries()
            for error in errors:
                warnings.warn(error, RuntimeWarning)
            if not languages:
                globalSettings.spellCheck = False
            if globalSettings.spellCheck:
                self.actionEnableSC.setChecked(True)
        self.fileSystemWatcher = QFileSystemWatcher()
        self.fileSystemWatcher.fileChanged.connect(self.fileChanged)

    def restoreLastOpenedFiles(self):
        for file in globalCache.lastFileList:
            self.openFileWrapper(file)

        # Show the tab of last opened file
        lastTabIndex = globalCache.lastTabIndex
        if lastTabIndex >= 0 and lastTabIndex < self.tabWidget.count():
            self.tabWidget.setCurrentIndex(lastTabIndex)

    def iterateTabs(self):
        for i in range(self.tabWidget.count()):
            yield self.tabWidget.widget(i)

    def updateStyleSheet(self):
        self.ss = None
        if globalSettings.styleSheet:
            try:
                with open(globalSettings.styleSheet) as sheetfile:
                    self.ss = sheetfile.read()
            except OSError as ex:
                QMessageBox.warning(self, '', str(ex))

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
        self.tabWidget.setTabBarAutoHide(globalSettings.tabBarAutoHide)

    def initDirectoryTree(self):
        path = globalSettings.directoryPath
        self.fileSystemModel = ReTextFileSystemModel(self.treeView)
        self.fileSystemModel.setRootPath(path)
        supportedExtensions = ['.txt']
        for markup in markups.get_all_markups():
            supportedExtensions += markup.file_extensions
        filters = ["*" + s for s in supportedExtensions]
        self.fileSystemModel.setNameFilters(filters)
        self.fileSystemModel.setNameFilterDisables(False)
        self.treeView.setModel(self.fileSystemModel)
        self.treeView.setRootIndex(self.fileSystemModel.index(path))
        self.treeView.setColumnHidden(1, True)
        self.treeView.setColumnHidden(2, True)
        self.treeView.setColumnHidden(3, True)
        self.treeView.setHeaderHidden(True)

    def treeItemSelected(self, signal):
        file_path = self.fileSystemModel.filePath(signal)
        if os.path.isdir(file_path):
            return
        self.openFileWrapper(file_path)

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
        print('Exception occurred while parsing document:', file=sys.stderr)
        traceback.print_exc()

    def updateTabTitle(self, ind, tab):
        changed = tab.editBox.document().isModified()
        if changed:
            title = tab.getBaseName() + '*'
        else:
            title = tab.getBaseName()
        self.tabWidget.setTabText(ind, title)

    def tabFileNameChanged(self, tab):
        '''
        Perform all UI state changes that need to be done when the
        filename of the current tab has changed.
        '''
        if tab == self.currentTab:
            if tab.fileName:
                self.setWindowTitle("")
                if globalSettings.windowTitleFullPath:
                    self.setWindowTitle(tab.fileName + '[*]')
                self.setWindowFilePath(tab.fileName)
                self.updateTabTitle(self.ind, tab)
                self.tabWidget.setTabToolTip(self.ind, tab.fileName)
                QDir.setCurrent(QFileInfo(tab.fileName).dir().path())
            else:
                self.setWindowFilePath('')
                self.setWindowTitle(self.tr('New document') + '[*]')

            canReload = bool(tab.fileName) and not tab.autoSaveActive()
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
            self.actionSave.setEnabled(changed)
            self.updateTabTitle(self.ind, tab)
            self.setWindowModified(changed)

    def createTab(self, fileName):
        previewState = previewStatesByName.get(globalSettings.defaultPreviewState, PreviewDisabled)
        if previewState == PreviewNormal and not fileName:
            previewState = PreviewDisabled  # Opening empty document in preview mode makes no sense
        self.currentTab = ReTextTab(self, fileName, previewState)
        self.currentTab.fileNameChanged.connect(lambda: self.tabFileNameChanged(self.currentTab))
        self.currentTab.modificationStateChanged.connect(
            lambda: self.tabModificationStateChanged(self.currentTab)
        )
        self.currentTab.activeMarkupChanged.connect(lambda: self.tabActiveMarkupChanged(self.currentTab))
        self.tabWidget.addTab(self.currentTab, self.tr("New document"))
        self.currentTab.updateBoxesVisibility()
        if previewState > 0:
            QTimer.singleShot(500, self.currentTab.triggerPreviewUpdate)

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
        editBox.setFocus(Qt.FocusReason.OtherFocusReason)

        self.tabFileNameChanged(self.currentTab)
        self.tabModificationStateChanged(self.currentTab)
        self.tabActiveMarkupChanged(self.currentTab)

    def changeEditorFont(self):
        font, ok = QFontDialog.getFont(globalSettings.getEditorFont(), self)
        if ok:
            self.setEditorFont(font)

    def setEditorFont(self, font):
        globalSettings.editorFont = font.toString()
        for tab in self.iterateTabs():
            tab.editBox.updateFont()

    def changePreviewFont(self):
        font, ok = QFontDialog.getFont(globalSettings.getPreviewFont(), self)
        if ok:
            self.setPreviewFont(font)

    def setPreviewFont(self, font):
        globalSettings.font = font.toString()
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

    def enableWebEngine(self, enable):
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

    def getSpellCheckDictionaries(self):
        """Returns the list of languages and the list of errors."""
        dictionaries = []
        errors = []
        if enchant is None:
            return dictionaries, errors
        for language in self.spellCheckLanguages.split(','):
            try:
                dict = enchant.Dict(language.strip() or None)
            except enchant.errors.Error as e:
                errors.append(str(e))
            else:
                dictionaries.append(dict)
        return dictionaries, errors

    def enableSpellCheck(self, yes):
        dictionaries = []
        if yes:
            dictionaries, errors = self.getSpellCheckDictionaries()
            if errors:
                QMessageBox.warning(self, '', '\n'.join(errors))
        for tab in self.iterateTabs():
            tab.highlighter.dictionaries = dictionaries
            tab.highlighter.rehighlight()
        globalSettings.spellCheck = bool(dictionaries)
        self.actionEnableSC.setChecked(bool(dictionaries))

    def changeLocale(self):
        localedlg = LocaleDialog(self, defaultText=self.spellCheckLanguages)
        if localedlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.spellCheckLanguages = localedlg.localeEdit.text()
        self.enableSpellCheck(True)
        globalSettings.spellCheckLocale = self.spellCheckLanguages

    def search(self):
        self.searchBar.setVisible(True)
        self.searchEdit.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def goToLine(self):
        line, ok = QInputDialog.getInt(self, self.tr("Go to line"), self.tr("Type the line number"))
        if ok:
            self.currentTab.goToLine(line-1)

    def searchBarVisibilityChanged(self, visible):
        if visible:
            self.searchEdit.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def find(self, back=False, replace=False):
        flags = QTextDocument.FindFlag(0)
        if back:
            flags |= QTextDocument.FindFlag.FindBackward
        if self.csBox.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
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
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.Base,
                         Qt.GlobalColor.white if found else QColor(255, 102, 102))
        self.searchEdit.setPalette(palette)

    def showInDir(self):
        if self.currentTab.fileName:
            path = QFileInfo(self.currentTab.fileName).path()
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, '', self.tr("Please, save the file somewhere."))

    def moveToTopOfRecentFileList(self, fileName):
        if fileName:
            files = globalCache.recentFileList
            if fileName in files:
                files.remove(fileName)
            files.insert(0, fileName)
            recentCount = globalSettings.recentDocumentsCount
            if len(files) > recentCount:
                del files[recentCount:]
            globalCache.recentFileList = files

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
        filesOld = globalCache.recentFileList
        files = []
        for f in filesOld:
            if QFile.exists(f):
                files.append(f)
                self.recentFilesActions.append(self.act(f, trig=self.openFunction(f)))
        globalCache.recentFileList = files
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
        datadirs = QStandardPaths.standardLocations(
            QStandardPaths.StandardLocation.GenericDataLocation)
        for datadir in datadirs:
            extsdir = QDir(os.path.join(datadir, 'retext', 'export-extensions'))
            if extsdir.exists():
                for fileInfo in extsdir.entryInfoList(['*.desktop', '*.ini'],
                QDir.Filter.Files | QDir.Filter.Readable):
                    extensions.append(self.readExtension(fileInfo.filePath()))
        locale = QLocale.system().name()
        self.extensionActions = []
        for extension in extensions:
            try:
                locale_short = locale.split('_')[0]
                if f'Name[{locale}]' in extension:
                    name = extension[f'Name[{locale}]']
                elif f'Name[{locale_short}]' in extension:
                    name = extension[f'Name[{locale_short}]']
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
                enabled = (mimetype == "text/markdown")
            elif markupClass == markups.ReStructuredTextMarkup:
                enabled = (mimetype == "text/x-rst")
            else:
                enabled = False
            action[0].setEnabled(enabled)

    def readExtension(self, fileName):
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(fileName)
        return dict(parser.items('Desktop Entry'))

    def openFile(self):
        supportedExtensions = ['.txt']
        for markup in markups.get_all_markups():
            supportedExtensions += markup.file_extensions
        fileFilter = ' (' + ' '.join('*' + ext for ext in supportedExtensions) + ');;'
        fileNames = QFileDialog.getOpenFileNames(self,
            self.tr("Select one or several files to open"), QDir.currentPath(),
            self.tr("Supported files") + fileFilter + self.tr("All files (*)"))
        for fileName in fileNames[0]:
            self.openFileWrapper(fileName)

    @pyqtSlot(str)
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
            elif globalSettings.defaultPreviewState == "normal-preview":
                self.actionPreview.setChecked(True)
                self.preview(True)
            if fileName:
                self.fileSystemWatcher.addPath(fileName)
            self.currentTab.readTextFromFile(fileName)
            self.moveToTopOfRecentFileList(self.currentTab.fileName)

    def showEncodingDialog(self):
        if not self.maybeSave(self.ind):
            return
        dialog = EncodingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            encoding = dialog.encodingEdit.text()
            self.currentTab.readTextFromFile(None, encoding)

    def saveFileAs(self):
        self.saveFile(dlg=True)

    def saveAll(self):
        for tab in self.iterateTabs():
            if tab.autoSaveActive() and tab.editBox.document().isModified():
                tab.saveTextToFile()

    def saveFile(self, dlg=False):
        fileNameToSave = self.currentTab.fileName

        if (not fileNameToSave) or dlg:
            proposedFileName = ""
            markupClass = self.currentTab.getActiveMarkupClass()
            if (markupClass is None) or not hasattr(markupClass, 'default_extension'):
                defaultExt = self.tr("Plain text (*.txt)")
                ext = ".txt"
            else:
                defaultExt = (
                    self.tr('%s files', 'Example of final string: Markdown files') % markupClass.name
                    + ' ('
                    + ' '.join('*' + extension for extension in markupClass.file_extensions)
                    + ')'
                )
                if markupClass == markups.MarkdownMarkup:
                    ext = globalSettings.markdownDefaultFileExtension
                elif markupClass == markups.ReStructuredTextMarkup:
                    ext = globalSettings.restDefaultFileExtension
                else:
                    ext = markupClass.default_extension
            if fileNameToSave is not None:
                proposedFileName = fileNameToSave
            fileNameToSave = QFileDialog.getSaveFileName(self,
                self.tr("Save file"), proposedFileName, defaultExt)[0]
            if fileNameToSave:
                if not QFileInfo(fileNameToSave).suffix():
                    fileNameToSave += ext
                # Make sure we don't overwrite a file opened in other tab
                for tab in self.iterateTabs():
                    if tab is not self.currentTab and tab.fileName == fileNameToSave:
                        QMessageBox.warning(self, "",
                            self.tr("Cannot save to file which is open in another tab!"))
                        return False
                self.actionSetEncoding.setDisabled(self.currentTab.autoSaveActive())
        if fileNameToSave:
            if self.currentTab.saveTextToFile(fileNameToSave):
                self.moveToTopOfRecentFileList(self.currentTab.fileName)
                return True
        return False

    def saveHtml(self, fileName):
        if not QFileInfo(fileName).suffix():
            fileName += ".html"
        try:
            _, htmltext, _ = self.currentTab.getDocumentForExport(webenv=True)
        except Exception:
            return self.printError()

        encoding = globalSettings.defaultCodec or None
        try:
            with open(fileName, 'w', encoding=encoding) as htmlFile:
                htmlFile.write(htmltext)
        except (OSError, UnicodeEncodeError, LookupError) as ex:
            QMessageBox.warning(self, '', str(ex))

    def textDocument(self, title, htmltext):
        td = QTextDocument()
        td.setMetaInformation(QTextDocument.MetaInformation.DocumentTitle, title)
        td.setHtml(htmltext)
        td.setDefaultFont(globalSettings.getPreviewFont())
        return td

    def saveOdf(self):
        title, htmltext, _ = self.currentTab.getDocumentForExport()
        try:
            document = self.textDocument(title, htmltext)
        except Exception:
            return self.printError()
        fileName = QFileDialog.getSaveFileName(self,
            self.tr("Export document to ODT"), self.currentTab.getBaseName() + ".odt",
            self.tr("OpenDocument text files (*.odt)"))[0]
        if not QFileInfo(fileName).suffix():
            fileName += ".odt"
        writer = QTextDocumentWriter(fileName)
        writer.setFormat(b"odf")
        writer.write(document)

    def saveFileHtml(self):
        fileName = QFileDialog.getSaveFileName(self,
            self.tr("Save file"), self.currentTab.getBaseName() + ".html",
            self.tr("HTML files (*.html *.htm)"))[0]
        if fileName:
            self.saveHtml(fileName)

    def getDocumentForPrint(self, title, htmltext, preview):
        try:
            return self.textDocument(title, htmltext)
        except Exception:
            self.printError()

    def standardPrinter(self, title):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(title)
        printer.setCreator(f'ReText {app_version}')
        if globalSettings.paperSize:
            pageSize = self.getPageSizeByName(globalSettings.paperSize)
            if pageSize is not None:
                printer.setPageSize(pageSize)
            else:
                QMessageBox.warning(self, '',
                    self.tr('Unrecognized paperSize setting "%s".') %
                    globalSettings.paperSize)
        return printer

    def getPageSizeByName(self, pageSizeName):
        """ Returns a validated QPageSize instance corresponding to the given
        name. Returns None if the name is not a valid PageSize.
        """
        sizesByName = {e.name.lower(): e for e in QPageSize.PageSizeId}
        sizeId = sizesByName.get(pageSizeName.lower())
        if sizeId is not None:
            return QPageSize(sizeId)

    def savePdf(self):
        fileName = QFileDialog.getSaveFileName(self,
            self.tr("Export document to PDF"),
            self.currentTab.getBaseName() + ".pdf",
            self.tr("PDF files (*.pdf)"))[0]
        if fileName:
            if not QFileInfo(fileName).suffix():
                fileName += ".pdf"
            title, htmltext, preview = self.currentTab.getDocumentForExport()
            if globalSettings.useWebEngine:
                pageSize = self.getPageSizeByName(globalSettings.paperSize)
                if pageSize is None:
                    pageSize = QPageSize(QPageSize.PageSizeId.A4)
                margins = QMarginsF(20, 20, 13, 20)  # left, top, right, bottom (in millimeters)
                layout = QPageLayout(
                    pageSize,
                    QPageLayout.Orientation.Portrait,
                    margins,
                    QPageLayout.Unit.Millimeter,
                )
                preview.page().printToPdf(fileName, layout)
                return
            printer = self.standardPrinter(title)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(fileName)
            document = self.getDocumentForPrint(title, htmltext, preview)
            if document is not None:
                document.print(printer)

    def printFile(self):
        title, htmltext, preview = self.currentTab.getDocumentForExport()
        printer = self.standardPrinter(title)
        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle(self.tr("Print document"))
        if (dlg.exec() == QDialog.DialogCode.Accepted):
            document = self.getDocumentForPrint(title, htmltext, preview)
            if document is not None:
                document.print(printer)

    def printPreview(self):
        title, htmltext, preview = self.currentTab.getDocumentForExport()
        document = self.getDocumentForPrint(title, htmltext, preview)
        if document is None:
            return
        printer = self.standardPrinter(title)
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
        else:
            fileName = 'out' + defaultext
        basename = f'.{self.currentTab.getBaseName()}.retext-temp'
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

    def clipboardDataChanged(self):
        mimeData = QApplication.instance().clipboard().mimeData()
        if mimeData is not None:
            self.actionPaste.setEnabled(mimeData.hasText())
            self.actionPasteImage.setEnabled(mimeData.hasImage())

    def insertFormatting(self, formatting):
        if formatting == 'table':
            dialog = InsertTableDialog(self)
            dialog.show()
            self.formattingBox.setCurrentIndex(0)
            return

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
        self.currentTab.editBox.setFocus(Qt.FocusReason.OtherFocusReason)

        if moveCursorTo:
            cursor.setPosition(moveCursorTo)
            self.currentTab.editBox.setTextCursor(cursor)

    def insertSymbol(self, num):
        if num:
            self.currentTab.editBox.insertPlainText('&'+self.usefulChars[num-1]+';')
        self.symbolBox.setCurrentIndex(0)

    def fileChanged(self, fileName):
        tab = None
        for testtab in self.iterateTabs():
            if testtab.fileName == fileName:
                tab = testtab
        if tab is None:
            self.fileSystemWatcher.removePath(fileName)
            return
        if not QFile.exists(fileName):
            self.tabWidget.setCurrentWidget(tab)
            tab.editBox.document().setModified(True)
            QMessageBox.warning(self, '', self.tr(
                'This file has been deleted by other application.\n'
                'Please make sure you save the file before exit.'))
        elif not tab.editBox.document().isModified():
            # File was not modified in ReText, reload silently
            tab.readTextFromFile()
        else:
            tab.forceDisableAutoSave = True
            self.tabWidget.setCurrentWidget(tab)
            text = self.tr(
                'This document has been modified by other application.\n'
                'Do you want to reload the file (this will discard all '
                'your changes)?\n')
            if globalSettings.autoSave:
                text += self.tr(
                    'Automatic saving has been temporarily disabled for this '
                    'tab to prevent data loss. It will be re-enabled when you '
                    'reload the file or save it manually.')
            messageBox = QMessageBox(QMessageBox.Icon.Warning, '', text)
            reloadButton = messageBox.addButton(self.tr('Reload'), QMessageBox.ButtonRole.YesRole)
            messageBox.addButton(QMessageBox.StandardButton.Cancel)
            messageBox.exec()
            if messageBox.clickedButton() is reloadButton:
                tab.readTextFromFile()
        if fileName not in self.fileSystemWatcher.files():
            # https://github.com/retext-project/retext/issues/137
            self.fileSystemWatcher.addPath(fileName)

    def maybeSave(self, ind):
        tab = self.tabWidget.widget(ind)
        if tab.autoSaveActive():
            tab.saveTextToFile()
            return True
        if not tab.editBox.document().isModified():
            return True
        self.tabWidget.setCurrentIndex(ind)
        ret = QMessageBox.warning(
            self,
            '',
            self.tr("The document has been modified.\nDo you want to save your changes?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if ret == QMessageBox.StandardButton.Save:
            return self.saveFile(False)
        elif ret == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def closeEvent(self, closeevent):
        for ind in range(self.tabWidget.count()):
            if not self.maybeSave(ind):
                return closeevent.ignore()
        if globalSettings.saveWindowGeometry:
            globalCache.windowGeometry = self.saveGeometry()
            if self.treeView.isVisible():
                globalCache.splitterState = self.splitter.saveState()
            else:
                globalCache.splitterState = QByteArray()
        else:
            globalCache.windowGeometry = QByteArray()
            globalCache.splitterState = QByteArray()
        if globalSettings.openLastFilesOnStartup:
            files = [tab.fileName for tab in self.iterateTabs()]
            globalCache.lastFileList = files
            globalCache.lastTabIndex = self.tabWidget.currentIndex()
        closeevent.accept()

    def viewHtml(self):
        htmlDlg = HtmlDialog(self)
        try:
            _, htmltext, _ = self.currentTab.getDocumentForExport(includeStyleSheet=False)
        except Exception:
            return self.printError()
        winTitle = self.currentTab.getBaseName()
        htmlDlg.setWindowTitle(winTitle+" ("+self.tr("HTML code")+")")
        htmlDlg.textEdit.setPlainText(htmltext.rstrip())
        htmlDlg.hl.rehighlight()
        htmlDlg.show()
        htmlDlg.raise_()
        htmlDlg.activateWindow()

    def insertImages(self):
        supportedExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
        fileFilter = ' (' + ' '.join('*' + ext for ext in supportedExtensions) + ');;'
        fileNames, _selectedFilter = QFileDialog.getOpenFileNames(self,
            self.tr("Select one or several images to open"), QDir.currentPath(),
            self.tr("Supported files") + fileFilter + self.tr("All files (*)"))

        cursor = self.currentTab.editBox.textCursor()

        imagesMarkup = '\n'.join(
            self.currentTab.editBox.getImageMarkup(fileName)
            for fileName in fileNames)
        cursor.insertText(imagesMarkup)

        self.formattingBox.setCurrentIndex(0)
        self.currentTab.editBox.setFocus(Qt.FocusReason.OtherFocusReason)

    def openHelp(self):
        QDesktopServices.openUrl(QUrl('https://github.com/retext-project/retext/wiki'))

    def openReleases(self):
        QDesktopServices.openUrl(QUrl('https://github.com/retext-project/retext/releases'))

    def aboutDialog(self):
        QMessageBox.about(self, self.aboutWindowTitle,
        '<p><b>' + (self.tr('ReText %s (using PyMarkups %s)') % (app_version, markups.__version__))
        +'</b></p>' + self.tr('Simple but powerful editor'
        ' for Markdown and reStructuredText')
        +'</p><p>'+self.tr('Author: Dmitry Shachnev, 2011').replace('2011', '2011–2025')
        +'<br><a href="https://github.com/retext-project/retext">GitHub</a> | '
        +'<a href="https://daringfireball.net/projects/markdown/syntax">'
        +self.tr('Markdown syntax')
        +'</a> | <a href="https://docutils.sourceforge.io/docs/user/rst/quickref.html">'
        +self.tr('reStructuredText syntax')+'</a></p>')

    def setDefaultMarkup(self, markupClass):
        globalSettings.defaultMarkup = markupClass.name
        for tab in self.iterateTabs():
            if not tab.fileName:
                tab.updateActiveMarkupClass()
