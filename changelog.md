## ReText 8.1.0 (2025-01-09)

* Dependency changes:
    - Python 3.9 or later is now required.
    - Markups 4.0 or later is now required.
* Improvements and bugs fixed:
    - Issue #622 — added support for Ctrl+Tab and Ctrl+Shift+Tab for switching
      tabs.
    - PR #634 — WebEngine previewer now shows link on hover (contributed by
      red-kite).
    - Issue #623, PR #640 — changed mouse cursor to pointing hand on link
      hover (contributed by Donjan Rodic).
    - Added F9 shortcut for showing/hiding directory tree dynamically.
    - In the directory tree, for files with long names the full name is shown
      in a tooltip.
    - Issue #383 — splitter state and WebEngine preview zoom factor are now
      cached between runs.
    - Preferences dialog now has links to open the selected stylesheet file
      and working directories externally.
    - It is now possible to pass a directory on the command line, it will be
      shown in the tree.
    - Issue #649 — pasted image URLs are now converted to image markup.
    - Issue #650 — pressing Up key on the first line moves the cursor to the
      beginning of the document, and pressing Down key on the last line moves
      it to the end of the document.
    - When the system theme is dark, Qt WebEngine now uses dark mode too.
    - Issue #617 — added `markdownHeaders` setting for the highlighter.
    - Issue #489 — added initial AsciiDoc support (beta).
    - Issue #519 — added Ctrl+H shortcut for viewing HTML code.
* Internal changes:
    - PR #592 — auto-generated config options were moved to a separate file,
      `cache.conf` (contributed by Okko Makkonen).
    - Build system was ported to `pyproject.toml`.
    - Adopted `ruff` for code quality checks.
* Translation updates:
    - Danish (contributed by Morten Juhl-Johansen).
    - Dutch (contributed by Heimen Stoffels).
    - Irish (new, contributed by Aindriú Mac Giolla Eoin).
    - Italian (contributed by albanobattistella).
    - Ukrainian (contributed by dmytro22).

## ReText 8.0.2 (2024-03-16)

* Improvements and bugs fixed:
    - Fixed synchronized scrolling for zoom factors other than 1 (contributed
      by Maurice van der Pot).
    - Stopped passing `.desktop` suffix to setDesktopFileName() (contributed
      by Chris Mayo in #633).
    - Issue #98 — Made `mdx_posmap` not break indented code blocks which use
      `pymdownx.superfences` extension.
    - Issue #637 — Fixed crash when clicking on line information area.
* Translations updated:
    - Basque (contributed by Aitor Salaberria).
    - German (contributed by cosmic_snow).
    - Korean (contributed by Minpa Lee).
    - Ukrainian (contributed by Oleksandr Tsvirkun).

## ReText 8.0.1 (2023-05-28)

* Bugs fixed:
    - Issue #594 — Fix opening files in existing window by relative path.
    - Issue #597 — Fix unreachable text at the bottom of the file.
    - Issue #599 — Fix truncating file when new text cannot be encoded with
      the selected encoding.
    - Issue #604 — Allow WebEngine renderer to load iframes such as YouTube
      embeds.
    - Issue #609 — Fix incorrect font size with WebEngine renderer.
    - Issue #620 — LICENSE_GPL file now has text of GPL v2.
* Translations updated:
    - Dutch (contributed by Heimen Stoffels).
    - French (contributed by uGwA0XP3cm2w).
    - Italian (contributed by Alessandro Melillo).
    - Norwegian (Bokmål) (new, contributed by Sverre Våbenø).
    - Persian (contributed by Hadi F and Arya Younesi).
    - Portuguese (Brazil) (contributed by Rodrigo Zimmermann).
    - Spanish (contributed by Antonio Villamarin).
    - Turkish (contributed by Serkan ÖNDER).

## ReText 8.0.0 (2022-07-24)

* Dependency changes:
    - ReText is now using Qt 6 and PyQt6.
    - PyQt6-WebEngine is required for JavaScript support.
    - WebKit is no longer supported.
* Improvements and bugs fixed:
    - PR #543 — Added Apply button to Preferences dialog (contributed by Amos
      Kong).
    - Issue #384 — Save button is now enabled in auto-save mode.
    - Issue #536 — Support spell checking for multiple languages.
    - Issue #555 — Support setting bold font for editor.
    - Issue #581 — Added backtick key to surround keys.
    - Run-time resources are now installed into package directory.
    - `setup.py` now allows building wheels.
* Translations updated:
    - Polish (contributed by Maciej Haudek).
    - Spanish (contributed by Pedro Torcatt).
    - Turkish (contributed by Serkan ÖNDER in #556).

## ReText 7.2.3 (2022-02-03)

* Issues #573, #574 — Fixed TypeError crash with Python 3.10 and Qt WebKit.
* Translations updated:
    - Chinese (China) (contributed by liulitchi).
    - Portuguese (Brazil) (contributed by Igor Garcia and Christiano Morais).
    - Slovak (contributed by Jose Riha).

## ReText 7.2.2 (2021-10-11)

* Issue #552 — Fixed bad Spanish translation causing a crash.
* Fixed `TypeError: index 0 has type 'float' but 'int' is expected` with
  Python 3.10.
* Fixed `RuntimeError: ffi_prep_cif_var failed` in XSettings code.

## ReText 7.2.1 (2021-03-06)

* Issues #255, #492 — Improved support for dark Qt themes.
* Fixed preview jumping to top during MathJax rendering.
* Issue #544 — Fixed QTextBrowser-based preview jumping.
* Issue #548 — Fixed opening files with spaces from QTextBrowser-based
  preview.
* Issue #549 — Use `defaultCodec` setting by default when saving files;
  correctly detect encoding for UTF-8 files with BOM.

## ReText 7.2.0 (2021-02-08)

* Dependency changes:
    - Python ≥ 3.6 is now required.
    - Qt and PyQt ≥ 5.11 are now required.
* General improvements:
    - Added ability to show a side panel with directory tree (contributed by
      Xavier Gouchet in #531).
    - Added support for searching in the preview mode.
    - When some text is selected and a quote, bracket or emphasis key is
      pressed, the text is surrounded rather than replaced (contributed by
      Daniel Venturini in #520).
    - Added an option to fully highlight wrapped lines (contributed by
      nihillum in #523).
    - Improved current line highlighting for right-to-left text layout.
    - Ordered list behavior can now be configured to repeat or increment the
      list item number (contributed by Binokkio in #527).
    - Added mnemonics to open the menus from keyboard (contributed by David
      Hebbeker in #528).
    - Added Apply button to the Preferences dialog (contributed by Amos Kong
      in #543).
    - Removed use of deprecated Python, Python-Markdown, Qt and PyQt API.
* Bugs fixed:
    - Issue #507 — Improved the error message when trying to build ReText as a
      wheel package.
    - Issue #529 — Markup that intersects with code blocks is no longer
      highlighted.
    - PR #530 — Preview is no longer updated when it is not shown (contributed
      by rhn in #530).
    - Issue #533 — Fixed showing local images with Qt WebEngine 5.15.
* Translations updated:
    - Arabic (contributed by ZamanOof).
    - Chinese (China) (contributed by liulitchi).
    - Dutch (contributed by Heimen Stoffels).
    - Japanese (contributed by YAMADA Shinichirou).
    - Persian (contributed by Hadi F).
    - Polish (contributed by Maciej Haudek).
    - Russian.
    - Spanish (contributed by Félix Fischer).
    - Swedish (contributed by Philip Andersen).

## ReText 7.1.0 (2020-04-04)

* General improvements:
    - New files are now opened in new tabs by default, not new windows
      (contributed by Daniele Scasciafratte in #476). This can be disabled
      using `openFilesInExistingWindow` configuration option.
    - Preferences dialog improvements: it now uses tabs; added a link to
      configuration file (contributed by Xavier Gouchet in #327); clicking on
      checkbox label now changes checkbox state.
    - Return key now automatically continues quote blocks and ordered lists
      (contributed by Xavier Gouchet in #298 and #326).
    - It is now possible to close the current tab with Ctrl+W (contributed by
      Xavier Gouchet in #283).
    - Ctrl+wheel on editor now increases/decreases font size (contributed by
      Xavier Gouchet in #328). Ctrl+wheel in preview zooms in/out (#400).
    - Alt+Up/Down arrow now moves the current line up/down (contributed by
      Xavier Gouchet in #337).
    - Added “Jump to Line” feature, with Ctrl+G shortcut (contributed by
      Xavier Gouchet in #382).
    - Table mode improvements (contributed by Maurice van der Pot).
    - “Paste Image” moved to a separate action, with Ctrl+Shift+V shortcut.
    - Added “Insert table” dialog (contributed by Changhee Kim in #431).
    - Clicking a link to nonexistent file now prompts the user to create it
      (contributed by red-kite in #436 and Xavier Gouchet in #459).
    - Added a menu action to insert images from filesystem (contributed by
      Daniel Venturini in #500).
* New options added:
    - `relativeLineNumbers` — count line numbers as relative to the current
      line (contributed by Xavier Gouchet in #270).
    - `documentStatsEnabled` — show text statistics in the lower left corner
      of the editor (contributed by Xavier Gouchet in #268 and #338).
    - `rightMarginWrap` — soft-wrap text at user specified margin line
      (contributed by Oğuzhan Öğreden in #313).
    - `paperSize` — set the default paper size for print or PDF export
      (contributed by mray271 in #335).
    - `recentDocumentsCount` — number of recent files to show in the menu
      (contributed by red-kite in #407).
    - `windowTitleFullPath` — show full path in window title (contributed by
      red-kite in #429).
    - `defaultPreviewState` — mode for new tabs: `editor`, `normal-preview` or
      `live-preview` (contributed by red-kite in #435). It replaces the old
      `livePreviewByDefault` option.
    - `wideCursor` — make cursor as wide as characters.
* Bugs fixed:
    - Issue #252 — Limit max-width of images to 100%.
    - Issue #267 — setup.py now installs retext.svg icon.
    - Issues #281, #469 — Autofill current filename for PDF export and Save As
      dialogs (the Save As part contributed by Xavier Gouchet in #474).
    - Issue #291 — Make sure search result does not overlap with stats/info
      areas.
    - Issue #301 — Made the Markdown include extension working.
    - PR #315 — Fixed handling multi-line rows in reStructuredText tables in
      table mode (contributed by R1dO).
    - Issue #346 — Ctrl+F now focuses the search field, not closes the search
      bar. To close the search bar, now the Escape key can be used.
    - Issue #378 — Ensure that cursor is visible after resizes.
    - Issue #397 — Only check whether .css file exists on initial page load.
    - Issue #399 — Try to load libGL.so.1 before creating QApplication.
    - Issue #408 — Fix printing with dark themes.
    - Issue #409 — Make the WebKit renderer use disk cache.
    - PRs #411, #417, #426, #494 — AppData file improvements (contributed by
      scx).
    - Issue #441 — Files reloading no longer triggers tab change.
    - Issue #445 — Implemented PDF export for the WebEngine renderer.
    - Issue #451 — Make the synchronized scroll implementation not break the
      pymdownx.highlight extension.
    - Issues #452, #497, #499 — Prevent pip from building wheels, as that
      results in broken desktop files.
    - Issues #467, #488 — WebEngine renderer broken with new Qt versions.
    - Issue #468 — Include the stylesheet in exported HTML.
    - Issue #479 — Display `*` in tab title when document is modified and
      unsaved (contributed by Xavier Gouchet in #480).
    - Issue #487 — Added a workaround for missing icons in Ubuntu 19.10 Yaru
      theme.
    - PR #496 — Enable HiDPI icons (contributed by Guo Yunhe).
* Translations updated:
    - Chinese (China) (contributed by liulitchi and the Chinese team).
    - Czech (contributed by David Kolibáč).
    - Danish (contributed by scootergrisen).
    - Dutch (contributed by Heimen Stoffels).
    - Finnish (contributed by elguitar).
    - German (contributed by Oliver A. Gubler in #370, Carsten Beck).
    - Italian (contributed by Alessandro Menti).
    - Korean (contributed by MukKim in #415).
    - Portuguese (Brazil) (contributed by EdemarSantos).
    - Portuguese (European) (contributed by Ricardo Simões in #278).
    - Russian (contributed by Vladislav Glinsky, Виктор Ерухин).
    - Serbian (contributed by Slobodan Simić).
    - Spanish (contributed by Félix Fischer, Fito JB).
    - Swedish (contributed by Philip Andersen).
    - Ukrainian (contributed by Vladislav Glinsky).

## ReText 7.0 (2017-02-11)

* It is now possible to install ReText on Windows and macOS using a simple
  `pip install ReText` command. This will pull PyQt5 wheels from PyPI,
  and also download and extract the icons pack needed on this platforms.
  Setup now also generates a wrapper batch script (this was contributed by
  Hong-She Liang).
* Added experimental Qt WebEngine renderer, in addition to the existing
  Qt WebKit one.
* The highlighter got support for reStructuredText links, field lists
  and for Markdown and reStructuredText code spans.
* The replace option was added to the search toolbar.
* The WebKit and WebEngine previewers can now detect links to local HTML
  files and open the corresponding source files in new tab if those are
  found.
* The table mode is now able to insert inter-cell line breaks and new rows,
  when Return and Shift-Return are pressed (respectively).
* ReText can now automatically detect files encoding when `chardet` module
  is present (contributed by Hong-She Liang).
* A configuration option for automatically opening last files was added
  (contributed by Hong-She Liang).
* A configuration option for hiding the tabs bar when there is only one tab
  was added.

*Bugfix update 7.0.1 was released on 2017-06-25 with improved installation
procedure in setup.py, some crash fixes, and updated translations.*

*Bugfix update 7.0.2 was released on 2018-06-05, fixing many bugs. Most
importantly, issues with installation (#324, #363, #365), with synchronized
scrolling breaking code blocks highlighting (#299), with emoji support
(#357, #368), and with some lines disappearing after opening files (#345).*

*Bugfix update 7.0.3 was released on 2018-06-06 with minor changes and
fixed tarball contents.*

*Bugfix update 7.0.4 was released on 2018-09-23 with improved editor
performance (#360), fixed crash on Windows when pasting images (#385),
support for Python-Markdown 3.0, and updated translations.*

## ReText 6.0 (2016-05-10)

* The live preview now automatically scrolls to match its position with the
  editor (only for Markdown).
* Markup conversion is now performed in a background process, improving
  responsiveness of the editor.
* Images can now be copied and pasted into ReText (contributed by Bart
  Clephas).
* Added a button to quickly close the search bar.
* Added basic CSS styling for tables.
* Replaced the tags box with the new “Formatting” box for Markdown
  (contributed by Donato Marrazzo).
* Hitting return twice now ends the Markdown list.
* ReText now depends on version 2.0 or higher of pymarkups.
* The QtWebKit dependency is now optional (though still recommended).

*Bugfix update 6.0.1 was released on 2016-06-25, fixing some crashes and
making auto-save work again.*

*Bugfix update 6.0.2 was released on 2016-10-03, fixing an issue with
startup on Plasma and adding some new translations.*

## ReText 5.3 (2015-12-20)

* Tabs are now reorderable.
* All colors used in editor and highlighter are now configurable via the
  configuration file.
* Links referencing other source files are now opened in ReText as new tabs
  (feature contributed by Jan Korte).
* Code refactoring: some code moved to the new tab.py module, and some old
  hacks dropped.
* The ReText logo is now installed to the data directory.
* Appstream metadata updated to a newer format.
* The desktop file no longer hardcodes the executable path (fix contributed
  by Buo-Ren Lin).

## ReText 5.2 (2015-09-23)

* ReText now tries to load the icon theme from system settings if
  Qt cannot auto-detect it.
* Added a GUI option to change the editor font.
* Added appdata file for appstream.

## ReText 5.1 (2015-06-30)

* Editor now displays cursor position in bottom-right corner.
* Added FakeVim mode (contributed by Lukas Holecek).
* ReText now shows a notification when the file was modified by another
  application, to prevent data loss.
* WebPages generator removed (as better alternatives exist).
* Plain text mode removed.
* Added ability to configure file extensions for Markdown and
  reStructuredText.

## ReText 5.0 (2014-07-26)

* Table editing mode.
* New settings: `colorSchemeFile` and `uiLanguage`.
* More settings are now configurable from GUI.
* Code base simplification and modernization.
* Dropped support for Qt 4.
* Added testsuite.

## ReText 4.1 (2013-08-18)

* Added configuration dialog.
* Added current line highlighting and line numbers support.
* Added support for PyQt5 and PySide libraries.
* Use new signals/slots syntax.
* Added option to select file encoding.
* Dropped support for Python 2 and support for running without WebKit
  installed.

## ReText 4.0 (2012-12-06)

* Switch to pymarkups backend.
* Switch to Python 3 by default.
* Split `retext.py` to smaller files.
* MathJax support.
* Tab now inserts 4 spaces by default.
* Automatic indentation of new lines.
* External links are now opened in a web browser by default.
* Support for per-document CSS stylesheets.

## ReText 3.1 (2012-06-07)

* Spell checker suggestions.
* Markup-specific highlighting.
* Re-written parser and document-type logic.
* Lots of code clean-up.

## ReText 3.0 (2012-03-08)

* Python 3 support.
* Improved highlighter.
* Export extensions.
* Recent files menu.
* Spell checking improvements.
* Shortcuts for formatting.
* WebKit engine improvements.

## ReText 2.1 (2011-10-02)

* Ability to use QtWebKit.
* Splitter between edit and preview boxes.
* Support for opening several files via command-line.
* Support for GData 3 API and replacing existing document in Google Docs.
* Help page.

## ReText 2.0 (2011-08-04)

* Support for reStructuredText, with a GUI option to switch between
  Markdown and reStructuredText.
* Text search.
* Global CSS file support.
* File auto-save support.
* WpGen 0.4, also with reST support.
* Getting title from ReST title or Markdown metadata.
* Changed the default extension for Markdown to `.mkd`.
* New “About” dialog.

## ReText 1.1 (2011-05-28)

* Added spell checker based on enchant.
* Added fullscreen mode.

## ReText 1.0 (2011-04-24)

* First stable release.
* Add “Select default font” option.
* Use HTML input when Markdown is not loaded.
* Add Ctrl+Shift+E sequence for Live preview.

## ReText 0.8 (2011-04-09)

* Add “Show folder”, “Markdown syntax examples” actions.
* Start even if Python-Markdown is not installed.
* Do not highlight quotes outside the tags.
* Save plain text documents with `*.txt` format.

## ReText 0.7 (2011-04-05)

* Tabs support.
* GUI for WpGen.
* Launching preview on Ctrl+E shortcut.

## ReText 0.4 (2011-03-13)

* First public beta release.
