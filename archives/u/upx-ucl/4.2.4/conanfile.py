#!/usr/bin/env python3
"""Conan recipe: upx-ucl/4.2.4 (UPX - the Ultimate Packer for eXecutables)

OHOS adaptation notes (see notes.md for full rationale):
- Pure CMake build, CMake >= 3.8, C++17. Zero external dependencies: ucl,
  zlib, lzma-sdk, doctest, valgrind headers are all vendored under
  vendor/ -> no requires at all.
- OHOS libc++ linking: the bundled clang defaults break C++ executables.
  CXXFLAGS "-stdlib=libc++" + LDFLAGS "-lc++ -lpthread" — same
  cache_variables pattern as ada/4.0.0, same knowledge as the archived
  upx/5.1.1 entry (knowledge_gained: cmake_with_libcxx).
- The source tarball has no .git dir, so UPX_VERSION_GITREV is disabled
  automatically (CMakeLists checks IS_DIRECTORY .git); nothing to do.
- Upstream tests are a first-class ctest suite (see misc/cmake/6_test):
  4.2.4 registers 44 cases (9 CLI smoke, 8 self-pack, list/fileinfo/-t,
  8 unpack, 7 byte-compare, 1 run-unpacked, 8 run-packed). The recipe
  disables the run-packed group (UPX_CONFIG_DISABLE_RUN_PACKED_TEST):
  MateBook evidence (2026-09-30) shows HM-MAC (use_task) intercepts the
  packed binary's execve (upx self-unpacking via /proc/self/exe
  remapping) while the unpacked binary execs fine in the same directory
  with no noexec mounts -- a platform boundary, documented in notes.md.
  The remaining 36 cases are deterministic and run hard-fail in build().
  The "exhaustive" matrix (4 methods x 7 levels ~= 170 extra self-packs)
  is disabled for CI runtime.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import export_conandata_patches, get


class UpxUclConan(ConanFile):
    name = "upx-ucl"
    version = "4.2.4"
    description = "UPX - the Ultimate Packer for eXecutables (UCL/NRV/LZMA)"
    homepage = "https://upx.github.io"
    license = "GPL-2.0-or-later"
    url = "https://github.com/upx/upx"
    topics = ("packer", "compression", "executable", "cli")

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"
    # Delivered product is the single executable bin/upx; no headers/libs.
    # R38 commands.json required (CLI tool artifact).

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS libc++: C++ executable needs explicit libc++ linking
        # (upx/5.1.1 knowledge_gained cmake_with_libcxx; ada/4.0.0 precedent).
        # R32: platform guard uses tuple form; on a gcc-based Linux host
        # these clang flags are a latent-compat concern only, OHOS is the
        # delivery target.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_CXX_FLAGS"] = "-stdlib=libc++"
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-lc++ -lpthread"
        # Disable the run-packed group: MateBook 2026-09-30 decisive
        # experiment -- packed upx execve is denied by HM-MAC (use_task)
        # in build tree / user tmp (755) / /data/local/tmp alike, while
        # the unpacked binary execs rc=0 in the same directory; all
        # relevant mounts lack noexec. Root cause is the UPX runtime's
        # /proc/self/exe remapping being intercepted at execve, ahead of
        # any upx code. Platform boundary, not a recipe defect; see
        # notes.md for the full evidence chain.
        tc.cache_variables["UPX_CONFIG_DISABLE_RUN_PACKED_TEST"] = True
        # Trim the test matrix: default exhaustive suite re-self-packs the
        # binary 28x (4 methods x 7 levels, each ~1-2 MB x --all-filters),
        # which is hostile to CI time budgets. The basic suite (44 cases
        # upstream; 36 after the run-packed disable) still covers all 4
        # methods (nrv2b/nrv2d/nrv2e/lzma) and the filter variants; see
        # notes.md.
        tc.cache_variables["UPX_CONFIG_DISABLE_EXHAUSTIVE_TESTS"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Native (non-cross) builds register the upstream ctest suite:
        # 9 CLI smoke + 8 self-pack + list/fileinfo/-t + 8 unpack +
        # 7 compare + 1 run-unpacked = 36 cases after the run-packed
        # disable in generate() (upstream total is 44 incl. 8 run-packed).
        # All remaining cases are deterministic on the OHOS build host
        # (MateBook 2026-09-30: 36/36 excluding run-packed), so the
        # suite runs hard-fail -- a real regression must block packaging.
        if self.conf.get("tools.build:skip_test", default=False):
            self.output.info("tools.build:skip_test -> skip ctest")
            return
        self.run(
            'ctest --test-dir "{}" --output-on-failure --no-tests=error --timeout 300'.format(
                self.build_folder
            )
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: delivered product is bin/upx only.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
