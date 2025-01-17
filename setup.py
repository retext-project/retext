#!/usr/bin/env python3

import logging
import os
from glob import glob
from os.path import join
from subprocess import check_call, check_output

from setuptools import Command, setup
from setuptools.command.build import build
from setuptools.command.install import install
from setuptools.command.sdist import sdist


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
        except OSError:
            logging.exception('Could not run qmake6:')
        else:
            qt6_path = qt6_path.decode('utf-8').rstrip()
            environment['PATH'] = qt6_path + os.pathsep + environment['PATH']
        for ts_file in glob(join('ReText', 'locale', '*.ts')):
            try:
                check_call(('lrelease', ts_file), env=environment)
            except Exception:
                logging.exception('Failed to build translations:')
                break


class retext_build(build):
    sub_commands = [('build_translations', None)] + build.sub_commands


class retext_sdist(sdist):
    def run(self):
        self.run_command('build_translations')
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
            return
        # Fix Exec and Icon fields in the desktop file
        icon_path = join(self.orig_install_lib, 'ReText', 'icons', 'retext.svg')
        with open(desktop_file_path, encoding="utf-8") as desktop_file:
            desktop_contents = desktop_file.read()
        logging.info('fixing Exec line in %s', desktop_file_path)
        desktop_contents = desktop_contents.replace('Exec=retext', f'Exec={retext}')
        if self.orig_install_data != '/usr':
            logging.info('fixing Icon line in %s', desktop_file_path)
            desktop_contents = desktop_contents.replace('Icon=retext', f'Icon={icon_path}')
        with open(desktop_file_path, 'w', encoding="utf-8") as desktop_file:
            desktop_file.write(desktop_contents)


setup(
    cmdclass={
        'build_translations': retext_build_translations,
        'build': retext_build,
        'sdist': retext_sdist,
        'install': retext_install,
    }
)
