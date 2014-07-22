# This file is part of ReText
# Copyright: Dmitry Shachnev 2012-2014
# License: GNU GPL v2 or higher

import os
import sys
import shutil
from glob import glob1
from functools import wraps
from markups.web import WebLibrary

templatesDir = os.path.abspath(os.path.dirname(sys.argv[0])) + "/templates/"
if not os.path.exists(templatesDir):
	templatesDir = "/usr/share/wpgen/"
if not os.path.exists(templatesDir):
	templatesDir = "/usr/local/share/wpgen/"

def handleErrors(functionIn):
	@wraps(functionIn)
	def functionOut(*args, **kwds):
		try:
			return functionIn(*args, **kwds)
		except IOError as e:
			print('Exception occured: %s' % e, file=sys.stderr)
	return functionOut

@handleErrors
def wpInit():
	if not os.path.exists("html"):
		os.mkdir("html")
	shutil.copy(templatesDir+"template_Default.html", "template.html")
	shutil.copy(templatesDir+"style_Default.css", "html/style.css")

@handleErrors
def wpUpdate(pages):
	wl = WebLibrary()
	for page in pages:
		wl.update(page)

@handleErrors
def wpUpdateAll():
	wl = WebLibrary()
	wl.update_all()

def wpUseStyle(styleName):
	if os.path.exists(templatesDir+"style_%s.css" % styleName):
		if not os.path.exists("html"):
			os.mkdir("html")
		shutil.copy(templatesDir+"style_%s.css" % styleName, "html/style.css")
	else:
		print('Error: no such style!', file=sys.stderr)

def wpListStyles():
	for fileName in glob1(templatesDir, "style_*.css"):
		print(fileName[6:-4])
