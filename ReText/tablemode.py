# vim: ts=4:sw=4:expandtab
#
# This file is part of ReText
# Copyright: 2014, 2017 Maurice van der Pot
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

import sys

from markups import MarkdownMarkup, ReStructuredTextMarkup
from PyQt6.QtGui import QTextCursor

LARGER_THAN_ANYTHING = sys.maxsize

class Row:
    def __init__(self, block=None, text=None, separatorline=False, paddingchar=' '):
        self.block = block
        self.text = text
        self.separatorline = separatorline
        self.paddingchar = paddingchar

    def __repr__(self):
        return f"<Row '{self.text}' {self.separatorline} '{self.paddingchar}'>"

def _getTableLines(doc, pos, markupClass):
    startblock = doc.findBlock(pos)
    editedlineindex = 0
    offset = pos - startblock.position()

    rows = [ Row(block = startblock,
                 text = startblock.text()) ]

    block = startblock.previous()
    while any(c in block.text() for c in '+|'):
        rows.insert(0, Row(block = block,
                           text = block.text()))
        editedlineindex += 1
        block = block.previous()

    block = startblock.next()
    while any(c in block.text() for c in '+|'):
        rows.append(Row(block = block,
                        text = block.text()))
        block = block.next()

    if markupClass == MarkdownMarkup:
        for i, row in enumerate(rows):
            if i == 1:
                row.separatorline = True
                row.paddingchar = '-'
    elif markupClass == ReStructuredTextMarkup:
        for row in rows:
            if row.text.strip().startswith(('+-','+=')):
                row.separatorline = True
                row.paddingchar = row.text.strip()[1]
                row.text = row.text.replace('+', '|')
    return rows, editedlineindex, offset

# Modify the edited line to put the table borders after the edition in their original positions.
# It does not matter that this function changes the position of table borders before the edition,
# because table editing mode only ever changes the table to the right of the cursor position.
def _sortaUndoEdit(rows, editedlineindex, offset, editsize):
    aftertext = rows[editedlineindex].text
    if editsize < 0:
        beforetext = ' ' * -editsize + aftertext
    else:
        beforetext = aftertext[:offset] + aftertext[offset + editsize:]

    rows[editedlineindex].text = beforetext

# Given text and the position of the n-th edge, returns n - 1
def _getEdgeIndex(text, edge):
    return text[:edge].count('|')

def _determineRoomInCell(row, edge, edgeIndex, shrinking, startposition=0):

    if len(row.text) > edge and row.text[edge] == '|' and \
       (not edgeIndex or _getEdgeIndex(row.text, edge) == edgeIndex):
        clearance = 0
        cellwidth = 0
        afterContent = True
        for i in range(edge - 1, startposition - 1, -1):
            if row.text[i] == '|':
                break
            else:
                if row.text[i] == row.paddingchar and afterContent:
                    clearance += 1
                else:
                    afterContent = False
                cellwidth += 1

        if row.separatorline:
            if shrinking:
                # do not shrink separator cells below 3
                room = max(0, cellwidth - 3)
            else:
                # start expanding the cell if only the space for a right-align marker is left
                room = max(0, cellwidth - 1)
        else:
            room = clearance
    else:
        room = LARGER_THAN_ANYTHING

    return room

# Add an edit for a row to match the specified shift if it has an edge on the
# specified position
def _performShift(row, rowShift, edge, edgeIndex, shift):
    editlist = []

    # Any row that has an edge on the specified position and that doesn't
    # already have edits that shift it 'shift' positions, will get an
    # additional edit
    if len(row.text) > edge and row.text[edge] == '|' and rowShift != shift and \
       (not edgeIndex or _getEdgeIndex(row.text, edge) == edgeIndex):
        editsize = -(rowShift - shift)
        rowShift = shift

        # Insert one position further to the left on separator lines, because
        # there may be a space (for esthetical reasons) or an alignment marker
        # on the last position before the edge and that should stay next to the
        # edge.
        if row.separatorline:
            edge -= 1

        editlist.append((edge, editsize))

    return editlist, rowShift

# Finds the next edge position starting at offset in any row that is shifting.
# Rows that are not shifting when we are searching for an edge starting at
# offset, are rows that (upto offset) did not have any edges that aligned with
# shifting edges on other rows.
def _determineNextEdge(rows, rowShifts, offset):
    nextedge = None
    nextedgerow = None

    for row, rowShift in zip(rows, rowShifts):
        if rowShift != 0:
            edge = row.text.find('|', offset)
            if edge != -1 and (nextedge is None or edge < nextedge):
                nextedge = edge
                nextedgerow = row

    return nextedge, _getEdgeIndex(nextedgerow.text, nextedge) if nextedge else None

# Return a list of edits to be made in other lines to adapt the table lines to
# a single edit in the edited line.
def _determineEditLists(rows, editedlineindex, offset, editsize, alignWithAnyEdge):

    # rowShift represents how much the characters on a line will shift as a
    # result of the already collected edits to be made.
    rowShifts = [0 for _ in rows]
    rowShifts[editedlineindex] = editsize

    editLists = [[] for _ in rows]

    # Find the next edge position on the edited row
    currentedge, currentedgeindex = _determineNextEdge(rows, rowShifts, offset)
    firstEdge = True


    while currentedge:

        if alignWithAnyEdge:
            # Ignore what column the edge belongs to
            currentedgeindex = None

        if editsize < 0:
            # How much an edge shifts to the left depends on how much room
            # there is in the cells on any row that shares this edge.
            leastLeftShift = min(
                -rowShift + _determineRoomInCell(row, currentedge, currentedgeindex, True)
                for row, rowShift in zip(rows, rowShifts)
            )

            shift = max(editsize, -leastLeftShift)
        else:
            # When shifting right, determine how much only once based on how
            # much the edited cell needs to expand
            if firstEdge:
                room = _determineRoomInCell(
                    rows[editedlineindex],
                    currentedge,
                    currentedgeindex,
                    False,
                    offset,
                )
                shift = max(0, editsize - room)

        for i, row in enumerate(rows):
            editList, newRowShift = _performShift(
                row,
                rowShifts[i],
                currentedge,
                currentedgeindex,
                shift,
            )
            rowShifts[i] = newRowShift
            editLists[i].extend(editList)

        currentedge, currentedgeindex = _determineNextEdge(rows, rowShifts, currentedge + 1)
        firstEdge = False

    return editLists

def _performEdits(cursor, rows, editLists, linewithoffset, offset):
    cursor.joinPreviousEditBlock()
    for i, (row, editList) in enumerate(zip(rows, editLists)):

        for editpos, editsize in sorted(editList, reverse=True):

            if i == linewithoffset:
                editpos += offset

            cursor.setPosition(row.block.position() + editpos)
            if editsize > 0:
                cursor.insertText(editsize * row.paddingchar)
            else:
                for _ in range(-editsize):
                    cursor.deletePreviousChar()
    cursor.endEditBlock()

def adjustTableToChanges(doc, pos, editsize, markupClass):
    if markupClass in (MarkdownMarkup, ReStructuredTextMarkup):

        # This is needed because in ReSt cells can span multiple columns
        # and we can therefore not determine which edges in other rows
        # are supposed to be aligned with the edges in the edited row.
        alignWithAnyEdge = (markupClass == ReStructuredTextMarkup)

        rows, editedlineindex, offset = _getTableLines(doc, pos, markupClass)

        _sortaUndoEdit(rows, editedlineindex, offset, editsize)

        editLists = _determineEditLists(rows, editedlineindex, offset, editsize, alignWithAnyEdge)

        cursor = QTextCursor(doc)
        _performEdits(cursor, rows, editLists, editedlineindex, editsize)

def handleReturn(cursor, markupClass, newRow):
    if markupClass not in (MarkdownMarkup, ReStructuredTextMarkup):
        return False
    positionInBlock = cursor.positionInBlock()
    cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
    oldLine = cursor.selectedText().lstrip('\u2029')
    if not ('| ' in oldLine or ' |' in oldLine):
        cursor.setPosition(cursor.block().position() + positionInBlock)
        return False
    indent = 0
    while oldLine[indent] in ' \t':
        indent += 1
    indentChars, oldLine = oldLine[:indent], oldLine[indent:]
    newLine = ''.join('|' if c in '+|' else ' ' for c in oldLine).rstrip()
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    if newRow and markupClass == MarkdownMarkup:
        sepLine = ''.join(c if c in ' |' else '-' for c in oldLine)
        cursor.insertText('\n' + indentChars + sepLine)
    elif newRow:
        sepLine = ''.join('+' if c in '+|' else '-' for c in oldLine)
        cursor.insertText('\n' + indentChars + sepLine)
    cursor.insertText('\n' + indentChars + newLine)
    positionInBlock = min(positionInBlock, len(indentChars + newLine))
    cursor.setPosition(cursor.block().position() + positionInBlock)
    return True
