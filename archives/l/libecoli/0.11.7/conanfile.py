#!/usr/bin/env python3
"""Conan recipe for libecoli 0.11.7 (Meson, C99).

Libecoli is an Extensible COmmand LIne library: grammar-based parsing,
dynamic completion, shell-like lexing and string-vector helpers.

Build choices (Path A, deterministic):
- Optional features yaml/editline are disabled, so the package has zero
  Conan dependencies and the unit-test set is fixed (32 tests, no yaml).
  Upstream enables them via auto-detection; explicit disabled keeps the
  OHOS build reproducible and avoids wiring libyaml/libedit in v1.
- doc/examples are disabled (doc needs doxygen, examples need libedit).
- Upstream tests are executed in build() via `meson test`.
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibecoliConan(ConanFile):
    name = "libecoli"
    version = "0.11.7"
    description = "Extensible COmmand LIne library (grammar parsing, completion, shell lexing)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rjarry/libecoli"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # True-machine/CI workers only guarantee cmake/make/ninja/python3
        # on PATH (HMBS_BUILD_TOOLS); meson must come from the registry.
        # meson/1.11.0 and ninja/1.12.1 are both published (see SUMMARY.md).
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _inject_ohos_archiver(self):
        """Add SDK binutils when the OHOS profile only declares clang."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        # Prefer the verified compiler discovered in build() (env CC), as
        # the profile path may be stale on some workers/preflight hosts.
        if os.environ.get("CC") and os.path.isfile(os.environ["CC"]):
            compiler = os.environ["CC"]
        compiler_dir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or (
            os.path.join(compiler_dir, "llvm-ar") if compiler_dir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(compiler_dir, "llvm-ranlib") if compiler_dir else ""
        )
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not (ar and os.path.isfile(ar) and os.path.isfile(native_file)):
            return

        with open(native_file, encoding="utf-8") as stream:
            content = stream.read()
        if "\nar =" in content or "[binaries]\n" not in content:
            return

        additions = "ar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib and os.path.isfile(ranlib):
            additions += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        content = content.replace("[binaries]\n", "[binaries]\n" + additions, 1)
        with open(native_file, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.get_safe("shared") else "static"
        )
        # Deterministic Path-A feature set: no optional deps, no docs.
        tc.project_options["yaml"] = "disabled"
        tc.project_options["editline"] = "disabled"
        tc.project_options["doc"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "enabled"
        # Upstream sets werror=true; OHOS SDK headers may emit warnings
        # that are not actionable upstream, so do not fail the build on them.
        if self.settings.os == "OHOS":
            tc.project_options["werror"] = "false"
        tc.generate()

        if self.settings.os == "OHOS":
            self._inject_ohos_archiver()

    @staticmethod
    def _probe_tool(cmd):
        """True if `cmd --version` runs (rc 0); filters stale PATH entries."""
        try:
            proc = subprocess.run(
                [cmd, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _discover_ohos_compilers(self):
        """Find working C/CXX drivers (profile path may not exist).

        Returns (c, cxx); either may be None when nothing usable is found.
        When only one side works, the caller reuses it for the other side.
        """
        if self.settings.os != "OHOS":
            return None, None
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        c_cands = []
        cxx_cands = []
        if executables.get("c"):
            c_cands.append(executables["c"])
        if executables.get("cpp"):
            cxx_cands.append(executables["cpp"])
        if os.environ.get("CC"):
            c_cands.append(os.environ["CC"])
        if os.environ.get("CXX"):
            cxx_cands.append(os.environ["CXX"])
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found and found not in c_cands:
                c_cands.append(found)
        for name in ("clang++", "c++", "g++"):
            found = shutil.which(name)
            if found and found not in cxx_cands:
                cxx_cands.append(found)
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/clang",
            "/data/service/hnp/ohos-sdk/ohos/native/llvm/bin/clang",
            "/storage/Users/currentUser/usr/local/bin/clang",
        ):
            for path in sorted(glob.glob(pattern)):
                if path not in c_cands:
                    c_cands.append(path)
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/clang++",
            "/data/service/hnp/ohos-sdk/ohos/native/llvm/bin/clang++",
            "/storage/Users/currentUser/usr/local/bin/clang++",
        ):
            for path in sorted(glob.glob(pattern)):
                if path not in cxx_cands:
                    cxx_cands.append(path)
        c = next((p for p in c_cands if p and self._probe_tool(p)), None)
        cxx = next((p for p in cxx_cands if p and self._probe_tool(p)), None)
        if c is None and cxx is not None:
            c = cxx
        if cxx is None and c is not None:
            cxx = c
        return c, cxx

    def _fix_meson_native_compilers(self):
        """Rewrite native-file c/cpp rows to verified drivers (meson port).

        Mirrors the validated spglib approach (probe then regex-replace the
        toolchain file), adapted from conan_toolchain.cmake to
        conan_meson_native.ini. Must run in build() after buildenv is
        active and before meson.configure().
        """
        if self.settings.os != "OHOS":
            return
        c, cxx = self._discover_ohos_compilers()
        if not c and not cxx:
            return
        native_file = os.path.join(
            self.generators_folder, "conan_meson_native.ini"
        )
        if not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as stream:
            content = stream.read()
        if c:
            content, _ = re.subn(
                r"(?m)^c\s*=\s*'.*'$",
                "c = '{}'".format(c.replace("\\", "/")),
                content,
                count=1,
            )
            os.environ["CC"] = c
        if cxx:
            content, _ = re.subn(
                r"(?m)^cpp\s*=\s*'.*'$",
                "cpp = '{}'".format(cxx.replace("\\", "/")),
                content,
                count=1,
            )
            os.environ["CXX"] = cxx
        with open(native_file, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        self.output.info("meson native compilers -> c={} cpp={}".format(c, cxx))

    def _ensure_writable_tmp(self):
        """Redirect TMPDIR/TMP/TEMP to a writable dir (readonly-/tmp hosts).

        HMBS preflight/CI hosts mount /tmp read-only and inject a writable
        per-task TMPDIR (see HMBS_PLATFORM_CAPABILITIES.tmpdir). Reuse the
        injected value when it is usable; otherwise fall back to a `hmbs-tmp`
        directory under the build folder. Only the temp root is redirected;
        no test is skipped or removed.
        """
        import tempfile

        tmp = None
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var)
            if not val or not os.path.isdir(val) or not os.access(val, os.W_OK):
                continue
            try:
                fd, probe = tempfile.mkstemp(dir=val)
            except OSError:
                continue
            os.close(fd)
            os.remove(probe)
            tmp = val
            break
        if tmp is None:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp
        self.output.info("writable tmp -> {}".format(tmp))

    def _emit_hmbs_upstream(self, discovered, executed, passed, failed,
                            skipped, reason, command):
        """Dual-channel HMBS upstream evidence + persist for cache-hit rounds.

        Emits HMBS_UPSTREAM_TEST_RESULT via both print() and
        self.output.info() (HMBS scrapes both channels), then persists the
        same payload to build_folder/hmbs_upstream.json so package() can
        carry it into package/res for test_package re-emission.
        Numbers come from the real `meson test` run in build() (success =
        all discovered tests passed; failure path re-parses meson logs).
        """
        payload = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "meson",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": reason,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            payload, separators=(",", ":"))
        # Dual-channel: stdout print + conan output (cache-hit safe).
        print(line, flush=True)
        self.output.info(line)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, separators=(",", ":"))
                stream.write("\n")
        except Exception as exc:
            self.output.info("hmbs_upstream persist skipped: {}".format(exc))
        return payload

    def _parse_meson_testlog(self):
        """Best-effort parse of meson-logs/testlog.txt for real counts.

        Returns (executed, passed, failed, skipped) or None when the log
        is absent/unparseable. Never raises; caller falls back to the
        audited 32-test accounting.
        """
        log_path = os.path.join(self.build_folder, "meson-logs", "testlog.txt")
        try:
            with open(log_path, encoding="utf-8", errors="replace") as stream:
                content = stream.read()
        except OSError:
            return None
        # Meson testlog format: lines like "1/32 complete_test OK ..."
        import re as _re
        ok = len(_re.findall(r"(?m)^\d+/\d+\s+\S+\s+OK\b", content))
        fail = len(_re.findall(r"(?m)^\d+/\d+\s+\S+\s+FAIL\b", content))
        skip = len(_re.findall(r"(?m)^\d+/\d+\s+\S+\s+(?:SKIP|EXPECTEDFAIL)\b",
                               content))
        total_m = _re.search(r"(?m)^\d+/(\d+)\s+\S+\s+(?:OK|FAIL|SKIP)", content)
        if total_m is None and (ok + fail + skip) == 0:
            return None
        executed = ok + fail + skip
        return executed, ok, fail, skip

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        self._fix_meson_native_compilers()
        if self.settings.os == "OHOS":
            self._inject_ohos_archiver()
        meson = Meson(self)
        meson.configure()
        meson.build()

        # Upstream unit tests (32 binaries, suite 'unit', see test/meson.build).
        # The yaml test is not built because the yaml feature is disabled.
        if not self.conf.get(
            "tools.build:skip_test", default=False, check_type=bool
        ):
            cmd = 'meson test -v --print-errorlogs --no-rebuild -C "{}"'.format(
                self.build_folder
            )
            short_cmd = "meson test -v --print-errorlogs --no-rebuild"
            try:
                self.run(cmd)
            except Exception:
                # Test command failed: still emit truthful evidence, then fail.
                parsed = self._parse_meson_testlog()
                if parsed is not None:
                    executed, ok, fail, skip = parsed
                    failed = max(fail, 1)
                    passed = ok
                    executed = max(executed, passed + failed + skip)
                else:
                    executed, passed, failed, skip = 32, 0, 32, 0
                self._emit_hmbs_upstream(
                    32, executed, passed, failed, skip,
                    "meson test failed on OHOS aarch64; see meson-logs/testlog.txt",
                    short_cmd)
                raise
            parsed = self._parse_meson_testlog()
            if parsed is not None:
                executed, ok, fail, skip = parsed
                # Trust framework output when parseable.
                self._emit_hmbs_upstream(
                    32, executed, ok, fail, skip,
                    "meson testlog.txt parsed; 32 unit tests audited from"
                    " test/meson.build, yaml_test excluded (yaml=disabled)",
                    short_cmd)
            else:
                # self.run succeeded => all 32 discovered tests passed.
                self._emit_hmbs_upstream(
                    32, 32, 32, 0, 0,
                    "meson test passed 32/32 on OHOS aarch64; 32 unit tests"
                    " audited from test/meson.build,"
                    " yaml_test excluded (yaml=disabled, 1 conditional"
                    " not built)",
                    short_cmd)

    def package(self):
        meson = Meson(self)
        meson.install()
        # Carry in-build upstream evidence into the package for cache-hit
        # rounds (build()/package() are skipped then, test_package re-emits).
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir, "hmbs_upstream.json"))
                self.output.info("hmbs_upstream.json carried to package/res")
        except Exception as exc:
            self.output.info("carry hmbs_upstream.json skipped: {}".format(exc))

    def package_info(self):
        self.cpp_info.libs = ["ecoli"]
        self.cpp_info.set_property("cmake_file_name", "libecoli")
        self.cpp_info.set_property("cmake_target_name", "libecoli::libecoli")
        self.cpp_info.set_property("pkg_config_name", "libecoli")
