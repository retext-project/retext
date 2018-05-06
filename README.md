Welcome to ReText!
==================

[![Travis CI status][Travis SVG]][Travis]
[![Appveyor CI status][Appveyor SVG]][Appveyor]

ReText is a simple but powerful editor for Markdown and reStructuredText markup
languages. ReText is written in Python language and works on Linux and other
POSIX-compatible platforms. To install ReText, use `setup.py install` command.

![ReText on Plasma 5 desktop](data/retext-kde5.png)

You can read more about ReText in the [wiki].

ReText requires the following packages to run:

* [python](https://www.python.org/) — version 3.2 or higher
* [pyqt5](https://riverbankcomputing.com/software/pyqt/intro)
* [python-markups](https://pypi.org/project/Markups/) — version 2.0 or higher

We also recommend having these packages installed:

* [python-markdown](https://pypi.org/project/Markdown/) — for Markdown
  language support
* [python-docutils](https://pypi.org/project/docutils/) — for reStructuredText
  language support
* [python-enchant](https://pypi.org/project/pyenchant/) — for spell checking
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
[PyPI]: https://pypi.org/project/ReText/
[Transifex]: https://www.transifex.com/mitya57/ReText/
[Travis]: https://travis-ci.org/retext-project/retext
[Travis SVG]: https://api.travis-ci.org/retext-project/retext.svg?branch=master
[Appveyor]: https://ci.appveyor.com/project/mitya57/retext
[Appveyor SVG]: https://ci.appveyor.com/api/projects/status/github/retext-project/retext?branch=master&svg=true
