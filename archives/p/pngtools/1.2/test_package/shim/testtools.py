#!/usr/bin/env python3
"""Minimal testtools compatibility layer for the upstream test suite."""

import unittest


class TestCase(unittest.TestCase):
    """Expose the one testtools helper used by pngtools' tests."""

    def useFixture(self, fixture):
        fixture.setUp()
        self.addCleanup(fixture.cleanUp)
        return fixture
