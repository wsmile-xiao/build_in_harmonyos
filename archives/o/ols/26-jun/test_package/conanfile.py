#!/usr/bin/env python3
"""Consumer test for ols 26-jun (LSP smoke test via JSON-RPC).

Sends an LSP `initialize` request over stdin, then `shutdown` and `exit`.
Validates that:
  1. ols binary exists and has ELF magic (R34)
  2. ols returns JSON-RPC Content-Length frames with a result object
  3. ols exits cleanly (RC == 0)

Emits HMBS_TEST_PACKAGE_RESULT marker for the HMBS hard gate.
"""
import json
import os
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class OlsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        # Send Conan's generated env files (conanbuild.sh / conanrun.sh /
        # metadata/) to a separate build folder instead of the recipe folder.
        # Without this, test_package pollutes archives/o/ols/26-jun/test_package
        # with generated artifacts that HMBS cannot read (Permission denied on
        # metadata/), blocking the preflight.
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["ols"]
        package_folder = dep.package_folder
        ols_bin = os.path.join(package_folder, "bin", "ols")

        # R34: verify the binary exists and is ELF
        if not os.path.isfile(ols_bin):
            raise RuntimeError(f"ols binary not found: {ols_bin}")
        with open(ols_bin, "rb") as f:
            magic = f.read(4)
        if magic != b"\x7fELF":
            raise RuntimeError(f"ols is not ELF: {magic!r}")

        # EMIT_HMBS_MARKER_PRE
        test_pkg = {
            "executed": True,
            "passed": False,
            "command": f'"{ols_bin}"',
            "discovered": 1,
            "passedCount": 0,
        }

        if not can_run(self):
            test_pkg["executed"] = False
            self.output.info("跨平台构建：仅验证 ELF 头部")
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" +
                json.dumps(test_pkg, ensure_ascii=False)
            )
            return

        # Set up environment so ols can find its builtin definitions
        env = os.environ.copy()
        builtin_folder = os.path.join(package_folder, "builtin")
        if os.path.isdir(builtin_folder):
            env["OLS_BUILTIN_FOLDER"] = builtin_folder

        # Build JSON-RPC sequence: initialize → shutdown → exit
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": None,
                    "rootUri": "file:///tmp",
                    "capabilities": {}
                }
            },
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
        stdin_data = ""
        for msg in messages:
            body = json.dumps(msg, separators=(",", ":"))
            header = f"Content-Length: {len(body)}\r\n\r\n"
            stdin_data += header + body

        # Write stdin to temp file.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonrpc", delete=False) as f:
            f.write(stdin_data)
            stdin_file = f.name

        # Use the on-disk test script (test_ols_lsp.sh).  This satisfies:
        #   L0c — test_package/ contains a .sh test source file besides conanfile.py
        #   L1d — the test() body calls self.run() with a real LSP protocol run
        #   R34 — the script pipes JSON-RPC data into the actual ols binary
        script = os.path.join(self.recipe_folder, "test_ols_lsp.sh")

        try:
            # L1d: self.run() executes real ols LSP protocol interaction.
            # Invoke via `sh` to avoid needing the executable bit
            # (Conan export strips it from recipe-checked-in scripts).
            self.run(
                f'sh "{script}" "{stdin_file}" "{builtin_folder}" "{ols_bin}"',
                env="conanrun",
            )
            test_pkg["passed"] = True
            test_pkg["passedCount"] = 1
        except Exception as exc:
            test_pkg["passed"] = False
            test_pkg["message"] = str(exc)[:200]
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" +
                json.dumps(test_pkg, ensure_ascii=False)
            )
            raise
        finally:
            os.unlink(stdin_file)

        # EMIT_HMBS_MARKER_POST
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" +
            json.dumps(test_pkg, ensure_ascii=False)
        )
        self.output.info("PASS: ols consumer test passed")