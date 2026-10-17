#!/usr/bin/env python3
"""Exercise the packaged sedparse module and CLI from the Conan payload."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import sedparse

assert sedparse.__version__ == "0.1.2"
expected_root = Path(os.environ["SEDPARSE_PACKAGE_ROOT"]).resolve()
module_path = Path(sedparse.__file__).resolve()
assert module_path.name == "sedparse.py"
assert expected_root in module_path.parents

parsed = []
sedparse.compile_string(parsed, "s/foo/bar/g")
assert len(parsed) == 1 and parsed[0].cmd == "s"
assert parsed[0].to_dict()["x"]["cmd_subst"]["regx"]["pattern"] == "foo"
assert json.loads(parsed[0].to_json())["cmd"] == "s"

parsed_addr = []
sedparse.compile_string(parsed_addr, "5d")
assert parsed_addr[0].cmd == "d" and str(parsed_addr[0].a1) == "5"
assert str(parsed_addr[0]) == "5 d"  # struct_sed_cmd.__str__ inserts a space after addresses (cf. upstream test_str expects "q 0")

try:
    sedparse.compile_string([], "u")
    sedparse.check_final_program()
    raise SystemExit("expected ParseError for unknown command")
except sedparse.ParseError as err:
    assert "unknown command" in err.message

proc = subprocess.run(
    [sys.executable, "-m", "sedparse", "-e", "s/foo/bar/g"],
    capture_output=True,
    text=True,
    check=True,
)
assert json.loads(proc.stdout)[0]["cmd"] == "s"

with tempfile.NamedTemporaryFile(mode="w", suffix=".sed", delete=False) as handle:
    handle.write("1,10!d\n")
    script_file = handle.name
proc_file = subprocess.run(
    [sys.executable, "-m", "sedparse", "-f", script_file],
    capture_output=True,
    text=True,
    check=True,
)
os.unlink(script_file)
file_doc = json.loads(proc_file.stdout)[0]
assert file_doc["cmd"] == "d" and file_doc.get("addr_bang") is True

parsed_block = []
sedparse.compile_string(parsed_block, "11,/foo/ {\n    $!N\n    s/\\n/-/gi\n}\n")
assert [item.cmd for item in parsed_block] == ["{", "N", "s", "}"]

print("sedparse 0.1.2 module and CLI: PASS")
