"""Tests for Yapsy's dependency-free StrictVersion replacement."""

import unittest

from yapsy._version import StrictVersion


class StrictVersionCompatibilityTests(unittest.TestCase):

    def test_release_and_prerelease_order(self):
        self.assertEqual(StrictVersion("1.2"), StrictVersion("1.2.0"))
        self.assertLess(StrictVersion("1.2a1"), StrictVersion("1.2b1"))
        self.assertLess(StrictVersion("1.2b1"), StrictVersion("1.2"))
        self.assertGreater(StrictVersion("1.2.1"), StrictVersion("1.2"))

    def test_string_form_preserves_metadata(self):
        self.assertEqual("1.2", str(StrictVersion("1.2")))
        self.assertEqual("1.2a1", str(StrictVersion("1.2a1")))
        self.assertEqual("StrictVersion ('1.2')", repr(StrictVersion("1.2")))

    def test_rejects_non_strict_release_suffix(self):
        with self.assertRaises(ValueError):
            StrictVersion("1.2.3rc1")


suite = unittest.TestSuite([
    unittest.TestLoader().loadTestsFromTestCase(StrictVersionCompatibilityTests),
])
