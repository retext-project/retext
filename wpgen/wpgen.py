#!/usr/bin/python
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

try:
	import markdown
except:
	use_md = False
else:
	use_md = True

try:
	from docutils.core import publish_parts
except:
	use_docutils = False
else:
	use_docutils = True

app_name = "ReText Webpages generator"
app_version = "0.5.4"
app_site = "http://sourceforge.net/p/retext/"

if os.path.exists("/usr/share/wpgen/"):
	templates_dir = "/usr/share/wpgen/"
else:
	templates_dir = "templates/"

class WebLibrary(object):
	def __init__(self, directoryPath="."):
		"""Construct a new WebLibrary object"""
		self.dirPath = directoryPath
	
	def updateAll(self):
		"""Process all documents in the directory"""
		self._initTemplate()
		self._initExtensions()
		for fname in filter(os.path.isfile, os.listdir(self.dirPath)):
			self._processPage(fname)
	
	def update(self, fileName):
		"""Process fileName file in the directory"""
		self._initTemplate()
		self._initExtensions()
		if os.path.exists(self.dirPath+"/"+fileName):
			self._processPage(fileName)
	
	def _initExtensions(self):
		self.extensions = []
		extspath = self.dirPath+"/markdown-extensions.txt"
		if os.path.exists(extspath):
			extsfile = open(extspath)
			self.extensions = [ext.rstrip() for ext in extsfile]
			extsfile.close()
	
	def _initTemplate(self):
		templatefile = open(self.dirPath+"/template.html", "r")
		try:
			self.template = unicode(templatefile.read(), 'utf-8')
		except:
			# For Python 3
			self.template = templatefile.read()
		templatefile.close()
		self.template = self.template.replace("%GENERATOR%", app_name + " " + app_version)
		self.template = self.template.replace("%APPINFO%", "<a href=\""+ app_site + "\">" + app_name + "</a>")
	
	def _processPage(self, fname):
		bn, ext = os.path.splitext(fname)
		html = pagename = ''
		md = markdown.Markdown(self.extensions, output_format='html4')
		inputfile = open(self.dirPath+"/"+fname, "r")
		try:
			text = unicode(inputfile.read(), 'utf-8')
		except:
			# For Python 3
			text = inputfile.read()
		inputfile.close()
		if ext in (".md", ".mkd", ".re") and use_md:
			html = md.convert(text)
			try:
				pagename = str.join(' ', md.Meta['title'])
			except:
				pass
		elif ext in (".rst", ".rest") and use_docutils:
			parts = publish_parts(text, writer_name='html')
			html = parts['body']
			if parts['title']:
				pagename = parts['title']
		elif ext in (".htm", ".html") and bn != "template":
			html = text
		if pagename == '':
			pagename = bn
		if html or bn == "index":
			content = self.template
			content = content.replace("%CONTENT%", html)
			try:
				pagename = unicode(pagename, 'utf-8')
				bn = unicode(bn, 'utf-8')
			except:
				# Not needed for Python 3
				pass
			content = content.replace("%PAGENAME%", pagename)
			content = content.replace("%HTMLDIR%", ".")
			content = content.replace(" href=\""+bn+".html\"", "")
			content = content.replace("%\\", "%")
			outputfile = open(self.dirPath+"/html/"+bn+".html", "w")
			try:
				outputfile.write(content.encode('utf-8'))
			except:
				# For Python 3
				outputfile.write(content)
			outputfile.close()

def main(argv):
	if len(argv) > 1:
		if argv[1] in ('updateall', 'update', 'usestyle') and not os.path.exists("html"):
			print("Could not find html directory!")
			return
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
