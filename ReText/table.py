from ReText import globalSettings
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTabWidget, \
    QDialogButtonBox, QWidget, QGridLayout, QLabel, QSpinBox


class ClickableLabel(QLabel):
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class TableWizardDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.layout = QVBoxLayout(self)
        self.tabWidget = QTabWidget(self)
        self.layout.addWidget(self.tabWidget)
        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok | 
            QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.makeTable)
        buttonBox.rejected.connect(self.close)
        self.initWidgets()
        self.layout.addWidget(buttonBox)

    def initWidgets(self):
        self.configurators = {}
        tabTitle = 'Table'

        page = self.getPageWidget()
        self.tabWidget.addTab(page, tabTitle)
	
    def getPageWidget(self):
        page = QWidget(self)
        layout = QGridLayout(page)
        
        label_row = ClickableLabel('Row:', self)
        label_column = ClickableLabel('Column:', self)
        self.configurators['tableDefaultRowCount'] = QSpinBox(self)
        self.configurators['tableDefaultColumnCount'] = QSpinBox(self)
		
        self.configurators['tableDefaultRowCount'].setRange(1,10)
        self.configurators['tableDefaultColumnCount'].setRange(1,10)
        self.configurators['tableDefaultRowCount'].setValue(3)				# tableDefaultRowCount
        self.configurators['tableDefaultColumnCount'].setValue(3)			# tableDefaultColumnCount

        layout.addWidget(label_row, 0, 0)
        layout.addWidget(self.configurators['tableDefaultRowCount'], 0, 1, Qt.AlignRight)
        layout.addWidget(label_column, 1, 0)
        layout.addWidget(self.configurators['tableDefaultColumnCount'], 1, 1, Qt.AlignRight)
        
        return page

    def makeTable(self):
        rowCount = self.configurators['tableDefaultRowCount'].value()
        columnCount = self.configurators['tableDefaultColumnCount'].value()
	

        # Table column's name section (table Header)
        tableHeader = ''
        for column in range(columnCount):
            tableHeader += '|    '
        tableHeader += '|\n'

        for column in range(columnCount):
            tableHeader += '|----'
        tableHeader += '|\n'
        self.parent.currentTab.editBox.insertPlainText(tableHeader)


        # Table Content section (table body)		
        for row in range(rowCount):
            tableBody = ''
            for column in range(columnCount):
                tableBody += '|    '
            tableBody += '|\n'
            self.parent.currentTab.editBox.insertPlainText(tableBody)
        self.close()

