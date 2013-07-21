from .game import Game, GameError
from .cache import RandomChoiceDict


class Referee(object):

    def __init__(self):
        self.wait_games = RandomChoiceDict()
        self.play_games = {}

    def create_game(self, username, side):
        if username in self.wait_games or username in self.play_games:
            raise GameError('already_in_game')
        self.wait_games[username] = Game(username, side)

    def join_game(self, username):
        if username in self.wait_games or username in self.play_games:
            raise GameError('already_in_game')
        if not self.wait_games:
            raise GameError('no_waiting_games')
        game = self.wait_games.pop_random()
        game.join(username)
        self.play_games[username] = game
        self.play_games[game.players[0].name] = game
        return game

    def move(self, username, x, y):
        game = self.play_games.get(username)
        if game is None or game.state != Game.READY:
            raise GameError('game_not_ready')

        if game.move(username, x, y):
            for p in game.players:
                self.play_games.pop(p.name)
        return game

    def stats(self):
        return dict(wait=len(self.wait_games), play=len(self.play_games))
