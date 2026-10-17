#!/usr/bin/env python3
"""test_package for glances 4.5.4 — binary smoke test (R34).

Glances is a Python CLI tool (application). The test verifies:
1. The glances binary/script exists in the package bin/ directory.
2. The glances Python module can be imported and its __version__ read.
3. The glances binary can be executed (--version output).
4. The bundled runtime deps keep their package layout (hard check).

Note: psutil's C extension cannot be loaded on OHOS without ELF signing
(E179 platform limitation). When that happens the test falls back to
importing the pure-Python bundled deps and verifying the version from
the packaged source.
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class GlancesTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        glances_pkg = self.dependencies["glances"].package_folder
        if not glances_pkg:
            raise ConanException("glances package_folder not found")

        glances_bin = os.path.join(glances_pkg, "bin", "glances")
        glances_dir = os.path.join(glances_pkg, "glances")
        init_file = os.path.join(glances_dir, "__init__.py")
        deps_path = os.path.join(glances_pkg, "glances-deps")

        # Verify binary and module directory exist
        if not os.path.isfile(glances_bin):
            raise ConanException(f"glances binary not found at {glances_bin}")
        if not os.path.isfile(init_file):
            raise ConanException(f"glances __init__.py not found at {init_file}")

        # Verify bundled runtime deps keep their package layout (psutil/,
        # jinja2/, ...). A flattened deps dir would make the package
        # unusable at runtime, so this is a hard structural check.
        expected_deps = {
            "psutil": os.path.join(deps_path, "psutil", "__init__.py"),
            "defusedxml": os.path.join(deps_path, "defusedxml", "__init__.py"),
            "packaging": os.path.join(deps_path, "packaging", "__init__.py"),
            "jinja2": os.path.join(deps_path, "jinja2", "__init__.py"),
            "pyinstrument": os.path.join(deps_path, "pyinstrument", "__init__.py"),
            "shtab": os.path.join(deps_path, "shtab", "__init__.py"),
        }
        missing = [name for name, path in expected_deps.items()
                   if not os.path.isfile(path)]
        if missing:
            raise ConanException(
                f"bundled deps broken (missing package layout): {missing} "
                f"under {deps_path}"
            )
        self.output.info("glances bundled deps layout verified "
                         f"({len(expected_deps)} packages)")

        # R34: Execute the glances binary (--version)
        # Fails when psutil is not signed (OHOS ELF signing limitation)
        # Use try/except because self.run() raises on non-zero exit code
        binary_ok = False
        try:
            self.run(
                f'"{glances_bin}" --version 2>&1 | grep -q "4.5.4"',
                env="conanrun"
            )
            binary_ok = True
        except ConanException:
            binary_ok = False

        # R34: Import the glances module (calls package API)
        # PYTHONPATH includes package root (parent of glances/) and deps
        import_ok = False
        try:
            self.run(
                f'PYTHONPATH="{glances_pkg}:{deps_path}" python3 -c '
                f'"import glances; assert glances.__version__ == \'4.5.4\', '
                f'\'version mismatch\'"',
                env="conanrun"
            )
            import_ok = True
        except ConanException:
            import_ok = False

        if binary_ok and import_ok:
            self.output.info("glances smoke test passed — binary executed and module imported")
        else:
            # psutil's C extension cannot be dlopen'd without ELF signing on
            # this platform (E179 platform limitation). Before falling back,
            # prove the failure IS the psutil load limitation and not a real
            # packaging defect: the actual glances entry point must execute
            # and emit its own psutil diagnostic ("psutil library not found").
            # Any other failure (broken shebang, syntax error, missing file)
            # fails this check and the test hard-fails.
            with tempfile.TemporaryDirectory() as tmpdir:
                diag_log = os.path.join(tmpdir, "glances-version.log")
                self.run(
                    f'"{glances_bin}" --version >"{diag_log}" 2>&1; '
                    f'grep -q "psutil library not found" "{diag_log}"',
                    env="conanrun"
                )
            # Fall back to what CAN be verified without loading native code:
            # 1. pure-Python bundled deps import correctly from the deps dir
            # 2. glances version matches the packaged source
            self.run(
                f'PYTHONPATH="{deps_path}" python3 -c '
                f'"import defusedxml, packaging, shtab, jinja2; '
                f'print(\'pure-python deps import OK\')"',
                env="conanrun"
            )
            self.run(
                f'grep -q "__version__ = \\"4.5.4\\"" "{init_file}"',
                env="conanrun"
            )
            self.output.info("glances smoke test passed via source verification (psutil unavailable)")

        self.output.info("glances package smoke test passed")
