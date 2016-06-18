# This file is part of ReText
# Copyright: 2016 Hong-She Liang
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

import functools
import struct
from PyQt5.QtCore import pyqtSignal, QObject, QSharedMemory, QSystemSemaphore
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

class SingleApplication(QObject):
	"""
	SingleApplication is a class that wrap around the single application
	framework.
	"""

	# Modes
	(
		# Server mode indicated that we started the first application
		Server,
		# Client mode means that another App already started, we should just
		# exit or send some message to that App.
		Client,
	) = range(0, 2)

	# Signals

	receivedMessage = pyqtSignal(bytes)

	def __init__(self, name, parent=None):
		QObject.__init__(self, parent)
		self._name = name
		self._mode = self.Server
		self._sharedMemory = QSharedMemory(self._name)
		self._systemSemaphore = QSystemSemaphore(self._name + "-2", 1)
		self._server = None
		self._client = None
		self._localSockets = {}

		# Fix for *nix:
		# http://stackoverflow.com/questions/5006547/qt-best-practice-for-a-single-instance-app-protection
		# http://habrahabr.ru/post/173281/

		self._systemSemaphore.acquire();
		try:
			unixFix = QSharedMemory(self._name)
			unixFix.attach()
			unixFix.detach()
			unixFix = None
		finally:
			self._systemSemaphore.release();

	@property
	def name(self):
		return self._name

	@property
	def mode(self):
		return self._mode

	def _onLocalSocketReadyRead(self, localSocket):
		if localSocket.bytesAvailable() <= 0:
			return

		self._localSockets[localSocket] += localSocket.readAll()
		data = self._localSockets[localSocket]
		if len(data) > 4:
			# First 4bytes is a native Integer.
			dataSize = struct.unpack("@I", data[:4])[0]
			receivedDataSize = len(data) - 4
			if receivedDataSize < dataSize:
				return

			self.receivedMessage.emit(bytes(data[4:]))

			# Remove the command socket
			del self._localSockets[localSocket]
			localSocket.deleteLater()

	def _onServerNewConnection(self):
		while self._server.hasPendingConnections():
			localSocket = self._server.nextPendingConnection()
			self._localSockets[localSocket] = b""
			localSocket.readyRead.connect(functools.partial(
				self._onLocalSocketReadyRead, localSocket))

	def start(self):
		# Ensure we run only one application
		isAnotherRunning = False
		if not self._sharedMemory.isAttached():
			# If shared memory is attachable, that means there exists another
			# running application
			self._systemSemaphore.acquire()
			try:
				isAnotherRunning = self._sharedMemory.attach()
				if isAnotherRunning:
					self._sharedMemory.detach()
			finally:
				self._systemSemaphore.release()

		if not isAnotherRunning:
			# If we already attached by previous attach test, we will create
			# the shared memory.
			self._systemSemaphore.acquire()
			try:
				isAnotherRunning = not self._sharedMemory.create(1, QSharedMemory.ReadWrite)
			finally:
				self._systemSemaphore.release()

			# If there something happened during create procedure lead us can't
			# create one, we should detach that shared memory.
			if isAnotherRunning:
				self._systemSemaphore.acquire()
				try:
					if self._sharedMemory.isAttached():
						self._sharedMemory.detach()
				finally:
					self._systemSemaphore.release();

		# Fine, now we could take different action on different situation.
		if isAnotherRunning:
			# Detach immediately if create failed.
			#
			# WARNING: On windows os, seems if we don't detach the shared memory
			# after failed to create, another ReText can't create the shared
			# memory after original instance exitted while there still have
			# ReText as client.

			self._mode = self.Client
			self._client = QLocalSocket(self)
			self._client.connectToServer(self._name)
		else:
			self._mode = self.Server
			self._server = QLocalServer(self)
			self._server.newConnection.connect(self._onServerNewConnection)
			# Access is restricted to the same user as the process that created
			# the socket.
			self._server.setSocketOptions(QLocalServer.UserAccessOption)
			if not self._server.listen(self._name):
				# Failed to listen, is there have another application crashed
				# without normally shutdown it's server?
				#
				# We try to remove the old dancing server and restart a new
				# server.
				self._server.removeServer(self._name)
				if not self._server.listen(self._name):
					raise RuntimeError("Local server failed to listen on '%s'" % self._name)

	def sendMessage(self, message):
		# Only accept bytes message
		if not isinstance(message, bytes):
			raise TypeError("message must be bytes type!")

		data = struct.pack("@I%ss" % len(message), len(message), message)
		self._client.write(data)
