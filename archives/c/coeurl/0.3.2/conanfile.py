#!/usr/bin/env python3
"""Conan recipe — coeurl 0.3.2 (Meson).

coeurl — a simple C++17 asynchronous HTTP client library on top of libcurl
and libevent (Nheko-Reborn). Adapted to HarmonyOS PC (aarch64, musl, clang).

Native exploration evidence (device, this task):
  - meson setup with pkg-config deps (spdlog/libcurl/libevent_core/
    libevent_pthreads/doctest) + wrap-mode=nofallback: all deps found,
    the libevent CMake subproject fallback path is NOT taken.
  - library `lib` target: versionned libcoeurl.so.0.3 (soversion 0.3),
    headers include/coeurl/{client,request,errors,headers}.hpp,
    pkg-config file coeurl.pc (Requires.private: spdlog, libcurl,
    libevent_core, libevent_pthreads).
  - Upstream tests (doctest): requests 17/17 + requests_tls 17/17 on the
    device against local flask test servers (upstream scripts), evidence
    in reports/. NOT built by conan create: they need running localhost
    servers; the package dependency chain stays test-free (doctest is a
    meson fallback-only dependency and upstream marks tests non-installed).

pkg-config consumption doctrine (workflow §5.1): meson probes dependencies
via pkg-config; the Conan发行 curl package ships a curl-config whose prefix
points at a dead packaging-machine path — never consumed here. PkgConfigDeps
regenerates .pc files whose prefixes point at real package folders.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class CoeurlConan(ConanFile):
    name = "coeurl"
    version = "0.3.2"
    description = ("Simple asynchronous HTTP(S) client library on top of "
                   "libcurl and libevent (Nheko-Reborn)")
    license = "MIT"
    homepage = "https://nheko.im/nheko-reborn/coeurl"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("http", "libcurl", "libevent", "async", "network")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # coeurl meson.build deps: threads (system), spdlog, libcurl,
        # libevent_core + libevent_pthreads. libevent is a hard dependency
        # here (both .pc files provided by the ohpcd libevent package);
        # the upstream CMake-subproject fallback path is not taken.
        # fmt comes in transitively through spdlog; doctest is only the
        # upstream test framework (fallback dependency, not packaged).
        self.requires("libcurl/8.5.0")
        self.requires("spdlog/1.17.0")
        self.requires("libevent/2.1.13")
        # fmt: spdlog.pc declares "Requires: fmt" (compiled spdlog with
        # SPDLOG_FMT_EXTERNAL), but the CMakeDeps target chain of the ohpcd
        # spdlog package does not propagate fmt::fmt to consumers (conan
        # 2.29 transitive-data gap, workflow §5.3). The static libcoeurl.a
        # carries inline spdlog logger-template code with undefined fmt
        # symbols, so fmt MUST be linkable by consumers — declare it here
        # (version matches spdlog/1.17.0's own resolved requirement).
        self.requires("fmt/12.2.0")

    def build_requirements(self):
        # meson probes `ninja --version` at configure time; a static ninja
        # is on the build-profile PATH (device + CI workers), same doctrine
        # as gupnp 1.6.10 — do NOT tool_require the registry ninja.
        pass

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # Upstream defaults tests=false / examples=false — the packaged
        # build only compiles the library. Test/example targets and the
        # doctest fallback are exercised in the native exploration phase.
        tc.project_options["tests"] = False
        tc.project_options["examples"] = False
        # meson probes the static archiver by compiler-derived tool name
        # ("llvm-ar" for clang toolchains) via PATH lookup. CI workers ship
        # a shorter PATH where that bare name is not resolvable, failing
        # configure with "Unknown linker(s): [['llvm-ar']]" even though the
        # tool exists in the same hnp bin dir as the pinned clang++ (CI
        # build 42742/42735 evidence). Pin the archiver with an absolute
        # path, same doctrine as the profile's compiler_executables conf;
        # fall back to plain `ar` when the hnp layout differs.
        ar_path = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        if not os.path.exists(ar_path):
            ar_path = shutil.which("ar") or "ar"
        tc.binaries["ar"] = ar_path
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        if self.options.shared:
            # meson install rewrites DT_RUNPATH (bytes inside .dynstr),
            # invalidating the embedded .codesign hash -> dlopen
            # Permission denied (libsoup3 evidence, gupnp doctrine).
            # Overwrite the installed .so with the untouched build-tree
            # artifact.
            _lib = "libcoeurl.so.0.3"
            _src = os.path.join(self.build_folder, _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["coeurl"]
        self.cpp_info.system_libs = ["m", "pthread"]
        # The packaged ohpcd spdlog is compiled against EXTERNAL fmt
        # (upstream config targets carry INTERFACE_COMPILE_DEFINITIONS
        # "SPDLOG_SHARED_LIB;SPDLOG_COMPILED_LIB;SPDLOG_FMT_EXTERNAL"), but
        # the recipe's cpp_info does not re-declare them, so CMakeDeps
        # generates an empty spdlog_DEFINITIONS and consumer TUs including
        # <spdlog/logger.h> (exposed by coeurl public headers) fall into the
        # bundled-fmt include path, which does not exist in the package.
        # Declare the same interface on the coeurl target so consumers
        # compile spdlog headers with the configuration matching the
        # packaged library.
        self.cpp_info.defines = [
            "SPDLOG_FMT_EXTERNAL",
            "SPDLOG_COMPILED_LIB",
            "SPDLOG_SHARED_LIB",
        ]
        # Public headers include <curl/curl.h>, <event2/*.h>, <spdlog/logger.h>
        # — declare the dependency chain so consumers' CMake targets get the
        # include dirs transitively (component names per the dep recipes'
        # declared targets: CURL::libcurl, spdlog::spdlog, libevent::core,
        # libevent::pthreads).
        self.cpp_info.requires = [
            "libcurl::libcurl",
            "spdlog::spdlog",
            "libevent::core",
            "libevent::pthreads",
            "fmt::fmt",
        ]
        # ⚠️ CMakeDeps (conan 2.29) generates empty data for TRANSITIVE deps
        # (gupnp 1.6.10 doctrine): expose the dependency include/lib dirs here
        # so consumers compiling coeurl public headers find curl/event2/spdlog
        # headers, and runtime loaders find the shared dep libs.
        for depname in ("libcurl", "spdlog", "libevent", "fmt"):
            dep = self.dependencies.get(depname)
            if dep and dep.package_folder:
                _inc = os.path.join(dep.package_folder, "include")
                if os.path.isdir(_inc):
                    self.cpp_info.includedirs.append(_inc)
                _lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(_lib):
                    self.cpp_info.libdirs.append(_lib)
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", _lib)
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
