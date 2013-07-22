import json
import logging
import tornadoredis
import tornado.ioloop
import tornado.web
import tornado.gen
from tornado import websocket
from tornado.options import define, options, parse_command_line

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


class ProtocolError(Exception): pass


class StatsHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def get(self):
        log.debug('stats {}'.format(self.request.arguments))
        self.write(referee.stats())
        self.finish()


class GameWebSocket(websocket.WebSocketHandler):

    def open(self):
        log.debug("WebSocket opened {}".format(hash(self)))

    @tornado.web.asynchronous
    @tornado.gen.engine
    def on_message(self, message):
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        sid = self.get_cookie('sid')
        username = cache.get(sid)
        if username is None:
            username = yield tornado.gen.Task(redis.get, sid)
            cache.set(sid, username)
        if username is None:
            self.write_message(dict(error='session_expirered'))
            log.warning('session_error {}'.format(message))
            return

        try:
            msg = json.loads(message)
            cmd = msg.pop('cmd')
            getattr(self, '_'+cmd)(username, msg)
        except (ValueError, KeyError):
            self.write_message(dict(error='protocol_error'))
            log.error('protocol_error {}'.format(message))
#        except AttributeError:
#            self.write_message(dict(error='unknown_command'))
#            log.error('unknown_command {}'.format(message))
        except GameError as e:
            self.write_message(dict(error=e.message))
            log.warning('game_erroor {}, msg {}'.format(e.message, message))

    def _create(self, username, msg):
        referee.create_game(username, **msg)
        sockets[username] = self
        self.write_message(dict(
            reply='created'))

    def _join(self, username, msg):
        game = referee.join_game(username, **msg)
        sockets[username] = self
        for p in game.players:
            print(p)
            sockets[p.name].write_message(dict(reply='joined',
                                               user=username))

    def _move(self, username, msg):
        game = referee.move(username, **msg)
        for p in game.players:
            sockets[p.name].write_message(
                dict(reply='move',
                     name=username,
                     side=p.side,
                     **msg
                     ))
            if game.state == Game.FINISH:
                sockets[p.name].write_message(
                    dict(reply='finish',
                         winner=username,
                         ))

    def on_close(self):
        log.debug("WebSocket closed {}".format(hash(self)))


if __name__ == '__main__':
    parse_command_line()
    application = tornado.web.Application([
        (r'/ws', GameWebSocket),
        (r'/stats', StatsHandler),
        ])
    application.listen(options.port)
    log.info('Game started on: {}'.format(options.port))

    tornado.ioloop.IOLoop.instance().start()
