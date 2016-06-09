#!/usr/bin/env python3

import markups
import multiprocessing as mp
import pickle
import signal
import struct
import traceback
import weakref

try:
	from socket import socketpair
except ImportError:
	# Windows compatibility: socket.socketpair backport for Python < 3.5
	from backports.socketpair import socketpair

from PyQt5.QtCore import pyqtSignal, QObject, QSocketNotifier

def recvall(sock, remaining):
    alldata = bytearray()
    while remaining > 0:
        data = sock.recv(remaining)
        if len(data) == 0:
            raise EOFError('Received 0 bytes from socket while more bytes were expected. Did the sender process exit unexpectedly?')
        alldata.extend(data)
        remaining -= len(data)

    return alldata

def receiveObject(sock):
    sizeBuf = recvall(sock, 4)
    size = struct.unpack('I', sizeBuf)[0]
    message = recvall(sock, size)
    obj = pickle.loads(message)
    return obj

def sendObject(sock, obj):
    message = pickle.dumps(obj)
    sizeBuf = struct.pack('I', len(message))
    sock.sendall(sizeBuf)
    sock.sendall(message)

class ConversionError(Exception):
    pass

class MarkupNotAvailableError(Exception):
    pass

def _indent(text, prefix):
    return ''.join(('%s%s\n' % (prefix, line) for line in text.splitlines()))

def _converter_process_func(conn_parent, conn_child):
    conn_parent.close()

    # Ignore ctrl-C. The main application will also receive the signal and
    # determine if the application should be stopped or not.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    current_markup = None

    while True:
        job = receiveObject(conn_child)
        if job['command'] == 'quit':
            break
        elif job['command'] == 'convert':
            try:
                if (not current_markup or
                    current_markup.name != job['markup_name'] or
                    current_markup.filename != job['filename']):
                    markup_class = markups.find_markup_class_by_name(job['markup_name'])
                    if not markup_class.available():
                        raise MarkupNotAvailableError('The specified markup was not available')

                    current_markup = markup_class(job['filename'])
                    current_markup.requested_extensions = job['requested_extensions']

                converted = current_markup.convert(job['text'])
                result = ('ok', converted)
            except MarkupNotAvailableError as e:
                result = ('markupnotavailableerror', e.args)
            except Exception:
                result = ('conversionerror',
                          'The background markup conversion process received this exception:\n%s' %
                          _indent(traceback.format_exc(), '    '))

            try:
                sendObject(conn_child, result)
            except BrokenPipeError:
                # Continue despite the broken pipe because we expect that a
                # 'quit' command will have been sent. If it has been then we
                # should terminate without any error messages. If no command
                # was queued we will get an EOFError from the read, giving us a
                # second chance to show that something went wrong by exiting
                # with a traceback.
                continue


class ConverterProcess(QObject):

    conversionDone = pyqtSignal()

    def __init__(self):
        super(QObject, self).__init__()

        conn_parent, conn_child = socketpair()

        # TODO: figure out which of the two sockets should be set to 
        #       inheritable and which should be passed to the child
        if hasattr(conn_child, 'set_inheritable'):
            conn_child.set_inheritable(True)

        # Use a local variable for child so that we can talk to the child in
        # on_finalize without needing a reference to self
        child = mp.Process(target=_converter_process_func, args=(conn_parent, conn_child))
        child.daemon = True
        child.start()
        self.child = child

        conn_child.close()
        self.conn = conn_parent

        self.busy = False
        self.notificationPending = False
        self.conversionNotifier = QSocketNotifier(self.conn.fileno(),
                                                  QSocketNotifier.Read)
        self.conversionNotifier.activated.connect(self._conversionNotifierActivated)

        def on_finalize(conn):
            sendObject(conn_parent, {'command':'quit'})
            conn_parent.close()
            child.join()

        weakref.finalize(self, on_finalize, conn_parent)

    def _conversionNotifierActivated(self):
        # The ready-for-read signal on the socket may be triggered multiple
        # times, but we only send a single notification to the client as soon
        # as the results of the conversion are starting to come in. This makes
        # it easy for clients to avoid multiple calls to get_result for the
        # same conversion.
        if self.notificationPending:
            self.notificationPending = False

            # Set the socket to blocking before waking up any interested parties,
            # because it has been set to unblocking by QSocketNotifier
            self.conn.setblocking(True)
            self.conversionDone.emit()

    def start_conversion(self, markup_name, filename, requested_extensions, text):
        if self.busy:
            raise RuntimeError('Already converting')

        sendObject(self.conn, {'command': 'convert',
                               'markup_name' : markup_name,
                               'filename' : filename,
                               'requested_extensions' : requested_extensions,
                               'text' : text})
        self.busy = True
        self.notificationPending = True

    def get_result(self):
        if not self.busy:
            raise RuntimeError('No ongoing conversion')

        self.busy = False

        status, result = receiveObject(self.conn)

        if status == 'markupnotavailableerror':
            raise MarkupNotAvailableError(result)
        elif status == 'conversionerror':
            raise ConversionError(result)

        return result

    def stop(self):
        sendObject(self.conn, {'command': 'quit'})
        self.conn.close()

