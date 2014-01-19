# vim: noexpandtab:ts=4:sw=4
# This file is part of ReText
# Copyright: Maurice van der Pot 2014
# License: GNU GPL v2 or higher

import unittest
from ReText import tablemode


class TestTableMode(unittest.TestCase):

	def checkDetermineEditLists(self, paddingChars, before, edit, after):
		class Row():
			def __init__(self, text, separatorLine, paddingChar):
				self.text = text
				self.separatorline = separatorLine
				self.paddingchar = paddingChar


		# Do some sanity checks on the test data to catch simple mistakes
		self.assertEqual(len(paddingChars), len(before),
		                 'The number of padding chars should be equal to the number of rows')
		self.assertEqual(len(before), len(after),
		                 'The number of rows before and after should be the same')
		# Apart from spacing edit only contains a's or d's 
		self.assertTrue(edit[1].strip(' d') == '' or
		                edit[1].strip(' a') == '',
						"An edit should be a sequence of a's or d's surrounded by spaces")

		rows = []
		for paddingChar, text in zip(paddingChars, before):
			rows.append(Row(text, (paddingChar != ' '), paddingChar))


		editline = edit[0]
		editstripped = edit[1].lstrip()
		offset = len(edit[1]) - len(editstripped)
		try:
			editsize = editstripped.index(' ')
		except ValueError:
			editsize = len(editstripped)
		if editstripped[0] == 'd':
			editsize = -editsize


		editLists = tablemode._determineEditLists(rows, edit[0], offset, editsize)
		editedRows = []

		self.assertEqual(len(editLists), len(rows))

		for i, (row, editList) in enumerate(zip(rows, editLists)):
			editedText = row.text

			if i == editline:
				if editsize < 0:
					editedText = editedText[:offset] + editedText[offset - editsize:]
				else:
					editedText = editedText[:offset] + editstripped.rstrip() + editedText[offset:]

			for editEntry in editList:
				editOffset = editEntry[0]

				if i == editline:
					editOffset += editsize

				if editEntry[1] < 0:
					editedText = editedText[:editOffset + editEntry[1]] + editedText[editOffset:]
				else:
					editedText = editedText[:editOffset] + editEntry[1] * row.paddingchar + editedText[editOffset:]
			editedRows.append(editedText)

		if editedRows != after:
			assertMessage = ["Output differs.",
							 "",
							 "Input:"] + \
							["%3d '%s'" % (i, line) for i, line in enumerate(before)] + \
							["",
							 "Edit:",
							 "%3d '%s'" % edit,
							 "",
							 "Expected output:"] + \
							["%3d '%s'" % (i, line) for i, line in enumerate(after)] + \
							["",
							 "Actual output:"] + \
							["%3d '%s'" % (i, line) for i, line in enumerate(editedRows)]

			self.fail('\n'.join(assertMessage))

	def test_simpleInsert(self):
		# Insert at the start of a cell so it doesn't need to grow
		separatorChars = '  '
		before  = ['|    |',
		           '|    |']

		edit = (0, ' a   ')

		after   = ['|a   |',
		           '|    |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert at the last position in a cell where it doesn't need to grow
		separatorChars = '  '
		before  = ['|    |',
		           '|    |']

		edit = (0, '    a')

		after   = ['|   a|',
		           '|    |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert at the end of a cell so it will have to grow
		separatorChars = '  '
		before  = ['|    |',
		           '|    |']

		edit = (0, '     a')

		after   = ['|    a|',
		           '|     |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

	def test_insertPushAhead(self):

		# Insert with enough room to push without growing the cell
		separatorChars = '  '
		before  = ['|  x |',
		           '|    |']

		edit = (0, ' a    ')

		after   = ['|a  x|',
		           '|    |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert without enough room to push, so the cell will have to grow
		separatorChars = '  '
		before  = ['|   x|',
		           '|    |']

		edit = (0, ' a    ')

		after   = ['|a   x|',
		           '|     |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert multiple characters forcing a partial grow
		separatorChars = '  '
		before  = ['|    |',
		           '|    |']

		edit = (0, '  aaaaaa')

		after   = ['| aaaaaa|',
		           '|       |']

		# Insert multiple characters forcing a partial grow through pushing other chars ahead
		separatorChars = '  '
		before  = ['| bb   |',
		           '|      |']

		edit = (0, '  aaaaaaa')

		after   = ['| aaaaaaabb|',
		           '|          |']


		self.checkDetermineEditLists(separatorChars, before, edit, after)

	def test_insertInSeparatorCell(self):

		# Insert in a cell on a separator line
		separatorChars = ' -'
		before  = ['|    |',
		           '|----|']

		edit = (1, '   a  ')

		after   = ['|    |',
		           '|--a-|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert in a cell on a separator line forcing it to grow
		separatorChars = ' -'
		before  = ['|    |',
		           '|----|']

		edit = (1, '    a ')

		after   = ['|     |',
		           '|---a-|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert in a cell on a separator line with an alignment marker
		separatorChars = ' -'
		before  = ['|    |',
		           '|---:|']

		edit = (1, '   a ')

		after   = ['|    |',
		           '|--a:|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert in a cell on a separator line with an alignment marker forcing it to grow
		separatorChars = ' -'
		before  = ['|    |',
		           '|---:|']

		edit = (1, '    a ')

		after   = ['|     |',
		           '|---a:|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert in a cell on a separator line after the alignment marker forcing it to grow
		separatorChars = ' -'
		before  = ['|    |',
		           '|---:|']

		edit = (1, '     a')

		after   = ['|     |',
		           '|---:a|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

	def test_insertAboveSeparatorLine(self):
		# Insert on another line, without growing the cell
		separatorChars = ' -'
		before  = ['|    |',
		           '|----|']

		edit = (0, '    a')

		after   = ['|   a|',
		           '|----|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert on another line, forcing the separator cell to grow
		separatorChars = ' -'
		before  = ['|    |',
		           '|----|']

		edit = (0, '     a')

		after   = ['|    a|',
		           '|-----|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert on another line, without growing the cell with alignment marker
		separatorChars = ' -'
		before  = ['|    |',
		           '|---:|']

		edit = (0, '    a')

		after   = ['|   a|',
		           '|---:|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert on another line, forcing the separator cell with alignment marker to grow
		separatorChars = ' -'
		before  = ['|    |',
		           '|---:|']

		edit = (0, '     a')

		after   = ['|    a|',
		           '|----:|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Insert on another line, forcing the separator cell that ends with a regular char to grow
		separatorChars = ' -'
		before  = ['|    |',
		           '|--- |']

		edit = (0, '     a')

		after   = ['|    a|',
		           '|---- |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

	def test_insertCascade(self):
		# Test if growing of cells cascades onto other lines through edges that are shifted
		separatorChars = '    '
		before  = ['|    |',
		           '     |    |',
				   '          |    |',
				   '     |']

		edit = (0, '     a')

		after   = ['|    a|',
		           '      |    |',
				   '           |    |',
				   '      |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Test if growing of cells cascades onto other lines but does not affect unconnected edges
		separatorChars = '   '
		before  = ['|    |',
		           '     |    |',
				   '       |  |    |']

		edit = (0, '     a')

		after   = ['|    a|',
		           '      |    |',
				   '       |   |    |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

	def test_simpleDelete(self):
		# Delete at start of cell
		separatorChars = '  '
		before  = ['|abcd|',
		           '|    |']

		edit = (0, ' d   ')

		after   = ['|bcd|',
		           '|   |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Delete at end of cell
		separatorChars = '  '
		before  = ['|abcd|',
		           '|    |']

		edit = (0, '    d')

		after   = ['|abc|',
		           '|   |']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

	def test_deleteShrinking(self):
		# Shrinking limited by cell on other row
		separatorChars = '  '
		before  = ['|abc |',
		           '|efgh|']

		edit = (0, ' d  ')

		after   = ['|bc  |',
		           '|efgh|']

		# Shrinking limited by cell on other row (cont'd)
		separatorChars = '  '
		before  = ['|abcd|',
		           '|efgh|']

		edit = (0, '    d')

		after   = ['|abc |',
		           '|efgh|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Shrinking of next cell limited by cell on other row
		separatorChars = '  '
		before  = ['|abc |    |',
		           '|efghijklm|']

		edit = (0, ' d  ')

		after   = ['|bc |     |',
		           '|efghijklm|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Shrink current cell fully, shrink next cell partially
		separatorChars = '  '
		before  = ['| aabb|    |',
		           '|xxxxxxxx  |']

		edit = (0, '  dddd')

		after   = ['| |      |',
		           '|xxxxxxxx|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

	def test_deleteShrinkingSeparatorRow(self):
		# Shrinking not limited by size of separator cell
		separatorChars = ' -'
		before  = ['|abcd|',
		           '|----|']

		edit = (0, '  d ')

		after   = ['|acd|',
		           '|---|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Shrinking limited by size of separator cell
		separatorChars = ' -'
		before  = ['|abc|',
		           '|---|']

		edit = (0, '  d  ')

		after   = ['|ac |',
		           '|---|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Shrinking not limited by size of separator cell with alignment markers
		separatorChars = ' -'
		before  = ['|abcd|',
		           '|:--:|']

		edit = (0, '  d ')

		after   = ['|acd|',
		           '|:-:|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Shrinking limited by size of separator cell with alignment markers
		separatorChars = ' -'
		before  = ['|abc|',
		           '|:-:|']

		edit = (0, '  d  ')

		after   = ['|ac |',
		           '|:-:|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

		# Shrinking partially limited by size of separator cell with alignment markers
		separatorChars = ' -'
		before  = ['|abcde|',
		           '|:---:|']

		edit = (0, '  dddd')

		after   = ['|a  |',
		           '|:-:|']

		self.checkDetermineEditLists(separatorChars, before, edit, after)

if __name__ == '__main__':
	unittest.main()
