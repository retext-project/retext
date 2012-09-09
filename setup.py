#!/usr/bin/python3

from distutils.core import setup
from ReText import app_version

setup(name='ReText',
	version=app_version,
	description='Simple editor for Markdown and reStructuredText',
	author='Dmitry Shachnev',
	author_email='mitya57@gmail.com',
	url='http://retext.sourceforge.net/',
	packages=['ReText'],
	scripts=['retext', 'wpgen'],
	license='GPL 2+'
)
