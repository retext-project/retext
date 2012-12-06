#!/usr/bin/env python3

VERSION = '4.0.0'

long_description = '''\
ReText is simple text editor that supports Markdown and reStructuredText
markup languages. It is written in Python using PyQt libraries.'''

from distutils.core import setup
from distutils.command.build import build
from distutils.command.sdist import sdist
from subprocess import check_call
from glob import glob

def build_translations():
	print('running build_translations')
	error = None
	for ts_file in glob('locale/*.ts'):
		try:
			check_call(('lrelease', ts_file))
		except Exception as e:
			error = e
	if error:
		print('Failed to build translations:', error)

class retext_build(build):
	def run(self):
		build.run(self)
		if not glob('locale/*.qm'):
			build_translations()

class retext_sdist(sdist):
	def run(self):
		build_translations()
		sdist.run(self)

setup(name='ReText',
	version=VERSION,
	description='Simple editor for Markdown and reStructuredText',
	long_description=long_description,
	author='Dmitry Shachnev',
	author_email='mitya57@gmail.com',
	url='http://retext.sourceforge.net/',
	packages=['ReText'],
	scripts=['retext.py', 'wpgen.py'],
	cmdclass={'build': retext_build, 'sdist': retext_sdist},
	license='GPL 2+'
)
