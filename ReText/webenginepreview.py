# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2017 Dmitry Shachnev
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
from ReText.preview import ReTextWebPreview
from ReText.syncscroll import SyncScroll
from PyQt5.QtGui import QDesktopServices, QGuiApplication
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineView, QWebEngineSettings


class ReTextWebEnginePage(QWebEnginePage):
    def __init__(self, parent, tab):
        QWebEnginePage.__init__(self, parent)
        self.tab = tab

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


class ReTextWebEnginePreview(ReTextWebPreview, QWebEngineView):

    def __init__(self, tab,
                 editorPositionToSourceLineFunc,
                 sourceLineToEditorPositionFunc):

        QWebEngineView.__init__(self, parent=tab)
        webPage = ReTextWebEnginePage(self, tab)
        self.setPage(webPage)

        self.syncscroll = SyncScroll(webPage,
                                     editorPositionToSourceLineFunc,
                                     sourceLineToEditorPositionFunc)
        ReTextWebPreview.__init__(self, tab.editBox)

        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls,
                              False)

    def updateFontSettings(self):
        settings = self.settings()
        settings.setFontFamily(QWebEngineSettings.StandardFont,
                               globalSettings.font.family())
        settings.setFontSize(QWebEngineSettings.DefaultFontSize,
                             globalSettings.font.pointSize())

    def setHtml(self, html, baseUrl):
        # A hack to prevent WebEngine from stealing the focus
        self.setEnabled(False)
        QWebEngineView.setHtml(self, html, baseUrl)
        self.setEnabled(True)

    def _handleWheelEvent(self, event):
        # Only pass wheelEvents on to the preview if syncscroll is
        # controlling the position of the preview
        if self.syncscroll.isActive():
            QGuiApplication.sendEvent(self.focusProxy(), event)
