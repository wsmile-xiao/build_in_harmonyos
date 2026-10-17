#!/usr/bin/env python3
"""Consumer assertions for the packaged j2 entry point and Python module."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import j2cli

checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)


def main():
    executable = sys.argv[1]
    check(j2cli.__version__ == "0.3.12b", "module version mismatch")
    check(Path(executable).is_file(), "packaged j2 executable missing")

    version = run([executable, "--version"])
    check(
        version.returncode == 0,
        "j2 --version failed rc=%d stdout=%r stderr=%r"
        % (version.returncode, version.stdout, version.stderr),
    )
    check("j2cli 0.3.12b" in version.stdout, "j2 entry point version mismatch")
    check("Jinja2" in version.stdout, "Jinja2 dependency not visible through entry point")

    with tempfile.TemporaryDirectory(prefix="j2cli-consumer-", dir=os.getcwd()) as temp:
        template = Path(temp) / "greeting.j2"
        data = Path(temp) / "data.json"
        output = Path(temp) / "rendered.txt"
        template.write_text("Hello {{ user.name }} from {{ place }}!\n", encoding="utf-8")
        data.write_text(json.dumps({"user": {"name": "Harmony"}, "place": "j2"}), encoding="utf-8")

        rendered = run([executable, "--format=json", str(template), str(data)])
        check(rendered.returncode == 0, "j2 JSON rendering failed: " + rendered.stderr)
        check(rendered.stdout == "Hello Harmony from j2!\n", "j2 JSON render output mismatch")

        written = run([executable, "--format=json", "-o", str(output), str(template), str(data)])
        check(written.returncode == 0, "j2 -o output failed: " + written.stderr)
        check(output.read_text(encoding="utf-8") == "Hello Harmony from j2!\n", "j2 -o content mismatch")

        yaml_template = Path(temp) / "yaml.j2"
        yaml_data = Path(temp) / "data.yaml"
        yaml_template.write_text("{{ service.name }}:{{ service.port }}\n", encoding="utf-8")
        yaml_data.write_text("service:\n  name: api\n  port: 8080\n", encoding="utf-8")
        yaml_result = run([executable, "--format=yaml", str(yaml_template), str(yaml_data)])
        check(yaml_result.returncode == 0, "optional YAML extra failed: " + yaml_result.stderr)
        check(yaml_result.stdout == "api:8080\n", "YAML render output mismatch")

    if checks != 11:
        raise AssertionError("consumer assertion count mismatch: expected 11, got %d" % checks)
    print("PASS: j2cli consumer entry-point checks (%d/11 assertions)" % checks)


if __name__ == "__main__":
    main()
