Welcome to ReText!
==================

[![Travis CI status][Travis SVG]][Travis]
[![Appveyor CI status][Appveyor SVG]][Appveyor]

ReText is a simple but powerful editor for Markdown and reStructuredText markup
languages. One can also add support for [custom markups] using Python modules.

![ReText on Plasma 5 desktop](data/retext-kde5.png)

To install ReText, make sure that you have [Python] (3.5 or later) installed,
and run `pip3 install ReText`. By default it installs system wide, pass
`--user` for installing into the user’s home directory. You can also manually
download the tarball from [PyPI].

ReText requires the following Python modules to run (`pip` will install them
automatically):

* [PyQt5](https://riverbankcomputing.com/software/pyqt/intro) (5.6 or later)
* [Markups](https://pypi.org/project/Markups/) (2.0 or later)

We also recommend having these packages installed:

* [Markdown](https://pypi.org/project/Markdown/) — for Markdown support
* [docutils](https://pypi.org/project/docutils/) — for reStructuredText support
* [pyenchant](https://pypi.org/project/pyenchant/) — for spell checking support

Translation files are already compiled for release tarballs and will be
automatically loaded. For development snapshots, compile translations using
`lrelease locale/*.ts` command (on Debian-based systems, `lrelease` is
available in `qttools5-dev-tools` package). Translation files can also be
loaded from `/usr/share/retext/` directory.

You can translate ReText into your language on [Transifex].

ReText is Copyright 2011–2020 [Dmitry Shachnev](https://mitya57.me),
2011–2016 [Maurice van der Pot](mailto:griffon26@kfk4ever.com), and is
licensed under GNU GPL (v2+) license, the current version is available in
`LICENSE_GPL` file.

ReText icon is based on `accessories-text-editor` icon from the Faenza theme.

You can read more about ReText in the [wiki].

[wiki]: https://github.com/retext-project/retext/wiki
[PyPI]: https://pypi.org/project/ReText/
[Transifex]: https://www.transifex.com/mitya57/ReText/
[Travis]: https://travis-ci.org/retext-project/retext
[Travis SVG]: https://api.travis-ci.org/retext-project/retext.svg?branch=master
[Appveyor]: https://ci.appveyor.com/project/mitya57/retext
[Appveyor SVG]: https://ci.appveyor.com/api/projects/status/github/retext-project/retext?branch=master&svg=true
[custom markups]: https://pymarkups.readthedocs.io/en/latest/custom_markups.html
[Python]: https://www.python.org/
