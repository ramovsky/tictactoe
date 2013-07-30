from .game import Game, GameError


class Referee(object):

    def __init__(self):
        self.games = {}

    def create_game(self, gid, creator, side, opponent):
        game = Game(creator, side)
        self.games[gid] = game
        game.join(opponent)

    def move(self, gid, username, x, y):
        game = self.get_game(gid)
        winner = game.move(username, x, y)
        if winner:
            self.games.pop(gid)
        return game, winner

    def stats(self):
        return dict(play=len(self.games))

    def get_game(self, gid):
        game = self.games.get(gid)
        if game is None or game.state != Game.READY:
            raise GameError('game_not_ready')
        return game

    def get_field(self, gid):
        if gid in self.games:
            return self.games[gid].field.arr
        return ()
