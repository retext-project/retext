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
