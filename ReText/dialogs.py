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

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from ReText import globalSettings
from ReText.highlighter import ReTextHighlighter


class HtmlDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.resize(700, 600)
        verticalLayout = QVBoxLayout(self)
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setFont(globalSettings.getEditorFont())
        self.hl = ReTextHighlighter(self.textEdit.document())
        self.hl.docType = 'html'
        verticalLayout.addWidget(self.textEdit)
        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)
        buttonBox.rejected.connect(self.close)
        verticalLayout.addWidget(buttonBox)

class LocaleDialog(QDialog):
    def __init__(self, parent, defaultText=None):
        QDialog.__init__(self, parent)
        verticalLayout = QVBoxLayout(self)
        labelText = self.tr('Enter locale name (example: en_US)') + '\n'
        labelText += self.tr('It is possible to specify multiple languages, separated by comma.')
        verticalLayout.addWidget(QLabel(labelText, self))
        self.localeEdit = QLineEdit(self)
        if defaultText:
            self.localeEdit.setText(defaultText)
        verticalLayout.addWidget(self.localeEdit)
        self.checkBox = QCheckBox(self.tr('Set as default'), self)
        verticalLayout.addWidget(self.checkBox)
        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        verticalLayout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)


class EncodingDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        verticalLayout = QVBoxLayout(self)
        verticalLayout.addWidget(QLabel(self.tr('Enter encoding name:'), self))
        self.encodingEdit = QLineEdit(self)
        self.encodingEdit.textChanged.connect(self.handleTextChanged)
        verticalLayout.addWidget(self.encodingEdit)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel
                                          | QDialogButtonBox.StandardButton.Ok)
        verticalLayout.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def handleTextChanged(self, value):
        button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        try:
            "1".encode(value)
        except LookupError:
            button.setEnabled(False)
        else:
            button.setEnabled(True)
