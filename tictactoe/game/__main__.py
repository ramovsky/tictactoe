import json
import logging
import tornadoredis
import tornado.ioloop
import tornado.web
import tornado.gen
from tornado.options import define, options, parse_command_line

from .referee import Referee
from .game import Game, GameError
from tictactoe.utils import authorized, WSBase, sockets, GameError


define("redis_host", default="127.0.0.1", help="Reids host")
define("redis_port", default=6379, help="Reids port", type=int)
define("port", default=8881, help="Server port", type=int)

log = logging.getLogger('game')
log.setLevel(logging.DEBUG)

referee = Referee()


class StatsHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def get(self):
        log.debug('stats {}'.format(self.request.arguments))
        self.write(referee.stats())
        self.finish()


class GameWebSocket(WSBase):

    def open(self):
        super(GameWebSocket, self).open()
        self.gid = None

    @tornado.gen.engine
    def _auth(self, msg):
        super(GameWebSocket, self)._auth(msg)

        gid = msg['gid']
        if gid is None:
            raise GameError('gid_not_valid')

        field = referee.get_field(gid)
        for y, row in enumerate(field):
            for x, c in enumerate(row):
                if c != ' ':
                    self.write_message(dict(reply='move', name=self.username,
                                            side=c, x=x, y=y))

        if not field:
            redis = tornadoredis.Client(options.redis_host, options.redis_port)
            data = yield tornado.gen.Task(redis.hgetall, 'game:'+gid)
            if data is None:
                raise GameError('gid_not_valid')
            referee.create_game(gid, data['creator'], data['side'], data['opponent'])
        self.gid = gid

    @tornado.gen.engine
    @authorized
    def _move(self, username, msg):
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        game, winner = referee.move(self.gid, username, **msg)
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
                yield tornado.gen.Task(redis.srem, 'playing', name)
        if winner:
            yield tornado.gen.Task(redis.delete, 'game'+self.gid)
            self.gid = None

    @tornado.gen.engine
    @authorized
    def _surrender(self, username, msg):
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        game = referee.get_game(self.gid)
        winner = None
        for name in game.players:
            s = sockets.get(name)
            if s and name != username:
                winner = name
                s.write_message(
                    dict(reply='finish',
                         winner=winner,
                         ))
                yield tornado.gen.Task(redis.zincrby, 'win', name, 1)
            else:
                yield tornado.gen.Task(redis.zincrby, 'lose', name, 1)
            yield tornado.gen.Task(redis.zincrby, 'games', name, 1)
            yield tornado.gen.Task(redis.srem, 'playing', name)
        yield tornado.gen.Task(redis.delete, 'game'+self.gid)
        self.gid = None


if __name__ == '__main__':
    parse_command_line()
    application = tornado.web.Application([
        (r'/ws', GameWebSocket),
        (r'/stats', StatsHandler),
        ])
    application.listen(options.port)
    log.info('Game started on: {}'.format(options.port))
    tornado.ioloop.IOLoop.instance().start()
