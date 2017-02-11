# This file is part of ReText
# Copyright: 2014 Maurice van der Pot
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

from PyQt5.QtGui import QTextCursor

LARGER_THAN_ANYTHING = sys.maxsize

class Row:
	def __init__(self, block=None, text=None, separatorline=False, paddingchar=' '):
		self.block = block
		self.text = text
		self.separatorline = separatorline
		self.paddingchar = paddingchar

	def __repr__(self):
		return "<Row '%s' %s '%s'>" % (self.text, self.separatorline, self.paddingchar)

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
		for i, row in enumerate(rows):
			if i & 1 == 0: # i is even
				row.separatorline = True
				row.paddingchar = '=' if (i == 2) else '-'
				row.text = row.text.replace('+', '|')

	return rows, editedlineindex, offset

def _sortaUndoEdit(rows, editedlineindex, editsize):
	aftertext = rows[editedlineindex].text
	if editsize < 0:
		beforetext = ' ' * -editsize + aftertext
	else:
		beforetext = aftertext[editsize:]

	rows[editedlineindex].text = beforetext

def _determineRoomInCell(row, edge, shrinking, startposition=0):
	if edge >= len(row.text) or row.text[edge] != '|':
		room = LARGER_THAN_ANYTHING
	else:
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

	return room

def _performShift(row, rowShift, edge, shift):
	editlist = []

	if len(row.text) > edge and row.text[edge] == '|' and rowShift != shift:
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

def _determineNextEdge(rows, rowShifts, offset):
	nextedge = None
	for row, rowShift in zip(rows, rowShifts):
		if rowShift != 0:
			edge = row.text.find('|', offset)
			if edge != -1 and (nextedge is None or edge < nextedge):
				nextedge = edge
	return nextedge

def _determineEditLists(rows, editedlineindex, offset, editsize):
	rowShifts = [0 for _ in rows]
	rowShifts[editedlineindex] = editsize

	editLists = [[] for _ in rows]

	currentedge = _determineNextEdge(rows, rowShifts, offset)
	firstEdge = True


	while currentedge:

		if editsize < 0:
			leastLeftShift = min((-rowShift + _determineRoomInCell(row, currentedge, True)
				for row, rowShift in zip(rows, rowShifts)))

			shift = max(editsize, -leastLeftShift)
		else:
			if firstEdge:
				room = _determineRoomInCell(rows[editedlineindex], currentedge, False, offset)
				shift = max(0, editsize - room)

		for i, row in enumerate(rows):
			editList, newRowShift = _performShift(row, rowShifts[i], currentedge, shift)
			rowShifts[i] = newRowShift
			editLists[i].extend(editList)

		currentedge = _determineNextEdge(rows, rowShifts, currentedge + 1)
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
		rows, editedlineindex, offset = _getTableLines(doc, pos, markupClass)

		_sortaUndoEdit(rows, editedlineindex, editsize)

		editLists = _determineEditLists(rows, editedlineindex, offset, editsize)

		cursor = QTextCursor(doc)
		_performEdits(cursor, rows, editLists, editedlineindex, editsize)

def handleReturn(cursor, markupClass, newRow):
	if markupClass not in (MarkdownMarkup, ReStructuredTextMarkup):
		return False
	positionInBlock = cursor.positionInBlock()
	cursor.select(QTextCursor.BlockUnderCursor)
	oldLine = cursor.selectedText().lstrip('\u2029')
	if not ('| ' in oldLine or ' |' in oldLine):
		cursor.setPosition(cursor.block().position() + positionInBlock)
		return False
	indent = 0
	while oldLine[indent] in ' \t':
		indent += 1
	indentChars, oldLine = oldLine[:indent], oldLine[indent:]
	newLine = ''.join('|' if c in '+|' else ' ' for c in oldLine).rstrip()
	cursor.movePosition(QTextCursor.EndOfBlock)
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
