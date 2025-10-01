# vim: ts=4:sw=4:expandtab

# This file is part of ReText
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pytest

from markups import MarkdownMarkup

from ReText.tab import get_markdown_requested_extensions, MARKDOWN_TAB_LENGTH_EXTENSION


@pytest.mark.parametrize('indent', ['  ', '    '])
def test_markdown_tablength_extension_handles_nested_lists(indent):
    markup = MarkdownMarkup(
        filename=None,
        extensions=['ReText.mdx_tablength'],
    )

    text = f"1. Item\n{indent}- nested\n2. Item two\n"

    html = markup.convert(text).get_document_body()

    assert '<ul>' in html, 'Expected a nested unordered list'
    assert 'nested' in html


def test_get_markdown_requested_extensions_includes_tablength():
    extensions_without_sync = get_markdown_requested_extensions(False)
    assert MARKDOWN_TAB_LENGTH_EXTENSION in extensions_without_sync
    assert 'ReText.mdx_posmap' not in extensions_without_sync

    extensions_with_sync = get_markdown_requested_extensions(True)
    assert 'ReText.mdx_posmap' in extensions_with_sync
