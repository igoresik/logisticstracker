import sys
import unittest

import vault


class VaultTest(unittest.TestCase):
    def test_plain_text_passes_through(self):
        self.assertEqual(vault.unlock("old-plain-key"), "old-plain-key")
        self.assertEqual(vault.lock(""), "")

    @unittest.skipUnless(sys.platform == "win32", "DPAPI is Windows only")
    def test_round_trip_hides_the_value(self):
        locked = vault.lock("s3cret-key")
        self.assertTrue(locked.startswith(vault.PREFIX))
        self.assertNotIn("s3cret-key", locked)
        self.assertEqual(vault.unlock(locked), "s3cret-key")
        self.assertEqual(vault.lock(locked), locked)

    def test_unreadable_value_becomes_empty(self):
        self.assertEqual(vault.unlock(vault.PREFIX + "bm90IGEgcmVhbCBibG9i"), "")


if __name__ == "__main__":
    unittest.main()
