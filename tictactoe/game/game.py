NOTREADY = 0
READY = 1
FINISH = 2


class GameError(Exception): pass


class Field(object):

    def __init__(self):
        self.arr = [' ']*3*3

    def move(self, x, y, side):
        assert side in ('x', 'o'), 'Wrong side symbol'
        try:
            if self.arr[x*3+y] != ' ':
                raise KeyError
        except KeyError:
            raise GameError('wrong move')
        self.arr[x][y] = side
        return self.check_win()

    def check_win(self):
        for i in range(3):
            pass

    @staticmethod
    def from_text( text):
        obj = Field()
        obj.arr = text.replace('\n', '')
        return obj

    def __repr__(self):
        s = ''
        for i in range(3):
            s += ''.join(self.arr[i*3: i*3+3]) + '\n'
        return s


class Game(object):

    def __init__(self, creator, side='x'):
        self.creator = creator
        self.opponent = None
        self.side = side
        self.turn = creator
        self.state = NOTREADY

    def join(self, opponent):
        if opponent == self.creator:
            raise GameError('join to self')
        if self.state != NOTREADY:
            raise GameError('game already started')
        self.opponent = opponent
        self.state = READY

    def move(self, user, x, y):
        if user != self.turn:
            raise GameError('wrong turn')
        self.turn = self.opponent if user == self.creator else self.creator
