#!/usr/bin/env python3
"""Conan recipe — vibes 0.3.4 (custom: single-unit C++ client API library).

VIBES (VIsualizer for Intervals and BoxES) is an open-source scientific
visualization system pairing a viewer application with a small client API
exposed to several languages. This recipe packages the **C++ client API**
(`client-api/C++`): a single translation unit `vibes.cpp` (with its header
`vibes.h`) that downstream consumers link against to send JSON drawing
commands to the VIBES viewer. The viewer itself is a Qt5/Qt6 GUI desktop
application that cannot run headless on HarmonyOS; only the dependency-free
C++ client library is shipped here.

OHOS notes:
  - Pure C++11, zero external dependencies (STL + stdio only); no patches.
  - Upstream ships no build system for the client API (no Makefile / CMake
    lists at `client-api/C++`; only `examples/` demos), so build() compiles
    `vibes.cpp` directly into ``libvibes``.
  - All drawing/connection functions write JSON to a file (the viewer is a
    separate process that watches it), so the library is fully testable
    headless via `beginDrawing(file)` + drawing commands.
  - Upstream client API has no automated test suite (only `examples/`
    demo programs, no assertions); see test_package/MANIFEST.yml audit.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.env import Environment


class VibesConan(ConanFile):
    name = "vibes"
    version = "0.3.4"
    description = (
        "VIBES C++ client API - Visualizer for Intervals and BoxES, "
        "JSON drawing commands to the VIBES viewer"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/ENSTABretagneRobotics/VIBES"
    url = "https://github.com/ENSTABretagneRobotics/VIBES"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
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
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vibes is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = os.path.join("build", "generators")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        # [readonly_tmp]: /tmp is read-only on the device. Prefer the
        # HMBS-injected task-private TMPDIR/TMP/TEMP after a real
        # creatability probe (isdir alone is not proof); fall back to a
        # dir under build_folder so clang temp files never touch /tmp.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                try:
                    probe = os.path.join(candidate, ".hmbs_write_probe")
                    with open(probe, "w") as handle:
                        handle.write("ok")
                    os.remove(probe)
                    return candidate
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _resolve_tool_compiler(self, kind):
        # R33: never rely on bare, undefined shell env vars. Prefer the
        # profile-pinned tools.build:compiler_executables path; if it does
        # not exist on a given runner, fall back to PATH discovery (hmbs
        # prepends its tool dirs to PATH).
        try:
            configured = self.conf.get(
                "tools.build:compiler_executables:%s" % kind, check_type=str)
        except Exception:
            configured = None
        if configured:
            if os.path.exists(configured):
                return configured
            base = os.path.basename(configured)
            for cand in ([base]
                         + (["clang", "cc"] if kind == "c"
                            else ["clang++", "c++"])):
                found = shutil.which(cand)
                if found:
                    self.output.warning(
                        "configured %s compiler missing: %s; "
                        "falling back to PATH: %s" % (kind, configured, found))
                    return found
            return base
        default = "clang" if kind == "c" else "clang++"
        return shutil.which(default) or default

    def _resolve_archiver(self):
        candidates = []
        try:
            adef = self.conf.get(
                "tools.build:compiler_executables:ar", default=None,
                check_type=str)
        except Exception:
            adef = None
        if adef:
            candidates.append(adef)
        for name in ("llvm-ar", "ar"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)
        for cand in candidates:
            if not cand:
                continue
            if os.path.basename(cand) == cand:
                if shutil.which(cand):
                    return cand
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return "llvm-ar"

    def _cxx_flags(self, cxx):
        flags = []
        # Empty-string guard so we never pass stray empty args.
        flags.append("-std=c++11")
        flags.append("-O2")
        if self.settings.build_type == "Debug":
            flags = ["-std=c++11", "-g"]
        if getattr(self.options, "shared", False) or self.options.fPIC:
            flags.append("-fPIC")
        return flags

    def generate(self):
        tmpdir = self._writable_tmpdir()
        env = Environment()
        for key in ("TMPDIR", "TMP", "TEMP"):
            env.define(key, tmpdir)
        cxx = self._resolve_tool_compiler("cpp")
        cc = self._resolve_tool_compiler("c")
        env.define("CXX", cxx)
        env.define("CC", cc)
        ar = self._resolve_archiver()
        env.define("AR", ar)
        env.vars(self).save_script("hmbs_tmp")

    def build(self):
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        cxx = self._resolve_tool_compiler("cpp")
        src_dir = os.path.join(self.source_folder,
                               "client-api", "C++", "src")
        cpp = os.path.join(src_dir, "vibes.cpp")
        if not os.path.isfile(cpp):
            raise RuntimeError("vibes.cpp not found under %s" % src_dir)
        flags = self._cxx_flags(cxx)
        obj = os.path.join(self.build_folder, "vibes.o")
        compile_cmd = [cxx] + flags + ["-c", cpp, "-o", obj]
        self.output.info("compile: " + " ".join(compile_cmd))
        self.run(" ".join(compile_cmd))
        libdir = os.path.join(self.build_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        if getattr(self.options, "shared", False):
            lib = os.path.join(libdir, "libvibes.so")
            link_cmd = [cxx, "-shared", obj, "-o", lib]
            self.output.info("link: " + " ".join(link_cmd))
            self.run(" ".join(link_cmd))
        else:
            lib = os.path.join(libdir, "libvibes.a")
            ar = self._resolve_archiver()
            # `ar rcs` includes the symbol index (the `s` modifier), so no
            # separate ranlib pass is required.
            ar_cmd = [ar, "rcs", lib, obj]
            self.output.info("archive: " + " ".join(ar_cmd))
            self.run(" ".join(ar_cmd))
        self._summary_marker()

    def _summary_marker(self):
        # Upstream client API ships no automated test suite (audited in
        # test_package/MANIFEST.yml). Emit an honest no_tests marker for the
        # hmbs gate and persist it for cache-hit rounds, mirroring the
        # upstream evidence pattern used across recipes.
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "no upstream test target (see test_package/MANIFEST.yml audit)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "VIBES C++ client API 0.3.4 ships no automated test suite: "
                "client-api/C++ has no test framework or build-system "
                "wiring (no TEST/ctest/make check); only examples/ demo "
                "programs with no assertions. The Qt viewer's tests/ "
                "folder holds a JSON fixture, not an executable test "
                "runner, and the viewer itself is a GUI app not built for "
                "OHOS. See test_package/MANIFEST.yml upstream_test_audit"
            ),
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        print(line, flush=True)
        try:
            summary_path = os.path.join(
                self.build_folder, "upstream_test_summary.json")
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(marker, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise RuntimeError(
                "failed to write upstream test summary: %s" % e)

    def package(self):
        src_inc = os.path.join(self.source_folder, "client-api", "C++", "src")
        copy(self, "vibes.h",
             src=src_inc,
             dst=os.path.join(self.package_folder, "include"))
        if getattr(self.options, "shared", False):
            libn = "libvibes.so"
        else:
            libn = "libvibes.a"
        copy(self, libn,
             src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # LGPL-3.0: VIBES is dual COPYING (GPL-3.0) + COPYING.LESSER (LGPL-3.0),
        # libraries are under the LGPL; ship both license texts.
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING.LESSER", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Upstream test evidence for cache-hit rounds (see _summary_marker).
        summary_src = os.path.join(self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_summary.json", src=self.build_folder,
                 dst=res_dir, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["vibes"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "vibes")
        self.cpp_info.set_property("cmake_target_name", "vibes::vibes")
