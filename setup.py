#!/usr/bin/env python3

VERSION = '5.0.2'

long_description = '''\
ReText is simple text editor that supports Markdown and reStructuredText
markup languages. It is written in Python using PyQt libraries.'''
requires = ['docutils', 'Markdown', 'Markups', 'pyenchant', 'Pygments']

import re
import sys
from os.path import basename, join
from distutils import log
from distutils.core import setup, Command
from distutils.command.build import build
from distutils.command.sdist import sdist
from distutils.command.install_scripts import install_scripts
from distutils.command.upload import upload
from subprocess import check_call
from glob import glob
from warnings import filterwarnings

if sys.version_info[0] < 3:
	sys.exit('Error: Python 3.x is required.')

def build_translations():
	print('running build_translations')
	error = None
	for ts_file in glob(join('locale', '*.ts')):
		try:
			check_call(('lrelease', ts_file))
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
			new_path = ('mandriver@frs.sourceforge.net:/home/frs/project/r/re/retext/ReText-%s/%s' %
			            (full_version[:-2], basename(filename)))
			args = ['scp', filename, new_path]
			print('calling process', args)
			check_call(args)

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
        'test': retext_test,
        'upload': retext_upload
      },
      license='GPL 2+'
)
