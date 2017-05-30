# This file is part of ReText
# Copyright: 2015 Dmitry Shachnev
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

# This is implementation of XSettings specification, described at
# <http://standards.freedesktop.org/xsettings-spec/xsettings-spec-0.5.html>

import ctypes
import ctypes.util
import struct

class _xcb_reply_t(ctypes.Structure):
	# this can be used instead of xcb_intern_atom_reply_t,
	# xcb_get_selection_owner_reply_t, etc
	_fields_ = [('response_type', ctypes.c_uint8),
	            ('pad0',          ctypes.c_uint8),
	            ('sequence',      ctypes.c_uint16),
	            ('length',        ctypes.c_uint32),
	            ('payload',       ctypes.c_uint32)]

class _xcb_cookie_t(ctypes.Structure):
	# this can be used instead of xcb_intern_atom_cookie_t,
	# xcb_get_selection_owner_cookie_t, etc
	_fields_ = [('sequence',      ctypes.c_uint)]

_xcb_error_messages = [
	None,
	'XCB error: socket, pipe and other stream error',
	'XCB connection closed: extension unsupported',
	'XCB connection closed: insufficient memory',
	'XCB connection closed: request length exceeded',
	'XCB connection closed: DISPLAY parse error',
	'XCB connection closed: invalid screen'
]

class XSettingsError(RuntimeError):
	pass

class XSettingsParseError(XSettingsError):
	pass

def get_raw_xsettings(display=0):
	# initialize the libraries
	xcb_library_name = ctypes.util.find_library('xcb')
	if xcb_library_name is None:
		raise XSettingsError('Xcb library not found')
	xcb = ctypes.CDLL(xcb_library_name)

	c_library_name = ctypes.util.find_library('c')
	if c_library_name is None:
		raise XSettingsError('C library not found')
	c = ctypes.CDLL(c_library_name)

	# set some args and return types
	c.free.argtypes = [ctypes.c_void_p]
	c.free.restype = None
	xcb.xcb_connect.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
	xcb.xcb_connect.restype = ctypes.c_void_p
	xcb.xcb_connection_has_error.argtypes = [ctypes.c_void_p]
	xcb.xcb_connection_has_error.restype = ctypes.c_int
	xcb.xcb_disconnect.argtypes = [ctypes.c_void_p]
	xcb.xcb_disconnect.restype = None
	xcb.xcb_intern_atom.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint16, ctypes.c_char_p]
	xcb.xcb_intern_atom.restype = _xcb_cookie_t
	xcb.xcb_intern_atom_reply.argtypes = [ctypes.c_void_p, _xcb_cookie_t, ctypes.c_void_p]
	xcb.xcb_intern_atom_reply.restype = ctypes.POINTER(_xcb_reply_t)
	xcb.xcb_get_selection_owner.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
	xcb.xcb_get_selection_owner.restype = _xcb_cookie_t
	xcb.xcb_get_selection_owner_reply.argtypes = [ctypes.c_void_p, _xcb_cookie_t, ctypes.c_void_p]
	xcb.xcb_get_selection_owner_reply.restype = ctypes.POINTER(_xcb_reply_t)
	xcb.xcb_get_property.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint32, ctypes.c_uint32,
	                                 ctypes.c_uint32, ctypes.c_uint32]
	xcb.xcb_get_property.restype = _xcb_cookie_t
	xcb.xcb_get_property_reply.argtypes = [ctypes.c_void_p, _xcb_cookie_t, ctypes.c_void_p]
	xcb.xcb_get_property_reply.restype = ctypes.c_void_p
	xcb.xcb_get_property_value_length.argtypes = [ctypes.c_void_p]
	xcb.xcb_get_property_value_length.restype = ctypes.c_int
	xcb.xcb_get_property_value.argtypes = [ctypes.c_void_p]
	xcb.xcb_get_property_value.restype = ctypes.c_void_p

	# open the connection
	connection = xcb.xcb_connect(None, None)
	error = xcb.xcb_connection_has_error(connection)
	if error:
		raise XSettingsError(_xcb_error_messages[error])

	# get selection atom cookie
	buffer = ('_XSETTINGS_S%d' % display).encode()
	cookie = xcb.xcb_intern_atom(connection, 0, len(buffer), buffer)

	# get selection atom reply
	reply = xcb.xcb_intern_atom_reply(connection, cookie, None)
	selection_atom = reply.contents.payload
	c.free(reply)

	# get selection owner cookie
	cookie = xcb.xcb_get_selection_owner(connection, selection_atom)

	# get selection owner reply
	reply = xcb.xcb_get_selection_owner_reply(connection, cookie, None)
	window = reply.contents.payload
	c.free(reply)

	# get settings atom cookie
	buffer = b'_XSETTINGS_SETTINGS'
	cookie = xcb.xcb_intern_atom(connection, 0, len(buffer), buffer)

	# get settings atom reply
	reply = xcb.xcb_intern_atom_reply(connection, cookie, None)
	settings_atom = reply.contents.payload
	c.free(reply)

	# get property cookie
	cookie = xcb.xcb_get_property(connection, 0, window, settings_atom, 0, 0, 0x2000)

	# get property reply
	reply = xcb.xcb_get_property_reply(connection, cookie, None)
	if reply is not None:
		length = xcb.xcb_get_property_value_length(reply)
		pointer = xcb.xcb_get_property_value(reply) if length else None
		result = ctypes.string_at(pointer, length)
		c.free(reply)

	# close the connection
	xcb.xcb_disconnect(connection)

	# handle possible errors
	if reply is None or not length:
		raise XSettingsError('XSettings not available')

	return result

def parse_xsettings(raw_xsettings):
	if len(raw_xsettings) < 12:
		raise XSettingsParseError('length < 12')

	if raw_xsettings[0] not in (0, 1):
		raise XSettingsParseError('wrong order byte: %d' % raw_xsettings[0])
	byte_order = '<>'[raw_xsettings[0]]
	settings_count = struct.unpack(byte_order + 'I', raw_xsettings[8:12])[0]

	TypeInteger, TypeString, TypeColor = range(3)
	result = {}

	raw_xsettings = raw_xsettings[12:]
	offset = 0
	for i in range(settings_count):
		setting_type = raw_xsettings[offset]
		offset += 2
		name_length = struct.unpack(byte_order + 'H', raw_xsettings[offset:offset + 2])[0]
		offset += 2
		name = raw_xsettings[offset:offset + name_length]
		offset += name_length
		if offset & 3:
			offset += 4 - (offset & 3)
		offset += 4     # skip last-change-serial

		if setting_type == TypeInteger:
			value = struct.unpack(byte_order + 'I', raw_xsettings[offset:offset + 4])[0]
			offset += 4
		elif setting_type == TypeString:
			value_length = struct.unpack(byte_order + 'I', raw_xsettings[offset:offset + 4])[0]
			offset += 4
			value = raw_xsettings[offset:offset + value_length]
			offset += value_length
			if offset & 3:
				offset += 4 - (offset & 3)
		elif setting_type == TypeColor:
			value = struct.unpack(byte_order + 'HHHH', raw_xsettings[offset:offset + 8])
			offset += 8
		else:
			raise XSettingsParseError('Wrong setting type: %d' % setting_type)
		result[name] = value
	return result

def get_xsettings(display=0):
	raw_xsettings = get_raw_xsettings(display)
	return parse_xsettings(raw_xsettings)
