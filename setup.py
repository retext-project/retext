#!/usr/bin/env python3

VERSION = '4.1.3'

long_description = '''\
ReText is simple text editor that supports Markdown and reStructuredText
markup languages. It is written in Python using PyQt libraries.'''
requires = ['docutils', 'Markdown', 'Markups', 'pyenchant', 'Pygments']

import sys
from os.path import join
from distutils import log
from distutils.core import setup
from distutils.command.build import build
from distutils.command.sdist import sdist
from distutils.command.install_scripts import install_scripts
from subprocess import check_call
from glob import glob
from warnings import filterwarnings

def build_translations():
	print('running build_translations')
	error = None
	for ts_file in glob(join('locale', '*.ts')):
		try:
			check_call(('lrelease', ts_file))
		except OSError:
			try:
				check_call(('lrelease-qt4', ts_file))
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

if '--no-rename' in sys.argv:
	retext_install_scripts = install_scripts
	sys.argv.remove('--no-rename')

filterwarnings('ignore', "Unknown distribution option: 'install_requires'")

setup(name='ReText',
      version=VERSION,
      description='Simple editor for Markdown and reStructuredText',
      long_description=long_description,
      author='Dmitry Shachnev',
      author_email='mitya57@gmail.com',
      url='http://retext.sourceforge.net/',
      packages=['ReText'],
      scripts=['retext.py', 'wpgen.py'],
      data_files=[
      	('share/retext/locale', glob('locale/*.qm')),
      	('share/wpgen', glob('templates/*.css') + glob('templates/*.html'))
      ],
      requires=requires,
      install_requires=requires,
      cmdclass={
        'build': retext_build,
        'sdist': retext_sdist,
        'install_scripts': retext_install_scripts,
      },
      license='GPL 2+'
)
