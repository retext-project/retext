# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

from ReText import *
from ReText.highlighter import ReTextHighlighter

class HtmlDialog(QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		self.resize(700, 600)
		self.verticalLayout = QVBoxLayout(self)
		self.textEdit = QTextEdit(self)
		self.textEdit.setReadOnly(True)
		self.textEdit.setFont(monofont)
		hl = ReTextHighlighter(self.textEdit.document())
		hl.docType = DOCTYPE_HTML
		self.verticalLayout.addWidget(self.textEdit)
		self.buttonBox = QDialogButtonBox(self)
		self.buttonBox.setStandardButtons(QDialogButtonBox.Close)
		self.connect(self.buttonBox, SIGNAL("clicked(QAbstractButton*)"), self.doClose)
		self.verticalLayout.addWidget(self.buttonBox)
	
	def doClose(self):
		self.close()
