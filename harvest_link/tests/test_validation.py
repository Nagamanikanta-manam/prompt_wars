import unittest
from harvest_link.agent import validate_food_items

class TestValidation(unittest.TestCase):
    def test_valid_items(self):
        items = [{"name": "vegetables", "amount": 60}]
        self.assertTrue(validate_food_items(items))

    def test_invalid_type(self):
        with self.assertRaises(ValueError) as context:
            validate_food_items("not a list")
        self.assertEqual(str(context.exception), "Invalid food_items format")

    def test_invalid_structure(self):
        with self.assertRaises(ValueError) as context:
            validate_food_items([{"name": "vegetables"}]) # Missing amount
        self.assertEqual(str(context.exception), "Invalid item structure")

if __name__ == "__main__":
    unittest.main()
