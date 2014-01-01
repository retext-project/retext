# vim: noexpandtab:ts=4:sw=4
# This file is part of ReText
# Copyright: Maurice van der Pot 2014
# License: GNU GPL v2 or higher

from ReText import QtGui

QTextCursor = QtGui.QTextCursor

def _reconstructLineBeforeEdit(text, relpos, editsize):
	if editsize < 0:
		insertpos = text.find('|', relpos)
		if insertpos == -1:
			insertpos = relpos
		textbeforeedit = text[:insertpos] + -editsize * ' ' + text[insertpos:]
	else:
		textbeforeedit = text[:relpos] + text[relpos + editsize:]
	return textbeforeedit

def _getTableLines(doc, pos, editsize):
	startblock = doc.findBlock(pos)
	editedlineindex = 0
	offset = pos - startblock.position()

	starttext = startblock.text()
	if editsize < 0:
		starttext = ' ' * -editsize + starttext
	else:
		starttext = starttext[editsize:]

	rows = [ { 'shift' : editsize,
			   'block' : startblock,
			   'line' : starttext,
			   'editlist' : []} ]

	block = startblock.previous()
	while '|' in block.text():
		rows.insert(0, { 'shift' : 0,
						  'block' : block,
						  'line'  : block.text(),
						  'editlist' : [] })
		editedlineindex += 1
		block = block.previous()

	block = startblock.next()
	while '|' in block.text():
		rows.append({ 'shift' : 0,
					  'block' : block,
					  'line'  : block.text(),
					  'editlist' : [] })
		block = block.next()

	return rows, editedlineindex, offset

def _determineRoomInCell(row, edge, separatorline, startposition=0):
	if edge >= len(row['line']) or row['line'][edge] != '|':
		room = 9999
	else:
		clearance = 0
		cellwidth = 0
		afterContent = True
		for i in range(edge - 1, startposition - 1, -1):
			if row['line'][i] == '|':
				break
			else:
				if row['line'][i] == ' ' and afterContent:
					clearance += 1
				else:
					afterContent = False
				cellwidth += 1

		if separatorline:
			room = max(0, cellwidth - 4)
		else:
			room = clearance

	return room
		

def _performShift(row, edge, separatorLine, shift):
	editList = []

	if len(row['line']) > edge and row['line'][edge] == '|' and row['shift'] != shift:
		editsize = -(row['shift'] - shift)
		row['shift'] = shift

		line = row['line']
		if separatorLine and line[edge - 1] == ':':
			edge -= 1

		editList.append([edge, editsize])

	return editList

def _determineNextEdge(rows, offset):
	nextedge = None
	for row in rows:
		if row['shift'] != 0:
			edge = row['line'].find('|', offset)
			if edge != -1 and (nextedge == None or edge < nextedge):
				nextedge = edge
	return nextedge

def _performEdits(rows, linewithoffset, offset):
	cursor = QTextCursor(rows[0]['block'])
	cursor.beginEditBlock()
	for i, row in enumerate(rows):
		if i == 1:
			paddingchar = '-'
		else:
			paddingchar = ' '

		for editpos, editsize in sorted(row['editlist'], reverse=True):

			if i == linewithoffset:
				editpos += offset

			cursor.setPosition(row['block'].position() + editpos)
			if editsize > 0:
				cursor.insertText(editsize * paddingchar)
			else:
				for _ in range(-editsize):
					cursor.deletePreviousChar()
	cursor.endEditBlock()


def adjustTableToChanges(doc, pos, editsize):
	rows, editedlineindex, offset = _getTableLines(doc, pos, editsize)

	currentedge = _determineNextEdge(rows, offset)

	firstEdge = True

	# code currently only for left shifts
	while currentedge:

		if editsize < 0:
			leastLeftShift = 9999
			for i, row in enumerate(rows):
				leastLeftShift = min(leastLeftShift, -row['shift'] + _determineRoomInCell(row, currentedge, i == 1))
			
			shift = max(editsize, -leastLeftShift)
		else:
			if firstEdge:
				room = _determineRoomInCell(rows[editedlineindex], currentedge, editedlineindex == 1, offset)
				shift = max(0, editsize - room)

		for i, row in enumerate(rows):
			row['editlist'].extend(_performShift(row, currentedge, i == 1, shift))

		currentedge = _determineNextEdge(rows, currentedge + 1)
		firstEdge = False

	_performEdits(rows, editedlineindex, editsize)

