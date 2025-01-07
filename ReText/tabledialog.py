# This file is part of ReText
# Copyright: 2018 Changhee Kim, 2018-2024 Dmitry Shachnev
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

from markups import ReStructuredTextMarkup
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QGridLayout, QLabel, QSpinBox


class InsertTableDialog(QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setWindowTitle(self.tr('Insert table'))
        buttonBox = QDialogButtonBox(self)
        buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Ok |
                                     QDialogButtonBox.StandardButton.Cancel)
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
        layout.addWidget(self.rowsSpinBox, 0, 1, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(columnsLabel, 1, 0)
        layout.addWidget(self.columnsSpinBox, 1, 1, Qt.AlignmentFlag.AlignRight)
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

        # Activate the Table editing mode
        self.parent.actionTableMode.setChecked(True)
        tab.editBox.tableModeEnabled = True
