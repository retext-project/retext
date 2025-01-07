# This file is part of ReText
# Copyright: 2013-2024 Dmitry Shachnev
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

import sys
from os.path import join

from markups.common import CONFIGURATION_DIR
from PyQt6.QtCore import QFile, QFileInfo, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ReText import getBundledIcon, getSettingsFilePath, globalSettings
from ReText.icontheme import get_icon_theme

MKD_EXTS_FILE = join(CONFIGURATION_DIR, 'markdown-extensions.txt')

class FileDialogButton(QPushButton):
    def __init__(self, parent, fileName, label):
        icon = parent.parent.actIcon('document-open')
        super().__init__(icon, self.tr('Select'), parent)
        self.fileName = fileName
        self.label = label
        self.defaultText = self.tr('(none)')
        self.updateLabelText()
        self.clicked.connect(self.processClick)

    def processClick(self):
        raise NotImplementedError

    def updateLabelText(self):
        template = '<small>' + self.tr('Currently selected: %s') + '</small>'
        if self.fileName:
            self.label.setText(template % f'<a href="{self.fileName}">{self.fileName}</a>')
        else:
            self.label.setText(template % self.defaultText)

class FileSelectButton(FileDialogButton):
    def processClick(self):
        startDir = (QFileInfo(self.fileName).absolutePath()
                    if self.fileName else '')
        self.fileName = QFileDialog.getOpenFileName(
            self,
            self.tr('Select file to open'),
            startDir,
            self.tr('CSS files (*.css)') + ';;' + self.tr('All files (*)'),
        )[0]
        self.updateLabelText()

class DirectorySelectButton(FileDialogButton):
    def processClick(self):
        startDir = (QFileInfo(self.fileName).absolutePath()
                    if self.fileName else '')
        self.fileName = QFileDialog.getExistingDirectory(
            self, self.tr('Select directory to open'), startDir)
        self.updateLabelText()

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


def setIconThemeFromSettings():
    QIcon.setThemeName(globalSettings.iconTheme)
    if QIcon.themeName() in ('hicolor', ''):
        if not QFile.exists(getBundledIcon('document-new')):
            QIcon.setThemeName(get_icon_theme())


class ConfigDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.initConfigOptions()
        self.layout = QVBoxLayout(self)
        path = getSettingsFilePath()
        pathLabel = QLabel(self.tr('Using configuration file at:') +
            f' <a href="{path}">{path}</a>', self)
        pathLabel.linkActivated.connect(self.openLink)
        self.layout.addWidget(pathLabel)
        self.tabWidget = QTabWidget(self)
        self.layout.addWidget(self.tabWidget)
        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.acceptSettings)
        buttonBox.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.saveSettings)
        buttonBox.rejected.connect(self.close)
        self.initWidgets()
        self.configurators['rightMargin'].valueChanged.connect(self.handleRightMarginSet)
        rightMarginWrap = self.configurators['rightMarginWrap']
        if hasattr(rightMarginWrap, 'checkStateChanged'):  # Qt >= 6.7
            rightMarginWrap.checkStateChanged.connect(self.handleRightMarginWrapSet)
        else:
            rightMarginWrap.stateChanged.connect(
                lambda state: self.handleRightMarginWrapSet(Qt.CheckState(state))
            )
        self.layout.addWidget(buttonBox)

    def initConfigOptions(self):
        self.tabs = (
            (self.tr('Behavior'), (
                (self.tr('Automatically save documents'), 'autoSave'),
                (self.tr('Automatically open last documents on startup'), 'openLastFilesOnStartup'),
                (self.tr('Number of recent documents'), 'recentDocumentsCount'),
                (self.tr('Restore window geometry'), 'saveWindowGeometry'),
                (self.tr('Default preview state'), 'defaultPreviewState'),
                (self.tr('Open external links in ReText window'), 'handleWebLinks'),
                (self.tr('Markdown syntax extensions (comma-separated)'), 'markdownExtensions'),
                (self.tr('Enable synchronized scrolling for Markdown'), 'syncScroll'),
            #    (self.tr('Default Markdown file extension'), 'markdownDefaultFileExtension'),
            #    (self.tr('Default reStructuredText file extension'), 'restDefaultFileExtension'),
            )),
            (self.tr('Editor'), (
                (self.tr('Highlight current line'), 'highlightCurrentLine'),
                (self.tr('Show line numbers'), 'lineNumbersEnabled'),
                (self.tr('Line numbers are relative to current line'), 'relativeLineNumbers'),
                (self.tr('Tab key inserts spaces'), 'tabInsertsSpaces'),
                (self.tr('Tabulation width'), 'tabWidth'),
                (self.tr('Draw vertical line at column'), 'rightMargin'),
                (self.tr('Enable soft wrap'), 'rightMarginWrap'),
                (self.tr('Show document stats'), 'documentStatsEnabled'),
                (self.tr('Ordered list mode'), 'orderedListMode'),
            )),
            (self.tr('Interface'), (
                (self.tr('Hide toolbar'), 'hideToolBar'),
                (self.tr('Icon theme name'), 'iconTheme'),
                (self.tr('Stylesheet file'), 'styleSheet', True),
                (self.tr('Hide tabs bar when there is only one tab'), 'tabBarAutoHide'),
                (self.tr('Show full path in window title'), 'windowTitleFullPath'),
                (self.tr('Show directory tree'), 'showDirectoryTree'),
                (self.tr('Working directory'), 'directoryPath', True),
            ))
        )

    def initWidgets(self):
        self.configurators = {}
        for tabTitle, options in self.tabs:
            page = self.getPageWidget(options)
            self.tabWidget.addTab(page, tabTitle)

    def getPageWidget(self, options):
        page = QWidget(self)
        layout = QGridLayout(page)
        index = 0
        for option in options:
            displayname, name = option[:2]
            fileselector = option[2] if len(option) > 2 else False
            label = ClickableLabel(displayname + ':', self)
            if name == 'markdownExtensions':
                url = QUrl('https://github.com/retext-project/retext/wiki/Markdown-extensions')
                helpButton = QPushButton(self.tr('Help'), self)
                helpButton.clicked.connect(lambda: QDesktopServices.openUrl(url))
                layout.addWidget(label, index, 0)
                layout.addWidget(helpButton, index, 1)
                index += 1
                try:
                    extsFile = open(MKD_EXTS_FILE)
                    value = extsFile.read().rstrip().replace(extsFile.newlines, ', ')
                    extsFile.close()
                except Exception:
                    value = ''
                self.configurators[name] = QLineEdit(self)
                self.configurators[name].setText(value)
                layout.addWidget(self.configurators[name], index, 0, 1, 2)
                index += 1
                continue
            fileLabel = None
            if fileselector:
                fileLabel = QLabel(self)
                fileLabel.setIndent(15)
                fileLabel.linkActivated.connect(self.openLink)
            value = getattr(globalSettings, name)
            if name == 'defaultPreviewState':
                self.configurators[name] = QComboBox(self)
                self.configurators[name].addItem(self.tr('Editor'), 'editor')
                self.configurators[name].addItem(self.tr('Live preview'), 'live-preview')
                self.configurators[name].addItem(self.tr('Normal preview'), 'normal-preview')
                comboBoxIndex = self.configurators[name].findData(value)
                self.configurators[name].setCurrentIndex(comboBoxIndex)
            elif name == 'highlightCurrentLine':
                self.configurators[name] = QComboBox(self)
                self.configurators[name].addItem(self.tr('Disabled'), 'disabled')
                self.configurators[name].addItem(self.tr('Cursor Line'), 'cursor-line')
                self.configurators[name].addItem(self.tr('Wrapped Line'), 'wrapped-line')
                comboBoxIndex = self.configurators[name].findData(value)
                self.configurators[name].setCurrentIndex(comboBoxIndex)
            elif name == 'orderedListMode':
                self.configurators[name] = QComboBox(self)
                self.configurators[name].addItem(self.tr('Increment'), 'increment')
                self.configurators[name].addItem(self.tr('Repeat'), 'repeat')
                comboBoxIndex = self.configurators[name].findData(value)
                self.configurators[name].setCurrentIndex(comboBoxIndex)
            elif name == 'directoryPath':
                self.configurators[name] = DirectorySelectButton(self, value, fileLabel)
            elif isinstance(value, bool):
                self.configurators[name] = QCheckBox(self)
                self.configurators[name].setChecked(value)
                label.clicked.connect(self.configurators[name].nextCheckState)
            elif isinstance(value, int):
                self.configurators[name] = QSpinBox(self)
                if name == 'tabWidth':
                    self.configurators[name].setRange(1, 10)
                elif name == 'recentDocumentsCount':
                    self.configurators[name].setRange(5, 20)
                else:
                    self.configurators[name].setMaximum(200)
                self.configurators[name].setValue(value)
            elif isinstance(value, str) and fileselector:
                self.configurators[name] = FileSelectButton(self, value, fileLabel)
            elif isinstance(value, str):
                self.configurators[name] = QLineEdit(self)
                self.configurators[name].setText(value)
            layout.addWidget(label, index, 0)
            layout.addWidget(self.configurators[name], index, 1, Qt.AlignmentFlag.AlignRight)
            if fileLabel is not None:
                index += 1
                layout.addWidget(fileLabel, index, 0, 1, 2)
            index += 1
        return page

    def handleRightMarginSet(self, value):
        if value < 10:
            self.configurators['rightMarginWrap'].setChecked(False)

    def handleRightMarginWrapSet(self, state):
        if state == Qt.CheckState.Checked and self.configurators['rightMargin'].value() < 10:
            self.configurators['rightMargin'].setValue(80)

    def saveSettings(self):
        for name, configurator in self.configurators.items():
            if name == 'markdownExtensions':
                continue
            if isinstance(configurator, QCheckBox):
                value = configurator.isChecked()
            elif isinstance(configurator, QSpinBox):
                value = configurator.value()
            elif isinstance(configurator, QLineEdit):
                value = configurator.text()
            elif isinstance(configurator, QComboBox):
                value = configurator.currentData()
            elif isinstance(configurator, FileDialogButton):
                value = configurator.fileName
            setattr(globalSettings, name, value)
        self.applySettings()

    def applySettings(self):
        setIconThemeFromSettings()
        try:
            extsFile = open(MKD_EXTS_FILE, 'w')
            for ext in self.configurators['markdownExtensions'].text().split(','):
                if ext.strip():
                    extsFile.write(ext.strip() + '\n')
            extsFile.close()
        except Exception as e:
            print(e, file=sys.stderr)
        for tab in self.parent.iterateTabs():
            tab.editBox.updateFont()
            tab.editBox.setWrapModeAndWidth()
            tab.editBox.viewport().update()
        self.parent.updateStyleSheet()
        self.parent.tabWidget.setTabBarAutoHide(globalSettings.tabBarAutoHide)
        self.parent.toolBar.setVisible(not globalSettings.hideToolBar)
        self.parent.editBar.setVisible(not globalSettings.hideToolBar)
        path = globalSettings.directoryPath
        self.parent.fileSystemModel.setRootPath(path)
        self.parent.treeView.setRootIndex(self.parent.fileSystemModel.index(path))
        self.parent.actionShowDirectoryTree.setChecked(globalSettings.showDirectoryTree)
        self.parent.treeView.setVisible(globalSettings.showDirectoryTree)
        if globalSettings.autoSave:
            self.parent.autoSaveTimer.start(60000)
        else:
            self.parent.autoSaveTimer.stop()

    def acceptSettings(self):
        self.saveSettings()
        self.close()

    def openLink(self, link):
        QDesktopServices.openUrl(QUrl.fromLocalFile(link))
