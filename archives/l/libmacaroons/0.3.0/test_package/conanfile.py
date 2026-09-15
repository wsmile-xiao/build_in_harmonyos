#!/usr/bin/env python3
"""Conan test_package -- libmacaroons 0.3.0.

Direct-cc consumer (no CMake): compiles test_macaroons.c with the device
compiler from tools.build:compiler_executables and runs it on device.
Avoids CMakeToolchain's CMAKE_SYSTEM_NAME=HarmonyOS mapping -- cmake 4.4.3
has no Platform/HarmonyOS.cmake, so `cmake.configure()` dies at the
compiler check ("System is unknown to cmake" + CMAKE_C_COMPILER error).
Same proven pattern as archives/l/libsodium/1.0.20/test_package.

Emits HMBS_TEST_PACKAGE_RESULT with real PASS-line counts (3 checks).
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibmacaroonsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # HMBS readonly_tmp: device /tmp is read-only erofs. Mirror the
        # main recipe: prefer the hmbs-injected writable TMPDIR/TMP/TEMP
        # so the compiler driver and the test binary inherit it.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("libmacaroons_test_env")

    def _resolve_cc(self):
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            exes = {}
        cc = (exes or {}).get("c")
        if cc:
            parts = shlex.split(cc)
            # Absolute profile path may be stale; verify before use.
            if os.path.isabs(parts[0]):
                try:
                    if os.path.isfile(parts[0]) and os.access(parts[0], os.X_OK):
                        self.output.info("test_package selected cc=%s" % cc)
                        return parts
                except Exception:
                    pass
                self.output.warning(
                    "conf compiler '%s' unusable; falling back to PATH" % cc
                )
            else:
                self.output.info("test_package selected cc=%s" % cc)
                return parts
        for name in ("cc", "clang"):
            found = shutil.which(name)
            if found:
                self.output.info("test_package selected cc=%s" % found)
                return [found]
        raise ConanInvalidConfiguration(
            "no working C compiler for test_package (conf + PATH exhausted)"
        )

    def build(self):
        cc_parts = self._resolve_cc()
        dep = self.dependencies["libmacaroons"]
        # cpp_info include/lib dirs cover both libmacaroons and vendored
        # sodium headers/libs shipped in the same package.
        include_dirs = list(dep.cpp_info.includedirs)
        lib_dirs = list(dep.cpp_info.libdirs)
        source = os.path.join(self.source_folder, "test_macaroons.c")
        executable = os.path.join(self.build_folder, "macaroons_consumer")
        cmd = [
            *(shlex.quote(a) for a in cc_parts),
            "-O2",
            *("-I%s" % shlex.quote(d) for d in include_dirs),
            shlex.quote(source),
            *("-L%s" % shlex.quote(d) for d in lib_dirs),
            "-lmacaroons",
            "-lsodium",
            "-o",
            shlex.quote(executable),
        ]
        self.run(" ".join(cmd), env="conanbuild")

    def _reemit_upstream_result(self):
        # Cache-hit rounds skip build(), so the upstream marker emitted
        # there never appears. Re-emit the exact persisted result produced
        # by build() (4 HMAC vectors, doctest). No re-computation here;
        # missing file only warns, never fakes a pass.
        try:
            dep = self.dependencies["libmacaroons"]
            pkg = dep.package_folder
        except Exception as exc:
            self.output.warning("upstream re-emit unavailable (no dep): %s" % exc)
            return
        cands = [
            os.path.join(pkg, "share", "libmacaroons", "hmbs_upstream_result.json"),
            os.path.join(pkg, "share", "hmbs_upstream_result.json"),
        ]
        path = next((p for p in cands if os.path.isfile(p)), None)
        if not path:
            self.output.warning("upstream result file missing in package; not re-emitting")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            self.output.warning("cannot read upstream result %s: %s" % (path, exc))
            return
        try:
            line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
        except Exception as exc:
            self.output.warning("cannot encode upstream result: %s" % exc)
            return
        self.output.info(line)
        print(line)

    def test(self):
        marker = {
            "executed": True,
            "passed": False,
            "command": "./macaroons_consumer (direct cc, no CMake)",
            "discovered": 3,
            "passedCount": 0,
        }
        if not can_run(self):
            self.output.info("NOT_RUN consumer cross-building; skipping execution")
            self._reemit_upstream_result()
            return
        try:
            os.makedirs(self.build_folder, exist_ok=True)
        except Exception:
            pass
        log_path = os.path.join(self.build_folder, "macaroons_consumer.log")
        executable = os.path.join(self.build_folder, "macaroons_consumer")
        rc_out = None
        try:
            rc_out = self.run(
                '"%s" > "%s" 2>&1' % (executable, log_path),
                env="conanrun",
                stdout=True,
            )
        except ConanException:
            # Non-zero exit: parse the captured log below for counts.
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        out = out or (rc_out or "")
        for line in out.splitlines():
            self.output.info("[consumer] %s" % line[:220])
        passed = sum(1 for line in out.splitlines() if line.startswith("PASS:"))
        marker["passedCount"] = passed
        marker["passed"] = passed == 3
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        self._reemit_upstream_result()
        if not marker["passed"]:
            raise ConanException(
                "test_package failed: %d/3 consumer checks passed" % passed
            )
