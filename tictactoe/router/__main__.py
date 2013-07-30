import logging
import tornadoredis
import tornado.httpserver
import tornado.httpclient
import tornado.web
import tornado.ioloop
import tornado.gen
from tornado.options import define, options, parse_command_line

from .cache import RandomChoiceDict
from tictactoe.utils import get_sid, authorized, WSBase, sockets, GameError


define("redis_host", default="127.0.0.1", help="Reids host")
define("redis_port", default=6379, help="Reids port", type=int)
define("port", default=8888, help="Server port", type=int)
define("game", help="Game server to work with", multiple=True)

log = logging.getLogger('router')
log.setLevel(logging.ERROR)
EXPIRE = 36000
GAME_SERVERS = []
wait_games = RandomChoiceDict()


class LobbyHandler(WSBase):

    @tornado.gen.engine
    def _auth(self, msg):
        super(LobbyHandler, self)._auth(msg)

        gid = msg['gid']
        if gid is not None:
            redis = tornadoredis.Client(options.redis_host, options.redis_port)
            data = yield tornado.gen.Task(redis.hgetall, 'game:'+gid)
            if data:
                self.write_message(dict(reply='joined', gid=gid,
                                        url=data['url']))

    @tornado.gen.engine
    @authorized
    def _create(self, username, msg):
        if username in wait_games:
            raise GameError('already_wait')

        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        in_game = yield tornado.gen.Task(redis.sadd, 'playing', username)
        if in_game == 0:
            self.write_message(dict(error='in_game'))
            return

        wait_games[username] = msg['side']
        self.write_message(dict(reply='created'))

    @tornado.gen.engine
    @authorized
    def _join(self, username, msg):
        if not GAME_SERVERS:
            raise GameError("server_not_ready")
        if username in wait_games:
            raise GameError('already_wait')
        if not wait_games:
            raise GameError('no_waiting_games')

        creator, side = wait_games.pop_random()

        cr_soc = sockets.get(creator)
        if cr_soc is None:
            raise GameError('creation_error')

        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        in_game = yield tornado.gen.Task(redis.sadd, 'playing', username)
        if in_game == 0:
            raise GameError('in_game')

        i = hash(username) % len(GAME_SERVERS)
        url = GAME_SERVERS[i]

        gid = get_sid()
        key = 'game:' + gid
        pipe = redis.pipeline()
        pipe.hmset(key, {'creator': creator, 'opponent': username, 'side': side,
                         'url': url})
        pipe.expire(key, EXPIRE)
        yield tornado.gen.Task(pipe.execute)
        self.write_message(dict(reply='joined', gid=gid, url=url))
        cr_soc.write_message(dict(reply='joined', gid=gid, url=url))


class MainHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self, uri=None):
        if uri == 'game':
            log.debug('game {}'.format(self.request.arguments))
            self.render("game.html", games=len(wait_games))

        elif uri == 'top':
            redis = tornadoredis.Client(options.redis_host, options.redis_port)
            win = yield tornado.gen.Task(redis.zrevrange, 'win', 0, 10, 'WITHSCORES')
            lose = yield tornado.gen.Task(redis.zrevrange, 'lose', 0, 10, 'WITHSCORES')
            draw = yield tornado.gen.Task(redis.zrevrange, 'draw', 0, 10, 'WITHSCORES')
            games = yield tornado.gen.Task(redis.zrevrange, 'games', 0, 10, 'WITHSCORES')
            self.render("top.html", win=win, lose=lose, draw=draw, games=games
)
        else:
            self.render("template.html", error='')

    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self, uri=None):
        if uri == 'login':
            log.debug('login {}'.format(self.request.arguments))
            redis = tornadoredis.Client(options.redis_host, options.redis_port)
            login = self.request.arguments['login'][0]
            password = self.request.arguments['password'][0]
            cpassword = yield tornado.gen.Task(redis.hget, 'users', login)
            if password != cpassword:
                self.render('template.html', error= "Wrong login or password")

            else:
                sid = get_sid()
                pipe = redis.pipeline()
                pipe.set(sid, login)
                pipe.expire(sid, EXPIRE)
                yield tornado.gen.Task(pipe.execute)
                self.redirect('/game#{}'.format(sid), permanent=True)

        elif uri == 'register':
            log.debug('register {}'.format(self.request.arguments))
            redis = tornadoredis.Client(options.redis_host, options.redis_port)
            login = self.request.arguments['login'][0]
            password = self.request.arguments['password'][0]
            cpassword = self.request.arguments['cpassword'][0]
            if password != cpassword:
                self.render('template.html', error='Passwords not same')
            if len(login) < 1:
                self.render('template.html', error='Empty login')

            result = yield tornado.gen.Task(redis.hsetnx, 'users', login, password)
            if result == 1:
                sid = get_sid()
                pipe = redis.pipeline()
                pipe.set(sid, login)
                pipe.expire(sid, EXPIRE)
                yield tornado.gen.Task(pipe.execute)
                self.redirect('/game#{}'.format(sid), permanent=True)
            else:
                self.render('template.html', error='Login used')


@tornado.gen.engine
def ping():
    global GAME_SERVERS
    GAME_SERVERS = []
    http_client = tornado.httpclient.AsyncHTTPClient()
    for url in options.game:
        hurl = 'http://{}/stats'.format(url)
        resp = yield tornado.gen.Task(http_client.fetch, hurl, request_timeout=1)
        if not resp.error:
            GAME_SERVERS.append(url)


if __name__ == '__main__':
    parse_command_line()
    application = tornado.web.Application([
        (r'/ws', LobbyHandler),
        (r'/(.*)', MainHandler),
        ])
    application.listen(options.port)
    log.info('Router started on: {}'.format(options.port))

    tornado.ioloop.PeriodicCallback(ping, 2000).start()
    tornado.ioloop.IOLoop.instance().start()
