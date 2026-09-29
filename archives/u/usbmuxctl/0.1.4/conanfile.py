#!/usr/bin/env python3
"""Conan recipe for usbmuxctl 0.1.4 — Linux Automation USB-Mux control tool.

Upstream: https://github.com/linux-automation/usbmuxctl (PyPI usbmuxctl 0.1.4).
Pure-Python console application + importable module (usbmuxctl/__main__.py,
usbmuxctl/usbmuxctl.py, usbmuxctl/update.py, usbmuxctl/firmware/).
Entry point: usbmuxctl = usbmuxctl.__main__:main (pyproject [project.scripts]).
Runtime deps (pyproject dependencies): pyusb, termcolor (both pure-Python),
plus the libusb-1.0 shared library that pyusb loads at runtime via ctypes.

Dependency handling (R36/PF4): neither pyusb nor the Python termcolor exist
as ohpcd conan recipes (ohpcd termcolor/2.1.0 is the C++ header-only library,
not the Python package), so the two wheels are pip-vendored from the
community mirror into <package>/deps (labgrid 26.0 precedent);
package_info() puts site-packages + deps on PYTHONPATH so the consumer works
offline. The native USB backend comes from registry libusb/1.0.27
(uhubctl/usbutils/usbredir precedent, shared=True so pyusb ctypes can load
libusb-1.0.so); without it Mux.find_devices() raises
usb.core.NoBackendError: No backend available on a bare OHOS image.

Build: no C compilation. The sdist is installed by copying the usbmuxctl/
package tree verbatim into site-packages (packaging 26.3 precedent — avoids
PEP 517 setuptools_scm git-metadata lookup) plus a generated bin/usbmuxctl
console script. No patches; apply_conandata_patches() kept as no-op for
patch-readiness.

Upstream tests: none. The sdist contains no tests/ or test/ directory, no
pytest/ctest/make-check entry (Makefile only has ruff/codespell QA targets).
build() audits the tree, emits HMBS_UPSTREAM_TEST_RESULT status no_tests,
and persists res/upstream_test_result.json so test_package can re-emit the
marker on cached preflights (abuild-sudo precedent).
"""

import json
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

PYPI_MIRROR = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"
PYPI_HOST = "pypi.cnb.cool"

RUNTIME_PINS = [
    "pyusb==1.3.1",
    "termcolor==2.1.1",
]


class UsbmuxctlConan(ConanFile):
    name = "usbmuxctl"
    version = "0.1.4"
    description = "Tool to control a USB-Mux from the command line (Linux Automation)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/linux-automation/usbmuxctl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("usb", "mux", "labgrid", "cli", "python")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"usbmuxctl supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # Native USB backend for pyusb (ctypes): uhubctl/usbutils/usbredir
        # precedent. Python pyusb/termcolor stay pip-vendored (see docstring).
        self.requires("libusb/1.0.27")

    def configure(self):
        # pyusb loads libusb-1.0 via ctypes at runtime, so it needs the
        # shared object, not a static archive.
        self.options["libusb"].shared = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["usbmuxctl"], strip_root=True)

    def _python(self):
        for candidate in ("/data/service/hnp/bin/python3", sys.executable):
            if candidate and os.path.isfile(candidate):
                return candidate
        return sys.executable

    def _pip_install(self, packages, target):
        os.makedirs(target, exist_ok=True)
        cmd = [
            self._python(), "-m", "pip", "install",
            "--disable-pip-version-check", "--no-compile", "--quiet",
            "--index-url", PYPI_MIRROR, "--trusted-host", PYPI_HOST,
            "--target", target,
        ] + list(packages)
        self.output.info("[usbmuxctl] pip install: %s" % " ".join(packages))
        proc = subprocess.run(
            cmd, cwd=self.build_folder, capture_output=True, text=True, timeout=1200
        )
        for line in (proc.stdout + proc.stderr).splitlines()[-15:]:
            self.output.info("[usbmuxctl pip] %s" % line)
        if proc.returncode != 0:
            raise ConanException("[usbmuxctl] pip install failed: %s" % " ".join(packages))

    def _audit_no_tests(self):
        checks = []
        src = self.source_folder
        for rel in ("tests", "test", "pytest.ini", "tox.ini", "setup.cfg"):
            full = os.path.join(src, rel)
            if rel in ("setup.cfg",):
                # setup.cfg exists but only holds [egg_info], no test config.
                if os.path.isfile(full):
                    with open(full, "r", encoding="utf-8", errors="replace") as fh:
                        body = fh.read()
                    checks.append((rel, "present but no test config" if "test" not in body.lower() and "pytest" not in body.lower() else "HAS TEST CONFIG"))
                else:
                    checks.append((rel, "absent"))
            else:
                exists = os.path.exists(full)
                checks.append((rel, "PRESENT" if exists else "absent"))
                if exists:
                    raise ConanException(f"[usbmuxctl] unexpected upstream test path: {rel}")
        # Makefile only provides ruff/codespell QA, no test target.
        makefile = os.path.join(src, "Makefile")
        if os.path.isfile(makefile):
            with open(makefile, "r", encoding="utf-8", errors="replace") as fh:
                mk = fh.read()
            if "pytest" in mk or "make check" in mk or "ctest" in mk:
                raise ConanException("[usbmuxctl] Makefile unexpectedly references a test runner")
            checks.append(("Makefile", "qa-only (ruff/codespell), no test target"))
        return checks

    def build(self):
        apply_conandata_patches(self)
        checks = self._audit_no_tests()
        for name, result in checks:
            self.output.info(f"[usbmuxctl audit] {name}: {result}")

        # Vendor pure-Python runtime closure for the self-test import probe.
        deps = os.path.join(self.build_folder, "deps")
        self._pip_install(RUNTIME_PINS, deps)

        # Hardware-free self check: import the pristine tree with vendored deps.
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([self.source_folder, deps])
        probe = subprocess.run(
            [self._python(), "-c", "import usbmuxctl, usb.core, termcolor; print('import-ok')"],
            cwd=self.source_folder, env=env, capture_output=True, text=True, timeout=120,
        )
        self.output.info("[usbmuxctl] import probe rc=%d: %s" % (probe.returncode, (probe.stdout + probe.stderr).strip()[-500:]))
        if probe.returncode != 0:
            raise ConanException("[usbmuxctl] import probe failed")

        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream usbmuxctl 0.1.4 ships no automated tests; "
                "sdist has no tests/ or test/ directory, no pytest/ctest/make-check "
                "entry (Makefile only runs ruff/codespell QA); audit in build() "
                "verified each path absent"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        # Persist for test_package re-emit on cached preflights.
        res_dir = os.path.join(self.build_folder, "upstream_res")
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(res_dir, "upstream_test_result.json"), "w", encoding="utf-8") as fh:
            json.dump(marker, fh)

    def package(self):
        # Vendor runtime closure into the package.
        deps_dst = os.path.join(self.package_folder, "deps")
        self._pip_install(RUNTIME_PINS, deps_dst)

        pyver = "python%d.%d" % sys.version_info[:2]
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        os.makedirs(site, exist_ok=True)
        src_pkg = os.path.join(self.source_folder, "usbmuxctl")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"[usbmuxctl] package dir missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "usbmuxctl"),
            ignore=shutil.ignore_patterns("__pycache__"),
            dirs_exist_ok=True,
        )
        # Minimal dist-info so `pip show` / importlib.metadata can see it.
        dist_info = os.path.join(site, "usbmuxctl-0.1.4.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as fh:
            fh.write("Metadata-Version: 2.1\nName: usbmuxctl\nVersion: 0.1.4\n")
        with open(os.path.join(dist_info, "entry_points.txt"), "w", encoding="utf-8") as fh:
            fh.write("[console_scripts]\nusbmuxctl=usbmuxctl.__main__:main\n")

        # Console script bin/usbmuxctl (R38 application entry point).
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        script = os.path.join(bindir, "usbmuxctl")
        with open(script, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!/usr/bin/env python3\n")
            fh.write("from usbmuxctl.__main__ import main\n")
            fh.write("if __name__ == '__main__':\n")
            fh.write("    main()\n")
        os.chmod(script, 0o755)

        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

        # Persist upstream evidence for cached-preflight re-emit.
        res_src = os.path.join(self.build_folder, "upstream_res", "upstream_test_result.json")
        res_dst = os.path.join(self.package_folder, "res")
        os.makedirs(res_dst, exist_ok=True)
        if os.path.isfile(res_src):
            shutil.copyfile(res_src, os.path.join(res_dst, "upstream_test_result.json"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        pyver = "python%d.%d" % sys.version_info[:2]
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        for env in (self.runenv_info, self.buildenv_info):
            env.prepend_path("PYTHONPATH", site)
            env.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "deps"))
