#!/usr/bin/env python3
"""Host regression for native OHOS orchestration without device shell tools."""

import gzip
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_data import run_native


class NativeRunnerTests(unittest.TestCase):
    def exercise(self, sandbox_fails=False):
        payload = b'[503, "A", [1, 2]]\n'
        expected = {"sea503.gz": {"level": 503, "bytes": len(payload), "crc32": "12345678"}}
        consumer = Path("/absolute/ohos/test_seadata")
        sandbox_calls = []

        # The OHOS executable cannot run on the host. Accept only its calls;
        # any dependency on param or another shell tool fails this regression.
        def target_run(command, **kwargs):
            self.assertEqual(command[0], str(consumer))
            if command[1] == "--sandbox":
                sandbox_calls.append(command)
                self.assertTrue(kwargs["check"])
                source = Path(command[2])
                self.assertEqual(source.read_bytes(), payload)
                self.assertEqual(source.parent, Path(kwargs["env"]["TMPDIR"]))
                if sandbox_fails:
                    raise subprocess.CalledProcessError(1, command)
                return subprocess.CompletedProcess(command, 0)
            return subprocess.CompletedProcess(command, 0 if kwargs.get("check") else 1)

        with tempfile.TemporaryDirectory() as temporary:
            datadir = Path(temporary)
            (datadir / "seadata").mkdir()
            (datadir / "seadata" / "sea503.gz").write_bytes(gzip.compress(payload))
            with patch.dict(os.environ, {"PATH": ""}), patch("test_data.subprocess.run", target_run):
                run_native(consumer, datadir, expected, ohos=True)
        self.assertEqual(len(sandbox_calls), 1)

    def test_no_shell_tools_still_runs_ohos_sandbox(self):
        self.exercise()

    def test_sandbox_failure_is_not_skipped(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.exercise(sandbox_fails=True)


if __name__ == "__main__":
    unittest.main()
