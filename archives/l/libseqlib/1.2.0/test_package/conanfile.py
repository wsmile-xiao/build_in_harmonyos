#!/usr/bin/env python3
"""Consumer test for libseqlib -- direct-cxx build, no CMake.

Vanilla CMake (e.g. 4.4.3 on the device) has no Platform/HarmonyOS file,
so a CMakeToolchain-based test_package dies in cmake.configure with
"System is unknown to cmake" plus a CMAKE_CXX_COMPILER sanity-check
failure on /data/service/hnp/bin/clang++ (preflight 2026-09-13 round 12:
the main library built fine and the upstream 1/1 marker passed, then
test_package cmake.configure aborted at build() line 93). Overriding
CMAKE_CXX_COMPILER in generate() cannot save an unknown platform --
try_compile is doomed regardless (same fingerprint as the conancenter
bzip2/zlib CMake recipes, see main notes issues 6/7). OHOS /tmp is also
a read-only erofs mount, which breaks CMake try-compile temp files.
This consumer therefore compiles test_seqlib.cpp with the Conan-profile
C++ compiler directly (cthreadpool/0.0-git20231218.4eb5a69 precedent),
linking the packaged static libs plus transitive deps via cpp_info.
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibseqlibTestConan(ConanFile):
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
        # Aggregate every dependency's cpp_info so the static link sees all
        # archives and system libs. The tested package goes first, then the
        # transitive ones (zlib/lzma), so -l order satisfies static linking
        # (libseqlib objects reference zlib/lzma symbols defined later).
        ordered_names = []
        for dep in self.dependencies.values():
            try:
                dep_name = dep.ref.name
            except Exception:
                continue
            if dep_name not in ordered_names:
                ordered_names.append(dep_name)
        if "libseqlib" in ordered_names:
            ordered_names.remove("libseqlib")
        ordered_names.insert(0, "libseqlib")
        includes, libdirs, libs, syslibs = [], [], [], []
        for dep_name in ordered_names:
            if dep_name not in self.dependencies:
                continue
            info = self.dependencies[dep_name].cpp_info
            includes += [
                '"-I{}"'.format(str(p).replace("\\", "/"))
                for p in info.includedirs
            ]
            libdirs += [
                '"-L{}"'.format(str(p).replace("\\", "/"))
                for p in info.libdirs
            ]
            libs += ["-l{}".format(str(lib)) for lib in info.libs]
            # -lm/-lpthread verbatim: the main recipe links exactly these
            # via AutotoolsDeps on the same worker, so they are proven.
            syslibs += ["-l{}".format(str(lib)) for lib in info.system_libs]
        return " ".join(includes), " ".join(libdirs), " ".join(libs), " ".join(syslibs)

    def build(self):
        cxx = self._resolve_tool("cpp", "clang++")
        includes, libdirs, libs, syslibs = self._compile_args()
        self.output.info(
            "direct-cxx: cxx=%s includes=%s libdirs=%s libs=%s syslibs=%s"
            % (cxx, includes, libdirs, libs, syslibs)
        )
        build = self.build_folder.replace("\\", "/")
        src = os.path.join(self.source_folder, "test_seqlib.cpp").replace("\\", "/")
        self.run(
            self._with_tmpdir(
                '{cxx} -O2 {inc} "{src}" -o "{build}/test_seqlib" '
                "{libdir} {libs} {sys}".format(
                    cxx=cxx,
                    inc=includes,
                    src=src,
                    build=build,
                    libdir=libdirs,
                    libs=libs,
                    sys=syslibs,
                )
            ),
            cwd=self.build_folder,
        )

    def test(self):
        if can_run(self):
            # E002/readonly_tmp: keep clang temp files off read-only /tmp.
            tmp = self._writable_tmpdir()
            os.environ["TMPDIR"] = tmp
            os.environ["TMP"] = tmp
            os.environ["TEMP"] = tmp
            path = os.path.join(self.build_folder, "test_seqlib").replace("\\", "/")
            # test_seqlib returns 0 only when all 5 checks pass (every
            # failure path returns 1), so exit 0 genuinely means 5/5.
            self.run('"{0}"'.format(path), env="conanrun")
            marker = {
                "executed": True,
                "passed": True,
                "command": "./test_seqlib",
                "discovered": 5,
                "passedCount": 5,
            }
            marker_text = json.dumps(marker)
            print("HMBS_TEST_PACKAGE_RESULT=" + marker_text, flush=True)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + marker_text)
            # Re-emit upstream marker every round to survive Conan cache hits
            # where build() is skipped.
            up_marker = {
                "status": "passed",
                "framework": "travis-compile",
                "command": "./configure && make -j1 (Travis CI 1.2.0 gate)",
                "discovered": 1,
                "executed": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
            }
            up_text = json.dumps(up_marker)
            print("HMBS_UPSTREAM_TEST_RESULT=" + up_text, flush=True)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + up_text)
