#!/usr/bin/env python3

VERSION = '8.0.0'

long_description = '''\
ReText is simple text editor that supports Markdown and reStructuredText
markup languages. It is written in Python using PyQt libraries.

It supports live preview, tabs, math formulas, export to various formats
including PDF and HTML.

For more details, please go to the `home page`_ or to the `wiki`_.

.. _`home page`: https://github.com/retext-project/retext
.. _`wiki`: https://github.com/retext-project/retext/wiki'''

import os
import sys
from os.path import join, basename
from setuptools import setup, Command
from setuptools.command.sdist import sdist
from setuptools.command.install import install
from distutils import log
from distutils.command.build import build
from subprocess import check_call, check_output
from glob import glob

if sys.version_info[0] < 3:
	sys.exit('Error: Python 3.x is required.')


def bundle_icons():
	import urllib.request
	import tarfile
	from io import BytesIO
	icons_tgz = 'https://github.com/retext-project/retext/archive/icons.tar.gz'
	response = urllib.request.urlopen(icons_tgz)
	tario = BytesIO(response.read())
	tar = tarfile.open(fileobj=tario, mode='r')
	for member in tar:
		if member.isfile():
			member.path = basename(member.path)
			log.info('bundling ReText/icons/%s', member.path)
			tar.extract(member, join('ReText', 'icons'))
	tar.close()


class retext_build_translations(Command):
	description = 'Build .qm files from .ts files using lrelease'
	user_options = []

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		environment = dict(os.environ, QT_SELECT='6')
		# Add Qt 6 binaries directory to PATH.
		try:
			qt6_path = check_output(('qmake6', '-query', 'QT_INSTALL_BINS'))
		except OSError as e:
			log.warn('Could not run qmake6: %s', e)
		else:
			qt6_path = qt6_path.decode('utf-8').rstrip()
			environment['PATH'] = qt6_path + os.pathsep + environment['PATH']
		for ts_file in glob(join('ReText', 'locale', '*.ts')):
			try:
				check_call(('lrelease', ts_file), env=environment)
			except Exception as e:
				log.warn('Failed to build translations: %s', e)
				break


class retext_build(build):
	sub_commands = build.sub_commands + [('build_translations', None)]


class retext_sdist(sdist):
	def run(self):
		self.run_command('build_translations')
		bundle_icons()
		sdist.run(self)

class retext_install(install):
	def change_roots(self, *names):
		self.orig_install_scripts = self.install_scripts
		self.orig_install_data = self.install_data
		self.orig_install_lib = self.install_lib
		install.change_roots(self, *names)

	def run(self):
		install.run(self)

		if self.root is None:
			self.orig_install_scripts = self.install_scripts
			self.orig_install_data = self.install_data
			self.orig_install_lib = self.install_lib
		retext = join(self.orig_install_scripts, 'retext')

		desktop_file_path = join(self.install_data, 'share', 'applications',
		                         'me.mitya57.ReText.desktop')
		if self.root and self.root.endswith('/wheel'):
			# Desktop files don't allow relative paths, and we don't know the
			# absolute path when building a wheel.
			log.info('removing the .desktop file from the wheel')
			os.remove(desktop_file_path)
			return
		# Fix Exec and Icon fields in the desktop file
		icon_path = join(self.orig_install_lib, 'ReText', 'icons', 'retext.svg')
		with open(desktop_file_path, encoding="utf-8") as desktop_file:
			desktop_contents = desktop_file.read()
		log.info('fixing Exec line in %s', desktop_file_path)
		desktop_contents = desktop_contents.replace('Exec=retext', 'Exec=%s' % retext)
		if self.orig_install_data != '/usr':
			log.info('fixing Icon line in %s', desktop_file_path)
			desktop_contents = desktop_contents.replace('Icon=retext', 'Icon=%s' % icon_path)
		with open(desktop_file_path, 'w', encoding="utf-8") as desktop_file:
			desktop_file.write(desktop_contents)


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
      entry_points={
        'gui_scripts': ['retext = ReText.__main__:main'],
      },
      data_files=[
        ('share/applications', ['data/me.mitya57.ReText.desktop']),
        ('share/icons/hicolor/scalable/apps', ['ReText/icons/retext.svg']),
        ('share/metainfo', ['data/me.mitya57.ReText.appdata.xml']),
      ],
      package_data={
        'ReText': ['icons/*.png', 'icons/*.svg', 'locale/*.qm'],
      },
      python_requires='>=3.6',
      requires=['docutils', 'Markdown', 'Markups(>=2.0)', 'pyenchant', 'Pygments', 'PyQt6'],
      install_requires=[
        'docutils',
        'Markdown>=3.0',
        'Markups>=2.0',
        'Pygments',
        'chardet>=2.3',
        'PyQt6',
      ],
      extras_require={
        'spellcheck': ['pyenchant'],
        'webengine': ['PyQt6-WebEngine'],
      },
      cmdclass={
        'build_translations': retext_build_translations,
        'build': retext_build,
        'sdist': retext_sdist,
        'install': retext_install,
      },
      test_suite='tests',
      classifiers=classifiers,
      license='GPL 2+'
)
