#!/usr/bin/env python3
"""Conan recipe for wsdd 0.8 on HarmonyOS PC.

wsdd is a pure Python Web Service Discovery host daemon.  The upstream
source ships one executable module (src/wsdd.py), so the recipe installs it
as bin/wsdd and performs a syntax check during build().  Upstream does not
ship a formal unit-test framework, but its regression runner discovers three
shell tests.  One can run with the device Python 3.12 runtime; the other two
require Python 3.7-3.11 and netcat and are recorded as environment skips
rather than counted as passes.  A portability patch maps HarmonyOS onto the
OHOS address-monitor path from libc getifaddrs(), because the device Python
does not expose a working AF_NETLINK socket.
"""

import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
)
from conan.tools.layout import basic_layout


class WsddConan(ConanFile):
    name = "wsdd"
    version = "0.8"
    description = "Web Service Discovery host daemon for Windows Network Neighborhood interoperability"
    license = "MIT"
    homepage = "https://github.com/christgau/wsdd"
    url = "https://github.com/christgau/wsdd"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wsdd supports Linux and OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "src", "wsdd.py")
        if not os.path.isfile(script):
            raise ConanInvalidConfiguration(f"upstream wsdd.py is missing: {script}")
        self.run(f'"{sys.executable}" -m py_compile "{script}"')
        self._run_upstream_regressions()

    def _run_upstream_regressions(self):
        shell = "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(
                "HarmonyOS bash is required for upstream regressions"
            )
        root = os.path.join(self.source_folder, "test", "regressions")
        cases = (
            (
                "tcp-python-version-matrix",
                os.path.join(root, "01_asyncio_changes_python310", "run_tcp.sh"),
                True,
            ),
            (
                "unix-python-version-matrix",
                os.path.join(root, "01_asyncio_changes_python310", "run_unix.sh"),
                True,
            ),
            (
                "non-existing-interface-regression",
                os.path.join(root, "02_non_existing_interface", "run.sh"),
                False,
            ),
        )
        marker = os.path.join(self.build_folder, "wsdd-upstream-regression.rc")
        passed = 0
        skipped = 0
        executed = 0
        for name, script, allow_environment_skip in cases:
            if not os.path.isfile(script):
                raise ConanInvalidConfiguration(
                    f"missing upstream regression: {script}"
                )
            log = os.path.join(self.build_folder, f"wsdd-{name}.log")
            command = (
                f"WSDD_ROOT_DIR={shlex.quote(self.source_folder)} "
                f"WSDD_SCRIPT={shlex.quote(os.path.join(self.source_folder, 'src', 'wsdd.py'))} "
                f"{shlex.quote(shell)} {shlex.quote(script)} > {shlex.quote(log)} 2>&1; "
                "rc=$?; "
                f"cat {shlex.quote(log)} 2>/dev/null || true; "
                f"printf '%s' \"$rc\" > {shlex.quote(marker)}"
            )
            self.run(command, env="conanbuild", ignore_errors=True)
            with open(marker, encoding="ascii") as handle:
                rc = int(handle.read().strip())
            if rc == 0:
                with open(log, encoding="utf-8", errors="replace") as handle:
                    output = handle.read()
                if "Traceback (most recent call last)" in output:
                    raise ConanException(
                        f"upstream regression {name} returned 0 after a traceback"
                    )
                passed += 1
                executed += 1
            elif rc == 2 and allow_environment_skip:
                skipped += 1
            else:
                raise ConanException(
                    f"upstream regression {name} failed with exit code {rc}"
                )
        result = {
            "status": "executed_with_environment_skips" if skipped else "passed",
            "framework": "custom-shell-regressions",
            "command": "test/regressions/run-regressions.sh",
            "discovered": len(cases),
            "executed": executed,
            "passed": passed,
            "failed": 0,
            "skipped": skipped,
            "skipReason": (
                "the two Python-version matrix scripts require Python 3.7-3.11 "
                "and netcat; the OpenDesk image provides Python 3.12 only"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))

    def package(self):
        copy(
            self,
            "wsdd.py",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        launcher = os.path.join(self.package_folder, "bin", "wsdd")
        installed_script = os.path.join(self.package_folder, "bin", "wsdd.py")
        if not os.path.isfile(installed_script):
            raise ConanInvalidConfiguration(f"packaged wsdd.py is missing: {installed_script}")
        rename(self, installed_script, launcher)
        os.chmod(launcher, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
