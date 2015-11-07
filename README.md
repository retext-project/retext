Welcome to ReText!
==================

*This project forks from [ReText], and is improved to work on Windows platform.*
ReText is a simple but powerful editor for Markdown and reStructuredText markup
languages. ReText is written in Python language and works on Linux and other
POSIX-compatible platforms. To install ReText, use `setup.py install` command.

![ReText under KDE 5](https://a.fsdn.com/con/app/proj/retext/screenshots/retext-kde5.png)

You can read more about ReText in the [wiki].

ReText requires the following packages to run:

* [python](https://www.python.org/) — version 3.2 or higher
* [pyqt5](http://www.riverbankcomputing.co.uk/software/pyqt/intro)
* [python-markups](https://pypi.python.org/pypi/Markups)

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

ReText is Copyright 2011–2015 [Dmitry Shachnev](http://mitya57.me)
and is licensed under GNU GPL (v2+) license, the current version is available in
`LICENSE_GPL` file.

ReText icon is based on `accessories-text-editor` icon from the Faenza theme.


欢迎来到ReText！
==================

*本项目从[ReText]上fork而来，并针对Windows平台进行适配。*

ReText是一个简单但又强大的编辑器，它用来处理Markdown和reStructuredText标记语言。
ReText使用Python编写，运行Linux及其他POSIX兼容的平台上。要安装ReText，使用 
`setup.py install`命令。

![在KDE 5下的ReText](https://a.fsdn.com/con/app/proj/retext/screenshots/retext-kde5.png)

你可以通过[wiki]了解更多关于ReText的内容。

ReText需要下列包来运行：

* [python] —3.2 版或更新
* [pyqt5]
* [python-markups]

我们还建议你安装以下包：

* [python-markdown] — 用于Markdown语言支持
* [python-docutils] — 用于reStructuredText语言支持
* [python-enchant] — 用于拼写检查支持

最新的稳定版本可以从[PyPI]下载。你也可以使用 `pip install ReText` 指令来安装。

翻译文件已被编译为发布原始码，并且会自动载入。对于开发快照，使用`lrelease locale/*.ts`
命令编译翻译文件。翻译文件也能从`/usr/share/retext/`目录中载入。

你可以在[Transifex]上将ReText翻译为你的语言。

ReText 版权 2011–2015 [Dmitry Shachnev](http://mitya57.me)
使用GNU GPL (v2+) 许可证, 当前的版本在`LICENSE_GPL`文件中可以获取到。

ReText的图标是基于来自Faenza主题的`accessories-text-editor`图标。


[ReText]: https://github.com/retext-project/retext
[wiki]: https://github.com/retext-project/retext/wiki
[python]: https://www.python.org/
[pyqt5]: http://www.riverbankcomputing.co.uk/software/pyqt/intro
[python-markups]: https://pypi.python.org/pypi/Markups
[python-markdown]: https://pypi.python.org/pypi/Markdown
[python-docutils]: https://pypi.python.org/pypi/docutils
[python-enchant]: https://pypi.python.org/pypi/pyenchant
[PyPI]: https://pypi.python.org/pypi/ReText
[Transifex]: https://www.transifex.com/mitya57/ReText/