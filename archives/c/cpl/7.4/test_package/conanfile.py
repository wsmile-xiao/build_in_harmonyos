import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain


class CplTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Direct header providers: cpl public headers include cxmacros.h
        # (libcext), fitsio.h (cfitsio) and wcslib headers. CMakeDeps on this
        # toolchain leaves transitive INCLUDE_DIRS empty, so the consumer must
        # depend on them directly to get include dirs (no version leak beyond
        # the versions the recipe itself pins).
        self.requires("libcext/1.3.2")
        self.requires("cfitsio/4.6.4")
        self.requires("wcslib/8.4")
        self.requires("zlib/1.3.1.1")

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # The shared profile may point tools.build:compiler_executables at a
        # path that does not exist on every worker. When the configured
        # compiler is absent, override it with a real OHOS clang resolved from
        # PATH so CMake can configure (same as libcext/1.3.2).
        if str(self.settings.os) == "OHOS":
            cc = self._compiler_executable("c", "clang")
            cxx = self._compiler_executable("cpp", "clang++")
            tc.variables["CMAKE_C_COMPILER"] = cc
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: binaries packaged, skipping runtime test")
            self._emit_upstream_marker()
            return
        # No layout() is declared, so self.cpp.build.bindirs is empty and
        # indexing it raises IndexError (true-machine evidence). The binary
        # lands directly in build_folder for single-config CMake, so run it
        # by relative path like the sibling libcext/1.3.2 recipe does.
        self.run("./test_cpl", env="conanrun")
        # Re-emit upstream evidence every run: build() is skipped on cache
        # hits, so without this the preflight sees 0 upstream tests.
        self._emit_upstream_marker()

    def _emit_upstream_marker(self):
        marker = None
        try:
            package_folder = self.dependencies["cpl"].package_folder
            for cand in (
                os.path.join(package_folder, "res", "hmbs_upstream.json"),
                os.path.join(package_folder, "hmbs_upstream.json"),
            ):
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as f:
                        marker = json.load(f)
                    break
        except Exception as exc:
            self.output.warning(f"cpl diag read upstream marker failed: {exc}")
            marker = None
        if not isinstance(marker, dict) or not marker.get("discovered"):
            # No fake pass: without the persisted build-time marker there is
            # no real make-check count to report, so only warn. After this
            # fix every fresh build persists the file, and the recipe-revision
            # bump forces a rebuild, so cache hits will find it.
            self.output.warning("cpl diag hmbs_upstream.json missing, skip upstream re-emit")
            return
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)
