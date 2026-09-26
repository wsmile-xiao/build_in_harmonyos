#!/usr/bin/env python3
"""Conan recipe for udt 4.11 (UDP-based Data Transfer).

UDT is a makefile-based C++ library (src/Makefile -> libudt.so + libudt.a,
app/Makefile -> example/test programs).  Build details:

  - Compiler: we override the hard-coded `g++` with the Conan-toolchain C++
    compiler.  GNU make silently ignores a command-line `C++=...` override (the
    `+` in the variable name breaks make's override mechanism), so the upstream
    Makefiles must be patched (0002) to rename `C++` -> `CXX`; we then pass
    `CXX=<compiler>` which make honors (R33: `tools.build:compiler_executables:cpp`,
    defaults to clang++).
  - aarch64 timing: the src Makefile maps `arch=IA32/AMD64` to the
    `-DIA32`/`-DAMD64` macros, which select x86-specific `rdtsc` inline
    assembly inside CTimer.  That asm does not compile on aarch64.  By passing
    an *empty* `arch=` (so no arch macro is defined), UDT falls back to its
    portable `getTime()` microsecond timer, which is the correct path on OHOS.
  - os=LINUX: UDT only special-cases WIN32; Linux/OHOS share the POSIX socket
    code path (`#ifndef WIN32`).
  - Upstream test: the self-contained `app/test` binary runs 4 loopback data
    path cases (simple stream, parallel UDT+TCP, rendezvous, multi-thread) in
    one process.  Its per-thread failures only print to stdout and main()
    still returns 0, so we treat the output as the source of truth: mark failed
    if any failure indicator is present or fewer than 4 "Test # N completed."
    lines appear (falsification, not blind exit-code trust).
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class UdtConan(ConanFile):
    name = "udt"
    version = "4.11"
    description = "UDP-based Data Transfer (UDT): high-performance reliable application-level data transport protocol library"
    license = "BSD-3-Clause"
    homepage = "https://udt.sourceforge.io/"
    url = ""  # CI fills this

    package_type = "library"

    # Conan enforces that a `library` package_type declares a `shared` option;
    # without it `conan create` fails with
    # "Package type is 'library', but no 'shared' option declared".
    # UDT's Makefile builds both libudt.so and libudt.a unconditionally; the
    # option selects which artifacts package() ships to the consumer.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    settings = "os", "compiler", "build_type", "arch"

    # Upstream test count: app/test.cpp main() runs exactly 4 test cases
    # (Test_1..Test_4) via g_UDTPerThread-independent test_case = 4.
    _UPSTREAM_TEST_CASES = 4

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"udt is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # The UDT official tarball (udt.sdk.4.11.tar.gz) stores every entry with a
        # leading "./" prefix ("./udt4/src/...", "./udt4/app/...").  Conan's
        # untargz() strip_root logic computes the common root from
        # `name.split("/", 1)[0]` of the first (directory) member, which for
        # "./udt4/" yields "." -- so it strips only the "./" and the tree is
        # extracted under a `udt4/` subfolder (NOT src/, app/ at the top).
        # Relying on strip_root=True therefore leaves a udt4/ wrapper and makes
        # `make -C src` fail with "src: No such file or directory" (HMBS preflight
        # compile failure).  We drop strip_root and resolve the real tree root via
        # _src_root() (the single top-level udt4/ folder).
        get(self, **self.conan_data["sources"])
        apply_conandata_patches(self)

    def _src_root(self):
        """Resolve the unpacked source tree root.

        After get() (without strip_root) the archive extracts into a single
        top-level `udt4/` folder.  Return that folder (deterministic), falling
        back to source_folder if for some reason no wrapper dir was created.
        """
        root = self.source_folder
        try:
            entries = [
                e for e in os.listdir(root)
                if os.path.isdir(os.path.join(root, e))
            ]
        except OSError:
            return root
        for name in entries:
            if name == "udt4":
                return os.path.join(root, name)
        # Only one top-level folder -> that is the tree root.
        if len(entries) == 1 and entries[0] not in (".git",):
            return os.path.join(root, entries[0])
        return root

    def _cxx(self):
        """C++ compiler from Conan conf (R33), never from raw shell env vars."""
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return comp.get("cpp") or "clang++"

    def _tmp_env(self):
        """Return a build env with TMPDIR/TMP/TEMP forced to a writable dir.

        On HarmonyOS /tmp is a root-owned read-only directory (HMBS platform
        diag `readonly_tmp`).  The clang toolchain redirects its temporary
        assembler/compile files to $TMPDIR, and the Conan `self.run()` shell
        wrapper may also need a writable location for its own temporary files;
        if TMPDIR is unset or inherited as the read-only /tmp every compile
        fails with "can't create temporary file /tmp/...: Read-only file
        system" and `make -C src` reports Error 2.

        Key deviation from the earlier (ineffective) attempt: we do NOT trust
        any inherited TMPDIR/TMP/TEMP (those may resolve to the read-only
        /tmp) - we *always* force them onto the Conan build folder, which
        Conan guarantees to be writable.  We also build and return a dict that
        is passed to the make subprocess explicitly.
        """
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = dict(os.environ)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        return env

    def _make_path(self):
        """Absolute path of `make`, preferring the HMBS-injected one."""
        return (
            os.environ.get("HMBS_MAKE")
            or shutil.which("make")
            or "make"
        )

    def _run_make(self, make_cmd, cwd):
        """Run `make` via subprocess with an explicit writable-TMPDIR env.

        We spawn make directly (shell=False) instead of using `self.run()`
        because Conan 2's `self.run()` wraps the command in its own /bin/sh
        invocation that can itself hit the read-only /tmp for a temporary
        file; executing the make binary directly with an explicit env puts
        make, its recipe shells and clang all inside a writable-TMPDIR
        environment.
        """
        env = self._tmp_env()
        proc = subprocess.run(
            make_cmd, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        if proc.stdout:
            self.output.info(proc.stdout.rstrip())
        if proc.returncode != 0:
            raise ConanException(
                f"make failed ({proc.returncode}): {' '.join(make_cmd)}\n"
                f"{(proc.stdout or '')[-4000:]}"
            )

    def build(self):
        cxx = self._cxx()
        make = self._make_path()
        # Pass an empty `arch=` so no IA32/AMD64 macro is defined -> portable
        # microsecond timer instead of x86 rdtsc asm (aarch64-safe).
        # NOTE: upstream Makefiles hardcode `C++ = g++`.  GNU make *silently
        # ignores* a command-line `C++=...` override (the `+` in the variable
        # name breaks command-line/env overriding), so the hardcoded g++ always
        # won and, on workers without g++, builds failed with
        # "g++: No such file or directory".  We patch src/Makefile + app/Makefile
        # to rename the variable to `CXX` (0002 patch), which make DOES override,
        # and pass `CXX=` here.
        make_args = ["os=LINUX", "arch=", f"CXX={cxx}"]

        src_cmd = [make, "-C", "src", *make_args, "all"]
        self._run_make(src_cmd, cwd=self._src_root())

        # Build only the self-contained upstream test binary (links libudt).
        test_make_cmd = [make, "-C", "app", *make_args, "test"]
        self._run_make(test_make_cmd, cwd=self._src_root())

        self._run_upstream_test(cxx, src_cmd, test_make_cmd)

    def _run_upstream_test(self, cxx, src_cmd, test_make_cmd):
        """Run the upstream app/test binary and emit HMBS evidence.

        The test binary always exits 0 even when a sub-test fails (threads
        return void* and main() ignores them), so we count the "Test # N
        completed." markers and scan for explicit failure indicators.
        """
        src_root = self._src_root()
        app_dir = os.path.join(src_root, "app")
        src_dir = os.path.join(src_root, "src")
        # Run from the app dir so `../src` resolves to the just-built libudt.so.
        run_cmd = f"cd {app_dir} && LD_LIBRARY_PATH={src_dir} ./test"
        actual_commands = "; ".join(
            [" ".join(src_cmd), " ".join(test_make_cmd), run_cmd]
        )
        discovered = self._UPSTREAM_TEST_CASES

        env = self._tmp_env()  # writable TMPDIR/TMP/TEMP for the test binary
        env["LD_LIBRARY_PATH"] = src_dir
        try:
            proc = subprocess.run(
                [os.path.join(app_dir, "test")],
                cwd=app_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600,
            )
            output = proc.stdout or ""
            rc = proc.returncode
        except Exception as exc:  # subprocess-level failure
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                    "status": "failed",
                    "framework": "udt app/test",
                    "command": actual_commands,
                    "discovered": discovered,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": f"test harness could not run: {exc!r}",
                }, ensure_ascii=False)
            )
            raise

        # "Test # N completed." markers denote a fully executed test case.
        completed = len(re.findall(r"Test # \d+ completed\.", output))
        # Explicit failure indicators printed by the test cases.
        failure_indicators = [
            "DATA ERROR", "send:", "recv:", "illegal port",
            "bind:", "connect:", "socket:", " failed",
        ]
        has_failure = any(ind in output for ind in failure_indicators)

        if rc == 0 and completed == discovered and not has_failure and output.strip():
            result = {
                "status": "passed",
                "framework": "udt app/test",
                "command": actual_commands,
                "discovered": discovered,
                "executed": discovered,
                "passed": discovered,
                "failed": 0,
                "skipped": 0,
            }
        else:
            # Non-zero rc, or fewer completed markers than discovered, or an
            # explicit failure indicator, or empty output (silent-skip trap).
            reason = []
            if rc != 0:
                reason.append(f"exit code {rc}")
            if completed != discovered:
                reason.append(f"completed {completed}/{discovered} test markers")
            if has_failure:
                reason.append("failure indicator(s) present in output")
            if not output.strip():
                reason.append("empty test output (silent skip)")
            result = {
                "status": "failed",
                "framework": "udt app/test",
                "command": actual_commands,
                "discovered": discovered,
                "executed": completed,
                "passed": completed,
                "failed": max(1, discovered - completed),
                "skipped": 0,
                "reason": "; ".join(reason) or "upstream test failed",
            }
            self.output.warning("udt upstream test FAILED")
            self.output.info(output[-4000:])

        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        # Also emit on raw stdout so the marker is trivially greppable even
        # when conan's info() line-wrapping could interfere.
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(result, ensure_ascii=False), flush=True)

        # Persist the machine evidence so test_package can re-emit it on EVERY
        # preflight, including the "Already installed! (1 of 1)" case where
        # conan skips this cached build() entirely and no marker would
        # otherwise appear (HMBS marker chain: build() -> res/ -> test_package).
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(result, fh)

        if result["status"] != "passed":
            raise ConanException("udt upstream tests failed")

    def package(self):
        src_root = self._src_root()
        copy(self, "udt.h",
             os.path.join(src_root, "src"),
             os.path.join(self.package_folder, "include"))
        # Ship either the shared or the static lib depending on the option
        # (upstream builds both; we expose the requested one to the consumer).
        if self.options.shared:
            copy(self, "libudt.so",
                 os.path.join(src_root, "src"),
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libudt.a",
                 os.path.join(src_root, "src"),
                 os.path.join(self.package_folder, "lib"))
        # Persist the upstream test evidence in the packaged res/ so the
        # test_package stage can re-emit HMBS_UPSTREAM_TEST_RESULT on every
        # preflight — including cached "Already installed!" runs where build()
        # (and its marker) is skipped (HMBS marker chain).
        res_json = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(res_json):
            copy(self, "upstream_test_result.json",
                 self.build_folder, os.path.join(self.package_folder, "res"))
        else:
            self.output.warning(
                "upstream_test_result.json missing from build folder; "
                "test_package will fail rather than pass silently")
        copy(self, "LICENSE*",
             src_root,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["udt"]
        # Respect the shared option in the consumer link.
        self.cpp_info.set_property("cmake_file_name", "udt")
        self.cpp_info.set_property("cmake_target_name", "udt::udt")
        self.cpp_info.set_property("pkg_config_name", "udt")
        if not self.options.shared:
            self.cpp_info.defines.append("UDT_STATIC")
