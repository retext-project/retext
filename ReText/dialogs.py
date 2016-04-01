# This file is part of ReText
# Copyright: 2012-2015 Dmitry Shachnev
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
from ReText.highlighter import ReTextHighlighter

from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, \
 QLabel, QLineEdit, QTextEdit, QVBoxLayout

class HtmlDialog(QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		self.resize(700, 600)
		verticalLayout = QVBoxLayout(self)
		self.textEdit = QTextEdit(self)
		self.textEdit.setReadOnly(True)
		self.textEdit.setFont(globalSettings.editorFont)
		self.hl = ReTextHighlighter(self.textEdit.document())
		self.hl.docType = 'html'
		verticalLayout.addWidget(self.textEdit)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Close)
		buttonBox.rejected.connect(self.close)
		verticalLayout.addWidget(buttonBox)

class LocaleDialog(QDialog):
	def __init__(self, parent, defaultText=None):
		QDialog.__init__(self, parent)
		verticalLayout = QVBoxLayout(self)
		self.label = QLabel(self)
		self.label.setText(self.tr('Enter locale name (example: en_US)'))
		verticalLayout.addWidget(self.label)
		self.localeEdit = QLineEdit(self)
		if defaultText:
			self.localeEdit.setText(defaultText)
		verticalLayout.addWidget(self.localeEdit)
		self.checkBox = QCheckBox(self.tr('Set as default'), self)
		verticalLayout.addWidget(self.checkBox)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
		verticalLayout.addWidget(buttonBox)
		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)
