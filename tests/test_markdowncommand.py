# This file is part of ReText
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys

import pytest

from ReText import markdowncommand


def test_convert_with_system_markdown_extracts_body_and_title():
    command = [
        sys.executable,
        '-c',
        (
            "import sys\n"
            "data = sys.stdin.read()\n"
            "print('<html><head><title>Example</title></head><body>' + data + '</body></html>')\n"
        ),
    ]

    converted = markdowncommand.convert_with_system_markdown('content', command)

    assert 'content' in converted.get_document_body()
    assert converted.get_document_title() == 'Example'


def test_convert_with_system_markdown_failure():
    command = [sys.executable, '-c', 'import sys; sys.exit(1)']

    with pytest.raises(markdowncommand.MarkdownCommandError):
        markdowncommand.convert_with_system_markdown('content', command)
