# This file is part of ReText
# Copyright: 2016-2023 Maurice van der Pot
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

import time
from bisect import bisect_left

from PyQt6.QtCore import QPoint


class SyncScroll:

    def __init__(self, previewFrame,
                       editorPositionToSourceLineFunc,
                       sourceLineToEditorPositionFunc,
                       setEditorScrollValueFunc=None):
        self.posmap = {}
        self.frame = previewFrame
        self.editorPositionToSourceLine = editorPositionToSourceLineFunc
        self.sourceLineToEditorPosition = sourceLineToEditorPositionFunc
        # Optional callback to set the editor vertical scroll value (in pixels)
        self._setEditorScrollValue = setEditorScrollValueFunc

        self.previewPositionBeforeLoad = QPoint()
        self.contentIsLoading = False

        self.editorViewportHeight = 0
        self.editorViewportOffset = 0
        self.editorCursorPosition = 0

        # Guards to prevent recursive scroll feedback loops
        self._updating_preview = False
        self._updating_editor = False

        # Cached orderings for mapping between preview positions and source lines
        self._posmap_lines = []
        self._preview_posmap = []
        self._preview_positions = []
        # Track preview scroll events triggered by editor updates to avoid
        # reacting to them again and creating feedback loops.
        self._preview_scroll_pending = None
        self._preview_scroll_pending_time = 0.0
        self._preview_scroll_pending_count = 0

        self.frame.contentsSizeChanged.connect(self._handlePreviewResized)
        self.frame.loadStarted.connect(self._handleLoadStarted)
        self.frame.loadFinished.connect(self._handleLoadFinished)

    def isActive(self):
        return bool(self.posmap)

    def handleEditorResized(self, editorViewportHeight):
        self.editorViewportHeight = editorViewportHeight
        self._updatePreviewScrollPosition()

    def handleEditorScrolled(self, editorViewportOffset):
        # If we are programmatically updating the editor due to preview scroll,
        # ignore this event to avoid feedback loops.
        if self._updating_editor:
            return
        self.editorViewportOffset = editorViewportOffset
        return self._updatePreviewScrollPosition()

    def handleCursorPositionChanged(self, editorCursorPosition):
        self.editorCursorPosition = editorCursorPosition
        return self._updatePreviewScrollPosition()

    def _handleLoadStarted(self):
        # Store the current scroll position so it can be restored when the new
        # content is presented
        self.previewPositionBeforeLoad = self.frame.scrollPosition()
        self.contentIsLoading = True

    def _handleLoadFinished(self):
        self.frame.setScrollPosition(self.previewPositionBeforeLoad)
        self.contentIsLoading = False
        self.frame.getPositionMap(self._setPositionMap)

    def _handlePreviewResized(self):
        self.frame.getPositionMap(self._setPositionMap)
        self._updatePreviewScrollPosition()
        if not self.posmap and self.frame.scrollPosition().y() == 0:
            self.frame.setScrollPosition(self.previewPositionBeforeLoad)

    def _linearScale(self, fromValue, fromMin, fromMax, toMin, toMax):
        fromRange = fromMax - fromMin
        toRange = toMax - toMin

        toValue = toMin

        if fromRange:
            toValue += ((fromValue - fromMin) * toRange) / float(fromRange)

        return toValue

    def _updatePreviewScrollPosition(self):
        self._preview_scroll_pending = None
        self._preview_scroll_pending_time = 0.0
        self._preview_scroll_pending_count = 0
        if not self.posmap:
            # Loading new content resets the scroll position to the top. If we
            # don't have a posmap to calculate the new best position, then
            # restore the position stored at the beginning of the load.
            if self.contentIsLoading:
                self.frame.setScrollPosition(self.previewPositionBeforeLoad)
            return

        textedit_pixel_to_scroll_to = self.editorCursorPosition

        if textedit_pixel_to_scroll_to < self.editorViewportOffset:
            textedit_pixel_to_scroll_to = self.editorViewportOffset

        last_viewport_pixel = self.editorViewportOffset + self.editorViewportHeight
        if textedit_pixel_to_scroll_to > last_viewport_pixel:
            textedit_pixel_to_scroll_to = last_viewport_pixel

        line_to_scroll_to = self.editorPositionToSourceLine(textedit_pixel_to_scroll_to)

        # Do a binary search through the posmap to find the nearest line above
        # and below the line to scroll to for which the rendered position is
        # known.
        posmap_lines = self._posmap_lines
        min_index = 0
        max_index = len(posmap_lines) - 1
        while max_index - min_index > 1:
            current_index = (min_index + max_index) // 2
            if posmap_lines[current_index] > line_to_scroll_to:
                max_index = current_index
            else:
                min_index = current_index

        # number of nearest line above and below for which we have a position
        min_line = posmap_lines[min_index]
        max_line = posmap_lines[max_index]

        min_textedit_pos = self.sourceLineToEditorPosition(min_line)
        max_textedit_pos = self.sourceLineToEditorPosition(max_line)

        # rendered pixel position of nearest line above and below
        min_preview_pos = self.posmap[min_line]
        max_preview_pos = self.posmap[max_line]

        # calculate rendered pixel position of line corresponding to cursor
        # (0 == top of document)
        preview_pixel_to_scroll_to = self._linearScale(textedit_pixel_to_scroll_to,
                                                      min_textedit_pos, max_textedit_pos,
                                                      min_preview_pos, max_preview_pos)

        distance_to_top_of_viewport_editor = textedit_pixel_to_scroll_to - self.editorViewportOffset
        distance_to_top_of_viewport_preview = distance_to_top_of_viewport_editor / self.frame.zoomFactor()
        preview_scroll_offset = preview_pixel_to_scroll_to - distance_to_top_of_viewport_preview

        self._preview_scroll_pending = preview_scroll_offset
        self._preview_scroll_pending_time = time.monotonic()
        self._preview_scroll_pending_count = 2
        pos = self.frame.scrollPosition()
        pos.setY(preview_scroll_offset)
        # Prevent preview→editor feedback while we adjust preview scroll
        self._updating_preview = True
        try:
            self.frame.setScrollPosition(pos)
        finally:
            self._updating_preview = False

    def _setPositionMap(self, posmap):
        self.posmap = posmap
        if posmap:
            self.posmap[0] = 0
        if self.posmap:
            self._posmap_lines = sorted(self.posmap.keys())
            preview_sorted = sorted(self.posmap.items(), key=lambda item: item[1])
            self._preview_posmap = [(preview, line) for line, preview in preview_sorted]
            self._preview_positions = [preview for preview, _ in self._preview_posmap]
        else:
            self._posmap_lines = []
            self._preview_posmap = []
            self._preview_positions = []

    def handlePreviewScrolled(self, previewScrollPosition):
        """
        Update editor scroll position based on preview scroll position.

        previewScrollPosition can be either a QPointF/QPoint or a numeric Y value.
        """
        if not self._setEditorScrollValue:
            return
        # Avoid reacting to our own preview updates
        if self._updating_preview:
            return
        if not self.posmap:
            return

        # Extract Y coordinate
        try:
            preview_y = previewScrollPosition.y()
        except AttributeError:
            preview_y = float(previewScrollPosition)

        if self._preview_scroll_pending_count:
            # Ignore preview scroll events that we triggered ourselves shortly
            # before, otherwise we end up driving the editor back to an older
            # position because of out-of-order posmap entries.
            if time.monotonic() - self._preview_scroll_pending_time <= 0.3:
                self._preview_scroll_pending_count -= 1
                if self._preview_scroll_pending_count <= 0:
                    self._preview_scroll_pending = None
                    self._preview_scroll_pending_time = 0.0
                return
            self._preview_scroll_pending = None
            self._preview_scroll_pending_time = 0.0
            self._preview_scroll_pending_count = 0

        if not self._preview_posmap:
            return

        self._preview_scroll_pending = None
        self._preview_scroll_pending_time = 0.0
        self._preview_scroll_pending_count = 0

        if len(self._preview_posmap) == 1:
            _, line = self._preview_posmap[0]
            editor_scroll_to = self.sourceLineToEditorPosition(line)
        else:
            index = bisect_left(self._preview_positions, preview_y)
            if index <= 0:
                min_preview_pos, min_line = self._preview_posmap[0]
                max_preview_pos, max_line = self._preview_posmap[1]
            elif index >= len(self._preview_posmap):
                min_preview_pos, min_line = self._preview_posmap[-2]
                max_preview_pos, max_line = self._preview_posmap[-1]
            else:
                min_preview_pos, min_line = self._preview_posmap[index - 1]
                max_preview_pos, max_line = self._preview_posmap[index]

            min_textedit_pos = self.sourceLineToEditorPosition(min_line)
            max_textedit_pos = self.sourceLineToEditorPosition(max_line)

            editor_scroll_to = self._linearScale(
                preview_y,
                min_preview_pos,
                max_preview_pos,
                min_textedit_pos,
                max_textedit_pos,
            )

        editor_scroll_value = int(editor_scroll_to)

        # Apply editor scroll with guard to avoid triggering editor→preview update
        self._updating_editor = True
        try:
            self._setEditorScrollValue(editor_scroll_value)
        finally:
            self._updating_editor = False
