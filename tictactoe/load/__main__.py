import time
import random
import json
import tornado.gen
from tornado.websocket import websocket_connect
from tornado.options import define, options, parse_command_line


define("url", default="localhost:8889", help="Reids host")
define("users", default=4, help="Max concurent users", type=int)
define("delay", default=1000, help="Delay between requests, ms", type=int)

parse_command_line()
clients = []
stats = []


class LoadScenario(object):

    CREATED = 0
    LOGINED = 1
    AUTH = 2
    GAME = 3
    FINISH = 4
    GAMEAUTH = 5

    def __init__(self, login):
        self.state = self.CREATED
        self.login = login
        self.url = 'http://{1}/register?login={0}&password={0}&cpassword={0}'.format(login, options.url)
        self.connection = None
        self.data = None
        self.start = None
        self.gid = None

    @tornado.gen.engine
    def step(self):
        if self.state == self.CREATED:
            http_client = tornado.httpclient.AsyncHTTPClient()
            resp = yield tornado.gen.Task(http_client.fetch, self.url,
                                          request_timeout=1)
            url, self.sid = resp.effective_url.split('#')
            self.ws_url = 'ws://{}/ws'.format(url.split('/')[2])
            self.origin_url = self.ws_url
            self.state = self.LOGINED

        else:
            if self.data:
                if self.state == self.LOGINED:
                    if self.data.get('reply') == 'authorized':
                        self.state = self.AUTH

                if self.state == self.AUTH:
                    if self.data.get('reply') == 'joined':
                        self.state = self.GAMEAUTH
                        self.gid = self.data['gid']
                        self.ws_url = 'ws://{}/ws'.format(self.data['url'])
                        self.connection = None
                        return
                    self.send(cmd='join')
                    self.send(cmd='create', side='x')

                if self.state == self.GAMEAUTH:
                    if self.data.get('reply') == 'authorized':
                        self.state = self.GAME

                if self.state == self.GAME:
                    if self.data.get('reply') == 'finish':
                        self.state = self.AUTH
                        self.gid = None
                        self.ws_url = self.origin_url
                        self.connection = None
                        return
                    self.send(cmd='move', x=random.randint(0, 2),
                              y=random.randint(0, 2))
                self.data = None

            if self.connection is None:
                self.connection = yield websocket_connect(self.ws_url)
                self.send(cmd='auth', sid=self.sid, gid=self.gid)
            try:
                msg = yield self.connection.read_message()
            except AssertionError:
                self.connection = None
                return
            self.data = json.loads(msg)
            if self.start and \
                   (self.data.get('reply') == 'move'  or \
                    self.data.get('error') == 'wrong_turn') and \
                   self.data.get('name') == self.login:
                stats.append((time.time() - self.start)*1000)
                self.start = None

    def send(self, **dct):
        if self.connection is None:
            return
        self.connection.write_message(json.dumps(dct))
        if dct['cmd'] == 'move':
            self.start = time.time()


def step():
    if len(clients) < options.users:
        login = 'user'+str(random.random()*options.users)
        clients.append(LoadScenario(login))
    for c in clients:
        c.step()


def prin_stats():
    global stats
    if not stats:
        return
    print('='*80)
    stats.sort()
    print('clients: {} latency min: {:.1f}ms, max: {:.1f}ms, med: {:.1f}ms'.format(
        len(clients), min(stats), max(stats), stats[len(stats)//2]))
    print('')
    stats = []


if __name__ == '__main__':
    tornado.ioloop.PeriodicCallback(step, options.delay).start()
    tornado.ioloop.PeriodicCallback(prin_stats, 10000).start()
    tornado.ioloop.IOLoop.instance().start()
