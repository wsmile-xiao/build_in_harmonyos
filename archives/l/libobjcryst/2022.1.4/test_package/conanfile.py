#!/usr/bin/env python3
"""Conan test_package for libobjcryst 2022.1.4 — direct compile, no CMake.

The consumer previously used CMakeToolchain + CMake project(), which fails
on the HMBS/CI worker at configure time:

  System is unknown to cmake, create: Platform/HarmonyOS ...
  CMAKE_CXX_COMPILER: /data/service/hnp/bin/clang++ ...
  -- Configuring incomplete, errors occurred!

CMake 4.x cannot identify the OHOS SDK clang (no Platform/HarmonyOS
module). Three independent recipes hit the same wall (ddate doc: 3 rounds
incl. Linux-mapping still red; critnib; libe57format rounds 1-3), while
direct-compile consumers merged (libe57format 3.3.0). This test_package
therefore compiles test.cpp directly with the Conan-configured OHOS
clang++ (R33: compiler from tools.build:compiler_executables, never from
bare ${CXX}), links the installed ObjCryst package + header-only boost,
and runs ./test_libobjcryst. No CMake project() is executed, so the
"compiler identification is unknown" failure mode cannot occur.

test.cpp itself emits the HMBS_TEST_PACKAGE_RESULT machine marker
(discovered 7); this recipe only ensures the binary really runs and
propagates a non-zero exit.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class LibobjcrystTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _cxx(self):
        # Same rule as the main recipe (R33): compiler from the Conan conf,
        # never from a bare ${CXX} shell variable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        path = compilers.get("cpp")
        if path and os.path.isfile(path):
            return path
        if path:
            return shutil.which(os.path.basename(path)) or path
        return shutil.which("clang++") or "clang++"

    def _pkg_flags(self):
        try:
            pkg = self.dependencies[self.tested_reference_str]
        except Exception:
            raise ConanException("tested reference not in graph; cannot derive flags")
        incs = list(pkg.cpp_info.includedirs)
        libds = list(pkg.cpp_info.libdirs)
        libs = list(pkg.cpp_info.libs)
        syslibs = list(pkg.cpp_info.system_libs)
        # Header-only boost comes transitively via ObjCryst::ObjCryst
        # (package_info requires boost::boost); add its include dirs.
        if "boost" in self.dependencies:
            boost = self.dependencies["boost"]
            try:
                agg = boost.cpp_info.aggregated_components()
                boost_incs = list(agg.includedirs)
            except Exception:
                boost_incs = list(boost.cpp_info.includedirs)
            for d in boost_incs:
                if d not in incs:
                    incs.append(d)
        if not libs:
            raise ConanException("ObjCryst cpp_info.libs empty; cannot link")
        inc_flags = " ".join('"-I{0}"'.format(d) for d in incs)
        lib_flags = " ".join('"-L{0}"'.format(d) for d in libds)
        lib_names = " ".join('"-l{0}"'.format(l) for l in libs)
        sys_flags = " ".join('"-l{0}"'.format(l) for l in syslibs)
        self.output.info("test_package includes: {0}".format(inc_flags))
        self.output.info("test_package libs: {0} {1} {2}".format(
            lib_flags, lib_names, sys_flags))
        return inc_flags, lib_flags, lib_names, sys_flags

    def build(self):
        cxx = self._cxx()
        inc_flags, lib_flags, lib_names, sys_flags = self._pkg_flags()
        opt = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O2 -DNDEBUG"
        flags = "-std=c++14 -stdlib=libc++ -pthread {0}".format(opt)
        src = os.path.join(self.source_folder, "test.cpp")
        if not os.path.isfile(src):
            raise ConanException("test source missing: {0}".format(src))
        out = os.path.join(self.build_folder, "test_libobjcryst")
        self.output.info("test_package compile with cxx={0}".format(cxx))
        self.run('"{0}" {1} {2} "{3}" {4} {5} {6} -o "{7}"'.format(
            cxx, flags, inc_flags, src, lib_flags, lib_names, sys_flags, out))

    def test(self):
        if not can_run(self):
            return
        # R5: OHOS has no /bin/sh — wrap execution with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        exe = os.path.join(self.build_folder, "test_libobjcryst")
        run_prefix = ""
        try:
            is_shared = self.dependencies[self.tested_reference_str].options.shared
        except Exception:
            is_shared = False
        if is_shared:
            try:
                libdirs = self.dependencies[self.tested_reference_str].cpp_info.libdirs
            except Exception:
                libdirs = []
            if libdirs:
                run_prefix = 'LD_LIBRARY_PATH="{0}" '.format(libdirs[0])
        proc = subprocess.run(
            [bash, "-c", '{0}"{1}"'.format(run_prefix, exe)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=600, cwd=self.build_folder)
        self.output.info("=== test_libobjcryst ===\n{0}".format(proc.stdout or ""))
        if proc.returncode != 0:
            raise ConanException(
                "test_libobjcryst failed (rc={0})".format(proc.returncode))
        if "HMBS_TEST_PACKAGE_RESULT=" not in (proc.stdout or ""):
            raise ConanException("test binary did not emit HMBS_TEST_PACKAGE_RESULT")
        # Dual-channel re-emit of the test_package marker: the binary line
        # already went through output.info above; print() ensures it also
        # reaches stdout directly for the HMBS parser on all runners.
        for _line in (proc.stdout or "").splitlines():
            if "HMBS_TEST_PACKAGE_RESULT=" in _line:
                print(_line.strip(), flush=True)
                break
        self._reemit_upstream_marker()

    def _reemit_upstream_marker(self):
        # Cache-hit runs skip build(), so the build-time
        # HMBS_UPSTREAM_TEST_RESULT never prints. Re-emit the real
        # persisted result staged in package res/. Missing file: warn
        # only, never forge.
        try:
            ref = self.tested_reference_str or ""
            pkg_name = ref.split("/")[0].split("@")[0].strip() or "libobjcryst"
            try:
                pkg_folder = self.dependencies[pkg_name].package_folder
            except Exception:
                try:
                    pkg_folder = self.dependencies[self.tested_reference_str].package_folder
                except Exception:
                    pkg_folder = ""
            candidates = []
            if pkg_folder:
                candidates.append(os.path.join(
                    pkg_folder, "res", "hmbs_upstream_test_result.json"))
                candidates.append(os.path.join(
                    pkg_folder, "res", "hmbs_upstream_test_result.txt"))
            marker = None
            raw_line = ""
            for cand in candidates:
                if not cand or not os.path.isfile(cand):
                    continue
                if cand.endswith(".json"):
                    with open(cand, "r", encoding="utf-8") as f:
                        marker = json.load(f)
                    raw_line = ("HMBS_UPSTREAM_TEST_RESULT="
                                + json.dumps(marker, separators=(",", ":")))
                    break
                else:
                    with open(cand, "r", encoding="utf-8") as f:
                        raw_line = f.read().strip()
                    if "HMBS_UPSTREAM_TEST_RESULT=" in raw_line:
                        break
            if marker is None and not raw_line:
                self.output.warning(
                    "Upstream marker persistence not found in package res; "
                    "fresh builds emit it from build().")
                return
            if raw_line.startswith("HMBS_UPSTREAM_TEST_RESULT="):
                line = raw_line.splitlines()[0].strip()
            else:
                line = ("HMBS_UPSTREAM_TEST_RESULT="
                        + json.dumps(marker, separators=(",", ":")))
            print(line, flush=True)
            self.output.info(line)
        except Exception as exc:
            self.output.warning("Could not re-emit upstream marker: %s" % exc)
