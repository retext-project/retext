# vim: ts=4:sw=4:expandtab
#
# This file is part of ReText
# Copyright: 2017-2024 Dmitry Shachnev
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

import re
import time
from html.parser import HTMLParser
from itertools import accumulate
from os.path import exists

from PyQt6.QtCore import (
    QDir,
    QObject,
    QPointF,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QDesktopServices,
    QTextCursor,
    QTextDocument,
)
from PyQt6.QtWidgets import QTextBrowser

from ReText import globalSettings
from ReText.syncscroll import SyncScroll

POSMAP_ANCHOR_RE = re.compile(r'^posmap-(\d+)$')


class PosmapAnchorInserter(HTMLParser):
    """Finds where the anchors that replace the data-posmap attributes (which
    QTextDocument discards) have to be inserted: at the end of each element,
    so that their positions can be found in the laid out document."""

    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.html = html
        # getpos() returns (line, column), so remember where each line starts
        self.lineStarts = list(accumulate((len(line) + 1 for line in html.split('\n')), initial=0))
        self.stack = []  # (tag, posmap value or None)
        self.insertions = []  # (offset in html, anchor)

    @staticmethod
    def anchor(value):
        # Qt discards completely empty anchors,
        # &#8203; is the zero-width space.
        return f'<a name="posmap-{value}">&#8203;</a>'

    def currentOffset(self):
        line, column = self.getpos()
        return self.lineStarts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        self.stack.append((tag, dict(attrs).get('data-posmap')))

    def handle_startendtag(self, tag, attrs):
        # Self-closing syntax (<hr />): the element is complete right away
        value = dict(attrs).get('data-posmap')
        if value is not None:
            end = self.currentOffset() + len(self.get_starttag_text())
            self.insertions.append((end, self.anchor(value)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                value = self.stack[i][1]
                # Elements opened inside this one and never closed
                # (<hr> without a slash) are dropped with their anchor.
                del self.stack[i:]
                if value is not None:
                    self.insertions.append((self.currentOffset(), self.anchor(value)))
                break

    def result(self):
        pieces = []
        last = 0
        # Stable sort: anchors at the same offset keep the order they were found in
        for offset, anchor in sorted(self.insertions, key=lambda item: item[0]):
            pieces.append(self.html[last:offset])
            pieces.append(anchor)
            last = offset
        pieces.append(self.html[last:])
        return ''.join(pieces)


def insertPosmapAnchors(html):
    parser = PosmapAnchorInserter(html)
    parser.feed(html)
    parser.close()
    return parser.result()


class PreviewFrameAdapter(QObject):
    """Gives a QTextBrowser the interface that SyncScroll expects."""

    contentsSizeChanged = pyqtSignal()
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal()

    def __init__(self, preview):
        super().__init__(preview)
        self.preview = preview
        preview.document().documentLayout().documentSizeChanged.connect(self.contentsSizeChanged)

    def scrollPosition(self):
        return QPointF(0, self.preview.verticalScrollBar().value())

    def setScrollPosition(self, pos):
        self.preview.verticalScrollBar().setValue(int(pos.y()))

    def zoomFactor(self):
        return 1.0

    def getPositionMap(self, callback):
        doc = self.preview.document()
        layout = doc.documentLayout()
        result = {}
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                for name in it.fragment().charFormat().anchorNames():
                    m = POSMAP_ANCHOR_RE.match(name)
                    if m:
                        result[int(m.group(1))] = layout.blockBoundingRect(block).bottom()
                it += 1
            block = block.next()
        if result:
            callback(result)
        else:
            callback({})


class ReTextPreview(QTextBrowser):

    def __init__(self, tab, editorPositionToSourceLineFunc=None, sourceLineToEditorPositionFunc=None):
        QTextBrowser.__init__(self)
        self.tab = tab
        self.syncscroll = None
        self.editBox = None
        # if set to True, links to other files will unsuccessfully be opened as anchors
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.openInternal)
        self.lastRenderTime = 0
        self.distToBottom = None
        self.verticalScrollBar().rangeChanged.connect(self.updateScrollPosition)
        self.verticalScrollBar().setSingleStep(int(globalSettings.scrollFactor * 20))

        if globalSettings.syncScroll and editorPositionToSourceLineFunc:
            self.editBox = tab.editBox
            self.frameAdapter = PreviewFrameAdapter(self)
            self.syncscroll = SyncScroll(
                self.frameAdapter,
                editorPositionToSourceLineFunc,
                sourceLineToEditorPositionFunc,
                setEditorScrollValueFunc=self.editBox.verticalScrollBar().setValue,
            )
            self.editBox.cursorPositionChanged.connect(self._handleCursorPositionChanged)
            self.editBox.verticalScrollBar().valueChanged.connect(self.syncscroll.handleEditorScrolled)
            self.editBox.resized.connect(self._handleEditorResized)
            self.verticalScrollBar().valueChanged.connect(self.syncscroll.handlePreviewScrolled)

    def disconnectExternalSignals(self):
        if self.syncscroll is None:
            return
        self.editBox.cursorPositionChanged.disconnect(self._handleCursorPositionChanged)
        self.editBox.verticalScrollBar().valueChanged.disconnect(self.syncscroll.handleEditorScrolled)
        self.editBox.resized.disconnect(self._handleEditorResized)
        self.verticalScrollBar().valueChanged.disconnect(self.syncscroll.handlePreviewScrolled)

    def _handleCursorPositionChanged(self):
        self.syncscroll.handleCursorPositionChanged(
            self.editBox.verticalScrollBar().value() + self.editBox.cursorRect().top())

    def _handleEditorResized(self, rect):
        self.syncscroll.handleEditorResized(rect.height())

    def setHtml(self, html):
        if self.syncscroll is None:
            return super().setHtml(html)
        self.frameAdapter.loadStarted.emit()
        super().setHtml(insertPosmapAnchors(html))
        self.frameAdapter.loadFinished.emit()

    def openInternal(self, link):
        url = link.url()
        if url.startswith('#'):
            self.scrollToAnchor(url[1:])
            return
        elif link.isRelative():
            fileToOpen = QDir.current().filePath(url)
        else:
            fileToOpen = link.toLocalFile() if link.isLocalFile() else None
        if fileToOpen is not None:
            if exists(fileToOpen):
                link = QUrl.fromLocalFile(fileToOpen)
                if globalSettings.handleWebLinks and fileToOpen.endswith('.html'):
                    self.setSource(link)
                    return
            # This is outside the "if exists" block because we can prompt for
            # creating the file
            if self.tab.openSourceFile(fileToOpen):
                return
        QDesktopServices.openUrl(link)

    def findText(self, text, flags, wrap=False):
        cursor = self.textCursor()
        if wrap and flags & QTextDocument.FindFlag.FindBackward:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        elif wrap:
            cursor.movePosition(QTextCursor.MoveOperation.Start)
        newCursor = self.document().find(text, cursor, flags)
        if not newCursor.isNull():
            self.setTextCursor(newCursor)
            return True
        if not wrap:
            return self.findText(text, flags, wrap=True)
        return False

    def updateScrollPosition(self, minimum, maximum):
        """Called when vertical scroll bar range changes.

        If this happened during preview rendering (less than 0.5s since it
        was started), set the position such that distance to bottom is the
        same as before refresh.
        """
        timeSinceRender = time.time() - self.lastRenderTime
        if timeSinceRender < 0.5 and self.distToBottom is not None and maximum:
            newValue = maximum - self.distToBottom
            if newValue >= minimum:
                self.verticalScrollBar().setValue(newValue)

    def setFont(self, font):
        self.document().setDefaultFont(font)
