# This file is part of ReText
# Copyright: Dmitry Shachnev 2012-2014
# License: GNU GPL v2 or higher

from ReText import monofont, DOCTYPE_HTML
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
		self.textEdit.setFont(monofont)
		self.hl = ReTextHighlighter(self.textEdit.document())
		self.hl.docType = DOCTYPE_HTML
		verticalLayout.addWidget(self.textEdit)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Close)
		buttonBox.rejected.connect(self.close)
		verticalLayout.addWidget(buttonBox)

class LocaleDialog(QDialog):
	def __init__(self, parent, defaultText=""):
		QDialog.__init__(self, parent)
		verticalLayout = QVBoxLayout(self)
		self.label = QLabel(self)
		self.label.setText(self.tr('Enter locale name (example: en_US)'))
		verticalLayout.addWidget(self.label)
		self.localeEdit = QLineEdit(self)
		self.localeEdit.setText(defaultText)
		verticalLayout.addWidget(self.localeEdit)
		self.checkBox = QCheckBox(self.tr('Set as default'), self)
		verticalLayout.addWidget(self.checkBox)
		buttonBox = QDialogButtonBox(self)
		buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
		verticalLayout.addWidget(buttonBox)
		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)
