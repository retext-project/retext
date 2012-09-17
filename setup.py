#!/usr/bin/env python3

from distutils.core import setup
from distutils.command.build import build
from distutils.command.sdist import sdist
from subprocess import check_call
from glob import glob
from ReText import app_version

def build_translations():
	print('running build_translations')
	error = None
	for ts_file in glob('locale/*.ts'):
		try:
			check_call(('lrelease', ts_file))
		except Exception as e:
			error = e
	if error:
		print(error)

class retext_build(build):
	def run(self):
		build.run(self)
		build_translations()

class retext_sdist(sdist):
	def run(self):
		build_translations()
		sdist.run(self)

setup(name='ReText',
	version=app_version,
	description='Simple editor for Markdown and reStructuredText',
	author='Dmitry Shachnev',
	author_email='mitya57@gmail.com',
	url='http://retext.sourceforge.net/',
	packages=['ReText'],
	scripts=['retext.py', 'wpgen.py'],
	cmdclass={'build': retext_build, 'sdist': retext_sdist},
	license='GPL 2+'
)
