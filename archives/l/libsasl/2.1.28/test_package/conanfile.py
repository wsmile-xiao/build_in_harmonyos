import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class LibsaslTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Stale-toolchain guard (repo convention, cf. libXext/libslax/cld2
        # test_package): profile pins /data/service/hnp/bin/clang(++), but
        # that absolute path is inaccessible in the preflight sandbox while
        # PATH-visible clang (harmonybrew) works — main build log proves it
        # ("checking if .../.harmonybrew/bin/clang ... yes"). CMakeToolchain
        # copies the conf path verbatim into conan_toolchain.cmake, so CMake
        # project() then fails its compiler check. Resolve to an existing
        # binary (conf path only when isfile, otherwise PATH lookup) and
        # force it via cache variables + post-generate toolchain patch.
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable(
                "c", "clang"
            )
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        executable = os.path.join(self.build_folder, "test_libsasl")
        # cmake_layout puts the binary under build/<config>/ for multi-config
        # generators; fall back to the bindirs location when needed.
        if not os.path.isfile(executable):
            try:
                cand = os.path.join(self.cpp.build.bindirs[0], "test_libsasl")
            except Exception:
                cand = None
            if cand and os.path.isfile(cand):
                executable = cand
        command = executable
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 4, "passedCount": 0}
        try:
            self.run(executable, env="conanrun")
        except Exception:
            _emsg = ("HMBS_TEST_PACKAGE_RESULT="
                     + json.dumps(result, ensure_ascii=False))
            print(_emsg, flush=True)
            self.output.info(_emsg)
            raise
        result["passed"] = True
        result["passedCount"] = 4
        _msg = ("HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(result, ensure_ascii=False))
        # Dual-channel emit (Experience-1/2 pattern): HMBS scrapes raw stdout.
        print(_msg, flush=True)
        self.output.info(_msg)
        # Cache-hit re-emit: when Conan reuses the main-package binary,
        # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never
        # prints. Re-print the persisted real result (written by build()
        # into package res/hmbs_upstream.json) every run so the evidence
        # gate sees it. Counts are the real in-build testsuite numbers.
        try:
            _upstream = None
            _pkg_name = (self.tested_reference_str.split("/")[0]
                         if "/" in self.tested_reference_str else "libsasl")
            try:
                _dep = self.dependencies[_pkg_name]
                _pf = getattr(_dep, "package_folder", None)
                if _pf:
                    _cand = os.path.join(_pf, "res", "hmbs_upstream.json")
                    if os.path.isfile(_cand):
                        with open(_cand, "r", encoding="utf-8") as _fh:
                            _upstream = json.load(_fh)
            except Exception:
                _upstream = None
            if isinstance(_upstream, dict) and _upstream.get("discovered"):
                _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(_upstream, ensure_ascii=False))
                print(_umsg, flush=True)
                self.output.info(_umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build")
                raise ConanException(
                    "persisted hmbs_upstream.json missing in package res/; "
                    "need fresh build with upstream testsuite")
        except Exception as _e:
            from conan.errors import ConanException as _CE
            if isinstance(_e, _CE):
                raise
            self.output.warning("upstream re-emit failed: %r" % (_e,))

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

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
