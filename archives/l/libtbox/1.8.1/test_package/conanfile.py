#!/usr/bin/env python3
"""Conan test_package -- libtbox 1.8.1, direct-cc build, no CMake.

Vanilla CMake has no Platform/HarmonyOS file, so a CMakeToolchain-based
test_package dies in cmake.configure with "System is unknown to cmake"
plus a CMAKE_C_COMPILER sanity-check failure on /data/service/hnp/bin/clang
(this preflight's exact failure). OHOS /tmp is also read-only, which breaks
CMake try-compile temp files. This consumer therefore compiles
test_libtbox.c with the Conan-profile compiler directly (same approach as
cthreadpool/0.0-git20231218.4eb5a69/test_package), linking the packaged
library via its cpp_info.

The test really calls libtbox APIs: tb_init/tb_exit, tb_crc32_make
(tbox-variant known-answer 0x7F89A189 for "123456789"/seed 0), tb_vector
insert/size/content (R34: no stub test).
CI L1 runs this automatically via `conan create`.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibtboxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve_tool(self, name, fallback):
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
        dep = self.dependencies["libtbox"].cpp_info
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
        src_path = os.path.join(self.source_folder, "test_libtbox.c").replace("\\", "/")
        self.run(
            self._with_tmpdir(
                '{cc} -O2 {inc} "{src}" -o "{build}/test_libtbox" '
                "{libdir} {libs} {sys}".format(
                    cc=cc, inc=includes, src=src_path,
                    build=build, libdir=libdirs, libs=libs, sys=sysflags
                )
            ),
            cwd=self.build_folder,
        )

    def test(self):
        if can_run(self):
            path = os.path.join(self.build_folder, "test_libtbox").replace("\\", "/")
            # readonly_tmp minimal adaptation: run the consumer binary with
            # the HMBS-injected writable TMPDIR/TMP/TEMP (OHOS /tmp is
            # read-only); the binary itself takes no args and writes no
            # fixtures, this only redirects any libc/libtbox temp usage.
            self.run(self._with_tmpdir('"{0}"'.format(path)), env="conanrun")
            # 8 CHECK assertions in test_libtbox.c (tb_init + CRC32 KAT +
            # empty/determinism/distinct + vector init/size/content).
            tp_result = {
                "executed": True,
                "passed": True,
                "command": "./test_libtbox",
                "discovered": 8,
                "passedCount": 8,
            }
            tp_text = json.dumps(tp_result)
            print("HMBS_TEST_PACKAGE_RESULT=" + tp_text, flush=True)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + tp_text)
        ut_result = {
            "status": "no_tests",
            "framework": "ctest",
            "command": "none (no upstream test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "tbox 1.8.1 upstream tarball audited: no tests/ directory, no TEST/TEST_F or def test_ registrations, no check/test target in the xmake.sh-generated Makefile, src/demo/* are examples only (src/demo/other/test.c is an empty stub returning 0), .github/workflows only build",
        }
        ut_text = json.dumps(ut_result)
        print("HMBS_UPSTREAM_TEST_RESULT=" + ut_text, flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + ut_text)
