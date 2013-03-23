# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

from ReText import *
from ReText.highlighter import ReTextHighlighter

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
		self.connect(buttonBox, SIGNAL("rejected()"), self.close)
		verticalLayout.addWidget(buttonBox)
