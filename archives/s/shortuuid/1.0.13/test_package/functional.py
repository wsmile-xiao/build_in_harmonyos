"""Consumer checks for packaged shortuuid 1.0.13."""

import json
import os
import stat
import subprocess
import sys
import uuid
from pathlib import Path


def main():
    package = Path(sys.argv[1]).resolve()
    report = Path(sys.argv[2])
    import shortuuid

    results = []

    def check(name, action):
        try:
            action()
            results.append({"name": name, "passed": True})
            print("PASS", name, flush=True)
        except Exception as exc:
            results.append({"name": name, "passed": False,
                            "error": f"{type(exc).__name__}: {exc}"})
            print("FAIL", name, flush=True)

    def packaged_import():
        imported = Path(shortuuid.__file__).resolve()
        assert os.path.commonpath([str(imported), str(package)]) == str(package), imported

    def roundtrip():
        original = uuid.UUID("6ca4f0f8-2508-4bac-b8f1-5d1e3da2247a")
        encoded = shortuuid.encode(original)
        assert len(encoded) == 22
        assert shortuuid.decode(encoded) == original

    def named_uuid():
        first = shortuuid.uuid(name="example.com")
        assert first == shortuuid.uuid(name="example.com")
        assert len(first) == 22

    def alphabet_and_random():
        encoder = shortuuid.ShortUUID(alphabet="0001234567")
        assert encoder.get_alphabet() == "01234567"
        generated = encoder.random(length=16)
        assert len(generated) == 16
        assert set(generated) <= set("01234567")

    def cli_roundtrip():
        original = "6ca4f0f8-2508-4bac-b8f1-5d1e3da2247a"
        encoded = subprocess.run(
            [sys.executable, "-m", "shortuuid.cli", "encode", original],
            check=True, capture_output=True, text=True).stdout.strip()
        decoded = subprocess.run(
            [sys.executable, "-m", "shortuuid.cli", "decode", encoded],
            check=True, capture_output=True, text=True).stdout.strip()
        assert decoded == original

    def installed_command_roundtrip():
        command = package / "bin" / "shortuuid"
        assert command.is_file(), command
        assert command.stat().st_mode & stat.S_IXUSR, command
        original = "6ca4f0f8-2508-4bac-b8f1-5d1e3da2247a"
        encoded = subprocess.run(
            [str(command), "encode", original],
            check=True, capture_output=True, text=True).stdout.strip()
        decoded = subprocess.run(
            [str(command), "decode", encoded],
            check=True, capture_output=True, text=True).stdout.strip()
        assert decoded == original

    for name, action in (("packaged_import", packaged_import),
                         ("roundtrip", roundtrip),
                         ("named_uuid", named_uuid),
                         ("alphabet_and_random", alphabet_and_random),
                         ("cli_roundtrip", cli_roundtrip),
                         ("installed_command_roundtrip", installed_command_roundtrip)):
        check(name, action)

    summary = {"package_folder": str(package), "total": len(results),
               "passed": sum(item["passed"] for item in results),
               "cases": results}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} passed", flush=True)
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
