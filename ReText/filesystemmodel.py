# This file is part of ReText
# Copyright: 2024-2025 Dmitry Shachnev
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

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFileSystemModel


class ReTextFileSystemModel(QFileSystemModel):

    def data(self, index, role):
        # Show file name in tooltip
        if role == Qt.ItemDataRole.ToolTipRole:
            role = QFileSystemModel.Roles.FileNameRole
        return super().data(index, role)
