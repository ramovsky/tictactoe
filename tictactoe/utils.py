import uuid
import json
import logging
import tornado.websocket
import tornadoredis
import tornado.gen
from functools import wraps
from tornado.options import define, options, parse_command_line


log = logging.getLogger('utils')
log.setLevel(logging.ERROR)
sockets = {}


def get_sid():
    return str(uuid.uuid4()).replace('-', '')


def authorized(fun):
    @wraps(fun)
    def wrapper(self, *args, **kw):
        if self.username is None:
            self.write_message(dict(error='session_expirered'))
        else:
            return fun(self, self.username, *args, **kw)
    return wrapper


class GameError(Exception): pass


class WSBase(tornado.websocket.WebSocketHandler):

    def open(self):
        log.debug("WebSocket opened {}".format(hash(self)))
        self.username = None

    @tornado.gen.engine
    def on_message(self, message):
        log.debug("WebSocket message {}".format(message))
        try:
            msg = json.loads(message)
            cmd = msg.pop('cmd')
            getattr(self, '_'+cmd)(msg)
        except (ValueError, KeyError):
            self.write_message(dict(error='protocol_error'))
            log.error('protocol_error {}'.format(message))
        except AttributeError:
            self.write_message(dict(error='unknown_command'))
            log.error('unknown_command {}'.format(message))
        except GameError as e:
            self.write_message(dict(error=e.message))
            log.warning('game_erroor {}, msg {}'.format(e.message, message))

    @tornado.gen.engine
    def _auth(self, msg):
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        sid = msg['sid']
        username = yield tornado.gen.Task(redis.get, sid)
        if username is None:
            self.write_message(dict(error='session_expirered'))
            log.warning('session_error {}'.format(sid))
            return

        sockets[username] = self
        self.username = username
        self.write_message(dict(reply='authorized', user=username))

    def on_close(self):
        log.debug("WebSocket closed {}".format(hash(self)))
        if self.username:
            sockets.pop(self.username, None)
            self.username = None
