#!/usr/bin/env python3

VERSION = '6.0.0'

long_description = '''\
ReText is simple text editor that supports Markdown and reStructuredText
markup languages. It is written in Python using PyQt libraries.

It supports live preview, tabs, math formulas, export to various formats
including PDF and HTML.

For more details, please go to the `home page`_ or to the `wiki`_.

.. _`home page`: https://github.com/retext-project/retext
.. _`wiki`: https://github.com/retext-project/retext/wiki'''

import re
import sys
from os.path import join
from distutils import log
from distutils.core import setup, Command
from distutils.command.build import build
from distutils.command.sdist import sdist
from distutils.command.install_scripts import install_scripts
from distutils.command.upload import upload
from subprocess import check_call
from glob import glob, iglob
from warnings import filterwarnings

if sys.version_info[0] < 3:
	sys.exit('Error: Python 3.x is required.')

def build_translations():
	print('running build_translations')
	error = None
	for ts_file in glob(join('locale', '*.ts')):
		try:
			check_call(('lrelease', ts_file), env={'QT_SELECT': '5'})
		except Exception as e:
			error = e
	if error:
		print('Failed to build translations:', error)

class retext_build(build):
	def run(self):
		build.run(self)
		if not glob(join('locale', '*.qm')):
			build_translations()

class retext_sdist(sdist):
	def run(self):
		build_translations()
		sdist.run(self)

class retext_install_scripts(install_scripts):
	def run(self):
		import shutil
		install_scripts.run(self)
		for file in self.get_outputs():
			log.info('renaming %s to %s', file, file[:-3])
			shutil.move(file, file[:-3])

class retext_test(Command):
	user_options = []

	def initialize_options(self): pass
	def finalize_options(self): pass

	def run(self):
		from tests import main
		testprogram = main(module=None, argv=sys.argv[:1], verbosity=2, exit=False)
		if not testprogram.result.wasSuccessful():
			sys.exit(1)

class retext_upload(upload):
	def run(self):
		self.sign = True
		self.identity = '0x2f1c8ae0'
		upload.run(self)
		for command, pyversion, filename in self.distribution.dist_files:
			full_version = re.search(r'ReText-([\d\.]+)\.tar\.gz', filename).group(1)
			new_path = ('mandriver@frs.sourceforge.net:/home/frs/project/r/re/retext/ReText-%s/' %
			            full_version[:-2])
			args = ['scp', filename, filename + '.asc', new_path]
			print('calling process', args)
			check_call(args)

if '--no-rename' in sys.argv:
	retext_install_scripts = install_scripts
	sys.argv.remove('--no-rename')

filterwarnings('ignore', "Unknown distribution option: 'install_requires'")

classifiers = [
	'Development Status :: 5 - Production/Stable',
	'Environment :: X11 Applications :: Qt',
	'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
	'Programming Language :: Python :: 3 :: Only',
	'Topic :: Text Editors',
	'Topic :: Text Processing :: Markup'
]

setup(name='ReText',
      version=VERSION,
      description='Simple editor for Markdown and reStructuredText',
      long_description=long_description,
      author='Dmitry Shachnev',
      author_email='mitya57@gmail.com',
      url='https://github.com/retext-project/retext',
      packages=['ReText'],
      scripts=['retext.py'],
      data_files=[
        ('share/appdata', ['data/me.mitya57.ReText.appdata.xml']),
        ('share/applications', ['data/me.mitya57.ReText.desktop']),
        ('share/retext/icons', glob('icons/*')),
        ('share/retext/locale', iglob('locale/*.qm'))
      ],
      requires=['docutils', 'Markdown', 'Markups', 'pyenchant', 'Pygments'],
      install_requires=['docutils', 'Markdown', 'Markups>=2.0', 'pyenchant', 'Pygments'],
      cmdclass={
        'build': retext_build,
        'sdist': retext_sdist,
        'install_scripts': retext_install_scripts,
        'test': retext_test,
        'upload': retext_upload
      },
      classifiers=classifiers,
      license='GPL 2+'
)
