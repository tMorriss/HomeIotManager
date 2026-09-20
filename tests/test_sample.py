'''Sample test for initial CI and tox verification.'''

import unittest


class SampleTestCase(unittest.TestCase):
    '''Sample test case to verify test runner configuration.'''

    def test_sample(self):
        '''Simple dummy test.'''
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
