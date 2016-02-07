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

from ReText import app_version, enchant, enchant_available, globalSettings
from ReText.editor import ReTextEdit
from ReText.highlighter import ReTextHighlighter

try:
	from ReText.fakevimeditor import ReTextFakeVimHandler
except ImportError:
	ReTextFakeVimHandler = None

from PyQt5.QtCore import Qt, QDir, QFile, QFileInfo, QObject, QPoint, QTextStream, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QTextBrowser, QTextEdit, QSplitter
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtWebKitWidgets import QWebPage, QWebView

PreviewDisabled, PreviewLive, PreviewNormal = range(3)

class ReTextTab(QObject):
	def __init__(self, parent, fileName, previewState=PreviewDisabled):
		QObject.__init__(self, parent)
		self.p = parent
		self.fileName = fileName
		self.editBox = ReTextEdit(self)
		self.previewBox = self.createPreviewBox()
		self.markup = self.getMarkup()
		self.previewState = previewState
		self.previewBlocked = False
		self.previewScrollPosition = QPoint()
		self.posmap = {}

		textDocument = self.editBox.document()
		self.highlighter = ReTextHighlighter(textDocument)
		if enchant_available and parent.actionEnableSC.isChecked():
			self.highlighter.dictionary = enchant.Dict(parent.sl or None)
			self.highlighter.rehighlight()
		self.highlighter.docType = self.markup.name

		self.editBox.cursorPositionChanged.connect(self.scrollPreviewToCursorPosition)
		self.editBox.textChanged.connect(self.updateLivePreviewBox)
		self.editBox.undoAvailable.connect(parent.actionUndo.setEnabled)
		self.editBox.redoAvailable.connect(parent.actionRedo.setEnabled)
		self.editBox.copyAvailable.connect(parent.actionCopy.setEnabled)
		textDocument.modificationChanged.connect(parent.modificationChanged)

		self.updateBoxesVisibility()

	def createWebView(self):
		webView = QWebView()
		if not globalSettings.handleWebLinks:
			webView.page().setLinkDelegationPolicy(QWebPage.DelegateExternalLinks)
			webView.page().linkClicked.connect(QDesktopServices.openUrl)
		settings = webView.settings()
		settings.setAttribute(QWebSettings.LocalContentCanAccessFileUrls, False)
		settings.setDefaultTextEncoding('utf-8')
		webView.loadFinished.connect(self.restorePreviewScrollPosition)
		return webView

	def createPreviewBox(self):
		if globalSettings.useWebKit:
			return self.createWebView()
		browser = ReTextPreview(self)
		return browser

	def getSplitter(self):
		splitter = QSplitter(Qt.Horizontal)
		# Give both boxes a minimum size so the minimumSizeHint will be
		# ignored when splitter.setSizes is called below
		for widget in self.editBox, self.previewBox:
			widget.setMinimumWidth(125)
			splitter.addWidget(widget)
		splitter.setSizes((50, 50))
		splitter.setChildrenCollapsible(False)
		splitter.tab = self
		return splitter

	def getMarkupClass(self):
		if self.fileName:
			markupClass = get_markup_for_file_name(
				self.fileName, return_class=True)
			if markupClass:
				return markupClass
		return self.p.defaultMarkup

	def getMarkup(self):
		markupClass = self.getMarkupClass()
		if markupClass and markupClass.available():
			return markupClass(filename=self.fileName)

	def getDocumentTitle(self, baseName=False):
		if self.markup and not baseName:
			text = self.editBox.toPlainText()
			try:
				return self.markup.get_document_title(text)
			except Exception:
				self.p.printError()
		if self.fileName:
			fileinfo = QFileInfo(self.fileName)
			basename = fileinfo.completeBaseName()
			return (basename if basename else fileinfo.fileName())
		return self.tr("New document")

	def getHtml(self, includeStyleSheet=True, includeTitle=True,
	            includeMeta=False, webenv=False):
		if self.markup is None:
			markupClass = self.getMarkupClass()
			errMsg = self.tr('Could not parse file contents, check if '
			                 'you have the <a href="%s">necessary module</a> '
			                 'installed!')
			try:
				errMsg %= markupClass.attributes[MODULE_HOME_PAGE]
			except (AttributeError, KeyError):
				# Remove the link if markupClass doesn't have the needed attribute
				errMsg = errMsg.replace('<a href="%s">', '').replace('</a>', '')
			return '<p style="color: red">%s</p>' % errMsg
		text = self.editBox.toPlainText()
		headers = ''
		if includeStyleSheet:
			headers += '<style type="text/css">\n' + self.p.ss + '</style>\n'
		cssFileName = self.getDocumentTitle(baseName=True) + '.css'
		if QFile.exists(cssFileName):
			headers += ('<link rel="stylesheet" type="text/css" href="%s">\n'
			% cssFileName)
		if includeMeta:
			headers += ('<meta name="generator" content="ReText %s">\n'
			% app_version)
		fallbackTitle = self.getDocumentTitle() if includeTitle else ''
		return self.markup.get_whole_html(text,
			custom_headers=headers, include_stylesheet=includeStyleSheet,
			fallback_title=fallbackTitle, webenv=webenv)

	def updatePreviewBox(self):
		self.previewBlocked = False
		if isinstance(self.previewBox, QTextEdit):
			scrollbar = self.previewBox.verticalScrollBar()
			scrollbarValue = scrollbar.value()
			distToBottom = scrollbar.maximum() - scrollbarValue
		else:
			frame = self.previewBox.page().mainFrame()
			self.previewScrollPosition = frame.scrollPosition()
		try:
			html = self.getHtml()
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
			settings = self.previewBox.settings()
			settings.setFontFamily(QWebSettings.StandardFont,
			                       globalSettings.font.family())
			settings.setFontSize(QWebSettings.DefaultFontSize,
			                     globalSettings.font.pointSize())
			self.previewBox.setHtml(html, QUrl.fromLocalFile(self.fileName))

	def restorePreviewScrollPosition(self):
		frame = self.previewBox.page().mainFrame()

		# Create a list of input line positions mapped to vertical pixel positions
		# in the preview
		self.posmap = {}
		elements = frame.findAllElements('[data-posmap]')

		if elements:
			# If there are posmap attributes, then build a posmap
			# dictionary from them that will be used whenever the
			# cursor is moved.
			for el in elements:
				value = el.attribute('data-posmap', 'invalid')
				self.posmap[int(value)] = el.geometry().bottom()

			nr_of_lines = self.editBox.document().blockCount()
			self.posmap[0] = 0
			self.posmap[nr_of_lines] = frame.contentsSize().height()
			self.scrollPreviewToCursorPosition()
		else:
			# If there are no posmap attributes in the HTML then just
			# restore the scroll position that we had before the
			# new content was loaded
			frame = self.previewBox.page().mainFrame()
			frame.setScrollPosition(self.previewScrollPosition)

	def scrollPreviewToCursorPosition(self):
		if not self.posmap:
			return

		# Do a binary search through the posmap to find the nearest
		# line above and below the current cursor position for which
		# the rendered position is known.
		cursor = self.editBox.textCursor()
		cursor_line = cursor.blockNumber()
		nr_of_lines = self.editBox.document().blockCount()
		posmap_lines = [0] + sorted(self.posmap.keys()) + [nr_of_lines]
		min_index = 0
		max_index = len(posmap_lines) - 1
		while max_index - min_index > 1:
			current_index = int((min_index + max_index) / 2)
			if posmap_lines[current_index] > cursor_line:
				max_index = current_index
			else:
				min_index = current_index

		min_line = posmap_lines[min_index]
		max_line = posmap_lines[max_index]

		min_pos = self.posmap[min_line]
		max_pos = self.posmap[max_line]

		fraction_below_min_line = (cursor_line - min_line) / (max_line - min_line)
		cursor_pos = (max_pos - min_pos) * fraction_below_min_line + min_pos

		half_viewport_height = self.previewBox.page().viewportSize().height() / 2
		self.previewScrollPosition.setY(cursor_pos - half_viewport_height)

		frame = self.previewBox.page().mainFrame()
		frame.setScrollPosition(self.previewScrollPosition)

	def updateLivePreviewBox(self):
		if self.previewState == PreviewLive and not self.previewBlocked:
			self.previewBlocked = True
			QTimer.singleShot(1000, self.updatePreviewBox)

	def updateBoxesVisibility(self):
		self.editBox.setVisible(self.previewState < PreviewNormal)
		self.previewBox.setVisible(self.previewState > PreviewDisabled)

	def setMarkupClass(self, markupClass):
		self.markup = None
		if markupClass and markupClass.available:
			self.markup = markupClass(filename=self.fileName)
		self.highlighter.docType = markupClass.name if markupClass else None
		self.highlighter.rehighlight()

	def readTextFromFile(self, encoding=None):
		openfile = QFile(self.fileName)
		openfile.open(QFile.ReadOnly)
		stream = QTextStream(openfile)
		encoding = encoding or globalSettings.defaultCodec
		if encoding:
			stream.setCodec(encoding)
		text = stream.readAll()
		openfile.close()
		markupClass = get_markup_for_file_name(self.fileName, return_class=True)
		self.setMarkupClass(markupClass)
		modified = bool(encoding) and (self.editBox.toPlainText() != text)
		self.editBox.setPlainText(text)
		self.editBox.document().setModified(modified)

	def saveTextToFile(self, fileName=None, addToWatcher=True):
		if fileName is None:
			fileName = self.fileName
		self.p.fileSystemWatcher.removePath(fileName)
		savefile = QFile(fileName)
		result = savefile.open(QFile.WriteOnly)
		if result:
			savestream = QTextStream(savefile)
			if globalSettings.defaultCodec:
				savestream.setCodec(globalSettings.defaultCodec)
			savestream << self.editBox.toPlainText()
			savefile.close()
		if result and addToWatcher:
			self.p.fileSystemWatcher.addPath(fileName)
		return result

	def installFakeVimHandler(self):
		if ReTextFakeVimHandler:
			fakeVimEditor = ReTextFakeVimHandler(self.editBox, self)
			fakeVimEditor.setSaveAction(self.actionSave)
			fakeVimEditor.setQuitAction(self.actionQuit)
			# TODO: action is bool, really call remove?
			self.p.actionFakeVimMode.triggered.connect(fakeVimEditor.remove)


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

	def openInternal(self, link):
		url = link.url()
		isLocalHtml = (link.scheme() in ('file', '') and url.endswith('.html'))
		if url.startswith('#'):
			self.scrollToAnchor(url[1:])
		elif link.isRelative() and get_markup_for_file_name(url, return_class=True):
			fileToOpen = QDir.current().filePath(url)
			if not QFileInfo(fileToOpen).completeSuffix() and self.fileName:
				fileToOpen += '.' + QFileInfo(self.tab.fileName).completeSuffix()
			self.tab.p.openFileWrapper(fileToOpen)
		elif globalSettings.handleWebLinks and isLocalHtml:
			self.setSource(link)
		else:
			QDesktopServices.openUrl(link)
