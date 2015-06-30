ReText stores all of its configuration in a text file. A path to that
file is printed to stdout during ReText startup.

Possible configuration options
==============================

Configuration options that you can set to improve your experience:

option name                    | type      | description
-----------                    | ----      | -----------
`appStyleSheet`                | file path | file containing a Qt stylesheet file
`autoSave`                     | boolean   | whether to automatically save documents (default: false)
`colorSchemeFile`              | file path | file containing a highlighter color scheme
`defaultCodec`                 | string    | name of encoding to use by default (default: use system encoding)
`defaultMarkup`                | string    | name of markup to use for unknown files
`editorFont`                   | string    | font to use for editor: name (default: `monospace`)
`editorFontSize`               | integer   | font to use for editor: font size
`font`                         | string    | font to use for previews: name
`fontSize`                     | integer   | font to use for previews: font size
`handleWebLinks`               | boolean   | whether to use ReText preview area to open external links (default: false)
`hideToolBar`                  | boolean   | whether to hide the toolbars from the UI (default: false)
`highlightCurrentLine`         | boolean   | whether to highlight current line in editor (default: false)
`iconTheme`                    | string    | name of the system icon theme to use (see below)
`lineNumbersEnabled`           | boolean   | whether to show column with line numbers in editor (default: false)
`markdownDefaultFileExtension` | string    | default file extension for Markdown files (default: `.mkd`)
`pygmentsStyle`                | string    | name of Pygments syntax highlighting style to use (default: `default`)
`restDefaultFileExtension`     | string    | default file extension for reStructuredText files (default: `.rst`)
`restorePreviewState`          | boolean   | whether to restore preview state from previous session (default: false)
`rightMargin`                  | integer   | enable drawing of vertical line on defined position (or 0 to disable)
`saveWindowGeometry`           | boolean   | whether to restore window geometry from previous session (default: false)
`spellCheck`                   | boolean   | whether to enable spell checking
`spellCheckLocale`             | string    | short name of spell check locale to use (examples: `en_US`, `ru`, `pt_BR`)
`styleSheet`                   | file path | CSS file to use in preview area
`tabInsertsSpaces`             | boolean   | whether Tab key should insert spaces instead of tabs (default: true)
`tabWidth`                     | integer   | the width of tab character (default: 4)
`uiLanguage`                   | string    | short name of locale to use for interface (examples: `en_US, `ru, `pt_BR`)
`useFakeVim`                   | boolean   | whether to use the FakeVim editor, if available (default: false)
`useWebKit`                    | boolean   | whether to use the WebKit instead of QTextEdit as HTML previewer (default: false)

If the type is 'file path', then the value should be an absolute path
to a file.

These options can be set internally by ReText and should never be set
manually: `previewState`, `recentFileList` and `windowGeometry`.

Icon themes
===========

If ReText starts and does not show icons, go to Preferences dialog
and fill the "icon theme" field with the icon theme being used.

By default Qt (the toolkit used by ReText) can correctly detect icon
theme only on KDE and on a fixed list of Gtk+-based environments (when
the gtk platformtheme is used).

If you don't know name of your icon theme, look at the names of
subdirectories in `/usr/share/icons/` directory.

Color scheme files
==================

It is possible to configure ReText highlighter to use custom colors set,
by providing a color scheme file. The syntax of a such file is as follows:

    htmltags = green
    htmlsymbols = #ff8800
    htmlcomments = #abc

Possible color names: `htmltags`, `htmlsymbols`, `htmlquotes`, `htmlcomments`,
`markdownlinks`, `blockquotes`, `restdirectives`, `restroles`.
