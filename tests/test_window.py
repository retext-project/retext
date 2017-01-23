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

from contextlib import suppress
import markups
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
import warnings

from markups.abstract import ConvertedMarkup

from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import QApplication
import ReText
from ReText.window import ReTextWindow

defaultEventTimeout = 0.0
path_to_testdata = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testdata')

if hasattr(Qt, 'AA_ShareOpenGLContexts'):
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication.instance() or QApplication(sys.argv)
ReText.initializeDataDirs()

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

class FakeConverterProcess(QObject):
    conversionDone = pyqtSignal()

    def start_conversion(self, name, filename, extensions, text):
        self.conversionDone.emit()

    def get_result(self):
        return ConvertedMarkup('')

@patch('ReText.tab.converterprocess.ConverterProcess', FakeConverterProcess)
class TestWindow(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter("ignore", Warning)
        self.readListFromSettingsMock = patch('ReText.window.readListFromSettings', return_value=[]).start()
        self.writeListToSettingsMock  = patch('ReText.window.writeListToSettings').start()
        self.globalSettingsMock       = patch('ReText.window.globalSettings', MagicMock(**ReText.configOptions)).start()
        self.fileSystemWatcherMock    = patch('ReText.window.QFileSystemWatcher').start()
        ReText.tab.globalSettings = self.globalSettingsMock

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

    def test_windowTitleAndTabs_afterStartWithEmptyTab(self):
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        self.assertEqual(1, self.window.tabWidget.count())
        self.assertEqual('New document[*]', self.window.windowTitle())
        self.assertFalse(self.window.currentTab.fileName)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_windowTitleAndTabs_afterLoadingFile(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        # Check that file is opened in the existing empty tab
        self.assertEqual(1, self.window.tabWidget.count())
        self.assertEqual('existing_file.md[*]', self.window.windowTitle())
        self.assertTrue(self.window.currentTab.fileName.endswith('tests/testdata/existing_file.md'))
        self.assertFalse(self.window.isWindowModified())

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_windowTitleAndTabs_afterSwitchingTab(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        tab_with_file = self.window.currentTab

        self.window.createNew('bla')
        processEventsUntilIdle()

        tab_with_unsaved_content = self.window.currentTab

        self.assertEqual('New document[*]', self.window.windowTitle())
        self.assertIs(self.window.currentTab, tab_with_unsaved_content)
        self.assertIs(self.window.tabWidget.currentWidget(), tab_with_unsaved_content)

        self.window.switchTab()
        processEventsUntilIdle()

        self.assertEqual('existing_file.md[*]', self.window.windowTitle())
        self.assertIs(self.window.currentTab, tab_with_file)
        self.assertIs(self.window.tabWidget.currentWidget(), tab_with_file)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_activeTab_afterLoadingFileThatIsAlreadyOpenInOtherTab(self, getOpenFileNamesMock):
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
        self.assertIs(self.window.currentTab, tab_with_file)
        self.assertTrue(self.window.currentTab.fileName.endswith('tests/testdata/existing_file.md'))

    def test_markupDependentWidgetStates_afterStartWithEmptyTabAndMarkdownAsDefaultMarkup(self):
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        # markdown is the default markup
        self.check_widgets_enabled_for_markdown(self.window)

    def test_markupDependentWidgetStates_afterStartWithEmptyTabAndRestructuredtextAsDefaultMarkup(self):
        self.globalSettingsMock.defaultMarkup = 'reStructuredText'
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        self.check_widgets_enabled_for_restructuredtext(self.window)

    def test_markupDependentWidgetStates_afterChangingDefaultMarkup(self):
        self.window = ReTextWindow()
        self.window.createNew('')
        processEventsUntilIdle()

        self.window.setDefaultMarkup(markups.ReStructuredTextMarkup)

        self.check_widgets_enabled_for_restructuredtext(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_markupDependentWidgetStates_afterLoadingMarkdownDocument(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        self.check_widgets_enabled_for_markdown(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.rst')], None))
    def test_markupDependentWidgetStates_afterLoadingRestructuredtextDocument(self, getOpenFileNamesMock):
        self.window = ReTextWindow()
        self.window.createNew('')
        self.window.actionOpen.trigger()
        processEventsUntilIdle()

        self.check_widgets_enabled_for_restructuredtext(self.window)

    @patch('ReText.window.QFileDialog.getOpenFileNames', side_effect=[ ([os.path.join(path_to_testdata, 'existing_file.md')], None),
                                                                       ([os.path.join(path_to_testdata, 'existing_file.rst')], None) ])
    def test_markupDependentWidgetStates_afterSwitchingTab(self, getOpenFileNamesMock):
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
    def test_markupDependentWidgetStates_afterSavingDocumentAsDifferentMarkup(self, getOpenFileNamesMock, getSaveFileNameMock):
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
    def test_saveWidgetStates(self, getOpenFileNamesMock, getSaveFileNameMock):
        self.window = ReTextWindow()

        # check if save is disabled at first
        self.window.createNew('')
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionSave',))
        self.assertFalse(self.window.isWindowModified())

        # check if it's enabled after inserting some text
        self.window.currentTab.editBox.textCursor().insertText('some text')
        processEventsUntilIdle()
        self.check_widgets_enabled(self.window, ('actionSave',))
        self.assertTrue(self.window.isWindowModified())

        # check if it's disabled again after loading a file in a second tab and switching to it
        self.window.actionOpen.trigger()
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionSave',))
        self.assertFalse(self.window.isWindowModified())

        # check if it's enabled again after switching back
        self.window.switchTab()
        processEventsUntilIdle()
        self.check_widgets_enabled(self.window, ('actionSave',))
        self.assertTrue(self.window.isWindowModified())

        # check if it's disabled after saving
        try:
            self.window.actionSaveAs.trigger()
            processEventsUntilIdle()
            self.check_widgets_disabled(self.window, ('actionSave',))
            self.assertFalse(self.window.isWindowModified())
        finally:
            os.remove(os.path.join(path_to_testdata, 'not_existing_file.md'))

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    @patch('ReText.window.QFileDialog.getSaveFileName', return_value=(os.path.join(path_to_testdata, 'not_existing_file.md'), None))
    def test_saveWidgetStates_autosaveEnabled(self, getOpenFileNamesMock, getSaveFileNameMock):
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
    def test_encodingAndReloadWidgetStates(self, getOpenFileNamesMock):
        self.window = ReTextWindow()

        # check if reload/set encoding is disabled for a tab without filename set
        self.window.createNew('')
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionReload','actionSetEncoding'))

        self.window.actionOpen.trigger()
        processEventsUntilIdle()
        self.check_widgets_enabled(self.window, ('actionReload','actionSetEncoding'))

    @patch('ReText.window.QFileDialog.getOpenFileNames', return_value=([os.path.join(path_to_testdata, 'existing_file.md')], None))
    def test_encodingAndReloadWidgetStates_alwaysDisabledWhenAutosaveEnabled(self, getOpenFileNamesMock):
        self.globalSettingsMock.autoSave = True
        self.window = ReTextWindow()

        # check if reload/set encoding is disabled for a tab without filename set
        self.window.createNew('')
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionReload','actionSetEncoding'))

        self.window.actionOpen.trigger()
        processEventsUntilIdle()
        self.check_widgets_disabled(self.window, ('actionReload','actionSetEncoding'))

    def test_doesNotTweakSpecialCharacters(self):
        fileName = tempfile.mkstemp(suffix='.mkd')[1]
        content = 'Non-breaking\u00a0space\n\nLine\u2028separator\n'
        with open(fileName, 'w', encoding='utf-8') as tempFile:
            tempFile.write(content)
        window = ReTextWindow()
        window.openFileWrapper(fileName)
        self.assertTrue(window.saveFile())
        with open(fileName, encoding='utf-8') as tempFile:
            self.assertMultiLineEqual(content, tempFile.read())
        with suppress(PermissionError):
            os.remove(fileName)


if __name__ == '__main__':
    unittest.main()

