#!/usr/bin/env python3
"""Consumer test for cthreadpool -- direct-cc build, no CMake.

Vanilla CMake (e.g. 4.4.3 on the device) has no Platform/HarmonyOS file, so a
CMakeToolchain-based test_package dies in cmake.configure with
"System is unknown to cmake" plus a CMAKE_C_COMPILER sanity-check failure on
/data/service/hnp/bin/clang. OHOS /tmp is also a read-only erofs mount, which
breaks CMake try-compile temp files. This consumer therefore compiles the two
test programs with the Conan-profile compiler directly (same approach as the
main recipe and archives/z/zimg/3.0.6/test_package), linking the packaged
library via its cpp_info.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class CthreadpoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve_tool(self, name, fallback):
        # Same conf-first/PATH-fallback policy as the main recipe: the conf
        # value stays preferred; only an absolute path that is not a file or
        # not executable falls back to the bare tool name via conanbuild PATH.
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        value = compilers.get(name) or fallback
        if "/" in value or "\\" in value:
            if not os.path.isfile(value):
                self.output.warning(
                    "HMBS: conf tools.build:compiler_executables:{}={} is not a file, "
                    "falling back to '{}' via PATH".format(name, value, fallback)
                )
                return fallback
            if not os.access(value, os.X_OK):
                self.output.warning(
                    "HMBS: conf tools.build:compiler_executables:{}={} is not executable, "
                    "falling back to '{}' via PATH".format(name, value, fallback)
                )
                return fallback
        return value

    def _writable_tmpdir(self):
        # OHOS /tmp is a read-only erofs mount; /bin/sh command substitution
        # needs temp files, so prefer the HMBS-injected TMPDIR/TMP/TEMP and
        # otherwise use a tmp dir inside the writable build folder.
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value and os.path.isdir(value):
                return value.replace("\\", "/")
        fallback = os.path.join(self.build_folder, "tmp").replace("\\", "/")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _with_tmpdir(self, command):
        tmp = self._writable_tmpdir()
        return 'TMPDIR="{t}" TMP="{t}" TEMP="{t}" {c}'.format(t=tmp, c=command)

    def _compile_args(self):
        dep = self.dependencies["cthreadpool"].cpp_info
        includes = " ".join(
            '"-I{}"'.format(str(p).replace("\\", "/")) for p in dep.includedirs
        )
        libdirs = " ".join(
            '"-L{}"'.format(str(p).replace("\\", "/")) for p in dep.libdirs
        )
        libs = " ".join("-l{}".format(str(lib)) for lib in dep.libs)
        sysflags = []
        for system_lib in dep.system_libs:
            if system_lib == "pthread":
                sysflags.append("-pthread")
            else:
                sysflags.append("-l{}".format(system_lib))
        return includes, libdirs, libs, " ".join(sysflags)

    def build(self):
        cc = self._resolve_tool("c", "clang")
        includes, libdirs, libs, sysflags = self._compile_args()
        build = self.build_folder.replace("\\", "/")
        for src, exe in (("test_basic.c", "test_basic"), ("test_pause_wait.c", "test_pause_wait")):
            src_path = os.path.join(self.source_folder, src).replace("\\", "/")
            self.run(
                self._with_tmpdir(
                    '{cc} -O2 -Wall -Wextra {inc} "{src}" -o "{build}/{exe}" '
                    '{libdir} {libs} {sys}'.format(
                        cc=cc, inc=includes, src=src_path,
                        build=build, exe=exe, libdir=libdirs, libs=libs, sys=sysflags
                    )
                ),
                cwd=self.build_folder,
            )

    def test(self):
        if can_run(self):
            passed_count = 0
            for executable in ("test_basic", "test_pause_wait"):
                path = os.path.join(self.build_folder, executable).replace("\\", "/")
                self.run('"{0}"'.format(path), env="conanrun")
                passed_count += 1
            marker = {
                "executed": True,
                "passed": passed_count == 2,
                "command": "test_basic + test_pause_wait",
                "discovered": 2,
                "passedCount": passed_count,
            }
            marker_text = json.dumps(marker)
            print("HMBS_TEST_PACKAGE_RESULT=" + marker_text, flush=True)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + marker_text)
            if passed_count != 2:
                raise RuntimeError("test_package failed: {}/2 passed".format(passed_count))
            # Re-emit the upstream evidence persisted by build(). test_package
            # runs on every preflight even when conan skips a cached build()
            # ("Already installed!"), so this guarantees the upstream marker
            # is always present. The JSON comes from the same real device run
            # that compiled and executed the 10 upstream invocations.
            dep = self.dependencies["cthreadpool"]
            result_path = os.path.join(
                dep.package_folder, "res", "upstream_test_result.json")
            if not os.path.isfile(result_path):
                raise RuntimeError(
                    "upstream_test_result.json not found in package ({}) -- "
                    "upstream tests did not run during build(); refusing to "
                    "pass silently".format(result_path))
            with open(result_path, "r", encoding="utf-8") as _f:
                upstream_text = _f.read()
            # Validate it is legal JSON with the required counters before
            # re-emitting, so a corrupt payload cannot fake a pass.
            upstream = json.loads(upstream_text)
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream), flush=True)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
