# This file is part of ReText
# Copyright: 2026 ReText project
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

import json
from urllib.parse import parse_qs

from PyQt6.QtCore import QUrl

TOGGLE_URL_SCHEME = 'retext-heading-toggle'


class HeadingCollapseState:
    """
    Tracks which preview sections the user has collapsed or expanded, so
    that the state can be re-applied after the live preview HTML is
    regenerated (which happens on every edit, via a full reload of the
    QWebEngineView).
    """

    def __init__(self):
        self.overrides = {}
        self.bulkState = None

    def toggle(self, sectionId, collapsed):
        self.overrides[sectionId] = collapsed

    def setBulk(self, collapsed):
        # "Collapse all" / "Expand all": forget any individual overrides,
        # they would otherwise contradict the newly requested bulk state.
        self.bulkState = collapsed
        self.overrides.clear()

    def clear(self):
        self.overrides.clear()
        self.bulkState = None

    def toJsonBlob(self, initialCollapsed):
        data = {
            'overrides': self.overrides,
            'bulkState': self.bulkState,
            'initialCollapsed': initialCollapsed,
        }
        blob = json.dumps(data)
        # json.dumps() escapes the blob for JavaScript string/object syntax,
        # but not for the surrounding HTML parser: a heading containing a
        # literal "</script>" (e.g. decoded back from an escaped code span
        # via .textContent) could otherwise terminate the <script> tag early
        # on the next regeneration and inject arbitrary markup.
        return blob.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def parseToggleUrl(url: QUrl):
    """
    Parse a 'retext-heading-toggle://x?id=...&state=0|1' URL, as emitted by
    the script injected into the preview page when a heading is clicked.

    Returns a (sectionId, collapsed) tuple, or None if the URL does not use
    our custom scheme or does not have the expected query parameters.
    """
    if url.scheme() != TOGGLE_URL_SCHEME:
        return None
    query = parse_qs(url.query(QUrl.ComponentFormattingOption.FullyEncoded))
    ids = query.get('id')
    states = query.get('state')
    if not ids or not states:
        return None
    return ids[0], states[0] == '1'


COLLAPSE_CSS = '''
.retext-heading-toggle {
    display: inline-block;
    width: 1em;
    margin-right: 0.2em;
    cursor: pointer;
    user-select: none;
}
'''

# %(stateBlob)s is substituted by build_headers(). Uses %-formatting rather
# than str.format()/f-strings to avoid having to escape the many literal
# curly braces in the JavaScript source below.
COLLAPSE_SCRIPT_TEMPLATE = '''
<script>
document.addEventListener("DOMContentLoaded", function() {
    var state = %(stateBlob)s;

    function levelOf(heading) {
        return parseInt(heading.tagName.substring(1), 10);
    }

    function isSectioningParent(container, heading) {
        return container !== document.body
            && container.firstElementChild === heading
            && (container.tagName === "SECTION"
                || (container.tagName === "DIV" && container.classList.contains("section")));
    }

    function scopeOf(heading) {
        var container = heading.parentElement;
        if (isSectioningParent(container, heading)) {
            // reStructuredText output nests each section (and its
            // subsections) inside a <section>/<div class="section">
            // alongside its heading: hiding the rest of the container
            // hides the subsections too, for free.
            return Array.from(container.children).slice(1);
        }
        // Markdown output is flat: collect siblings up to the next
        // heading of equal or lower level.
        var level = levelOf(heading);
        var nodes = [];
        var sibling = heading.nextElementSibling;
        while (sibling && !(/^H[1-6]$/.test(sibling.tagName) && levelOf(sibling) <= level)) {
            nodes.push(sibling);
            sibling = sibling.nextElementSibling;
        }
        return nodes;
    }

    var headings = Array.from(document.querySelectorAll("h1, h2, h3, h4, h5, h6"));
    var ancestorStack = [];
    var occurrences = {};
    var records = [];

    function applyVisibility() {
        records.forEach(function(record) {
            record.scope.forEach(function(node) {
                node.style.display = record.collapsed ? "none" : "";
            });
            record.toggle.textContent = record.collapsed ? "▸" : "▾";
        });
    }

    headings.forEach(function(heading) {
        var level = levelOf(heading);
        while (ancestorStack.length && ancestorStack[ancestorStack.length - 1].level >= level) {
            ancestorStack.pop();
        }
        // Stable id, computed from the heading text *before* the toggle
        // symbol below is inserted into the DOM, so it never depends on
        // the current collapsed/expanded state.
        var text = heading.textContent.trim();
        var path = ancestorStack.map(function(a) { return a.text; }).concat([text]).join(" > ");
        var occurrenceCount = occurrences[path] || 0;
        occurrences[path] = occurrenceCount + 1;
        var id = occurrenceCount === 0 ? path : path + "#" + occurrenceCount;

        var collapsed;
        if (Object.prototype.hasOwnProperty.call(state.overrides, id)) {
            collapsed = state.overrides[id];
        } else if (state.bulkState !== null) {
            collapsed = state.bulkState;
        } else {
            collapsed = state.initialCollapsed;
        }

        var toggle = document.createElement("span");
        toggle.className = "retext-heading-toggle";
        toggle.setAttribute("aria-hidden", "true");
        heading.insertBefore(toggle, heading.firstChild);

        var record = {id: id, collapsed: collapsed, toggle: toggle, scope: scopeOf(heading)};
        records.push(record);
        ancestorStack.push({level: level, text: text});

        toggle.addEventListener("click", function(event) {
            event.preventDefault();
            event.stopPropagation();
            record.collapsed = !record.collapsed;
            applyVisibility();
            var url = "retext-heading-toggle://x?id=" + encodeURIComponent(record.id)
                + "&state=" + (record.collapsed ? "1" : "0");
            window.location.href = url;
        });
    });

    applyVisibility();

    // Used by ReTextWebEnginePreview.setAllHeadingsCollapsed() for the
    // "Collapse all sections" / "Expand all sections" preview menu actions.
    window.retextSetAllCollapsed = function(collapsed) {
        records.forEach(function(record) { record.collapsed = collapsed; });
        applyVisibility();
    };
});
</script>
'''


def buildHeaders(initialCollapsed: bool, state: HeadingCollapseState) -> str:
    """
    Return the <style>/<script> block to inject into the live WebEngine
    preview when collapsible headings are enabled. Must never be included
    in exported or printed HTML.
    """
    script = COLLAPSE_SCRIPT_TEMPLATE % {'stateBlob': state.toJsonBlob(initialCollapsed)}
    return f'<style type="text/css">\n{COLLAPSE_CSS}</style>\n{script}'
