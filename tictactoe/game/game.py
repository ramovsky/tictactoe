class GameError(Exception):

    def __index__(self, reason):
        self.reason = reason


class Field(object):

    def __init__(self):
        self.rows = [0] * 3
        self.cols = [0] * 3
        self.left_diag = 0
        self.right_diag = 0
        self.arr = [[' ']*3, [' ']*3, [' ']*3]

    def move(self, x, y, side):
        if not 0 <= x < 3:
            raise GameError('wrong_x_move')
        if not 0 <= y < 3:
            raise  GameError('wrong_y_move')
        if side not in 'xo':
            raise GameError('wrong_side_symbol')
        if self.arr[y][x] != ' ':
            raise GameError('cell_occupied', self.arr, y, x)

        val = 1 if side == 'x' else -1
        self.rows[y] += val
        self.cols[x] += val
        if x == y:
            self.left_diag += val
        if y == 2 - x:
            self.right_diag += val
        self.arr[y][x] = side

        return self.check_win(x, y)


    def check_win(self, x, y):
        return self.rows[y] % 3 == 0 \
            or self.cols[x] % 3 == 0 \
            or self.left_diag % 3 == 0 \
            or self.right_diag % 3 == 0

    @staticmethod
    def from_text( text):
        text = text.replace('\n', '')
        field = Field()

        for i, s in enumerate(text):
            if s != ' ':
                y = i//3
                x = i - y*3
                field.move(x, y, s)
        return field


class Player(object):

    def __init__(self, name, side):
        self.name = name
        self.side = side

class Game(object):

    NOTREADY = 0
    READY = 1
    FINISH = 2

    def __init__(self, creator, side='x'):
        self.players = [Player(creator, side)]

        if side == 'x':
            self.turn = self.players[0]
        elif side == 'o':
            self.turn = None
        else:
            raise GameError('wrong_side_symbol')

        self.field = Field()
        self.state = self.NOTREADY

    def join(self, opponent):
        if opponent == self.players[0].name:
            raise GameError('join_to_self')
        if self.state != self.NOTREADY:
            raise GameError('game_already_started')

        if self.turn is None:
            self.players.append(Player(opponent, 'x'))
            self.turn = self.players[1]
        else:
            self.players.append(Player(opponent, 'o'))

        self.state = self.READY

    def move(self, user, x, y):
        if self.state != Game.READY:
            raise GameError('game_not_ready')
        if user != self.turn.name:
            raise GameError('wrong_turn')
        if self.field.move(x, y, self.turn.side):
            self.state = Game.FINISH
            return user

        self.turn = self.opponent if user == self.creator else self.creator
