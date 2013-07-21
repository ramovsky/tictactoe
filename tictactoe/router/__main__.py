import logging
import uuid
import tornadoredis
import tornado.httpserver
import tornado.httpclient
import tornado.web
import tornado.ioloop
import tornado.gen
from tornado.options import define, options, parse_command_line

define("redis", default="127.0.0.1:6379", help="Reids DB")
define("port", default=8888, help="Port", type=int)
define("domain", default="localhost:8888", help="Cookie domain")
define("game", help="Game server to work with", multiple=True)

log = logging.getLogger('router')
log.setLevel(logging.DEBUG)
EXPIRE = 3600
GAME_SERVERS = []
redis = tornadoredis.Client(options.redis)


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("template.html", error='')


class GameHandler(tornado.web.RequestHandler):

    def get(self):
        log.debug('game {}'.format(self.request.arguments))
        self.render("game.html")


class LoginHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        log.debug('login {}'.format(self.request.arguments))
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
            self.set_cookie('sid', sid, domain=options.domain, expires=EXPIRE)
            self.redirect('/game#'+sid, permanent=True)


class RegisterHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        log.debug('register {}'.format(self.request.arguments))
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
            self.set_cookie('sid', sid, domain=DOMAIN, expires=EXPIRE)
            self.redirect('/game?game='+sid, permanent=True)
        else:
            self.render('template.html', error='Login used')



#@tornado.web.asynchronous
@tornado.gen.engine
def ping():
    global GAME_SERVERS
    GAME_SERVERS = []
    http_client = tornado.httpclient.AsyncHTTPClient()
    for url in options.game:
        resp = yield tornado.gen.Task(http_client.fetch, url, request_timeout=1)
        if not resp.error:
            GAME_SERVERS.append(url)


if __name__ == '__main__':
    parse_command_line()
    application = tornado.web.Application([
        (r'/', MainHandler),
        (r'/login', LoginHandler),
        (r'/register', RegisterHandler),
        (r'/game', GameHandler),
        ])
    application.listen(options.port)
    log.info('Router started on: {}'.format(options.port))

    tornado.ioloop.PeriodicCallback(ping, 2000).start()
    tornado.ioloop.IOLoop.instance().start()
