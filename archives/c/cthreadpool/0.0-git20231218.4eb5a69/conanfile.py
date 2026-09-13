#!/usr/bin/env python3
"""Conan recipe -- cthreadpool 0.0-git20231218.4eb5a69 (custom direct-cc build)."""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CthreadpoolConan(ConanFile):
    name = "cthreadpool"
    version = "0.0-git20231218.4eb5a69"
    description = "A minimal but powerful thread pool in ANSI C"
    license = "MIT"
    homepage = "https://github.com/Pithikos/C-Thread-Pool"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cthreadpool supports Linux and OHOS, not {}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, name, fallback):
        # HMBS: conf dict lookup never raises when the key is absent (unlike
        # the ":c"/":ar" suffixed single-key form which throws ConanException).
        # conf value stays preferred; only an absolute path that is not a file
        # or not executable falls back to the bare tool name via conanbuild PATH.
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
        # E002: OHOS /tmp is a read-only erofs mount; the shell itself needs
        # temp files for $(...) command substitution, and cc may need a temp
        # dir as well. Prefer the HMBS-injected TMPDIR/TMP/TEMP when present,
        # otherwise fall back to a tmp dir inside the writable build folder.
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

    def build(self):
        # R33: compiler and archiver come from the Conan configuration,
        # never from bare shell environment variables.
        cc = self._resolve_tool("c", "clang")
        ar = self._resolve_tool("ar", "llvm-ar")
        cflags = "-O2 -fPIC -Wall -pthread"
        if str(self.settings.build_type) == "Debug":
            cflags = "-O0 -g -fPIC -Wall -pthread"
        source = self.source_folder.replace("\\", "/")
        self.run(
            self._with_tmpdir(
                '{cc} {flags} -c "{src}/thpool.c" -o thpool.o'.format(
                    cc=cc, flags=cflags, src=source
                )
            ),
            cwd=self.build_folder,
        )
        self.run(
            self._with_tmpdir("{ar} rcs libthpool.a thpool.o".format(ar=ar)),
            cwd=self.build_folder,
        )
        self.run(
            self._with_tmpdir(
                '{cc} -O2 -fPIC -shared thpool.o -o libthpool.so -pthread'.format(cc=cc)
            ),
            cwd=self.build_folder,
        )
        try:
            self._upstream_executed = 0
            self._run_upstream_tests(cc)
        except Exception as exc:
            done = getattr(self, "_upstream_executed", 0)
            failed = {
                "status": "failed",
                "framework": "shell",
                "command": "source-tree compile-and-run: example_check, api_check, "
                           "conc_check x3, wait_check x2, pause_resume_check, "
                           "no_work_check, nonzero_check (10 invocations)",
                "discovered": 10,
                "executed": done,
                "passed": done,
                "failed": 10 - done,
                "skipped": 0,
                "reason": str(exc)[:300],
            }
            failed_text = json.dumps(failed)
            print("HMBS_UPSTREAM_TEST_RESULT=" + failed_text, flush=True)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + failed_text)
            raise
        upstream = {
            "status": "passed",
            "framework": "shell",
            "command": "source-tree compile-and-run: example_check, api_check, "
                       "conc_check x3, wait_check x2, pause_resume_check, "
                       "no_work_check, nonzero_check (10 invocations)",
            "discovered": 10,
            "executed": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
        }
        upstream_text = json.dumps(upstream)
        # Persist for cache-hit preflights: `conan create` skips build()
        # entirely when the binary is cached ("Already installed!"), so the
        # marker printed here would disappear. package() ships this JSON and
        # test_package re-emits it on every run.
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_path, "w", encoding="utf-8") as _f:
            _f.write(upstream_text)
        print("HMBS_UPSTREAM_TEST_RESULT=" + upstream_text, flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + upstream_text)

    def package(self):
        copy(self, "thpool.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libthpool.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libthpool.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Ship the upstream result so test_package can re-emit
        # HMBS_UPSTREAM_TEST_RESULT on cache-hit preflights where build()
        # is skipped ("Already installed!").
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_path):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_result.json",
                 src=self.build_folder, dst=res_dir, keep_path=False)
        else:
            self.output.warning("upstream_test_result.json not found in build "
                                "folder; package will lack upstream evidence")

    def package_info(self):
        self.cpp_info.libs = ["thpool"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "cthreadpool")
        self.cpp_info.set_property("cmake_target_name", "cthreadpool::cthreadpool")

    def _run_upstream_tests(self, cc):
        """Compile and run the portable subset of the upstream tests/ suite.

        Upstream drivers are plain shell scripts (tests/*.sh) without a test
        runner, so each test program is built exactly like upstream funcs.sh
        does (cc + thpool.c + -D THPOOL_DEBUG + -pthread) and executed
        directly. The valgrind-based memleaks.sh cases are excluded: valgrind
        is not available on OHOS (see notes.md for the case-by-case audit).

        OHOS /tmp is a read-only erofs mount (E002). The stock upstream
        driver idiom with shell command substitution needs temp files under
        /tmp and fails on device even when the binary is correct. The
        mass-addition checks therefore redirect to a file inside the writable
        build folder and assert with grep -qx -- same exact-sum semantics,
        no /tmp temp file, still one invocation per upstream case.
        """
        source = self.source_folder.replace("\\", "/")
        build = self.build_folder.replace("\\", "/")
        compile_cmd = '{cc} -O2 -I"{src}" -DTHPOOL_DEBUG -pthread'.format(cc=cc, src=source)
        self._check(
            '{compile} "{src}/example.c" "{src}/thpool.c" -o "{build}/example_check"'.format(
                compile=compile_cmd, src=source, build=build
            ),
            '"{build}/example_check"'.format(build=build),
        )
        self._check(
            '{compile} "{src}/tests/src/api.c" "{src}/thpool.c" -o "{build}/api_check"'.format(
                compile=compile_cmd, src=source, build=build
            ),
            '"{build}/api_check"'.format(build=build),
        )
        self._check(
            '{compile} "{src}/tests/src/conc_increment.c" "{src}/thpool.c" -o "{build}/conc_check"'.format(
                compile=compile_cmd, src=source, build=build
            ),
            '"{build}/conc_check" 100 4 > "{build}/conc_100_4.out" && grep -qx "100" "{build}/conc_100_4.out"'.format(build=build),
            '"{build}/conc_check" 100 1000 > "{build}/conc_100_1000.out" && grep -qx "100" "{build}/conc_100_1000.out"'.format(build=build),
            '"{build}/conc_check" 100000 1000 > "{build}/conc_100000_1000.out" && grep -qx "100000" "{build}/conc_100000_1000.out"'.format(build=build),
        )
        self._check(
            '{compile} "{src}/tests/src/wait.c" "{src}/thpool.c" -o "{build}/wait_check"'.format(
                compile=compile_cmd, src=source, build=build
            ),
            '"{build}/wait_check" 4 1 0'.format(build=build),
            '"{build}/wait_check" 2 4 1'.format(build=build),
        )
        self._check(
            '{compile} "{src}/tests/src/pause_resume.c" "{src}/thpool.c" -o "{build}/pause_resume_check"'.format(
                compile=compile_cmd, src=source, build=build
            ),
            '"{build}/pause_resume_check" 4'.format(build=build),
        )
        self._check(
            '{compile} "{src}/tests/src/no_work.c" "{src}/thpool.c" -o "{build}/no_work_check"'.format(
                compile=compile_cmd, src=source, build=build
            ),
            '"{build}/no_work_check" 4'.format(build=build),
        )
        self._check(
            '{compile} "{src}/tests/src/nonzero_heap_stack.c" "{src}/thpool.c" -o "{build}/nonzero_check"'.format(
                compile=compile_cmd, src=source, build=build
            ),
            '"{build}/nonzero_check"'.format(build=build),
        )

    def _check(self, compile_command, *run_commands):
        self.run(self._with_tmpdir(compile_command), cwd=self.build_folder)
        for command in run_commands:
            self.run(self._with_tmpdir(command), cwd=self.build_folder)
            self._upstream_executed += 1
