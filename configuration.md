ReText stores all of its configuration in a text file. A path to that
file is printed to stdout during ReText startup.

Possible configuration options
==============================

Configuration options that you can set to improve your experience:

option name                    | type      | description
-----------                    | ----      | -----------
`appStyleSheet`                | file path | file containing a [Qt stylesheet file]
`autoSave`                     | boolean   | whether to automatically save documents (default: false)
`defaultCodec`                 | string    | name of encoding to use by default (default: use system encoding)
`defaultMarkup`                | string    | name of markup to use for unknown files
`defaultPreviewState`          | string    | mode for new tabs: `editor`, `normal-preview` or `live-preview` (default: `editor`)
`detectEncoding`               | boolean   | whether to automatically detect files encoding; needs chardet package (default: true)
`directoryPath`                | string    | the path to the root directory to display in the side panel if `showDirectoryTree` is true (default: `~`)
`documentStatsEnabled`         | boolean   | whether to show document stats (word count, character count) (default: false)
`editorFont`                   | string    | font to use for editor (comma-separated string as returned by [QFont.toString()])
`font`                         | string    | font to use for previews (comma-separated string as returned by [QFont.toString()])
`handleWebLinks`               | boolean   | whether to use ReText preview area to open external links (default: false)
`hideToolBar`                  | boolean   | whether to hide the toolbars from the UI (default: false)
`highlightCurrentLine`         | string    | current line highlight mode: `disabled`, `cursor-line` or `wrapped-line` (default: `disabled`)
`iconTheme`                    | string    | name of the system icon theme to use (see below)
`lineNumbersEnabled`           | boolean   | whether to show column with line numbers in editor (default: false)
`markdownDefaultFileExtension` | string    | default file extension for Markdown files (default: `.mkd`)
`openFilesInExistingWindow`    | boolean   | whether to open new files in the existing window (default: true)
`openLastFilesOnStartup`       | boolean   | whether to automatically open last documents on startup (default: false)
`orderedListMode`              | string    | editor behavior for lists continuation: `increment` or `repeat` (default: `increment`)
`paperSize`                    | string    | name of default page size to use for print and export (e.g. A4, Letter)
`pygmentsStyle`                | string    | name of Pygments syntax highlighting style to use (default: `default`)
`recentDocumentsCount`         | integer   | number of recent files to show in the menu (default: 10)
`relativeLineNumbers`          | boolean   | whether to show line numbers as relative from the current line (default: false)
`restDefaultFileExtension`     | string    | default file extension for reStructuredText files (default: `.rst`)
`rightMargin`                  | integer   | enable drawing of vertical line on defined position (or 0 to disable)
`rightMarginWrap`              | boolean   | enable soft wrap at specified margin line (default: false)
`saveWindowGeometry`           | boolean   | whether to restore window geometry from previous session (default: false)
`showDirectoryTree`            | boolean   | whether to show a directory tree on the left side of the window (default: false)
`spellCheck`                   | boolean   | whether to enable spell checking
`spellCheckLocale`             | string    | spell check locale to use, possibly comma-separated (examples: `pt_BR`, `ru,en_US`)
`styleSheet`                   | file path | CSS file to use in preview area
`syncScroll`                   | boolean   | whether to enable synchronized scrolling for Markdown (default: true)
`tabBarAutoHide`               | boolean   | whether to hide the tabs bar when only one tab is open (default: false)
`tabInsertsSpaces`             | boolean   | whether Tab key should insert spaces instead of tabs (default: true)
`tabWidth`                     | integer   | the width of tab character (default: 4)
`uiLanguage`                   | string    | short name of locale to use for interface (examples: `en_US`, `ru`, `pt_BR`)
`useFakeVim`                   | boolean   | whether to use the FakeVim editor, if available (default: false)
`useWebEngine`                 | boolean   | whether to use the WebEngine (Chromium) as HTML previewer (default: false)
`wideCursor`                   | boolean   | make cursor as wide as characters (default: false)
`windowTitleFullPath`          | boolean   | whether the window title should show the full path of file (default: false)

[Qt stylesheet file]: https://doc.qt.io/qt-6/stylesheet-reference.html
[QFont.toString()]: https://doc.qt.io/qt-6/qfont.html#toString

If the type is 'file path', then the value should be an absolute path
to a file.

There is also a separate file called `cache.conf` which contains options
that are set internally by ReText and should never be set manually:

- `lastFileList`
- `lastTabIndex`
- `recentFileList`
- `splitterState`
- `webEngineZoomFactor`
- `windowGeometry`

Icon themes
===========

If ReText starts and does not show icons, go to Preferences dialog
and fill the "icon theme" field with the icon theme being used.

By default Qt (the toolkit used by ReText) can correctly detect icon
theme only on KDE and on a fixed list of GTK-based environments (when
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
`statsArea`            | `documentStatsEnabled` | the stats box in the bottom-right corner
`lineNumberArea`       | `lineNumbersEnabled`   | the line numbers area background
`lineNumberAreaText`   | `lineNumbersEnabled`   | the line numbers area foreground

Color names for the highlighter:

color name        | description
----------        | -----------
`htmlTags`        | HTML tags, e.g. `<foo>`
`htmlStrings`     | string properties inside HTML tags, e.g. `"baz"` inside `<foo bar="baz">`
`htmlSymbols`     | HTML symbols, e.g. `&bar;`
`htmlComments`    | HTML comments, e.g. `<!-- comment -->`
`markdownHeaders` | Markdown headers, e.g. `# Header`
`markdownLinks`   | Markdown links and images text, e.g. `foo` inside `[foo](http://example.com)`
`blockquotes`     | blockquotes, e.g. `> quote` in Markdown
`codeSpans`       | code spans, e.g. `` `code` `` in Markdown
`restDirectives`  | reStructuredText directives, e.g. `.. math::`
`restRoles`       | reStructuredText roles, e.g. `:math:`
`whitespaceOnEnd` | whitespace at line endings
