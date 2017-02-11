# This file is part of ReText
# Copyright: 2015-2016 Dmitry Shachnev
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

def get_from_xsettings():
	from ReText.xsettings import get_xsettings, XSettingsError
	try:
		xsettings = get_xsettings()
	except XSettingsError:
		return
	if b'Net/IconThemeName' in xsettings:
		return xsettings[b'Net/IconThemeName'].decode()
	if b'Net/FallbackIconTheme' in xsettings:
		return xsettings[b'Net/FallbackIconTheme'].decode()

def get_from_gsettings():
	try:
		from gi.repository import Gio
	except ImportError:
		return
	schema = 'org.gnome.desktop.interface'
	if schema in Gio.Settings.list_schemas():
		settings = Gio.Settings.new(schema)
		return settings.get_string('icon-theme')

def get_from_gtk():
	try:
		from gi import require_version
		require_version('Gtk', '3.0')
		from gi.repository import Gtk
	except (ImportError, ValueError):
		return
	settings = Gtk.Settings.get_default()
	return settings.get_property('gtk-icon-theme-name')

def get_icon_theme():
	return (get_from_xsettings()
	     or get_from_gsettings()
	     or get_from_gtk())
