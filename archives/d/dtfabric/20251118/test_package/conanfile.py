#!/usr/bin/env python3
"""Conan test_package for dtfabric 20251118 — Python library."""
import os
import sys
from conan import ConanFile


class DtfabricTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["dtfabric"]
        pkg_dir = dep.package_folder

        env_list = [f"PYTHONPATH={pkg_dir}"]

        helper = os.path.join(self.build_folder, "test_all.py")
        with open(helper, "w") as f:
            f.write(f'''#!/usr/bin/env python3
"""Combined dtfabric test: module import + CLI tool."""
import os, subprocess, sys

pkg_dir = {repr(pkg_dir)}

# 1. Module import test
sys.path.insert(0, pkg_dir)
from dtfabric import __version__ as ver
print("dtfabric version:", ver)
assert ver == "20251118", f"Version mismatch: {{ver}}"
from dtfabric import definitions as defs, reader, registry
assert defs.TYPE_INDICATOR_INTEGER == "integer"
assert defs.BYTE_ORDER_LITTLE_ENDIAN == "little-endian"
import io
yaml_data = b"""---
name: uint8
type: integer
attributes:
  format: unsigned
  size: 1
  units: bytes
"""
reg = registry.DataTypeDefinitionsRegistry()
fr = reader.YAMLDataTypeDefinitionsFileReader()
fr.ReadFileObject(reg, io.BytesIO(yaml_data))
uint8 = reg.GetDefinitionByName("uint8")
assert uint8 and uint8.size == 1
print("Module import test: PASSED")

# 2. CLI tool test — MUST be present for test to count as real
cli_path = os.path.join(pkg_dir, "bin", "validate-definitions.py")
if not os.path.isfile(cli_path):
    print("FAIL: CLI validate-definitions.py not found at", cli_path)
    print("test does not depend on dtfabric binary artifacts")
    sys.exit(1)
env = os.environ.copy()
env["PYTHONPATH"] = pkg_dir + ":" + env.get("PYTHONPATH", "")
result = subprocess.run(
    [sys.executable, cli_path, "--help"],
    capture_output=True, text=True, env=env)
print("CLI stdout:", result.stdout[:200])
if result.returncode != 0:
    print("CLI stderr:", result.stderr[:500])
    sys.exit(1)
print("CLI tool test: PASSED")
print("All dtfabric tests PASSED")
''')
        self.run(f"{sys.executable} {helper}", env=env_list)
