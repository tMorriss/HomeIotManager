'''Initial test suite setup.'''

import unittest


class BaseTestCase(unittest.TestCase):
    '''Base test case.'''

    def test_placeholder(self):
        '''Placeholder test.'''
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
