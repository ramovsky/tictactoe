import unittest
from game import *


class TestGame(unittest.TestCase):

    def test_start(self):
        game = Game('oleg')
        self.assertEqual(game.state, Game.NOTREADY)

        game.join('max')
        self.assertEqual(game.state, Game.READY)
        self.assertIn('oleg', game.players)
        self.assertIn('max', game.players)

    def test_wrong_side(self):
        self.assertRaises(GameError, Game, 'oleg', 'b')

    def test_creator_starts(self):
        game = Game('oleg', 'x')
        game.join('max')
        self.assertEqual('oleg', game.turn.name)

    def test_opponent_starts(self):
        game = Game('oleg', 'o')
        game.join('max')
        self.assertEqual('max', game.turn.name)

    def test_join_started(self):
        game = Game('oleg', 'o')
        game.join('max')
        self.assertRaises(GameError, game.join, 'den')

    def test_join_to_self(self):
        self.assertRaises(GameError, Game('oleg').join, 'oleg')

    def test_noready_move(self):
        game = Game('oleg', 'x')
        self.assertRaises(GameError, game.move, 'oleg', 0, 0)

    def test_finish_move(self):
        game = Game('oleg', 'x')
        game.join('max')
        game.field =  Field.from_text('x o'
                                      'xoo'
                                      '  x')
        winner = game.move('oleg', 0, 2)
        self.assertEqual(Game.FINISH, game.state)
        self.assertEqual('oleg', winner)
        self.assertRaises(GameError, game.move, 'max', 0, 1)


if __name__ == '__main__':
    unittest.main()
