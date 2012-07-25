#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ReText webpages generator
# Copyright 2011-2012 Dmitry Shachnev

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

import os
import sys
import shutil
from markups.web import WebLibrary

app_name = "ReText Webpages generator"
app_version = "0.6 (Git)"
app_data = (
	app_name,
	app_version,
	"http://sourceforge.net/p/retext/"
)

if os.path.exists("/usr/share/wpgen/"):
	templates_dir = "/usr/share/wpgen/"
else:
	templates_dir = "templates/"

def main(argv):
	if len(argv) > 1:
		if argv[1] in ('updateall', 'update', 'usestyle') and not os.path.exists("html"):
			print("Could not find html directory!")
			return
		if argv[1] == "updateall":
			wl = WebLibrary(app_data=app_data)
			try:
				wl.update_all()
			except IOError as e:
				print(e)
		elif argv[1] == "update" and len(argv) > 2:
			wl = WebLibrary(app_data=app_data)
			for i in argv[2:]:
				try:
					wl.update(i)
				except IOError as e:
					print(e)
		elif argv[1] == "init":
			if not os.path.exists("html"):
				os.mkdir("html")
			shutil.copy(templates_dir+"template_Default.html", "template.html")
			shutil.copy(templates_dir+"style_Default.css", "html/style.css")
		elif argv[1] == "usestyle" and len(argv) == 3:
			if os.path.exists(templates_dir+"style_"+argv[2]+".css"):
				shutil.copy(templates_dir+"style_"+argv[2]+".css", "html/style.css")
			else:
				print('Error: no such file!')
		else:
			printUsage()
	else:
		printUsage()

def printUsage():
	print(app_name + ", version " + app_version)
	print("Usage: wpgen COMMAND <ARGUMENTS>")
	print("")
	print("Available commands:")
	print("  init - create new web library")
	print("  updateall - generate html files from all pages")
	print("  update [filename] - generate html file from given file")
	print("  usestyle [stylename] - use the given style (example: Default, Simple)")

if __name__ == '__main__':
	main(sys.argv)
