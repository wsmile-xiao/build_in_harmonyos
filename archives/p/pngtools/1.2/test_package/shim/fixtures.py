#!/usr/bin/env python3
"""Minimal fixtures compatibility layer for the upstream test suite."""

import shutil
import tempfile


class TempDir:
    """Temporary directory fixture with the same surface used by pngtools."""

    def setUp(self):
        self.path = tempfile.mkdtemp(prefix="pngtools-test-")

    def cleanUp(self):
        shutil.rmtree(self.path, ignore_errors=True)
