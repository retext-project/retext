# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2017-2022 Dmitry Shachnev
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

from ReText import globalSettings
from ReText.syncscroll import SyncScroll
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QTextDocument
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView


class ReTextWebEngineUrlRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        if (info.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeXhr
                and info.requestUrl().isLocalFile()):
            # For security reasons, disable XMLHttpRequests to local files
            info.block(True)


class ReTextWebEnginePage(QWebEnginePage):
    def __init__(self, parent, tab):
        QWebEnginePage.__init__(self, parent)
        self.tab = tab
        self.interceptor = ReTextWebEngineUrlRequestInterceptor(self)
        self.setUrlRequestInterceptor(self.interceptor)

    def setScrollPosition(self, pos):
        self.runJavaScript("window.scrollTo(%s, %s);" % (pos.x(), pos.y()))

    def getPositionMap(self, callback):
        def resultCallback(result):
            if result:
                return callback({int(a): b for a, b in result.items()})

        script = """
        var elements = document.querySelectorAll('[data-posmap]');
        var result = {};
        var bodyTop = document.body.getBoundingClientRect().top;
        for (var i = 0; i < elements.length; ++i) {
            var element = elements[i];
            value = element.getAttribute('data-posmap');
            bottom = element.getBoundingClientRect().bottom - bodyTop;
            result[value] = bottom;
        }
        result;
        """
        self.runJavaScript(script, resultCallback)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        print("level=%r message=%r lineNumber=%r sourceId=%r" % (level, message, lineNumber, sourceId))

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if url.scheme() == "data":
            return True
        if url.isLocalFile():
            localFile = url.toLocalFile()
            if localFile == self.tab.fileName:
                self.tab.startPendingConversion()
                return False
            if self.tab.openSourceFile(localFile):
                return False
        if globalSettings.handleWebLinks:
            return True
        QDesktopServices.openUrl(url)
        return False


class ReTextWebEnginePreview(QWebEngineView):

    def __init__(self, tab,
                 editorPositionToSourceLineFunc,
                 sourceLineToEditorPositionFunc):

        QWebEngineView.__init__(self, parent=tab)
        webPage = ReTextWebEnginePage(self, tab)
        self.setPage(webPage)

        self.syncscroll = SyncScroll(webPage,
                                     editorPositionToSourceLineFunc,
                                     sourceLineToEditorPositionFunc)
        self.editBox = tab.editBox

        settings = self.settings()
        settings.setDefaultTextEncoding('utf-8')
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        # Events relevant to sync scrolling
        self.editBox.cursorPositionChanged.connect(self._handleCursorPositionChanged)
        self.editBox.verticalScrollBar().valueChanged.connect(self.syncscroll.handleEditorScrolled)
        self.editBox.resized.connect(self._handleEditorResized)

        # Scroll the preview when the mouse wheel is used to scroll
        # beyond the beginning/end of the editor
        self.editBox.scrollLimitReached.connect(self._handleWheelEvent)

    def setFont(self, font):
        settings = self.settings()
        settings.setFontFamily(QWebEngineSettings.FontFamily.StandardFont,
                               font.family())
        settings.setFontSize(QWebEngineSettings.FontSize.DefaultFontSize,
                             font.pointSize())

    def setHtml(self, html, baseUrl):
        # A hack to prevent WebEngine from stealing the focus
        self.setEnabled(False)
        super().setHtml(html, baseUrl)
        self.setEnabled(True)

    def _handleWheelEvent(self, event):
        # Only pass wheelEvents on to the preview if syncscroll is
        # controlling the position of the preview
        if self.syncscroll.isActive():
            QGuiApplication.sendEvent(self.focusProxy(), event)

    def event(self, event):
        # Work-around https://bugreports.qt.io/browse/QTBUG-43602
        if event.type() == QEvent.Type.ChildAdded:
            event.child().installEventFilter(self)
        elif event.type() == QEvent.Type.ChildRemoved:
            event.child().removeEventFilter(self)
        return super().event(event)

    def eventFilter(self, object, event):
        if event.type() == QEvent.Type.Wheel:
            if QGuiApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
                self.wheelEvent(event)
                return True
        return False

    def findText(self, text, flags):
        options = QWebEnginePage.FindFlag(0)
        if flags & QTextDocument.FindFlag.FindBackward:
            options |= QWebEnginePage.FindFlag.FindBackward
        if flags & QTextDocument.FindFlag.FindCaseSensitively:
            options |= QWebEnginePage.FindFlag.FindCaseSensitively
        super().findText(text, options)
        return True

    def disconnectExternalSignals(self):
        self.editBox.cursorPositionChanged.disconnect(self._handleCursorPositionChanged)
        self.editBox.verticalScrollBar().valueChanged.disconnect(self.syncscroll.handleEditorScrolled)
        self.editBox.resized.disconnect(self._handleEditorResized)

        self.editBox.scrollLimitReached.disconnect(self._handleWheelEvent)

    def _handleCursorPositionChanged(self):
        editorCursorPosition = self.editBox.verticalScrollBar().value() + \
                       self.editBox.cursorRect().top()
        self.syncscroll.handleCursorPositionChanged(editorCursorPosition)

    def _handleEditorResized(self, rect):
        self.syncscroll.handleEditorResized(rect.height())

    def wheelEvent(self, event):
        if QGuiApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
            zoomFactor = self.zoomFactor()
            zoomFactor *= 1.001 ** event.angleDelta().y()
            self.setZoomFactor(zoomFactor)
        return super().wheelEvent(event)
