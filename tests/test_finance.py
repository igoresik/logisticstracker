import unittest

from finance import net_profit


class NetProfitTest(unittest.TestCase):
    def test_fee_is_taken_from_sale_price(self):
        self.assertEqual(net_profit(40, 10, 10), (4.0, 26.0, 65.0))

    def test_counteroffer_lowers_fee_and_profit(self):
        self.assertEqual(net_profit(30, 10, 10), (3.0, 17.0, 56.7))

    def test_fixed_fee_and_shipping(self):
        self.assertEqual(net_profit(20, 5, 12.8, 0.30, 3.5), (2.86, 8.64, 43.2))

    def test_loss_gives_negative_margin(self):
        self.assertEqual(net_profit(10, 15, 10), (1.0, -6.0, -60.0))

    def test_zero_sale_price(self):
        self.assertEqual(net_profit(0, 5, 10), (0.0, -5.0, 0.0))


if __name__ == "__main__":
    unittest.main()
