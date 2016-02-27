Welcome to ReText!  [![Travis CI status][Travis SVG]][Travis]
=============================================================

ReText is a simple but powerful editor for Markdown and reStructuredText markup
languages. ReText is written in Python language and works on Linux and other
POSIX-compatible platforms. To install ReText, use `setup.py install` command.

![ReText under KDE 5](https://a.fsdn.com/con/app/proj/retext/screenshots/retext-kde5.png)

You can read more about ReText in the [wiki].

ReText requires the following packages to run:

* [python](https://www.python.org/) — version 3.2 or higher
* [pyqt5](http://www.riverbankcomputing.co.uk/software/pyqt/intro)
* [python-markups](https://pypi.python.org/pypi/Markups) — version 2.0 or higher

We also recommend having these packages installed:

* [python-markdown](https://pypi.python.org/pypi/Markdown) — for Markdown
  language support
* [python-docutils](https://pypi.python.org/pypi/docutils) — for reStructuredText
  language support
* [python-enchant](https://pypi.python.org/pypi/pyenchant) — for spell checking
  support

The latest stable version of ReText can be downloaded from [PyPI]. You can
also use `pip install ReText` command to install it from there.

Translation files are already compiled for release tarballs and will be
automatically loaded. For development snapshots, compile translations using
`lrelease locale/*.ts` command. Translation files can also be loaded from
`/usr/share/retext/` directory.

You can translate ReText into your language on [Transifex].

ReText is Copyright 2011–2016 [Dmitry Shachnev](https://mitya57.me),
2011–2016 [Maurice van der Pot](mailto:griffon26@kfk4ever.com), and is
licensed under GNU GPL (v2+) license, the current version is available in
`LICENSE_GPL` file.

ReText icon is based on `accessories-text-editor` icon from the Faenza theme.

[wiki]: https://github.com/retext-project/retext/wiki
[PyPI]: https://pypi.python.org/pypi/ReText
[Transifex]: https://www.transifex.com/mitya57/ReText/
[Travis]: https://travis-ci.org/retext-project/retext
[Travis SVG]: https://api.travis-ci.org/retext-project/retext.svg
