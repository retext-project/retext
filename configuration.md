ReText stores all of its configuration in a text file. A path to that
file is printed to stdout during ReText startup.

Possible configuration options
==============================

Configuration options that you can set to improve your experience:

option name                    | type      | description
-----------                    | ----      | -----------
`appStyleSheet`                | file path | file containing a Qt stylesheet file
`autoSave`                     | boolean   | whether to automatically save documents (default: false)
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
`livePreviewByDefault`         | boolean   | whether new tabs and windows should open in live preview mode (default: false)
`markdownDefaultFileExtension` | string    | default file extension for Markdown files (default: `.mkd`)
`pygmentsStyle`                | string    | name of Pygments syntax highlighting style to use (default: `default`)
`restDefaultFileExtension`     | string    | default file extension for reStructuredText files (default: `.rst`)
`rightMargin`                  | integer   | enable drawing of vertical line on defined position (or 0 to disable)
`saveWindowGeometry`           | boolean   | whether to restore window geometry from previous session (default: false)
`spellCheck`                   | boolean   | whether to enable spell checking
`spellCheckLocale`             | string    | short name of spell check locale to use (examples: `en_US`, `ru`, `pt_BR`)
`styleSheet`                   | file path | CSS file to use in preview area
`syncScroll`                   | boolean   | whether to enable synchronized scrolling for Markdown (default: true)
`tabInsertsSpaces`             | boolean   | whether Tab key should insert spaces instead of tabs (default: true)
`tabWidth`                     | integer   | the width of tab character (default: 4)
`uiLanguage`                   | string    | short name of locale to use for interface (examples: `en_US, `ru, `pt_BR`)
`useFakeVim`                   | boolean   | whether to use the FakeVim editor, if available (default: false)
`useWebKit`                    | boolean   | whether to use the WebKit instead of QTextEdit as HTML previewer (default: false)

If the type is 'file path', then the value should be an absolute path
to a file.

These options can be set internally by ReText and should never be set
manually: `recentFileList` and `windowGeometry`.

Icon themes
===========

If ReText starts and does not show icons, go to Preferences dialog
and fill the "icon theme" field with the icon theme being used.

By default Qt (the toolkit used by ReText) can correctly detect icon
theme only on KDE and on a fixed list of Gtk+-based environments (when
the gtk platformtheme is used).

If you don't know name of your icon theme, look at the names of
subdirectories in `/usr/share/icons/` directory.

Color scheme setting
====================

It is possible to configure ReText highlighter to use custom colors set,
by providing these colors in a separate section in the configuration file.

The example of such section is:

    [ColorScheme]
    htmlTags=green
    htmlSymbols=#ff8800
    htmlComments=#abc

Color names for the text editor:

color name             | main setting           | description
----------             | ------------           | -----------
`marginLine`           | `rightMargin`          | the vertical right margin line
`currentLineHighlight` | `highlightCurrentLine` | highlighting of the text line being edited
`infoArea`             |                        | the info box in the bottom-right corner
`lineNumberArea`       | `lineNumbersEnabled`   | the line numbers area background
`lineNumberAreaText`   | `lineNumbersEnabled`   | the line numbers area foreground

Color names for the highlighter:

color name        | description
----------        | -----------
`htmlTags`        | HTML tags, i.e. `<foo>`
`htmlStrings`     | string properties inside HTML tags, i.e. `"baz"` inside `<foo bar="baz">`
`htmlSymbols`     | HTML symbols, i.e. `&bar;`
`htmlComments`    | HTML comments, i.e. `<!-- comment -->`
`markdownLinks`   | Markdown links and images text, i.e. `foo` inside `[foo](http://example.com)`
`blockquotes`     | blockquotes, i.e. `> quote` in Markdown
`restDirectives`  | reStructuredText directives, i.e. `.. math::`
`restRoles`       | reStructuredText roles, i.e. `:math:`
`whitespaceOnEnd` | whitespace at line endings
