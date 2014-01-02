# vim: noexpandtab:ts=4:sw=4
# This file is part of ReText
# Copyright: Maurice van der Pot 2014
# License: GNU GPL v2 or higher

import sys
from ReText import QtGui, DOCTYPE_MARKDOWN, DOCTYPE_REST

QTextCursor = QtGui.QTextCursor

LARGER_THAN_ANYTHING = sys.maxsize

class Row:
	def __init__(self, shift=0, block=None, text=None, editlist=None, separatorline=False, paddingchar=' '):
		self.shift = shift
		self.block = block
		self.text = text
		self.editlist = editlist if editlist else []
		self.separatorline = separatorline
		self.paddingchar = paddingchar

	def __repr__(self):
		return "<Row '%s' %s %s '%s' %s>" % (self.text, self.shift,
			self.separatorline, self.paddingchar, self.editlist)

def _getTableLines(doc, pos, editsize, docType):
	startblock = doc.findBlock(pos)
	editedlineindex = 0
	offset = pos - startblock.position()

	starttext = startblock.text()
	if editsize < 0:
		starttext = ' ' * -editsize + starttext
	else:
		starttext = starttext[editsize:]

	rows = [ Row(shift = editsize,
	             block = startblock,
	             text = starttext) ]

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

	if docType == DOCTYPE_MARKDOWN:
		for i, row in enumerate(rows):
			if i == 1:
				row.separatorline = True
				row.paddingchar = '-'
	elif docType == DOCTYPE_REST:
		for i, row in enumerate(rows):
			if i & 1 == 0: # i is even
				row.separatorline = True
				row.paddingchar = '=' if (i == 2) else '-'
				row.text = row.text.replace('+', '|')

	return rows, editedlineindex, offset

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
				# do not shrink separator cells below 4
				room = max(0, cellwidth - 4)
			else:
				# start expanding the cell if only the space for a right-align marker is left
				room = max(0, cellwidth - 1)
		else:
			room = clearance

	return room

def _performShift(row, edge, shift):
	editlist = []

	if len(row.text) > edge and row.text[edge] == '|' and row.shift != shift:
		editsize = -(row.shift - shift)
		row.shift = shift

		if row.separatorline and row.text[edge - 1] == ':':
			edge -= 1

		editlist.append((edge, editsize))

	return editlist

def _determineNextEdge(rows, offset):
	nextedge = None
	for row in rows:
		if row.shift != 0:
			edge = row.text.find('|', offset)
			if edge != -1 and (nextedge == None or edge < nextedge):
				nextedge = edge
	return nextedge

def _performEdits(rows, linewithoffset, offset):
	cursor = QTextCursor(rows[0].block)
	cursor.beginEditBlock()
	for i, row in enumerate(rows):

		for editpos, editsize in sorted(row.editlist, reverse=True):

			if i == linewithoffset:
				editpos += offset

			cursor.setPosition(row.block.position() + editpos)
			if editsize > 0:
				cursor.insertText(editsize * row.paddingchar)
			else:
				for _ in range(-editsize):
					cursor.deletePreviousChar()
	cursor.endEditBlock()

def adjustTableToChanges(doc, pos, editsize, docType):
	if docType in (DOCTYPE_MARKDOWN, DOCTYPE_REST):
		rows, editedlineindex, offset = _getTableLines(doc, pos, editsize, docType)

		currentedge = _determineNextEdge(rows, offset)
		firstEdge = True

		while currentedge:

			if editsize < 0:
				leastLeftShift = min((-row.shift + _determineRoomInCell(row, currentedge, True)
					for row in rows))

				shift = max(editsize, -leastLeftShift)
			else:
				if firstEdge:
					room = _determineRoomInCell(rows[editedlineindex], currentedge, False, offset)
					shift = max(0, editsize - room)

			for row in rows:
				row.editlist.extend(_performShift(row, currentedge, shift))

			currentedge = _determineNextEdge(rows, currentedge + 1)
			firstEdge = False

		_performEdits(rows, editedlineindex, editsize)
