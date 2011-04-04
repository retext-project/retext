#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ReText webpages generator
# Copyright 2011 Dmitry Shachnev

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
import markdown

md = markdown.Markdown()

app_name = "ReText Webpages generator"
app_version = "0.3.0"
app_site = "http://sourceforge.net/p/retext/"

if sys.platform == "linux2" and os.path.exists("/usr/share/wpgen/"):
	templates_dir = "/usr/share/wpgen/"
else:
	templates_dir = "templates/"

class WebLibrary(object):
	def __init__(self):
		self.dirPath = "."
	
	def setDir(self, dirPath):
		"""Set the working directory to dirPath
		dirPath: relative or absolute path to directory"""
		if os.path.exists(dirPath):
			self.dirPath = dirPath
	
	def updateAll(self):
		"""Process all documents in the directory"""
		self._initTemplate()
		for fname in filter(os.path.isfile, os.listdir(self.dirPath)):
			self._processPage(fname)
	
	def update(self, pageName):
		"""Process document pageName.re or pageName in the directory
		pageName: basename of the page file"""
		self._initTemplate()
		if os.path.exists(self.dirPath+"/"+pageName+".re"):
			self._processPage(pageName+".re")
		elif os.path.exists(self.dirPath+"/"+pageName):
			self._processPage(pageName)
	
	def _initTemplate(self):
		templatefile = open(self.dirPath+"/template.html", "r")
		self.template = unicode(templatefile.read(), 'utf-8')
		templatefile.close()
		self.template = self.template.replace("%GENERATOR%", app_name + " " + app_version)
		self.template = self.template.replace("%APPINFO%", "<a href=\""+ app_site + "\">" + app_name + "</a> " + app_version)
	
	def _processPage(self, fname):
		bn, ext = os.path.splitext(fname)
		html = None
		if ext == ".re" or ext == ".md":
			inputfile = open(self.dirPath+"/"+fname, "r")
			html = md.convert(unicode(inputfile.read(), 'utf-8'))
			inputfile.close()
		elif ext == ".html" and bn != "template":
			inputfile = open(self.dirPath+"/"+fname, "r")
			html = unicode(inputfile.read(), 'utf-8')
			inputfile.close()
		if html:
			content = self.template
			content = content.replace("%CONTENT%", html)
			content = content.replace("%PAGENAME%", bn)
			content = content.replace("<a href=\""+bn+".html\">", "<a>")
			outputfile = open(self.dirPath+"/html/"+bn+".html", "w")
			outputfile.write(content.encode('utf-8'))
			outputfile.close()

def main(argv):
	if len(argv) > 1:
		if argv[1] == "updateall":
			wl = WebLibrary()
			wl.updateAll()
		elif argv[1] == "update" and len(argv) > 2:
			wl = WebLibrary()
			for i in argv[2:]:
				wl.update(i)
		elif argv[1] == "init":
			if not os.path.exists("html"):
				os.mkdir("html")
			shutil.copy(templates_dir+"template_Default.html", "template.html")
			shutil.copy(templates_dir+"style_Default.css", "html/style.css")
			if not os.path.exists("index.re"):
				index = open("index.re", "w")
				index.close()
		elif argv[1] == "usestyle" and len(argv) == 3:
			if os.path.exists(templates_dir+"style_"+argv[2]+".css"):
				shutil.copy(templates_dir+"style_"+argv[2]+".css", "html/style.css")
		else:
			printUsage()
	else:
		printUsage()

def printUsage():
	print(app_name + ", version " + app_version + "\n")
	print("Usage: wpgen command")
	print("Available commands:")
	print("  init - create new web library")
	print("  updateall - generate html files from all pages")
	print("  update [pagename] - generate html file from pagename.re page")
	print("  usestyle [stylename] - use the given style (example: Default, Simple)")

if __name__ == '__main__':
	main(sys.argv)
