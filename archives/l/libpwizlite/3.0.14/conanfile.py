#!/usr/bin/env python3
"""Conan recipe — libpwizlite 3.0.14 (PAPPSO proteoWizard lite).

libpwizlite is Filippo Rusconi's trimmed-down reissue of the proteoWizard
msdata library: mzML / mzXML / MGF / MSn mass-spectrometry data reading
for the PAPPSO suite (forgemia.inra.fr/pappso/libpwizlite, upstream tag
upstream/3.0.14). It is dependency #3 of the libpappsomspp 0.11.26 chain
(liblzf → libodsstream → libpwizlite → libpappsomspp).

Upstream build facts:
  - CMake (C++17), no Qt.
  - Dependencies: Boost (iostreams/thread/filesystem/chrono, >= 1.88 per
    unix-toolchain.cmake; the registry boost/1.91.0 satisfies it) and
    zlib. A small set of boost headers is vendored under src/boost/.
  - Builds pwizlite-static (STATIC) and pwizlite-shared (SHARED).
    The static target is packaged (shared disabled by option default —
    the registry zlib/1.3.1 static archive is non-PIC and cannot be
    linked into a shared lib on aarch64, same as libodsstream).
  - Upstream has NO test directory and no add_test registration
    (only -DWITHOUT_MZ5/-DWITHOUT_MZMLB build defines and a CPack
    source-package "tests/" ignore entry): N=0 declared in the PR
    statistics table, consumer-side mzML parsing test backs it (R34).

OHOS adaptations:
  - patch 0001: platform branch — CMAKE_SYSTEM_NAME=HarmonyOS leaves the
    UNIX variable undefined (no Platform/HarmonyOS.cmake in CMake 4.1),
    so upstream's elseif(UNIX AND NOT APPLE) skips unix-toolchain.cmake
    (ZLIB/Boost find_package) — same fix as libodsstream 0.9.18.
  - patch 0002: ZLIB::ZLIB / Boost target aliasing for the conan CMakeDeps
    naming, if module-mode find fails on OHOS.
  - R33: compiler/toolchain from Conan CMakeToolchain only.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibpwizliteConan(ConanFile):
    name = "libpwizlite"
    version = "3.0.14"
    description = "PAPPSO lite edition of proteoWizard msdata — mzML/mzXML/MGF/MSn mass spectrometry data reading"
    license = "Apache-2.0"
    homepage = "https://forgemia.inra.fr/pappso/libpwizlite"
    url = "https://forgemia.inra.fr/pappso/libpwizlite"

    package_type = "library"
    topics = ("mass-spectrometry", "proteomics", "mzml", "mzxml", "pappso", "pwiz")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*", "vendor-boost-libs/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # upstream unix-toolchain.cmake requires Boost >= 1.88
        # (iostreams thread filesystem chrono); registry has 1.91.0.
        # boost/1.91.0 registry binary drops several header-only modules
        # (logic/math/multi_index/numeric/ublas/spirit/interprocess/locale)
        # that pwiz headers need, and boost/1.90.0 ships no compiled
        # iostreams/filesystem archives; boost/1.84.0 has the full header
        # set AND libboost_iostreams/filesystem static archives.
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        get(self, **src, strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream links the canonical ZLIB::ZLIB / Boost:: targets
        # (module-mode names); map the conan CMakeDeps targets accordingly.
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.generate()
        tc = CMakeToolchain(self)
        # upstream hardcodes CMAKE_INSTALL_PREFIX /usr — restore conan's.
        tc.variables["CMAKE_INSTALL_PREFIX"] = self.package_folder
        # Honour BUILD_SHARED_LIBS for the static default (patch 0003).
        tc.variables["MAKE_TEST"] = "OFF"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME"] = "1"
        tc.generate()

    def _build_vendored_boost_libs(self, runtime_env):
        """Build boost thread/chrono compiled sources (vendored from
        boostorg/thread + boostorg/chrono tag boost-1.84.0) — the registry
        boost packages ship no libboost_thread/chrono archives but pwiz's
        SpectrumWorkerThreads needs those symbols."""
        vsrc = None
        for cand in (
            os.path.join(self.source_folder, "vendor-boost-libs"),
            os.path.join(self.build_folder, "vendor-boost-libs"),
        ):
            if os.path.isfile(os.path.join(cand, "CMakeLists.txt")):
                vsrc = cand
                break
        if vsrc is None:
            raise ConanException("vendor-boost-libs not found")
        bdir = os.path.join(self.build_folder, "vendor-boost-libs-build")
        os.makedirs(bdir, exist_ok=True)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        with runtime_env.vars(self).apply():
            self.run(
                " ".join([
                    "cmake", f'-S "{vsrc}"', f'-B "{bdir}"', "-G", '"Unix Makefiles"',
                    f'-DCMAKE_TOOLCHAIN_FILE="{toolchain}"',
                    "-DCMAKE_BUILD_TYPE=Release",
                ]),
                env="conanbuild",
            )
            self.run(f'cmake --build "{bdir}" -- -j2', env="conanbuild")
        return bdir

    def build(self):
        apply_conandata_patches(self)
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        boost_bdir = self._build_vendored_boost_libs(runtime_env)
        cmake = CMake(self)
        with runtime_env.vars(self).apply():
            cmake.configure()
            cmake.build()
        # Merge the vendored boost object files into the packaged static
        # lib so consumers get the boost thread/chrono symbols resolved.
        # (ar cannot embed archives into archives — extract the .o members
        # first, then append.)
        import glob as _glob
        import shutil as _shutil
        import subprocess as _subprocess
        import tempfile as _tempfile
        libpwiz = os.path.join(self.build_folder, "src", "libpwizlite.a")
        if not os.path.isfile(libpwiz):
            # fallback: search the whole build folder
            cands = _glob.glob(os.path.join(self.build_folder, "**", "libpwizlite.a"), recursive=True)
            cands = [c for c in cands if os.sep + "p" + os.sep not in c]
            if cands:
                libpwiz = cands[0]
        varchives = [
            os.path.join(boost_bdir, "libboost_thread_vendored.a"),
            os.path.join(boost_bdir, "libboost_chrono_vendored.a"),
        ]
        arbin = "/data/service/hnp/bin/llvm-ar"
        if os.path.isfile(libpwiz) and all(os.path.isfile(p) for p in varchives):
            # CI workers may not have ~/huawei/tmp (TemporaryDirectory's
            # dir= requires an existing directory) — create it, fall back
            # to the system default on failure.
            _tmpbase = os.path.expanduser("~/huawei/tmp")
            try:
                os.makedirs(_tmpbase, exist_ok=True)
                _tdctx = _tempfile.TemporaryDirectory(dir=_tmpbase)
            except OSError:
                _tdctx = _tempfile.TemporaryDirectory()
            with _tdctx as td:
                objs = []
                for va in varchives:
                    sub = os.path.join(td, os.path.basename(va) + ".d")
                    os.makedirs(sub, exist_ok=True)
                    _subprocess.run([arbin, "x", va], cwd=sub, check=True)
                    objs.extend(_glob.glob(os.path.join(sub, "*.o")))
                    objs.extend(_glob.glob(os.path.join(sub, "*.obj")))
                if objs:
                    _subprocess.run([arbin, "rcs", libpwiz] + objs, check=True)
                    self.output.info(f"merged {len(objs)} vendored boost objects into libpwizlite.a")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Headers: upstream installs src/pwiz tree
        hdr = os.path.join(self.package_folder, "include")
        if not os.path.isdir(os.path.join(hdr, "pwiz")):
            copy(self, "*", src=os.path.join(self.source_folder, "src", "pwiz"),
                 dst=os.path.join(hdr, "pwiz"))
        # Vendored boost headers needed by installed pwiz headers
        copy(self, "*", src=os.path.join(self.source_folder, "src", "boost"),
             dst=os.path.join(hdr, "boost"), keep_path=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PwizLite")
        self.cpp_info.set_property("cmake_target_name", "PwizLite::pwizlite")
        self.cpp_info.libs = ["pwizlite"]
        self.cpp_info.requires = ["boost::boost", "zlib::zlib"]
