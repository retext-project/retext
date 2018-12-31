from markups import ReStructuredTextMarkup
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QGridLayout, QLabel, \
    QSpinBox


class InsertTableDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setWindowTitle(self.tr('Insert table'))
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
        rowsCount = self.rowsSpinBox.value()
        columnsCount = self.columnsSpinBox.value() + 1

        tab = self.parent.currentTab
        cursor = tab.editBox.textCursor()

        tableCode = '' if cursor.atBlockStart() else '\n\n'
        if tab.activeMarkupClass == ReStructuredTextMarkup:
            # Insert reStructuredText grid table
            tableCode += '-----'.join('+' * columnsCount) + '\n'
            tableCode += '     '.join('|' * columnsCount) + '\n'
            tableCode += '====='.join('+' * columnsCount) + '\n'
            tableCode += ('     '.join('|' * columnsCount) + '\n' +
                          '-----'.join('+' * columnsCount) + '\n') * rowsCount
        else:
            # Insert Markdown table
            tableCode += '     '.join('|' * columnsCount) + '\n'
            tableCode += '-----'.join('|' * columnsCount) + '\n'
            tableCode += ('     '.join('|' * columnsCount) + '\n') * rowsCount

        cursor.insertText(tableCode)
        self.close()
