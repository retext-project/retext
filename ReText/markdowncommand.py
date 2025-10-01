# This file is part of ReText
# Copyright: 2025 ReText contributors
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

import html as html_module
import re
import subprocess
from typing import Sequence

from markups.markdown import ConvertedMarkdown


class MarkdownCommandError(RuntimeError):
    """Raised when running the external markdown command fails."""


def convert_with_system_markdown(text: str, command: Sequence[str]) -> ConvertedMarkdown:
    """Run *command* to convert *text* to HTML and wrap the result for ReText.

    The command is expected to read Markdown from ``stdin`` and print HTML to
    ``stdout``. The returned object mimics the value provided by
    :class:`markups.markdown.MarkdownMarkup` so the rest of the application can
    reuse the existing exporting and preview pipeline.
    """

    if not command:
        raise MarkdownCommandError('No markdown command configured.')

    try:
        completed = subprocess.run(
            command,
            input=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise MarkdownCommandError(str(exc)) from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        message = stderr or f'Markdown command exited with status {completed.returncode}'
        raise MarkdownCommandError(message)

    output = completed.stdout or completed.stderr or ''

    body = output
    title = ''
    lowered = output.lower()

    if '<body' in lowered:
        match = re.search(r'<body[^>]*>(.*?)</body>', output, re.IGNORECASE | re.DOTALL)
        if match:
            body = match.group(1)

    if '<title' in lowered:
        match = re.search(r'<title[^>]*>(.*?)</title>', output, re.IGNORECASE | re.DOTALL)
        if match:
            title = html_module.unescape(match.group(1).strip())

    return ConvertedMarkdown(body.strip(), title, '')

