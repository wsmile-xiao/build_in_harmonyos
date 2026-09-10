import platform
import sys
import unittest

from ptyprocess import PtyProcess


class OhosPtyRuntimeTest(unittest.TestCase):
    @unittest.skipUnless(
        sys.platform == "openharmony" or platform.system() in ("OHOS", "HarmonyOS"),
        "requires an OHOS/HarmonyOS Python runtime",
    )
    def test_ohos_runtime_pty_exchange(self):
        process = PtyProcess.spawn(["sh", "-c", "printf 'ohos-runtime\\n'"])
        output = process.read().decode("ascii").replace("\r\n", "\n")
        self.assertEqual(output, "ohos-runtime\n")
        self.assertEqual(process.wait(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
