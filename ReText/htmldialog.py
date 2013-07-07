# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

from ReText import QtWidgets, monofont, DOCTYPE_HTML
from ReText.highlighter import ReTextHighlighter

(QDialog, QDialogButtonBox, QTextEdit, QVBoxLayout) = (QtWidgets.QDialog,
 QtWidgets.QDialogButtonBox, QtWidgets.QTextEdit, QtWidgets.QVBoxLayout)

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
