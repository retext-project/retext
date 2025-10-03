# vim: ts=4:sw=4:expandtab
#
# This file is part of ReText
# Copyright: 2015-2025 Dmitry Shachnev
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

import locale
import time
from os.path import exists, splitext

from markups import find_markup_class_by_name, get_markup_for_file_name
from markups.common import MODULE_HOME_PAGE
from PyQt6.QtCore import QDir, QFile, QFileInfo, QPoint, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextDocument
from PyQt6.QtWidgets import QMessageBox, QSplitter, QTextEdit

from ReText import app_version, converterprocess, globalSettings
from ReText.editor import ReTextEdit
from ReText.highlighter import ReTextHighlighter
from ReText.preview import ReTextPreview

try:
    from ReText.webenginepreview import ReTextWebEnginePreview
except ImportError:
    ReTextWebEnginePreview = None

PreviewDisabled, PreviewLive, PreviewNormal = range(3)

class ReTextTab(QSplitter):

    fileNameChanged = pyqtSignal()
    modificationStateChanged = pyqtSignal()
    activeMarkupChanged = pyqtSignal()

    # Make _fileName a read-only property to make sure that any
    # modification happens through the proper functions. These functions
    # will make sure that the fileNameChanged signal is emitted when
    # applicable.
    @property
    def fileName(self):
        return self._fileName

    def __init__(self, parent, fileName, previewState=PreviewDisabled):
        super().__init__(Qt.Orientation.Horizontal, parent=parent)
        self.p = parent
        self._fileName = fileName
        self.editBox = ReTextEdit(self)
        self.previewBox = self.createPreviewBox(self.editBox)
        self.activeMarkupClass = None
        self.markup = None
        self.converted = None
        self.previewState = previewState
        self.previewOutdated = False
        self.conversionPending = False
        self.cssFileExists = False
        self.forceDisableAutoSave = False

        self.converterProcess = converterprocess.ConverterProcess()
        self.converterProcess.conversionDone.connect(self.updatePreviewBox)

        textDocument = self.editBox.document()
        self.highlighter = ReTextHighlighter(textDocument)
        if parent.actionEnableSC.isChecked():
            dictionaries, _errors = parent.getSpellCheckDictionaries()
            self.highlighter.dictionaries = dictionaries
            # Rehighlighting is tied to the change in markup class that
            # happens at the end of this function

        self.editBox.textChanged.connect(self.triggerPreviewUpdate)
        self.editBox.undoAvailable.connect(parent.actionUndo.setEnabled)
        self.editBox.redoAvailable.connect(parent.actionRedo.setEnabled)
        self.editBox.copyAvailable.connect(parent.enableCopy)

        # Give both boxes a minimum size so the minimumSizeHint will be
        # ignored when splitter.setSizes is called below
        for widget in self.editBox, self.previewBox:
            widget.setMinimumWidth(125)
            self.addWidget(widget)
        self.setSizes((50, 50))
        self.setChildrenCollapsible(False)

        textDocument.modificationChanged.connect(self.handleModificationChanged)

        self.updateActiveMarkupClass()

    def handleModificationChanged(self):
        self.modificationStateChanged.emit()

    def createPreviewBox(self, editBox):

        # Use closures to avoid a hard reference from ReTextWebEnginePreview
        # to self, which would keep the tab and its resources alive
        # even after other references to it have disappeared.

        def editorPositionToSourceLine(editorPosition):
            viewportPosition = editorPosition - editBox.verticalScrollBar().value()
            sourceLine = editBox.cursorForPosition(QPoint(0,viewportPosition)).blockNumber()
            return sourceLine

        def sourceLineToEditorPosition(sourceLine):
            doc = editBox.document()
            block = doc.findBlockByNumber(sourceLine)
            rect = doc.documentLayout().blockBoundingRect(block)
            return rect.top()

        if ReTextWebEnginePreview and globalSettings.useWebEngine:
            preview = ReTextWebEnginePreview(self,
                                             editorPositionToSourceLine,
                                             sourceLineToEditorPosition)
        else:
            preview = ReTextPreview(self)

        return preview

    def getActiveMarkupClass(self):
        '''
        Return the currently active markup class for this tab.
        No objects should be created of this class, it should
        only be used to retrieve markup class specific information.
        '''
        return self.activeMarkupClass

    def updateActiveMarkupClass(self):
        '''
        Update the active markup class based on the default class and
        the current filename. If the active markup class changes, the
        highlighter is rerun on the input text, the markup object of
        this tab is replaced with one of the new class and the
        activeMarkupChanged signal is emitted.
        '''
        previousMarkupClass = self.activeMarkupClass

        self.activeMarkupClass = find_markup_class_by_name(globalSettings.defaultMarkup)

        if self._fileName:
            markupClass = get_markup_for_file_name(
                self._fileName, return_class=True)
            if markupClass:
                self.activeMarkupClass = markupClass

        if self.activeMarkupClass != previousMarkupClass:
            self.highlighter.docType = self.activeMarkupClass.name if self.activeMarkupClass else None
            self.highlighter.rehighlight()

            self.activeMarkupChanged.emit()
            self.triggerPreviewUpdate()

    def getDocumentTitleFromConverted(self, converted):
        if converted:
            try:
                return converted.get_document_title()
            except Exception:
                self.p.printError()

        return self.getBaseName()

    def getBaseName(self):
        if self._fileName:
            fileinfo = QFileInfo(self._fileName)
            basename = fileinfo.completeBaseName()
            return (basename if basename else fileinfo.fileName())
        return self.tr("New document")

    def getHtmlFromConverted(self, converted, includeStyleSheet=True, webenv=False):
        if converted is None:
            markupClass = self.getActiveMarkupClass()
            errMsg = self.tr('Could not parse file contents, check if '
                             'you have the <a href="%s">necessary module</a> '
                             'installed!')
            try:
                errMsg %= markupClass.attributes[MODULE_HOME_PAGE]
            except (AttributeError, KeyError):
                # Remove the link if markupClass doesn't have the needed attribute
                errMsg = errMsg.replace('<a href="%s">', '').replace('</a>', '')
            return f'<p style="color: red">{errMsg}</p>'
        headers = ''
        if includeStyleSheet and self.p.ss is not None:
            headers += '<style type="text/css">\n' + self.p.ss + '</style>\n'
        elif includeStyleSheet:
            style = 'td, th { border: 1px solid #c3c3c3; padding: 0 3px 0 3px; }\n'
            style += 'table { border-collapse: collapse; }\n'
            style += 'img { max-width: 100%; }\n'
            headers += '<style type="text/css">\n' + style + '</style>\n'
        baseName = self.getBaseName()
        if self.cssFileExists:
            headers += f'<link rel="stylesheet" type="text/css" href="{baseName}.css">\n'
        headers += f'<meta name="generator" content="ReText {app_version}">\n'
        return converted.get_whole_html(
            custom_headers=headers, include_stylesheet=includeStyleSheet,
            fallback_title=baseName, webenv=webenv)

    def getDocumentForExport(self, includeStyleSheet=True, webenv=False):
        markupClass = self.getActiveMarkupClass()
        if markupClass and markupClass.available():
            exportMarkup = markupClass(filename=self._fileName)

            text = self.editBox.toPlainText()
            converted = exportMarkup.convert(text)
        else:
            converted = None

        return (self.getDocumentTitleFromConverted(converted),
                self.getHtmlFromConverted(converted, includeStyleSheet=includeStyleSheet, webenv=webenv),
            self.previewBox)

    def updatePreviewBox(self):
        self.conversionPending = False

        try:
            self.converted = self.converterProcess.get_result()
        except converterprocess.MarkupNotAvailableError:
            self.converted = None
        except converterprocess.ConversionError:
            return self.p.printError()

        if isinstance(self.previewBox, QTextEdit):
            scrollbar = self.previewBox.verticalScrollBar()
            scrollbarValue = scrollbar.value()
            # If scrollbar was not on top, save its distance to bottom so that
            # it will be restored in previewBox.updateScrollPosition() later.
            if scrollbarValue:
                self.previewBox.distToBottom = scrollbar.maximum() - scrollbarValue
            else:
                self.previewBox.distToBottom = None
        try:
            html = self.getHtmlFromConverted(self.converted)
        except Exception:
            return self.p.printError()
        self.previewBox.setFont(globalSettings.getPreviewFont())
        if isinstance(self.previewBox, QTextEdit):
            self.previewBox.lastRenderTime = time.time()
            self.previewBox.setHtml(html)
            self.previewBox.updateScrollPosition(scrollbar.minimum(),
                                                 scrollbar.maximum())
        else:
            # Always provide a baseUrl otherwise QWebView will
            # refuse to show images or other external objects
            if self._fileName:
                baseUrl = QUrl.fromLocalFile(self._fileName)
            else:
                baseUrl = QUrl.fromLocalFile(QDir.currentPath())
            self.previewBox.setHtml(html, baseUrl)

        if self.previewOutdated:
            self.triggerPreviewUpdate()

    def triggerPreviewUpdate(self):
        self.previewOutdated = True
        if self.previewState == PreviewDisabled:
            return

        if not self.conversionPending:
            self.conversionPending = True
            QTimer.singleShot(500, self.startPendingConversion)

    def startPendingConversion(self):
        self.previewOutdated = False

        requested_extensions = ['ReText.mdx_posmap'] if globalSettings.syncScroll else []
        self.converterProcess.start_conversion(self.getActiveMarkupClass().name,
                                               self.fileName,
                                               requested_extensions,
                                               self.editBox.toPlainText(),
                                               QDir.currentPath())

    def updateBoxesVisibility(self):
        self.editBox.setVisible(self.previewState < PreviewNormal)
        self.previewBox.setVisible(self.previewState > PreviewDisabled)

    def rebuildPreviewBox(self):
        self.previewBox.disconnectExternalSignals()
        self.previewBox.setParent(None)
        self.previewBox.deleteLater()
        self.previewBox = self.createPreviewBox(self.editBox)
        self.previewBox.setMinimumWidth(125)
        self.addWidget(self.previewBox)
        self.setSizes((50, 50))
        self.triggerPreviewUpdate()
        self.updateBoxesVisibility()

    def detectEncoding(self, raw: bytes):
        '''
        Detect content encoding of the given data.

        It will return None if it can't determine the encoding.
        '''
        try:
            import chardet
        except ImportError:
            return

        result = chardet.detect(raw)
        if result['confidence'] > 0.9:
            if result['encoding'].lower() == 'ascii':
                # UTF-8 files can be falsely detected as ASCII files if they
                # don't contain non-ASCII characters in first 2048 bytes.
                # We map ASCII to UTF-8 to avoid such situations.
                return 'utf-8'
            return result['encoding']

    def readTextFromFile(self, fileName=None, encoding=None):
        previousFileName = self._fileName
        fileName = fileName or self._fileName

        try:
            with open(fileName, 'rb') as openfile:
                data = openfile.read()
        except OSError as ex:
            QMessageBox.warning(self, '', str(ex))
            return

        # Only try to detect encoding if it is not specified
        if encoding is None and globalSettings.detectEncoding:
            encoding = self.detectEncoding(data[:2048])
        encoding = encoding or globalSettings.defaultCodec or None

        try:
            text = data.decode(encoding or locale.getpreferredencoding(False))
        except (UnicodeDecodeError, LookupError) as ex:
            QMessageBox.warning(self, '', str(ex))
            return

        if encoding:
            # If encoding is specified or detected, we should save the file with
            # the same encoding
            self.editBox.document().setProperty("encoding", encoding)

        self._fileName = fileName
        if previousFileName != self._fileName:
            self.updateActiveMarkupClass()

        self.forceDisableAutoSave = False
        self.editBox.setPlainText(text)
        self.editBox.document().setModified(False)
        self.handleModificationChanged()

        cssFileName = self.getBaseName() + '.css'
        self.cssFileExists = QFile.exists(cssFileName)

        if previousFileName != self._fileName:
            self.fileNameChanged.emit()

    def writeTextToFile(self, fileName=None):
        # Just writes the text to file, without any changes to tab object
        # Used directly for e.g. export extensions

        # Get text from the cursor to avoid tweaking special characters,
        # see https://bugreports.qt.io/browse/QTBUG-57552 and
        # https://github.com/retext-project/retext/issues/216
        cursor = self.editBox.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        text = cursor.selectedText().replace('\u2029', '\n')

        fileName = fileName or self._fileName
        encoding = self.editBox.document().property("encoding")
        encoding = encoding or globalSettings.defaultCodec or None
        try:
            data = text.encode(encoding or locale.getpreferredencoding(False))
        except (UnicodeEncodeError, LookupError) as ex:
            QMessageBox.warning(self, '', str(ex))
            return False
        try:
            with open(fileName, 'wb') as savefile:
                savefile.write(data)
        except OSError as ex:
            QMessageBox.warning(self, '', str(ex))
            return False
        return True

    def saveTextToFile(self, fileName=None):
        # Sets fileName as tab fileName and writes the text to that file
        if self._fileName:
            self.p.fileSystemWatcher.removePath(self._fileName)
        result = self.writeTextToFile(fileName)
        if result:
            self.forceDisableAutoSave = False
            self.editBox.document().setModified(False)
            self.p.fileSystemWatcher.addPath(fileName or self._fileName)
            if fileName and self._fileName != fileName:
                self._fileName = fileName
                self.updateActiveMarkupClass()
                self.fileNameChanged.emit()

        return result

    def goToLine(self,line):
        block = self.editBox.document().findBlockByLineNumber(line)
        if block.isValid():
            newCursor = QTextCursor(block)
            self.editBox.setTextCursor(newCursor)

    def find(self, text, flags, replaceText=None, wrap=False):
        if self.previewState == PreviewNormal and replaceText is None:
            return self.previewBox.findText(text, flags)
        cursor = self.editBox.textCursor()
        if wrap and flags & QTextDocument.FindFlag.FindBackward:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        elif wrap:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
        if replaceText is not None and cursor.selectedText() == text:
            newCursor = cursor
        else:
            newCursor = self.editBox.document().find(text, cursor, flags)
        if not newCursor.isNull():
            if replaceText is not None:
                newCursor.insertText(replaceText)
                newCursor.movePosition(
                    QTextCursor.MoveOperation.Left,
                    QTextCursor.MoveMode.MoveAnchor,
                    len(replaceText),
                )
                newCursor.movePosition(
                    QTextCursor.MoveOperation.Right,
                    QTextCursor.MoveMode.KeepAnchor,
                    len(replaceText),
                )
            self.editBox.setTextCursor(newCursor)
            if self.editBox.cursorRect().bottom() >= self.editBox.height() - 3:
                scrollValue = self.editBox.verticalScrollBar().value()
                areaHeight = self.editBox.fontMetrics().height()
                self.editBox.verticalScrollBar().setValue(scrollValue + areaHeight)
            return True
        if not wrap:
            return self.find(text, flags, replaceText, True)
        return False

    def replaceAll(self, text, replaceText):
        cursor = self.editBox.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        flags = QTextDocument.FindFlag(0)
        cursor = lastCursor = self.editBox.document().find(text, cursor, flags)
        while not cursor.isNull():
            cursor.insertText(replaceText)
            lastCursor = cursor
            cursor = self.editBox.document().find(text, cursor, flags)
        if not lastCursor.isNull():
            lastCursor.movePosition(
                QTextCursor.MoveOperation.Left,
                QTextCursor.MoveMode.MoveAnchor,
                len(replaceText),
            )
            lastCursor.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.KeepAnchor,
                len(replaceText),
            )
            self.editBox.setTextCursor(lastCursor)
        self.editBox.textCursor().endEditBlock()
        return not lastCursor.isNull()

    def openSourceFile(self, linkPath):
        """Finds and opens the source file for link target fileToOpen.

        When links like [test](test) are clicked, the file test.md is opened.
        It has to be located next to the current opened file.
        Relative paths like [test](../test) or [test](folder/test) are also possible.
        """

        fileToOpen = self.resolveSourceFile(linkPath)
        if exists(fileToOpen) and get_markup_for_file_name(fileToOpen, return_class=True):
            self.p.openFileWrapper(fileToOpen)
            return fileToOpen
        if get_markup_for_file_name(fileToOpen, return_class=True):
            if not QFile.exists(fileToOpen) and QFileInfo(fileToOpen).dir().exists():
                if self.promptFileCreation(fileToOpen):
                    self.p.openFileWrapper(fileToOpen)
                    return fileToOpen

    def promptFileCreation(self, fileToCreate):
        """
        Prompt user if a file should be created for the clicked link,
        and try to create it. Return True on success.
        """
        buttonReply = QMessageBox.question(
            self,
            self.tr('Create missing file?'),
            self.tr("The file '%s' does not exist.\n\nDo you want to create it?") % fileToCreate,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if buttonReply == QMessageBox.StandardButton.Yes:
            return self.createFile(fileToCreate)
        elif buttonReply == QMessageBox.StandardButton.No:
            return False

    def resolveSourceFile(self, linkPath):
        """
        Finds the actual path of the file to open in a new tab.
        When the link has no extension, eg: [Test](test), the extension of the current file is assumed
        (eg test.md for a markdown file).
        When the link is an html file eg: [Test](test.html), the extension of the current file is assumed
        (eg test.md for a markdown file).
        Relative paths like [test](../test) or [test](folder/test) are also possible.
        """
        basename, ext = splitext(linkPath)
        if self.fileName:
            currentExt = splitext(self.fileName)[1]
            if ext in ('.html', '') and (exists(basename+currentExt) or not exists(linkPath)):
                ext = currentExt

        return basename+ext

    def createFile(self, fileToCreate):
        """Try to create file, return True if successful"""
        try:
            # Create file:
            open(fileToCreate, 'x').close()
            return True
        except OSError as err:
            QMessageBox.warning(self, self.tr("File could not be created"),
                                self.tr("Could not create file '%s': %s") % (fileToCreate, err))
            return False

    def autoSaveActive(self) -> bool:
        return (globalSettings.autoSave
                and not self.forceDisableAutoSave
                and self.fileName is not None
                and QFileInfo(self.fileName).isWritable())
