#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt4.Qt import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import markdown
md = markdown.Markdown()

try:
	import gdata.docs
	import gdata.docs.service
	from gdata import MediaSource
except:
	use_gdocs = False
else:
	use_gdocs = True

app_name = "ReText"
app_version = "0.3.4 alpha"

class HtmlHighlighter(QSyntaxHighlighter):
	def __init__(self, parent):
		QSyntaxHighlighter.__init__(self, parent)
	
	def highlightBlock(self, text):
		charFormat = QTextCharFormat()
		patterns = ("<[^>]*>", "&[^;]*;", "\"[^\"]*\"", "<!--[^-->]*-->")
		foregrounds = [Qt.darkMagenta, Qt.darkCyan, Qt.darkYellow, Qt.gray]
		for i in range(len(patterns)):
			expression = QRegExp(patterns[i])
			index = expression.indexIn(text)
			if i == 3:
				charFormat.setFontWeight(QFont.Normal)
			else:
				charFormat.setFontWeight(QFont.Bold)
			charFormat.setForeground(foregrounds[i]);
			while (index >= 0):
				length = expression.matchedLength()
				self.setFormat(index, length, charFormat)
				index = expression.indexIn(text, index + length)

class ReTextWindow(QMainWindow):
	def __init__(self):
		QMainWindow.__init__(self)
		self.resize(800, 600)
		screen = QDesktopWidget().screenGeometry()
		size = self.geometry()
		self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
		self.setWindowTitle(self.tr('New document') + '[*] ' + QChar(0x2014) + ' ' + app_name)
		self.setWindowIcon(QIcon.fromTheme('retext', QIcon.fromTheme('accessories-text-editor')))
		self.centralwidget = QWidget(self)
		self.verticalLayout = QVBoxLayout(self.centralwidget)
		self.previewBox = QTextEdit(self.centralwidget)
		self.previewBox.setVisible(False)
		self.previewBox.setReadOnly(True)
		self.verticalLayout.addWidget(self.previewBox)
		self.editBox = QTextEdit(self.centralwidget)
		self.editBox.setAcceptRichText(False)
		monofont = QFont()
		monofont.setFamily('monospace')
		self.editBox.setFont(monofont)
		self.verticalLayout.addWidget(self.editBox)
		self.setCentralWidget(self.centralwidget)
		self.syntaxHighlighter = HtmlHighlighter(self.editBox.document())
		self.toolBar = QToolBar(self.tr('File toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, self.toolBar)
		self.editBar = QToolBar(self.tr('Edit toolbar'), self)
		self.addToolBar(Qt.TopToolBarArea, self.editBar)
		self.actionNew = QAction(QIcon.fromTheme('document-new'), self.tr('New'), self)
		self.actionNew.setShortcut(QKeySequence.New)
		self.connect(self.actionNew, SIGNAL('triggered()'), self.createNew)
		self.actionOpen = QAction(QIcon.fromTheme('document-open'), self.tr('Open'), self)
		self.actionOpen.setShortcut(QKeySequence.Open)
		self.connect(self.actionOpen, SIGNAL('triggered()'), self.openFile)
		self.actionSave = QAction(QIcon.fromTheme('document-save'), self.tr('Save'), self)
		self.actionSave.setEnabled(False)
		self.actionSave.setShortcut(QKeySequence.Save)
		self.connect(self.editBox.document(), SIGNAL('modificationChanged(bool)'), self.modificationChanged)
		self.connect(self.actionSave, SIGNAL('triggered()'), self.saveFile)
		self.actionSaveAs = QAction(QIcon.fromTheme('document-save-as'), self.tr('Save as'), self)
		self.actionSaveAs.setShortcut(QKeySequence.SaveAs)
		self.connect(self.actionSaveAs, SIGNAL('triggered()'), self.saveFileAs)
		self.actionPrint = QAction(QIcon.fromTheme('document-print'), self.tr('Print'), self)
		self.actionPrint.setShortcut(QKeySequence.Print)
		self.connect(self.actionPrint, SIGNAL('triggered()'), self.printFile)
		self.actionPreview = QAction(QIcon.fromTheme('x-office-document'), self.tr('Preview'), self)
		self.actionPreview.setCheckable(True)
		self.connect(self.actionPreview, SIGNAL('triggered(bool)'), self.preview)
		self.actionPerfectHtml = QAction(QIcon.fromTheme('text-html'), 'HTML', self)
		self.connect(self.actionPerfectHtml, SIGNAL('triggered()'), self.saveFilePerfect)
		self.actionPdf = QAction(QIcon.fromTheme('application-pdf'), 'PDF', self)
		self.connect(self.actionPdf, SIGNAL('triggered()'), self.savePdf)
		self.actionQuit = QAction(QIcon.fromTheme('application-exit'), self.tr('Quit'), self)
		self.actionQuit.setShortcut(QKeySequence.Quit)
		self.actionQuit.setMenuRole(QAction.QuitRole)
		self.connect(self.actionQuit, SIGNAL('triggered()'), qApp, SLOT('quit()'))
		self.actionUndo = QAction(QIcon.fromTheme('edit-undo'), self.tr('Undo'), self)
		self.actionUndo.setShortcut(QKeySequence.Undo)
		self.actionRedo = QAction(QIcon.fromTheme('edit-redo'), self.tr('Redo'), self)
		self.actionRedo.setShortcut(QKeySequence.Redo)
		self.connect(self.actionUndo, SIGNAL('triggered()'), self.editBox, SLOT('undo()'))
		self.connect(self.actionRedo, SIGNAL('triggered()'), self.editBox, SLOT('redo()'))
		self.actionUndo.setEnabled(False)
		self.actionRedo.setEnabled(False)
		self.connect(self.editBox.document(), SIGNAL('undoAvailable(bool)'), self.actionUndo, SLOT('setEnabled(bool)'))
		self.connect(self.editBox.document(), SIGNAL('redoAvailable(bool)'), self.actionRedo, SLOT('setEnabled(bool)'))
		self.actionCopy = QAction(QIcon.fromTheme('edit-copy'), self.tr('Copy'), self)
		self.actionCopy.setShortcut(QKeySequence.Copy)
		self.actionCopy.setEnabled(False)
		self.actionCut = QAction(QIcon.fromTheme('edit-cut'), self.tr('Cut'), self)
		self.actionCut.setShortcut(QKeySequence.Cut)
		self.actionCut.setEnabled(False)
		self.actionPaste = QAction(QIcon.fromTheme('edit-paste'), self.tr('Paste'), self)
		self.actionPaste.setShortcut(QKeySequence.Paste)
		self.connect(self.actionCut, SIGNAL('triggered()'), self.editBox, SLOT('cut()'))
		self.connect(self.actionCopy, SIGNAL('triggered()'), self.editBox, SLOT('copy()'))
		self.connect(self.actionPaste, SIGNAL('triggered()'), self.editBox, SLOT('paste()'))
		self.connect(qApp.clipboard(), SIGNAL('dataChanged()'), self.clipboardDataChanged)
		self.clipboardDataChanged()
		self.actionPlainText = QAction(self.tr('Plain text'), self)
		self.actionPlainText.setCheckable(True)
		self.connect(self.actionPlainText, SIGNAL('triggered(bool)'), self.enablePlainText)
		self.actionAutoFormatting = QAction(self.tr('Auto-formatting'), self)
		self.actionAutoFormatting.setCheckable(True)
		self.actionAutoFormatting.setChecked(True)
		self.actionRecentFiles = QAction(QIcon.fromTheme('document-open-recent'), self.tr('Open recent'), self)
		self.connect(self.actionRecentFiles, SIGNAL('triggered()'), self.openRecent)
		self.actionAbout = QAction(QIcon.fromTheme('help-about'), self.tr('About %1').arg(app_name), self)
		self.actionAbout.setMenuRole(QAction.AboutRole)
		self.connect(self.actionAbout, SIGNAL('triggered()'), self.aboutDialog)
		self.actionAboutQt = QAction(self.tr('About Qt'), self)
		self.actionAboutQt.setMenuRole(QAction.AboutQtRole)
		if use_gdocs:
			self.actionGDocsExport = QAction(QIcon.fromTheme('web-browser'), self.tr('Save to Google Docs'), self)
			self.connect(self.actionGDocsExport, SIGNAL('triggered()'), self.GDocsExport)
		self.connect(self.actionAboutQt, SIGNAL('triggered()'), qApp, SLOT('aboutQt()'))
		self.usefulTags = ('a', 'center', 'i', 'img', 's', 'span', 'table', 'td', 'tr', 'u')
		self.usefulChars = ('hellip', 'laquo', 'minus', 'mdash', 'nbsp', 'ndash', 'raquo')
		self.tagsBox = QComboBox(self.editBar)
		self.tagsBox.addItem(self.tr('Tags'))
		self.tagsBox.addItems(self.usefulTags)
		self.connect(self.tagsBox, SIGNAL('activated(int)'), self.insertTag)
		self.symbolBox = QComboBox(self.editBar)
		self.symbolBox.addItem(self.tr('Symbols'))
		self.symbolBox.addItems(self.usefulChars)
		self.connect(self.symbolBox, SIGNAL('activated(int)'), self.insertSymbol)
		self.menubar = QMenuBar(self)
		self.menubar.setGeometry(QRect(0, 0, 800, 25))
		self.setMenuBar(self.menubar)
		self.menuFile = self.menubar.addMenu(self.tr('File'))
		self.menuEdit = self.menubar.addMenu(self.tr('Edit'))
		self.menuHelp = self.menubar.addMenu(self.tr('Help'))
		self.menuFile.addAction(self.actionNew)
		self.menuFile.addAction(self.actionOpen)
		self.menuFile.addAction(self.actionRecentFiles)
		self.menuFile.addSeparator()
		self.menuFile.addAction(self.actionSave)
		self.menuFile.addAction(self.actionSaveAs)
		self.menuFile.addSeparator()
		self.menuExport = self.menuFile.addMenu(self.tr('Export'))
		self.menuExport.addAction(self.actionPerfectHtml)
		self.menuExport.addAction(self.actionPdf)
		if use_gdocs:
			self.menuExport.addAction(self.actionGDocsExport)
		self.menuFile.addAction(self.actionPrint)
		self.menuFile.addSeparator()
		self.menuFile.addAction(self.actionQuit)
		self.menuEdit.addAction(self.actionUndo)
		self.menuEdit.addAction(self.actionRedo)
		self.menuEdit.addSeparator()
		self.menuEdit.addAction(self.actionCut)
		self.menuEdit.addAction(self.actionCopy)
		self.menuEdit.addAction(self.actionPaste)
		self.menuEdit.addSeparator()
		self.menuEdit.addAction(self.actionPlainText)
		self.menuEdit.addAction(self.actionAutoFormatting)
		self.menuEdit.addAction(self.actionPreview)
		self.menuHelp.addAction(self.actionAbout)
		self.menuHelp.addAction(self.actionAboutQt)
		self.menubar.addMenu(self.menuFile)
		self.menubar.addMenu(self.menuEdit)
		self.menubar.addMenu(self.menuHelp)
		self.toolBar.addAction(self.actionOpen)
		self.toolBar.addAction(self.actionSave)
		self.toolBar.addAction(self.actionPrint)
		self.toolBar.addSeparator()
		self.toolBar.addAction(self.actionPreview)	
		self.editBar.addAction(self.actionUndo)
		self.editBar.addAction(self.actionRedo)
		self.editBar.addSeparator()
		self.editBar.addAction(self.actionCut)
		self.editBar.addAction(self.actionCopy)
		self.editBar.addAction(self.actionPaste)
		self.editBar.addWidget(self.tagsBox)
		self.editBar.addWidget(self.symbolBox)
		self.fileName = ""
	
	def preview(self, viewmode):
		self.editBar.setEnabled(not viewmode)
		self.editBox.setVisible(not viewmode)
		self.previewBox.setVisible(viewmode)
		if viewmode:
			if self.actionPlainText.isChecked():
				self.previewBox.setPlainText(self.editBox.toPlainText())
			else:
				self.previewBox.setHtml(self.parseText())
	
	def setCurrentFile(self):	
		curFile = self.fileName
		self.setWindowFilePath(curFile);
		settings = QSettings()
		files = settings.value("recentFileList").toStringList()
		files.removeAll(self.fileName)
		files.prepend(self.fileName)
		while len(files) > 10:
			files.removeLast()
		settings.setValue("recentFileList", files)
	
	def createNew(self):
		if self.maybeSave():
			self.fileName = ""
			self.editBox.clear()
			self.actionPreview.setChecked(False)
			self.actionPlainText.setChecked(False)
			self.enablePlainText(False)
			self.setWindowTitle(self.tr('New document') + '[*] ' + QChar(0x2014) + ' ' + app_name)
			self.setWindowFilePath("")
			self.editBox.document().setModified(False)
			self.modificationChanged(False)
			self.preview(False)
	
	def openRecent(self):
		settings = QSettings()
		files = settings.value("recentFileList").toStringList()
		for i in files:
			if not QFile.exists(i):
				files.removeAll(i)
		settings.setValue("recentFileList", files)
		(item, ok) = QInputDialog.getItem(self, app_name, self.tr("Open recent"), files, 0, False)
		if ok and not item.isEmpty():
			self.fileName = item
			self.openFileMain()
    
	def openFile(self):
		if self.maybeSave():
			self.fileName = QFileDialog.getOpenFileName(self, self.tr("Open file"), "", \
			self.tr("ReText files (*.re *.mdml *.txt)")+";;"+self.tr("All files (*)"))
			self.openFileMain()
		
	def openFileMain(self):
		if QFile.exists(self.fileName):
			openfile = QFile(self.fileName)
			openfile.open(QIODevice.ReadOnly)
			openstream = QTextStream(openfile)
			html = openstream.readAll()
			openfile.close()
			self.actionPreview.setChecked(False)
			self.editBox.setPlainText(html)
			self.editBox.document().setModified(False)
			self.modificationChanged(False)
			self.preview(False)
			suffix = QFileInfo(self.fileName).suffix()
			if suffix.startsWith("htm"):
				self.actionAutoFormatting.setChecked(False)
			if not suffix == "txt":
				self.actionPlainText.setChecked(False)
				self.enablePlainText(False)
			self.setWindowTitle("")
			self.setWindowFilePath(self.fileName)
			self.setCurrentFile()
	
	def saveFile(self):
		self.saveFileMain(False)
	
	def saveFileAs(self):
		self.saveFileMain(True)
	
	def saveFileMain(self, dlg):
		if (not self.fileName) or dlg:
			self.fileName = QFileDialog.getSaveFileName(self, self.tr("Save file"), "", self.tr("ReText files (*.re *.mdml *.txt)"))
		if self.fileName:
			if QFileInfo(self.fileName).suffix().isEmpty():
				self.fileName.append(".re")
			savefile = QFile(self.fileName)
			savefile.open(QIODevice.WriteOnly)
			savestream = QTextStream(savefile)
			savestream.__lshift__(self.editBox.toPlainText())
			savefile.close()
		self.editBox.document().setModified(False)
		self.setCurrentFile()
	
	def saveFilePerfect(self):
		if not self.fileName:
			self.fileName = QFileDialog.getSaveFileName(self, self.tr("Save file"), "", self.tr("HTML files (*.html *.htm)"))
		if self.fileName:
			if QFileInfo(self.fileName).suffix().isEmpty():
				self.fileName.append(".html")
			td = QTextDocument()
			td.setHtml(self.parseText())
			writer = QTextDocumentWriter(self.fileName)
			writer.write(td)
	
	def savePdf(self):
		fileName = QFileDialog.getSaveFileName(self, self.tr("Export document to PDF"), "", self.tr("PDF files (*.pdf)"));
		if fileName:
			if QFileInfo(fileName).suffix().isEmpty():
				fileName.append(".pdf")
			printer = QPrinter(QPrinter.HighResolution)
			printer.setOutputFormat(QPrinter.PdfFormat)
			printer.setOutputFileName(fileName)
			printer.setCreator(app_name+" "+app_version)
			td = QTextDocument()
			if self.actionPlainText.isChecked():
				td.setPlainText(self.editBox.toPlainText())
			else:
				td.setHtml(self.parseText())
			td.print_(printer)
	
	def printFile(self):
		printer = QPrinter(QPrinter.HighResolution)
		printer.setCreator(app_name+" "+app_version)
		dlg = QPrintDialog(printer, self)
		dlg.setWindowTitle(self.tr("Print Document"))
		if (dlg.exec_() == QDialog.Accepted):
			td = QTextDocument()
			if self.actionPlainText.isChecked():
				td.setPlainText(self.editBox.toPlainText())
			else:
				td.setHtml(self.parseText())
			td.print_(printer)
	
	def GDocsExport(self):
		settings = QSettings()
		login = settings.value("GDocsLogin").toString()
		passwd = settings.value("GDocsPasswd").toString()
		(login, ok) = QInputDialog.getText(self, app_name, self.tr("User name:"), QLineEdit.Normal, login)
		if ok and login:	
			(passwd, ok) = QInputDialog.getText(self, app_name, self.tr("Password:"), QLineEdit.Password, passwd)
		if ok and login:
			td = QTextDocument()
			if self.actionPlainText.isChecked():
				td.setPlainText(self.editBox.toPlainText())
			else:
				td.setHtml(self.parseText())
			writer = QTextDocumentWriter('temp.html')
			writer.write(td)
			gdClient = gdata.docs.service.DocsService()
			try:
				gdClient.ClientLogin(unicode(login), unicode(passwd))
			except gdata.service.BadAuthentication:
				QMessageBox.warning (self, app_name, self.tr("Incorrect user name or password!"))
			else:
				settings.setValue("GDocsLogin", login)
				settings.setValue("GDocsPasswd", passwd)
				ms = MediaSource(file_path='temp.html', content_type='text/html')
				if self.fileName:
					title = self.fileName
				else:
					title = self.tr("New document")
				entry = gdClient.Upload(ms, unicode(title))
				link = entry.GetAlternateLink().href
				QFile('temp.html').remove()
				QDesktopServices.openUrl(QUrl(link))
	
	def modificationChanged(self, changed):
		self.actionSave.setEnabled(changed)
		self.setWindowModified(changed)
	
	def clipboardDataChanged(self):
		self.actionPaste.setEnabled(qApp.clipboard().mimeData().hasText())
	
	def insertTag(self, num):
		if num:
			ut = self.usefulTags[num-1]
			hc = not ut in ('img', 'td', 'tr')
			arg = ''
			if ut == 'a':
				arg = ' href=""'
			if ut == 'img':
				arg = ' src=""'
			if ut == 'span':
				arg = ' style=""'
			tc = self.editBox.textCursor()
			if hc:
				toinsert = '<'+ut+arg+'>'+tc.selectedText()+'</'+ut+'>'
				tc.removeSelectedText
				tc.insertText(toinsert)
			else:
				tc.insertText('<'+ut+arg+'>'+tc.selectedText())
		self.tagsBox.setCurrentIndex(0)
	
	def insertSymbol(self, num):
		if num:
			self.editBox.insertPlainText('&'+self.usefulChars[num-1]+';')
		self.symbolBox.setCurrentIndex(0)
	
	def maybeSave(self):
		if not self.editBox.document().isModified():
			return True
		ret = QMessageBox.warning(self, app_name, self.tr("The document has been modified.\nDo you want to save your changes?"), \
		QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
		if ret == QMessageBox.Save:
			self.saveFileMain(False)
			return True
		elif ret == QMessageBox.Cancel:
			return False
		return True
	
	def closeEvent(self, closeevent):
		if self.maybeSave():
			closeevent.accept()
		else:
			closeevent.ignore()
	
	def aboutDialog(self):
		QMessageBox.about(self, self.tr('About %1').arg(app_name), \
		self.tr('This is <b>%1</b>, version %2<br>Author: Dmitry Shachnev, 2011<br>Website: <a href="http://sourceforge.net/p/retext/">sf.net/p/retext</a>').arg(app_name, app_version))
	
	def enablePlainText(self, value):
		self.actionAutoFormatting.setDisabled(value)
		self.actionPerfectHtml.setDisabled(value)
	
	def parseText(self):
		htmltext = self.editBox.toPlainText()
		if self.actionAutoFormatting.isChecked():
			toinsert = md.convert(unicode(htmltext))
		else:
			toinsert = htmltext
		return toinsert

def main(fileName):
	app = QApplication(sys.argv)
	app.setOrganizationName("ReText project")
	app.setApplicationName("ReText")
	RtTranslator = QTranslator()
	if not RtTranslator.load("retext_"+QLocale.system().name()):
		if sys.platform == "linux2":
			RtTranslator.load("retext_"+QLocale.system().name(), "/usr/lib/retext")
	QtTranslator = QTranslator()
	QtTranslator.load("qt_"+QLocale.system().name(), QLibraryInfo.location(QLibraryInfo.TranslationsPath))
	app.installTranslator(RtTranslator)
	app.installTranslator(QtTranslator)
	window = ReTextWindow()
	if QFile.exists(QString.fromUtf8(fileName)):
		window.fileName = QString.fromUtf8(fileName)
		window.openFileMain()
	window.show()
	sys.exit(app.exec_())

if __name__ == '__main__':
	if len(sys.argv) > 1:
		main(sys.argv[1])
	else:
		main("")
