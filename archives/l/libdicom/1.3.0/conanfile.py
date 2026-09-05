#!/usr/bin/env python3
"""Conan recipe for libdicom 1.3.0 — Meson project (pure C, zero deps).

libdicom is a C library and set of tools for reading DICOM (Digital Imaging
and COmmunications in Medicine) files.  Upstream uses the Meson build system
and depends only on uthash (header-only) plus the Check unit test framework
for its test suite.

Dependencies:
  - uthash/2.3.0 (host, header-only, dict/utarray macros used by src/)
  - check/0.15.2 (test_requires, Check framework for tests/check_dicom.c)

Build strategy (follows libavtp/0.2.0 verified pattern):
  - tool_requires meson/1.11.0 from ohpcd (no worker-global meson on PATH)
  - MesonToolchain generates conan_meson_cross.ini; PkgConfigDeps makes the
    uthash/check packages visible to meson's dependency() lookup
  - uthash is header-only: meson's cc.check_header() probes find the Conan
    package headers through the toolchain CFLAGS, no subproject wrap needed
  - upstream test suite (meson test, 1 check_dicom binary with 31 START_TEST
    cases) runs in build() on the build host (native build for OHOS runs on
    the same aarch64 device), counts parsed from the meson summary
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class LibdicomConan(ConanFile):
    name = "libdicom"
    version = "1.3.0"
    description = "C library for reading DICOM files"
    license = "MIT"
    homepage = "https://github.com/ImagingDataCommons/libdicom"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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
                f"libdicom requires a POSIX-like target (Linux or OHOS), "
                f"not {self.settings.os}"
            )

    def requirements(self):
        # uthash is a header-only library used by libdicom src/ (utarray.h,
        # uthash.h macros).  Conan package provides include/ headers; meson's
        # cc.check_header() probe succeeds via the toolchain CFLAGS, so the
        # upstream subproject wrap fallback is never taken.
        self.requires("uthash/2.3.0")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        if bool(self.options.tests):
            # Check unit-test framework for tests/check_dicom.c (31 cases).
            self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate *.pc files so meson dependency('uthash') / dependency('check')
        # resolve against the Conan packages instead of the wrap subprojects.
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if bool(self.options.shared) else "static"
        )
        # meson_options.txt declares tests as boolean: pass true/false, not
        # enabled/disabled (that syntax is for feature options).
        tc.project_options["tests"] = "true" if bool(self.options.tests) else "false"
        tc.generate()
        self._inject_archive_tools()

    def _meson_environment(self):
        """Conan-scoped environment for meson/ninja invocations."""
        environment = Environment()
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            environment.prepend_path("PATH", bindir)

        # The ambient LD_LIBRARY_PATH on this device contains whitespace-only
        # entries (e.g. "         /system/lib64") which musl's loader cannot
        # resolve, breaking the spawn of hnp tools linked against
        # libc++_shared.so (ninja).  Strip blank/whitespace entries and make
        # sure /system/lib64 stays searchable.
        ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        parts = [p.strip() for p in ld_path.split(":") if p.strip()]
        if "/system/lib64" not in parts:
            parts.append("/system/lib64")
        environment.define("LD_LIBRARY_PATH", ":".join(parts))
        return environment

    def _inject_archive_tools(self):
        """Add llvm-ar/llvm-ranlib/ninja to the meson machine files.

        Two reasons (both verified on this device):
        1. ar/ranlib: the profile only pins the compiler path; meson would
           otherwise probe bare `llvm-ar` names (follows libavtp/0.2.0).
        2. ninja: HarmonyOS CPython forces subprocess through posix_spawn,
           which does NOT resolve bare names against PATH — meson's ninja
           detection spawns `ninja --version` by bare name and fails with
           ENOENT.  Registering ninja in the [binaries] section of the
           machine file makes meson use the absolute path directly.
        """
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
        ninja = executables.get("ninja") or (
            os.path.join(bindir, "ninja") if bindir else ""
        )

        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insertion = "[binaries]\n"
            if ar and "\nar =" not in content:
                insertion += "ar = %r\n" % ar
            if ranlib and "ranlib =" not in content:
                insertion += "ranlib = %r\n" % ranlib
            if ninja and "ninja =" not in content:
                insertion += "ninja = %r\n" % ninja
            if insertion == "[binaries]\n":
                continue
            content = content.replace("[binaries]\n", insertion, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        with self._meson_environment().vars(self).apply():
            native_file = os.path.join(
                self.generators_folder, "conan_meson_native.ini"
            )
            self._run_meson(
                f'meson setup --native-file "{native_file}" '
                f'"{self.build_folder}" "{self.source_folder}" --prefix=/'
            )
            self._run_meson(f'meson compile -C "{self.build_folder}" -j1')

            if bool(self.options.tests):
                self._run_upstream_tests()

    def _run_meson(self, command, ignore_errors=False):
        """Run a meson subcommand with NINJA pointing at an absolute path.

        HarmonyOS CPython forces subprocess through posix_spawn, which does
        NOT resolve bare names against PATH.  Meson's ninja detection spawns
        `ninja --version` by bare name and fails with ENOENT even though
        ninja is on PATH, so we export NINJA=/data/service/hnp/bin/ninja
        (meson honours the NINJA env var in tooldetect, verified pattern
        from callaudiocli/0.1.10).
        """
        ninja = os.environ.get("NINJA")
        if not ninja or not os.path.isfile(ninja):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = executables.get("c") or ""
            candidate = (
                os.path.join(os.path.dirname(compiler), "ninja")
                if os.sep in compiler else ""
            )
            ninja = candidate if candidate and os.path.isfile(candidate) else ""
        if not ninja:
            ninja = shutil.which("ninja") or ""
        if ninja:
            self.run(f'NINJA="{ninja}" {command}', ignore_errors=ignore_errors)
        else:
            self.run(command, ignore_errors=ignore_errors)

    def _run_upstream_tests(self):
        """Run the upstream meson test suite (check framework, 1 binary
        check_dicom, 31 START_TEST cases) and record the pass rate.

        Counts come from the meson test summary (Ok:/Fail:/Skipped:), never
        from hardcoded values.  The HMBS_UPSTREAM_TEST_RESULT marker carries
        the structured result for the archive reports.
        """
        # check_dicom has build_by_default: false in meson.build — build the
        # test target explicitly before running meson test.
        self._run_meson(
            f'meson compile -C "{self.build_folder}" -j1 check_dicom'
        )
        log_path = os.path.join(self.build_folder, "meson_test.log")
        # Check's open_tmp_file() probes TEMP first, then P_tmpdir (/tmp is
        # read-only on OHOS), then TMPDIR.  CI workers set TMPDIR to a
        # cache partition that mkstemp() cannot write to, making every test
        # binary die with "Unable to create temporary file for
        # communication" (check_msg.c:317).  Point TEMP/TMPDIR at the build
        # folder, which is always writable in both local and CI runs.
        test_cmd = (
            f'TEMP="{self.build_folder}" TMPDIR="{self.build_folder}" '
            f'meson test -v -C "{self.build_folder}" '
            "--no-rebuild --print-errorlogs "
            f'> "{log_path}" 2>&1'
        )
        self._run_meson(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        def _cnt(pat):
            m = re.search(pat, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        not_run = _cnt(r"^Not run:\s+(\d+)")
        executed = ok + fail + skipped + timeout + not_run
        passed = ok
        gate_ok = (
            executed > 0 and fail == 0 and skipped == 0
            and timeout == 0 and not_run == 0
        )
        ut_status = "passed" if gate_ok else "failed"
        ut_result = {
            "status": ut_status,
            "framework": "meson+check",
            "command": test_cmd,
            "discovered": executed,
            "executed": executed,
            "passed": passed,
            "failed": fail,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(ut_result, ensure_ascii=False)
        )
        if ut_status != "passed":
            raise RuntimeError(
                "upstream meson tests failed: executed=%d failed=%d "
                "skipped=%d timeout=%d not_run=%d"
                % (executed, fail, skipped, timeout, not_run)
            )

    def package(self):
        with self._meson_environment().vars(self).apply():
            self._run_meson(
                f'meson install -C "{self.build_folder}" '
                f'--destdir "{self.package_folder}" --no-rebuild'
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if bool(self.options.shared):
            self._materialize_shared_aliases()

    def _materialize_shared_aliases(self):
        """HMDFS has no reliable symlinks: replace meson's libdicom.so.1.3.0
        alias chain with real copies (rm -f && cp, follows R5)."""
        library_dir = os.path.join(self.package_folder, "lib")
        source = os.path.join(library_dir, "libdicom.so.1.3.0")
        aliases = (
            os.path.join(library_dir, "libdicom.so.1"),
            os.path.join(library_dir, "libdicom.so"),
        )
        if not os.path.isfile(source) or os.path.islink(source):
            raise ConanException(
                f"installed libdicom shared object is missing: {source}"
            )
        for alias in aliases:
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copy2(source, alias)

    def package_info(self):
        self.cpp_info.libs = ["dicom"]
        self.cpp_info.set_property("cmake_file_name", "libdicom")
        self.cpp_info.set_property("cmake_target_name", "libdicom::dicom")
        self.cpp_info.set_property("pkg_config_name", "libdicom")
