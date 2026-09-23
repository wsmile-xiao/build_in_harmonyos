#!/usr/bin/env python3
"""Conan recipe for canfigger 0.3.2.

canfigger is a small C configuration-file parser library (linked list of
key/value nodes with typed attribute strings, XDG base-dir helpers and a
path-join utility).  Upstream builds with Meson; the recipe obtains the
versioned Meson runner from the ohpcd prebuilt tool package
(meson/1.11.0) instead of relying on a worker-global executable.

OHOS notes:
- Meson installs the shared library as libcanfigger.so.0.3.2 plus versioned
  symlinks.  The versioned aliases are materialized as real files because
  the HarmonyOS loader cannot reliably resolve versioned symlinks in package
  views (libavtp/0.2.0 precedent).
- The recipe deliberately does NOT re-sign the shared objects with
  binary-sign-tool: the hnp clang driver already embeds an ad-hoc
  .codesign section at link time (readelf evidence on every locally built
  .so), and a selfSign-produced copy of libcanfigger.so.0 segfaults the
  musl loader on this device while the linker-signed object loads and runs
  (tested 2026-09-05).  Removing the .codesign section from the re-signed
  copy restores loadability, which pins the crash on the re-signature.
- The upstream test suite is fully self-contained (assert-based C programs,
  no external test framework), so the complete suite is built and executed
  inside build().
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CanfiggerConan(ConanFile):
    name = "canfigger"
    version = "0.3.2"
    description = (
        "Simple configuration file parser library: parses key/value lines "
        "with attributes into a linked list, plus XDG dir helpers"
    )
    license = "MIT"
    homepage = "https://github.com/andy5995/canfigger"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "tests": True,
    }

    def export_sources(self):
        # canfigger 0.3.2 needs no patches; declaring the export keeps the
        # patch pipeline available for future recipe fixes (G1).
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"canfigger requires a POSIX-like target (Linux or OHOS), "
                f"not {self.settings.os}"
            )

    def build_requirements(self):
        # Meson is a published Conan build tool in ohpcd (W0: recipe +
        # OHOS binary verified with conan install --build=never).  Use the
        # tool package instead of a worker-global executable; 1.11.0.1 has
        # no prebuilt binary, so pin 1.11.0.
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = (
            "shared" if bool(self.options.shared) else "static"
        )
        # Upstream registers 12 unit tests plus 2 example programs as meson
        # test() entries when both options are enabled; the recipe runs the
        # complete 14-entry suite inside build() by default.
        toolchain.project_options["build_tests"] = (
            "true" if bool(self.options.tests) else "false"
        )
        toolchain.project_options["build_examples"] = (
            "true" if bool(self.options.tests) else "false"
        )
        toolchain.generate()
        self._inject_archive_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._meson_environment().vars(self).apply():
            meson.configure()
            # -j1: device-default serial build (jobserver noise on this
            # device shows up with higher parallelism).
            self.run(f'meson compile -C "{self.build_folder}" -j1')
            if bool(self.options.tests):
                if cross_building(self):
                    self.output.warning(
                        "Skipping executable upstream tests during a cross "
                        "build; the 14 test executables were compiled."
                    )
                else:
                    self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream meson test suite (12 unit tests + 2 examples,
        14 test entries total) and emit the HMBS_UPSTREAM_TEST_RESULT
        hard-gate marker.  Counts come from the meson framework summary
        (Ok:/Fail:/Skipped:), never from hardcoded values.
        """
        log_path = os.path.join(self.build_folder, "meson_test.log")
        test_cmd = (
            f'meson test -C "{self.build_folder}" --no-rebuild '
            f'--print-errorlogs --timeout-multiplier=16 > "{log_path}" 2>&1'
        )
        self.run(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        def _cnt(pattern):
            match = re.search(pattern, out, flags=re.MULTILINE)
            return int(match.group(1)) if match else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        not_run = _cnt(r"^Not run:\s+(\d+)")
        executed = ok + fail + skipped + timeout + not_run
        gate_ok = executed > 0 and fail == 0 and skipped == 0 \
            and timeout == 0 and not_run == 0
        status = "passed" if gate_ok else "failed"
        result = {
            "status": status,
            "framework": "meson",
            "command": test_cmd,
            "discovered": executed,
            "executed": executed,
            "passed": ok,
            "failed": fail,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        if status != "passed":
            raise RuntimeError(
                "upstream meson tests failed: executed=%d failed=%d skipped=%d"
                % (executed, fail, skipped)
            )

    def package(self):
        with self._meson_environment().vars(self).apply():
            Meson(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if bool(self.options.shared):
            self._materialize_shared_aliases()

    def package_info(self):
        self.cpp_info.libs = ["canfigger"]
        # Upstream pkg-config file ships -I${includedir}/canfigger, so
        # consumers include <canfigger.h>; mirror that layout.
        self.cpp_info.includedirs = [os.path.join("include", "canfigger")]
        self.cpp_info.set_property("cmake_file_name", "canfigger")
        self.cpp_info.set_property("cmake_target_name", "canfigger::canfigger")
        self.cpp_info.set_property("pkg_config_name", "canfigger")

    def _meson_environment(self):
        """Return a Conan-scoped environment for Meson."""
        environment = Environment()
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            environment.prepend_path("PATH", bindir)
        return environment

    def _inject_archive_tools(self):
        """Add llvm-ar/llvm-ranlib when the profile omits Meson's names."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        ar = executables.get("ar") or (
            os.path.join(bindir, "llvm-ar") if bindir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else ""
        )

        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not ar or not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content or "\nar =" in content:
                continue
            insertion = "[binaries]\nar = %r\n" % ar
            if ranlib:
                insertion += "ranlib = %r\n" % ranlib
            content = content.replace("[binaries]\n", insertion, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _materialize_shared_aliases(self):
        """Copy Meson's versioned .so aliases as real files: the HarmonyOS
        loader cannot reliably resolve versioned symlinks in package views.
        """
        library_dir = os.path.join(self.package_folder, "lib")
        source = os.path.join(library_dir, "libcanfigger.so.%s" % self.version)
        aliases = (
            os.path.join(library_dir, "libcanfigger.so.0"),
            os.path.join(library_dir, "libcanfigger.so"),
        )
        if not os.path.isfile(source) or os.path.islink(source):
            raise ConanException(
                f"installed libcanfigger shared object is missing: {source}"
            )
        for alias in aliases:
            if not os.path.islink(alias):
                continue
            os.unlink(alias)
            shutil.copy2(source, alias)
