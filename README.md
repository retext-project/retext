Welcome to ReText!
==================

[![GitHub Actions status][GitHub Actions SVG]][GitHub Actions]

ReText is a simple but powerful editor for markup languages. It is based on
[Markups] module which supports Markdown, reStructuredText, Textile and
AsciiDoc. One can also add support for [custom markups] using Python modules.

![ReText on Plasma 5 desktop][Screenshot]

To install ReText, make sure that you have [Python] (3.9 or later) installed,
and run `pip3 install ReText`. To avoid system-wide installation, you can
create a [virtual environment] and install from there. You can also manually
download the tarball from [PyPI] or clone the repository, and then run
`./retext.py`.

ReText requires [PyQt6] and [Markups] (4.0 or later) to run. When you run
`pip3 install ReText`, pip will install them automatically, but you can also
install manually and specify markups that you are going to use using extras
syntax, e.g.:

    pip3 install Markups[markdown,restructuredtext,textile]

We also recommend having these packages installed:

* [pyenchant](https://pypi.org/project/pyenchant/) — for spell checking support
* [chardet](https://pypi.org/project/chardet/) — for encoding detection support
* [PyQt6-WebEngine](https://pypi.org/project/PyQt6-WebEngine/) — a more
  powerful preview engine with JavaScript support

Translation files are already compiled for release tarballs and will be
automatically loaded. For development snapshots, compile translations using
`lrelease ReText/locale/*.ts` command (on Debian-based systems, use
`/usr/lib/qt6/bin/lrelease` from `qt6-l10n-tools` package). Translation files
can also be loaded from `/usr/share/retext/` directory.

You can translate ReText into your language on [Transifex].

ReText is Copyright 2011–2025 [Dmitry Shachnev](https://mitya57.me),
2011–2023 [Maurice van der Pot](mailto:griffon26@kfk4ever.com), and is
licensed under GNU GPL (v2+) license, the current version is available in
`LICENSE_GPL` file.

ReText icon is based on `accessories-text-editor` icon from the Faenza theme.

You can read more about ReText in the [wiki].

[Screenshot]: https://raw.githubusercontent.com/retext-project/retext/master/data/retext-kde6.png
[wiki]: https://github.com/retext-project/retext/wiki
[PyPI]: https://pypi.org/project/ReText/
[Transifex]: https://www.transifex.com/mitya57/ReText/
[GitHub Actions]: https://github.com/retext-project/retext/actions
[GitHub Actions SVG]: https://github.com/retext-project/retext/workflows/tests/badge.svg
[custom markups]: https://pymarkups.readthedocs.io/en/latest/custom_markups.html
[Python]: https://www.python.org/
[PyQt6]: https://pypi.org/project/PyQt6/
[Markups]: https://pypi.org/project/Markups/
[virtual environment]: https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/
