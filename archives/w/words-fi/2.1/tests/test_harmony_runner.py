"""Unit tests for the HarmonyOS device identity guard."""
import sys
from pathlib import Path
import unittest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "test_package"))
from test_harmony import (  # noqa: E402
    build_remote_test_command,
    validate_device_info,
    validate_remote_clang,
)


class DeviceInfoTests(unittest.TestCase):
    def test_accepts_openharmony_61_api23_aarch64(self) -> None:
        self.assertIsNone(validate_device_info("OpenHarmony-6.1.0.115", "23", "aarch64"))

    def test_rejects_missing_api_level(self) -> None:
        with self.assertRaises(ValueError):
            validate_device_info("OpenHarmony-6.1.0.115", "", "aarch64")

    def test_rejects_non_numeric_api_level(self) -> None:
        with self.assertRaises(ValueError):
            validate_device_info("OpenHarmony-6.1.0.115", "api23", "aarch64")

    def test_rejects_non_aarch64_machine(self) -> None:
        with self.assertRaises(ValueError):
            validate_device_info("OpenHarmony-6.1.0.115", "23", "x86_64")

    def test_rejects_unexpected_os_name(self) -> None:
        with self.assertRaises(ValueError):
            validate_device_info("HarmonyOS-6.0", "23", "aarch64")


class RemoteBuildTests(unittest.TestCase):
    def test_remote_compiler_builds_on_device_before_running_consumer(self) -> None:
        command = build_remote_test_command(
            "/storage/Users/currentUser/words-fi-abc",
            "/data/service/hnp/bin/clang++",
        )
        self.assertIn("'/data/service/hnp/bin/clang++' -std=c++17", command)
        self.assertIn("test_words_fi.cpp -o test_words_fi && chmod 700", command)
        self.assertIn("--require-ohos --expect-machine=aarch64 --expect-count=88328", command)

    def test_rejects_unsafe_remote_compiler_path(self) -> None:
        with self.assertRaises(ValueError):
            validate_remote_clang("/data/tool; rm -rf /")


if __name__ == "__main__":
    unittest.main()
