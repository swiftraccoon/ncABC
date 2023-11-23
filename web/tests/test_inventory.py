import unittest
from app import app


class InventoryTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        response = self.app.get('/inventory/')
        self.assertEqual(response.status_code, 200)

    # More tests...


if __name__ == '__main__':
    unittest.main()
