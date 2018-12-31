from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QGridLayout, QLabel, \
    QSpinBox


class TableWizardDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.parent = parent
        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.makeTable)
        buttonBox.rejected.connect(self.close)

        layout = QGridLayout(self)

        rowsLabel = QLabel(self.tr('Number of rows') + ':', self)
        columnsLabel = QLabel(self.tr('Number of columns') + ':', self)
        self.rowsSpinBox = QSpinBox(self)
        self.columnsSpinBox = QSpinBox(self)

        self.rowsSpinBox.setRange(1, 10)
        self.columnsSpinBox.setRange(1, 10)
        self.rowsSpinBox.setValue(3)
        self.columnsSpinBox.setValue(3)

        layout.addWidget(rowsLabel, 0, 0)
        layout.addWidget(self.rowsSpinBox, 0, 1, Qt.AlignRight)
        layout.addWidget(columnsLabel, 1, 0)
        layout.addWidget(self.columnsSpinBox, 1, 1, Qt.AlignRight)
        layout.addWidget(buttonBox, 2, 0, 1, 2)

    def makeTable(self):
        rowCount = self.rowsSpinBox.value()
        columnCount = self.columnsSpinBox.value()

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
