import json
import logging
import tornadoredis
import tornado.ioloop
import tornado.web
import tornado.gen
from tornado import websocket
from tornado.options import define, options, parse_command_line
from functools import wraps

from .referee import Referee
from .game import Game, GameError
from .cache import Cache

define("redis_host", default="127.0.0.1", help="Reids host")
define("redis_port", default=6379, help="Reids port", type=int)
define("port", default=8881, help="Server port", type=int)

log = logging.getLogger('game')
log.setLevel(logging.DEBUG)

referee = Referee()
cache = Cache()
sockets = {}


def autorized(fun):
    @wraps(fun)
    def wrapper(self, *args, **kw):
        if self.username is None:
            self.write_message(dict(error='session_expirered'))
        else:
            return fun(self, self.username, *args, **kw)
    return wrapper


class ProtocolError(Exception): pass


class StatsHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def get(self):
        log.debug('stats {}'.format(self.request.arguments))
        self.write(referee.stats())
        self.finish()


class GameWebSocket(websocket.WebSocketHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def open(self):
        log.debug("WebSocket opened {}".format(hash(self)))
        self.username = None

    @tornado.web.asynchronous
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
        username = cache.get(sid)
        if username is None:
            username = yield tornado.gen.Task(redis.get, sid)
            cache.set(sid, username)
        if username is None:
            self.write_message(dict(error='session_expirered'))
            log.warning('session_error {}'.format(sid))
            return

        sockets[username] = self
        self.username = username
        field = referee.get_field(username)
        for y, row in enumerate(field):
            for x, c in enumerate(row):
                if c != ' ':
                    self.write_message(dict(reply='move', name=username,
                                            side=c, x=x, y=y))
        self.write_message(dict(reply='authorized', user=username))

    @autorized
    def _create(self, username, msg):
        referee.create_game(username, **msg)
        self.write_message(dict(reply='created'))

    @autorized
    def _join(self, username, msg):
        game = referee.join_game(username, **msg)
        for name in game.players:
            s = sockets.get(name)
            if s:
                s.write_message(dict(reply='joined', user=username))

    @tornado.gen.engine
    @autorized
    def _move(self, username, msg):
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        game, winner = referee.move(username, **msg)
        for name in game.players:
            s = sockets.get(name)
            if s:
                s.write_message(
                    dict(reply='move',
                         name=username,
                         side=game.players[username].side,
                         **msg
                         ))
            if winner:
                if s:
                    s.write_message(
                        dict(reply='finish',
                             winner=winner,
                             ))
                if winner == 'draw':
                    yield tornado.gen.Task(redis.zincrby, 'draw', name, 1)
                elif winner == name:
                    yield tornado.gen.Task(redis.zincrby, 'win', name, 1)
                else:
                    yield tornado.gen.Task(redis.zincrby, 'lose', name, 1)
                yield tornado.gen.Task(redis.zincrby, 'games', name, 1)

    @tornado.web.asynchronous
    @tornado.gen.engine
    def on_close(self):
        log.debug("WebSocket closed {}".format(hash(self)))
        if self.username:
            sockets.pop(self.username, None)
            self.user = None


if __name__ == '__main__':
    parse_command_line()
    application = tornado.web.Application([
        (r'/ws', GameWebSocket),
        (r'/stats', StatsHandler),
        ])
    application.listen(options.port)
    log.info('Game started on: {}'.format(options.port))

    tornado.ioloop.IOLoop.instance().start()
