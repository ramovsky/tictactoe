import logging
import uuid
import tornadoredis
import tornado.httpserver
import tornado.httpclient
import tornado.web
import tornado.ioloop
import tornado.gen
from tornado.options import define, options, parse_command_line

define("redis_host", default="127.0.0.1", help="Reids host")
define("redis_port", default=6379, help="Reids port", type=int)
define("port", default=8888, help="Server port", type=int)
define("game", help="Game server to work with", multiple=True)

log = logging.getLogger('router')
log.setLevel(logging.ERROR)
EXPIRE = 36000
GAME_SERVERS = []


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("template.html", error='')


class TopHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        win = yield tornado.gen.Task(redis.zrevrange, 'win', 0, 10, 'WITHSCORES')
        lose = yield tornado.gen.Task(redis.zrevrange, 'lose', 0, 10, 'WITHSCORES')
        draw = yield tornado.gen.Task(redis.zrevrange, 'draw', 0, 10, 'WITHSCORES')
        games = yield tornado.gen.Task(redis.zrevrange, 'games', 0, 10, 'WITHSCORES')

        self.render("top.html", win=win, lose=lose, draw=draw, games=games)


class GameHandler(tornado.web.RequestHandler):

    def get(self):
        log.debug('game {}'.format(self.request.arguments))
        self.render("game.html")


class LoginHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        log.debug('login {}'.format(self.request.arguments))
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        if not GAME_SERVERS:
            self.render('template.html', error= "Servererr not ready!")

        login = self.request.arguments['login'][0]
        password = self.request.arguments['password'][0]
        cpassword = yield tornado.gen.Task(redis.hget, 'users', login)
        if password != cpassword:
            self.render('template.html', error= "Wrong login or password")

        else:
            sid = str(uuid.uuid4())
            pipe = redis.pipeline()
            pipe.set(sid, login)
            pipe.expire(sid, EXPIRE)
            yield tornado.gen.Task(pipe.execute)
            i = hash(login) % len(GAME_SERVERS)
            url = GAME_SERVERS[i]
            self.redirect('/game#{};{}'.format(url, sid), permanent=True)


class RegisterHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        log.debug('register {}'.format(self.request.arguments))
        redis = tornadoredis.Client(options.redis_host, options.redis_port)
        if not GAME_SERVERS:
            self.render('template.html', error= "Servererr not ready!")
        login = self.request.arguments['login'][0]
        password = self.request.arguments['password'][0]
        cpassword = self.request.arguments['cpassword'][0]
        if password != cpassword:
            self.render('template.html', error='Passwords not same')

        result = yield tornado.gen.Task(redis.hsetnx, 'users', login, password)
        if result == 1:
            sid = str(uuid.uuid4())
            pipe = redis.pipeline()
            pipe.set(sid, login)
            pipe.expire(sid, EXPIRE)
            yield tornado.gen.Task(pipe.execute)
            i = hash(login) % len(GAME_SERVERS)
            url = GAME_SERVERS[i]
            self.redirect('/game#{};{}'.format(url, sid), permanent=True)
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
        (r'/', MainHandler),
        (r'/login', LoginHandler),
        (r'/register', RegisterHandler),
        (r'/game', GameHandler),
        (r'/top', TopHandler),
        ])
    application.listen(options.port)
    log.info('Router started on: {}'.format(options.port))

    tornado.ioloop.PeriodicCallback(ping, 2000).start()
    tornado.ioloop.IOLoop.instance().start()
