#!/usr/bin/python3
# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2016 Maurice van der Pot
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import markups
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QFileDialog, QWidget
import ReText
from ReText.window import ReTextWindow

defaultEventTimeout = 0.0
path_to_testdata = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata')

# Keep a reference so it is not garbage collected
app = QApplication([])

def handle_timer_event():
    print('timer event received')

def processEventsUntilIdle(eventTimeout=defaultEventTimeout):
    '''
    Process Qt events until the application has not had any events for `eventTimeout` seconds
    '''
    if not app.hasPendingEvents():
        time.sleep(eventTimeout)
    while app.hasPendingEvents():
        #print ('outer loop')
        while app.hasPendingEvents():
            #print('inner loop')
            app.processEvents()
        time.sleep(eventTimeout)


class TestWindow(unittest.TestCase):

    def setUp(self):
        self.readListFromSettingsMock = patch('ReText.window.readListFromSettings', return_value=[]).start()
        self.writeListToSettingsMock  = patch('ReText.window.writeListToSettings').start()
        self.writeToSettingsMock      = patch('ReText.window.writeToSettings').start()
        self.globalSettingsMock       = patch('ReText.window.globalSettings', MagicMock(**ReText.configOptions)).start()
        self.fileSystemWatcherMock    = patch('ReText.window.QFileSystemWatcher').start()

    def tearDown(self):
        patch.stopall()


    #
    # Helper functions
    #

    @staticmethod
    def get_ui_enabled_states(window):
        enabled = set([])
        disabled = set([])

        for item in ('actionBold',
                     'actionCopy',
                     'actionCut',
                     'actionItalic',
                     'actionUnderline',
                     'actionUndo',
                     'actionRedo',
                     'actionReload',
                     'actionSave',
                     'actionSetEncoding',
                     'editBar',
                     'formattingBox',
                     'symbolBox'):
            if getattr(window, item).isEnabled():
                enabled.add(item)
            else:
                disabled.add(item)

        return enabled, disabled

    def check_widget_state(self, window, expected_enabled, expected_disabled):
        actually_enabled, actually_disabled = self.get_ui_enabled_states(window)

        self.assertEqual(expected_enabled - actually_enabled, set(), 'These widgets are unexpectedly disabled')
        self.assertEqual(expected_disabled - actually_disabled, set(), 'These widgets are unexpectedly enabled')

    def check_widgets_enabled_for_markdown(self, window):
        self.check_widget_state(window,
                                set(['actionBold', 'actionItalic', 'actionUnderline', 'formattingBox', 'symbolBox']),
                                set())

    def check_widgets_enabled_for_restructuredtext(self, window):
        self.check_widget_state(window,
                                set(['actionBold', 'actionItalic']),
                                set(['actionUnderline', 'formattingBox', 'symbolBox']))

    def check_widgets_enabled(self, window, widgets):
        self.check_widget_state(window,
                                set(widgets),
                                set())

    def check_widgets_disabled(self, window, widgets):
        self.check_widget_state(window,
                                set(),
                                set(widgets))


    #
    # Tests
    #

    def test_window_title_and_tabs__after_start_with_empty_tab(self):
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        self.assertEqual(1, self.window.tabWidget.count())
        self.assertEqual('New document[*]', self.window.windowTitle())
        self.assertFalse(self.window.currentTab.fileName)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_window_title_and_tabs__after_loading_file(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        # Check that file is opened in the existing empty tab
        self.assertEqual(1, self.window.tabWidget.count())
        self.assertEqual('existing_file.md[*]', self.window.windowTitle())
        self.assertTrue(self.window.currentTab.fileName.endswith('tests/testdata/existing_file.md'))

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_window_title_and_tabs__after_switching_tab(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        tab_with_file = self.window.currentTab

        self.window.createNew('bla')
        processEventsUntilIdle()

        tab_with_unsaved_content = self.window.currentTab

        self.assertEqual('New document[*]', self.window.windowTitle())
        self.assertTrue(self.window.currentTab is tab_with_unsaved_content)
        self.assertTrue(self.window.tabWidget.currentWidget().tab is tab_with_unsaved_content)

        self.window.switchTab()
        processEventsUntilIdle()

        self.assertEqual('existing_file.md[*]', self.window.windowTitle())
        self.assertTrue(self.window.currentTab is tab_with_file)
        self.assertTrue(self.window.tabWidget.currentWidget().tab is tab_with_file)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_active_tab__after_loading_file_that_is_already_open_in_other_tab(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()
        tab_with_file = self.window.currentTab

        self.window.createNew('')
        processEventsUntilIdle()

        # Make sure that the newly created tab is the active one
        self.assertFalse(self.window.currentTab.fileName)

        # Load the same document again
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        # Check that we have indeed been switched back to the previous tab
        self.assertTrue(self.window.currentTab is tab_with_file)
        self.assertTrue(self.window.currentTab.fileName.endswith('tests/testdata/existing_file.md'))

    def test_markup_dependent_widget_states__after_start_with_empty_tab_and_markdown_as_default_markup(self):
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        # markdown is the default markup
        self.check_widgets_enabled_for_markdown(self.window)

    def test_markup_dependent_widget_states__after_start_with_empty_tab_and_restructuredtext_as_default_markup(self):
        self.globalSettingsMock.defaultMarkup = 'reStructuredText'
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        self.check_widgets_enabled_for_restructuredtext(self.window)

    def test_markup_dependent_widget_states__after_changing_default_markup(self):
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        self.window.setDefaultMarkup(markups.ReStructuredTextMarkup)

        self.check_widgets_enabled_for_restructuredtext(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_markup_dependent_widget_states__after_loading_markdown_document(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        self.check_widgets_enabled_for_markdown(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.rst')], None))
    def test_markup_dependent_widget_states__after_loading_restructuredtext_document(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        self.check_widgets_enabled_for_restructuredtext(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', side_effect=[ ([os.path.join(path_to_testdata, 'existing_file.md')], None),
                                                                       ([os.path.join(path_to_testdata, 'existing_file.rst')], None) ])
    def test_markup_dependent_widget_states__after_switching_tab(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        # Just to make sure that sending two actionOpen triggers has had the desired effect
        self.assertIn('.rst', self.window.windowTitle())

        self.window.switchTab()
        processEventsUntilIdle()

        self.assertIn('.md', self.window.windowTitle())
        self.check_widgets_enabled_for_markdown(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    @patch('ReText.window.QFileDialog.getSaveFileName', return_value=(os.path.join(path_to_testdata, 'not_existing_file.rst'), None))
    def test_markup_dependent_widget_states__after_saving_document_as_different_markup(self, getOpenFileNamesMock, getSaveFileNameMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        try:
            self.window.actionSaveAs.trigger()
            processEventsUntilIdle()

        finally:
            os.remove(os.path.join(path_to_testdata, 'not_existing_file.rst'))

        self.check_widgets_enabled_for_restructuredtext(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    @patch('ReText.window.QFileDialog.getSaveFileName', return_value=(os.path.join(path_to_testdata, 'not_existing_file.md'), None))
    def test_save_widget_states(self, getOpenFileNamesMock, getSaveFileNameMock):
        self.window = ReTextWindow()

        # check if save is disabled at first
        self.window.createNew('')
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionSave',))

        # check if it's enabled after inserting some text
        self.window.currentTab.editBox.textCursor().insertText('some text')
        processEventsUntilIdle()
        self.check_widgets_enabled(self.window, ('actionSave',))

        # check if it's disabled again after loading a file in a second tab and switching to it
        self.window.actionOpen.trigger()
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionSave',))

        # check if it's enabled again after switching back
        self.window.switchTab()
        processEventsUntilIdle()
        self.check_widgets_enabled(self.window, ('actionSave',))

        # check if it's disabled after saving
        try:
            self.window.actionSaveAs.trigger()
            processEventsUntilIdle()
            self.check_widgets_disabled(self.window, ('actionSave',))
        finally:
            os.remove(os.path.join(path_to_testdata, 'not_existing_file.md'))

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    @patch('ReText.window.QFileDialog.getSaveFileName', return_value=(os.path.join(path_to_testdata, 'not_existing_file.md'), None))
    def test_save_widget_states__autosave_enabled(self, getOpenFileNamesMock, getSaveFileNameMock):
        self.globalSettingsMock.autoSave = True
        self.window = ReTextWindow()

        # check if save is disabled at first
        self.window.createNew('')
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionSave',))

        # check if it stays enabled after inserting some text (because autosave
        # can't save without a filename)
        self.window.currentTab.editBox.textCursor().insertText('some text')
        processEventsUntilIdle()
        self.check_widgets_enabled(self.window, ('actionSave',))

        # check if it's disabled after saving
        try:
            self.window.actionSaveAs.trigger()
            processEventsUntilIdle()
            self.check_widgets_disabled(self.window, ('actionSave',))

            # check if it is still disabled after inserting some text (because
            # autosave will take care of saving now that the filename is known)
            self.window.currentTab.editBox.textCursor().insertText('some text')
            processEventsUntilIdle()
            self.check_widgets_disabled(self.window, ('actionSave',))
        finally:
            os.remove(os.path.join(path_to_testdata, 'not_existing_file.md'))

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_encoding_and_reload_widget_states(self, getOpenFileNamesMock):
        self.window = ReTextWindow()

        # check if reload/set encoding is disabled for a tab without filename set
        self.window.createNew('')
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionReload','actionSetEncoding'))

        self.window.actionOpen.trigger()
        processEventsUntilIdle()
        self.check_widgets_enabled(self.window, ('actionReload','actionSetEncoding'))

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_encoding_and_reload_widget_states__always_disabled_when_autosave_enabled(self, getOpenFileNamesMock):
        self.globalSettingsMock.autoSave = True
        self.window = ReTextWindow()

        # check if reload/set encoding is disabled for a tab without filename set
        self.window.createNew('')
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionReload','actionSetEncoding'))

        self.window.actionOpen.trigger()
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionReload','actionSetEncoding'))

if __name__ == '__main__':
    unittest.main()

