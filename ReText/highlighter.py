# This file is part of ReText
# Copyright: 2012-2025 Dmitry Shachnev
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

import re
from enum import IntFlag, auto

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat

from ReText.editor import getColor

reFencedCodeStart = re.compile(r'^(`{3,})(\w+)?\s*$')
reFencedCodeEnd = re.compile(r'^`{3,}\s*$')
reHtmlTags     = re.compile('<[^<>@]*>')
reHtmlSymbols  = re.compile(r'&#?\w+;')
reHtmlStrings  = re.compile('"[^"<]*"(?=[^<]*>)')
reHtmlComments = re.compile('<!--[^<>]*-->')
reAsterisks    = re.compile(r'(?<!\*)\*[^ \*][^\*]*\*')
reUnderline    = re.compile(r'(?<!_|\w)_[^_]+_(?!\w)')
reDblAsterisks = re.compile(r'(?<!\*)\*\*((?!\*\*).)*\*\*')
reDblUnderline = re.compile(r'(?<!_|\w)__[^_]+__(?!\w)')
reTrpAsterisks = re.compile(r'\*{3,3}[^\*]+\*{3,3}')
reTrpUnderline = re.compile('___[^_]+___')
reMkdHeaders   = re.compile('^#.+')
reMkdLinksImgs = re.compile(r'(?<=\[)[^\[\]]*(?=\])')
reMkdLinkRefs  = re.compile(r'(?<=\]\()[^\(\)]*(?=\))')
reBlockQuotes  = re.compile('^ *>.+')
reReSTDirects  = re.compile(r'\.\. [a-z]+::')
reReSTRoles    = re.compile('(:[a-z-]+:)(`.+?`)')
reReSTLinks    = re.compile('(`.+?<)(.+?)(>`__?)')
reReSTLinkRefs = re.compile(r'\.\. _`?(.*?)`?: (.*)')
reReSTFldLists = re.compile('^ *:(.*?):')
reTextileHdrs  = re.compile(r'^h[1-6][()<>=]*\.\s.+')
reTextileQuot  = re.compile(r'^bq\.\s.+')
reMkdCodeSpans = re.compile('`[^`]*`')
reMkdMathSpans = re.compile(r'\\[\(\[].*?\\[\)\]]')
reReSTCodeSpan = re.compile('``.+?``')
reWords        = re.compile('[^_\\W]+')
reSpacesOnEnd  = re.compile(r'\s+$')
reADocHeaders  = re.compile('^={1,5} .*')
reADocConsBold = re.compile(r'(?<!\w|\*)\*[^\*]+\*(?!\w|\*)')
reADocConsItal = re.compile(r'(?<!\w|_)_[^_]+_(?!\w|_)')
reADocUnCnItal = re.compile('__[^_]+__')
reADocConsCode = re.compile(r'(?<!\w|`)`[^`]+`(?!\w|`)')
reADocLinks    = re.compile(r'(https?://[^ ]+)(\[[^\]]+\])')
reADocDocAttr  = re.compile('^:.+?:')
reADocBlckAttr = re.compile(r'^\[.+?\]$')


class Formatter:
    def __init__(self, funcs=None):
        self._funcs = funcs or []

    def __or__(self, other):
        result = Formatter(self._funcs.copy())
        if isinstance(other, Formatter):
            result._funcs.extend(other._funcs)
        elif isinstance(other, QFont.Weight):
            result._funcs.append(lambda f: f.setFontWeight(other))
        return result

    def format(self, charFormat):
        for func in self._funcs:
            func(charFormat)

NF = Formatter()
ITAL = Formatter([lambda f: f.setFontItalic(True)])
UNDL = Formatter([lambda f: f.setFontUnderline(True)])

Weight = QFont.Weight

def FG(colorName):
    def func(f):
        return f.setForeground(getColor(colorName))
    return Formatter([func])

def QString_length(text):
    # In QString, surrogate pairs are represented using multiple QChars,
    # so the length of QString is not always equal to the number of graphemes
    # in it (which is the case with Python strings).
    return sum(2 if ord(char) > 65535 else 1 for char in text)


class Markup(IntFlag):
    Mkd = auto()
    ReST = auto()
    Textile = auto()
    ADoc = auto()
    HTML = auto()

    # Special value which means that no other markup is allowed inside this pattern
    CodeSpan = auto()


docTypesMapping = {
    'Markdown': Markup.Mkd,
    'reStructuredText': Markup.ReST,
    'Textile': Markup.Textile,
    'asciidoc': Markup.ADoc,
    'html': Markup.HTML,
}


class ReTextHighlighter(QSyntaxHighlighter):
    dictionaries = None
    docType = None

    patterns = (
        # regex,         color,                                markups
        (reMkdCodeSpans, FG('codeSpans'),                      Markup.Mkd | Markup.CodeSpan),
        (reMkdMathSpans, FG('codeSpans'),                      Markup.Mkd | Markup.CodeSpan),
        (reReSTCodeSpan, FG('codeSpans'),                      Markup.ReST | Markup.ADoc | Markup.CodeSpan),  # noqa: E501
        (reHtmlTags,     FG('htmlTags') | Weight.Bold,         Markup.Mkd | Markup.Textile | Markup.HTML),
        (reHtmlSymbols,  FG('htmlSymbols') | Weight.Bold,      Markup.Mkd | Markup.HTML),
        (reHtmlStrings,  FG('htmlStrings') | Weight.Bold,      Markup.Mkd | Markup.HTML),
        (reHtmlComments, FG('htmlComments'),                   Markup.Mkd | Markup.HTML),
        (reAsterisks,    ITAL,                                 Markup.Mkd | Markup.ReST),
        (reUnderline,    ITAL,                                 Markup.Mkd | Markup.Textile),
        (reDblAsterisks, NF | Weight.Bold,                     Markup.Mkd | Markup.ReST | Markup.Textile | Markup.ADoc),  # noqa: E501
        (reDblUnderline, NF | Weight.Bold,                     Markup.Mkd),
        (reTrpAsterisks, ITAL | Weight.Bold,                   Markup.Mkd),
        (reTrpUnderline, ITAL | Weight.Bold,                   Markup.Mkd),
        (reMkdHeaders,   FG('markdownHeaders') | Weight.Black, Markup.Mkd),
        (reMkdLinksImgs, FG('markdownLinks'),                  Markup.Mkd),
        (reMkdLinkRefs,  ITAL | UNDL,                          Markup.Mkd),
        (reBlockQuotes,  FG('blockquotes'),                    Markup.Mkd),
        (reReSTDirects,  FG('restDirectives') | Weight.Bold,   Markup.ReST),
        (reReSTRoles,    NF, FG('restRoles') | Weight.Bold, FG('htmlStrings'), Markup.ReST),
        (reTextileHdrs,  NF | Weight.Black,                    Markup.Textile),
        (reTextileQuot,  FG('blockquotes'),                    Markup.Textile),
        (reAsterisks,    NF | Weight.Bold,                     Markup.Textile),
        (reDblUnderline, ITAL,                                 Markup.Textile),
        (reReSTLinks,    NF, NF, ITAL | UNDL, NF,              Markup.ReST),
        (reReSTLinkRefs, NF, FG('markdownLinks'), ITAL | UNDL, Markup.ReST),
        (reReSTFldLists, NF, FG('restDirectives'),             Markup.ReST),
        (reADocHeaders,  FG('markdownHeaders') | Weight.Black, Markup.ADoc),
        (reADocConsBold, NF | Weight.Bold,                     Markup.ADoc),
        (reADocConsItal, ITAL,                                 Markup.ADoc),
        (reADocUnCnItal, ITAL,                                 Markup.ADoc),
        (reADocConsCode, FG('codeSpans'),                      Markup.ADoc | Markup.CodeSpan),
        (reADocLinks,    FG('markdownLinks'), ITAL | UNDL,     Markup.ADoc),
        (reADocDocAttr,  FG('htmlTags'),                       Markup.ADoc),
        (reADocBlckAttr, FG('htmlTags'),                       Markup.ADoc),
    )

    def highlightBlock(self, text):
        # If inside fenced code block (not the fence line)
        if self.docType == 'Markdown' and self.previousBlockState() == 1:
            fmt = QTextCharFormat()
            fmt.setFontItalic(True)

            # Check if this line closes fenced block
            if reFencedCodeEnd.match(text):
                # Fence closes: highlight fence line in yellowgreen (codeSpans)
                fmt.setForeground(getColor('codeSpans'))  # fence color yellowgreen
                self.setFormat(0, len(text), fmt)
                self.setCurrentBlockState(0)
            else:
                # Inside fenced code: highlight in orange (codeBlock)
                fmt.setForeground(getColor('codeBlock'))  # code block content color orange
                self.setFormat(0, len(text), fmt)
                self.setCurrentBlockState(1)
            return

        # If this line is a fence opening line (3+ backticks with optional lang)
        if self.docType == 'Markdown' and reFencedCodeStart.match(text):
            fmt = QTextCharFormat()
            fmt.setForeground(getColor('codeSpans'))  # fence color yellowgreen
            fmt.setFontItalic(True)
            self.setFormat(0, len(text), fmt)
            self.setCurrentBlockState(1)
            return

        # Otherwise, normal highlighting for text outside fenced blocks
        self.setCurrentBlockState(0)

        codeSpans = set()
        if self.docType in docTypesMapping:
            markup = docTypesMapping[self.docType]
            for pattern, *formatters, markups in self.patterns:
                if not (markup & markups):
                    continue
                for match in pattern.finditer(text):
                    start, end = match.start(), match.end()
                    if markups & Markup.CodeSpan:
                        codeSpans.add((start, end))
                    elif any(start < codeEnd and end > codeStart
                             for codeStart, codeEnd in codeSpans):
                        # Ignore any syntax if its match intersects with code spans.
                        # See https://github.com/retext-project/retext/issues/529
                        continue
                    for i, formatter in enumerate(formatters):
                        charFormat = QTextCharFormat()
                        formatter.format(charFormat)
                        self.setFormat(QString_length(text[:match.start(i)]),
                                       QString_length(match.group(i)),
                                       charFormat)
        for match in reSpacesOnEnd.finditer(text):
            charFormat = QTextCharFormat()
            charFormat.setBackground(getColor('whitespaceOnEnd'))
            self.setFormat(QString_length(text[:match.start()]),
                           QString_length(match.group(0)),
                           charFormat)
        # Spell checker
        if self.dictionaries:
            charFormat = QTextCharFormat()
            charFormat.setUnderlineColor(Qt.GlobalColor.red)
            charFormat.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
            for match in reWords.finditer(text):
                finalFormat = QTextCharFormat()
                finalFormat.merge(charFormat)
                finalFormat.merge(self.format(match.start()))
                word = match.group(0)
                correct = any(dictionary.check(word) for dictionary in self.dictionaries)
                if not correct:
                    self.setFormat(QString_length(text[:match.start()]),
                                   QString_length(word),
                                   finalFormat)
