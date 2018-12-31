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

        self.configurators = {}
        layout = QGridLayout(self)

        label_row = QLabel('Row:', self)
        label_column = QLabel('Column:', self)
        self.configurators['tableDefaultRowCount'] = QSpinBox(self)
        self.configurators['tableDefaultColumnCount'] = QSpinBox(self)

        self.configurators['tableDefaultRowCount'].setRange(1, 10)
        self.configurators['tableDefaultColumnCount'].setRange(1, 10)
        self.configurators['tableDefaultRowCount'].setValue(3)
        self.configurators['tableDefaultColumnCount'].setValue(3)

        layout.addWidget(label_row, 0, 0)
        layout.addWidget(self.configurators['tableDefaultRowCount'], 0, 1, Qt.AlignRight)
        layout.addWidget(label_column, 1, 0)
        layout.addWidget(self.configurators['tableDefaultColumnCount'], 1, 1, Qt.AlignRight)
        layout.addWidget(buttonBox, 2, 0, 1, 2)

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
