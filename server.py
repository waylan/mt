#!/usr/bin/env python

import logging
import time
from threading import Timer
from tornado import websocket, web, ioloop
from tornado.options import define, options, parse_command_line
from tornado.log import LogFormatter

logger = logging.getLogger('meeting_timer')

define("port", default=8000, help="run on the given port", type=int)
define("host", default='0.0.0.0', help="run at the given address", type=str)


# Some Globals which get referenced by multiple WebSocketHandler instances.
clients = []
timer = None


def now():
    """ Return the current time in seconds since the epoch. """
    return int(time.time())


class Countdown(object):
    """
    Countdown timer starts immediatly on init from `start_value` and counts down
    to zero, then counts up with negated time. Only displays minutes and
    seconds. No pause or reset available. Each "tick" of the clock is passed to
    the callback function as a string. """
    
    def __init__(self, start_value, callback):
        self._finished = False
        self.start_value = start_value
        self.callback = callback
        self.start_time = now()
        self._update()

    def _update(self):
        self._set_time(now() - self.start_time)
        if not self._finished:
            self._timer = Timer(1, self._update)
            self._timer.start()

    def _set_time(self, value):
        neg = '' 
        if self.start_value > value:
            value = self.start_value - value
        elif self.start_value < value:
            value = value - self.start_value
            neg = '-'
        else:
            value = 0
        mm, ss = divmod(value, 60)
        self.callback("{}{:02d}:{:02d}".format(neg, mm, ss))

    def stop(self):
        self._timer.cancel()
        self._finished = True


class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")


class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        if self not in clients:
            logger.info('New client connected')
            clients.append(self)

    def push(self, msg):
        """ Push a message to all clients. """
        for client in clients:
            client.write_message(msg)
            logger.info('Server sent message: "{}"'.format(msg))

    def on_message(self, cmd):        
        logger.info('Server received command: "{}"'.format(cmd))
        global timer
        if cmd == 'start':
            # Start the timer
            timer = Countdown(10, self.push)
        elif cmd == 'next':
            # Start next timer
            timer.stop()
            timer = Countdown(70, self.push)
        else:
            # Stop the timer
            timer.stop()


    def on_close(self):
        if self in clients:
            logger.info('Client connection closed')
            clients.remove(self)


app = web.Application([
    (r'/', IndexHandler),
    (r'/ws', SocketHandler),
    (r'/(favicon.ico)', web.StaticFileHandler, {'path': './'}),
])


if __name__ == '__main__':
    parse_command_line()
    
    logger.info('Serving on http://{}:{}'.format(options.host, options.port))
    app.listen(options.port, options.host)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
            logger.info('Shutting down...')
