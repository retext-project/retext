# vim: ts=8:sts=8:sw=8:noexpandtab
#
# This file is part of ReText
# Copyright: 2015 Dmitry Shachnev
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

from markups import get_markup_for_file_name
from markups.common import MODULE_HOME_PAGE

from ReText import app_version, globalSettings, converterprocess
from ReText.editor import ReTextEdit
from ReText.highlighter import ReTextHighlighter

try:
	from ReText.fakevimeditor import ReTextFakeVimHandler
except ImportError:
	ReTextFakeVimHandler = None

try:
	import enchant
except ImportError:
	enchant = None

from PyQt5.QtCore import pyqtSignal, Qt, QDir, QFile, QFileInfo, QPoint, QTextStream, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QTextCursor, QTextDocument
from PyQt5.QtWidgets import QTextBrowser, QTextEdit, QSplitter

try:
	from ReText.webkitpreview import ReTextWebPreview
except ImportError:
	ReTextWebPreview = None

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

	def __init__(self, parent, fileName, defaultMarkup, previewState=PreviewDisabled):
		super(QSplitter, self).__init__(Qt.Horizontal, parent=parent)
		self.p = parent
		self._fileName = fileName
		self.editBox = ReTextEdit(self)
		self.previewBox = self.createPreviewBox(self.editBox)
		self.defaultMarkupClass = defaultMarkup
		self.activeMarkupClass = None
		self.markup = None
		self.converted = None
		self.previewState = previewState
		self.previewOutdated = False
		self.conversionPending = False

		self.converterProcess = converterprocess.ConverterProcess()
		self.converterProcess.conversionDone.connect(self.updatePreviewBox)

		textDocument = self.editBox.document()
		self.highlighter = ReTextHighlighter(textDocument)
		if enchant is not None and parent.actionEnableSC.isChecked():
			self.highlighter.dictionary = enchant.Dict(parent.sl or None)
			# Rehighlighting is tied to the change in markup class that
			# happens at the end of this function

		self.editBox.textChanged.connect(self.triggerPreviewUpdate)
		self.editBox.undoAvailable.connect(parent.actionUndo.setEnabled)
		self.editBox.redoAvailable.connect(parent.actionRedo.setEnabled)
		self.editBox.copyAvailable.connect(parent.actionCopy.setEnabled)

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

		# Use closures to avoid a hard reference from ReTextWebPreview
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

		if globalSettings.useWebKit:
			preview = ReTextWebPreview(editBox,
			                           editorPositionToSourceLine,
			                           sourceLineToEditorPosition)
		else:
			preview = ReTextPreview(self)

		return preview

	def setDefaultMarkupClass(self, markupClass):
		'''
		Set the default markup class to use in case a markup that
		matches the filename cannot be found. This function calls
		updateActiveMarkupClass so it can decide if the active 
		markup class also has to change.
		'''
		self.defaultMarkupClass = markupClass
		self.updateActiveMarkupClass()

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

		self.activeMarkupClass = self.defaultMarkupClass

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
			return '<p style="color: red">%s</p>' % errMsg
		headers = ''
		if includeStyleSheet:
			headers += '<style type="text/css">\n' + self.p.ss + '</style>\n'
		baseName = self.getBaseName()
		cssFileName = baseName + '.css'
		if QFile.exists(cssFileName):
			headers += ('<link rel="stylesheet" type="text/css" href="%s">\n'
			% cssFileName)
		headers += ('<meta name="generator" content="ReText %s">\n' % app_version)
		return converted.get_whole_html(
			custom_headers=headers, include_stylesheet=includeStyleSheet,
			fallback_title=baseName, webenv=webenv)

	def getDocumentForExport(self, includeStyleSheet, webenv):
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
		except converterprocess.ConversionError:
			self.converted = None
		if isinstance(self.previewBox, QTextEdit):
			scrollbar = self.previewBox.verticalScrollBar()
			scrollbarValue = scrollbar.value()
			distToBottom = scrollbar.maximum() - scrollbarValue
		try:
			html = self.getHtmlFromConverted(self.converted)
		except Exception:
			return self.p.printError()
		if isinstance(self.previewBox, QTextEdit):
			self.previewBox.setHtml(html)
			self.previewBox.document().setDefaultFont(globalSettings.font)
			# If scrollbar was at bottom (and that was not the same as top),
			# set it to bottom again
			if scrollbarValue:
				newValue = scrollbar.maximum() - distToBottom
				scrollbar.setValue(newValue)
		else:
			self.previewBox.updateFontSettings()

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

		if not self.conversionPending:
			self.conversionPending = True
			QTimer.singleShot(500, self.startPendingConversion)

	def startPendingConversion(self):
			self.previewOutdated = False

			requested_extensions = ['ReText.mdx_posmap'] if globalSettings.syncScroll else []
			self.converterProcess.start_conversion(self.getActiveMarkupClass().name,
			                                       self.fileName,
							       requested_extensions,
							       self.editBox.toPlainText())

	def updateBoxesVisibility(self):
		self.editBox.setVisible(self.previewState < PreviewNormal)
		self.previewBox.setVisible(self.previewState > PreviewDisabled)

	def readTextFromFile(self, fileName=None, encoding=None):
		previousFileName = self._fileName
		if fileName:
			self._fileName = fileName
		openfile = QFile(self._fileName)
		openfile.open(QFile.ReadOnly)
		stream = QTextStream(openfile)
		encoding = encoding or globalSettings.defaultCodec
		if encoding:
			stream.setCodec(encoding)
		text = stream.readAll()
		openfile.close()

		modified = bool(encoding) and (self.editBox.toPlainText() != text)
		self.editBox.setPlainText(text)
		self.editBox.document().setModified(modified)

		if previousFileName != self._fileName:
			self.updateActiveMarkupClass()
			self.fileNameChanged.emit()

	def writeTextToFile(self, fileName=None):
		# Just writes the text to file, without any changes to tab object
		# Used directly for i.e. export extensions
		savefile = QFile(fileName or self._fileName)
		result = savefile.open(QFile.WriteOnly)
		if result:
			savestream = QTextStream(savefile)
			if globalSettings.defaultCodec:
				savestream.setCodec(globalSettings.defaultCodec)
			savestream << self.editBox.toPlainText()
			savefile.close()
		return result

	def saveTextToFile(self, fileName=None):
		# Sets fileName as tab fileName and writes the text to that file
		if self._fileName:
			self.p.fileSystemWatcher.removePath(self._fileName)
		result = self.writeTextToFile(fileName)
		if result:
			self.editBox.document().setModified(False)
			self.p.fileSystemWatcher.addPath(fileName or self._fileName)
		if result and self._fileName != fileName:
			self._fileName = fileName
			self.updateActiveMarkupClass()
			self.fileNameChanged.emit()

		return result

	def installFakeVimHandler(self):
		if ReTextFakeVimHandler:
			fakeVimEditor = ReTextFakeVimHandler(self.editBox, self)
			fakeVimEditor.setSaveAction(self.actionSave)
			fakeVimEditor.setQuitAction(self.actionQuit)
			# TODO: action is bool, really call remove?
			self.p.actionFakeVimMode.triggered.connect(fakeVimEditor.remove)

	def find(self, text, flags):
		cursor = self.editBox.textCursor()
		newCursor = self.editBox.document().find(text, cursor, flags)
		if not newCursor.isNull():
			self.editBox.setTextCursor(newCursor)
			return True
		cursor.movePosition(QTextCursor.End if (flags & QTextDocument.FindBackward) else QTextCursor.Start)
		newCursor = self.editBox.document().find(text, cursor, flags)
		if not newCursor.isNull():
			self.editBox.setTextCursor(newCursor)
			return True
		return False


class ReTextPreview(QTextBrowser):
	"""
	When links like [test](test) are clicked, the file test.md is opened.
	It has to be located next to the current opened file.
	Relative pathes like [test](../test) or [test](folder/test) are also possible.
	"""

	def __init__(self, tab):
		QTextBrowser.__init__(self)
		self.tab = tab
		# if set to True, links to other files will unsuccessfully be opened as anchors
		self.setOpenLinks(False)
		self.anchorClicked.connect(self.openInternal)

	def disconnectExternalSignals(self):
		pass

	def openInternal(self, link):
		url = link.url()
		isLocalHtml = (link.scheme() in ('file', '') and url.endswith('.html'))
		if url.startswith('#'):
			self.scrollToAnchor(url[1:])
		elif link.isRelative() and get_markup_for_file_name(url, return_class=True):
			fileToOpen = QDir.current().filePath(url)
			if not QFileInfo(fileToOpen).completeSuffix() and self._fileName:
				fileToOpen += '.' + QFileInfo(self.tab.fileName).completeSuffix()
			self.tab.p.openFileWrapper(fileToOpen)
		elif globalSettings.handleWebLinks and isLocalHtml:
			self.setSource(link)
		else:
			QDesktopServices.openUrl(link)
