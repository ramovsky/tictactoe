import unittest
from game import *

class TestField(unittest.TestCase):

    def test_from_text(self):
        field = Field.from_text('oox'
                                ' x '
                                'x  ')

        self.assertEqual(-1, field.rows[0])
        self.assertEqual(1, field.rows[1])
        self.assertEqual(1, field.rows[2])

        self.assertEqual(0, field.cols[0])
        self.assertEqual(0, field.cols[1])
        self.assertEqual(1, field.cols[2])

        self.assertEqual(0, field.left_diag)
        self.assertEqual(3, field.right_diag)

    def test_win_column(self):
        field = Field.from_text('oox'
                                '  x'
                                '   ')
        self.assertTrue(field.move(2, 2, 'x'))

    def test_win_diag(self):
        field = Field.from_text('x o'
                                'xo '
                                '  x')
        self.assertTrue(field.move(0, 2, 'o'))

    def test_win_anti_diag(self):
        field = Field.from_text('x o'
                                'ox '
                                '   ')
        self.assertTrue(field.move(2, 2, 'x'))

    def test_win_row(self):
        field = Field.from_text('o o'
                                'x x'
                                'x  ')
        self.assertTrue(field.move(1, 0, 'o'))

    def test_not_win(self):
        field = Field.from_text('o o'
                                'x x'
                                'x  ')
        self.assertFalse(field.move(1, 0, 'x'))

    def test_cell_occupied(self):
        field = Field.from_text('o o'
                                'x x'
                                'x  ')
        self.assertRaises(GameError, field.move, 0, 1, 'x')


if __name__ == '__main__':
    unittest.main()
