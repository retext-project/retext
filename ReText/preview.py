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

import time
from os.path import exists

from PyQt6.QtCore import QDir, QUrl
from PyQt6.QtGui import QDesktopServices, QTextCursor, QTextDocument
from PyQt6.QtWidgets import QTextBrowser

from ReText import globalSettings


class ReTextPreview(QTextBrowser):

    def __init__(self, tab):
        QTextBrowser.__init__(self)
        self.tab = tab
        # if set to True, links to other files will unsuccessfully be opened as anchors
        self.setOpenLinks(False)
        self.anchorClicked.connect(self.openInternal)
        self.lastRenderTime = 0
        self.distToBottom = None
        self.verticalScrollBar().rangeChanged.connect(self.updateScrollPosition)

    def disconnectExternalSignals(self):
        pass

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
