#!/usr/bin/env python3
"""Conan recipe for grokj2k 20.3.6 — JPEG 2000 codec (Grok).

Grok is an open-source JPEG 2000 codec supporting Part 1 (core) and
Part 15 (HTJ2K). Build system: CMake 3.21+. All third-party deps
(zlib, libpng, libtiff, libjpeg-turbo, lcms2, highway, spdlog, taskflow,
CLI11) are bundled — zero external dependencies beyond pthreads/atomic.

License: AGPL-3.0 (GNU Affero General Public License v3).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout



class Grokj2kConan(ConanFile):
    name = "grokj2k"
    version = "20.3.6"
    description = "Open source JPEG 2000 codec — Grok (HTJ2K support)"
    license = "AGPL-3.0"
    homepage = "https://github.com/GrokImageCompression/grok"
    url = "https://github.com/GrokImageCompression/grok"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: 平台兼容性检查
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"grokj2k {self.version} only supports Linux and OHOS, "
                f"got os={self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def _sdk_llvm_libdir(self):
        """Find the OHOS SDK's llvm/lib directory containing libxml2.so.16.

        The OHOS clang driver spawns lld for linking, and lld depends on
        libxml2.so.16 which lives in the SDK's llvm/lib. On CI workers the
        ambient LD_LIBRARY_PATH can shadow that dir with an incompatible
        libxml2, making lld fail with 'symbol not found' errors.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        comp = self.conf.get("tools.build:compiler_executables",
                             check_type=dict, default={})
        cxx = comp.get("cpp", "") if comp else ""
        if not cxx:
            return ""
        compiler = os.path.realpath(cxx)
        candidates = []
        # Derive SDK llvm/lib from clang's real path
        # /data/service/hnp/.../llvm/bin/clang → /data/service/hnp/.../llvm/lib
        clang_dir = os.path.dirname(compiler)       # .../llvm/bin
        llvm_dir = os.path.dirname(clang_dir)       # .../llvm
        candidates.append(os.path.join(llvm_dir, "lib"))
        # Also try resolving lld's path (lld is in the same llvm tree)
        for lld_name in ("ld.lld", "lld"):
            for search_dir in ("/data/service/hnp/bin", clang_dir):
                lld_path = os.path.join(search_dir, lld_name)
                if os.path.islink(lld_path):
                    lld_real = os.path.realpath(lld_path)
                    lld_llvm = os.path.dirname(os.path.dirname(lld_real))
                    candidates.append(os.path.join(lld_llvm, "lib"))
        # Fallback: well-known SDK layout on CI workers
        for sdk_base in (
            "/data/service/hnp/ohos-sdk.org",
            "/data/service/hnp/ohos-sdk",
        ):
            if os.path.isdir(sdk_base):
                for entry in sorted(os.listdir(sdk_base), reverse=True):
                    lib_dir = os.path.join(
                        sdk_base, entry, "ohos/native/llvm/lib"
                    )
                    candidates.append(lib_dir)
        # Try clang -print-resource-dir
        try:
            resource_dir = subprocess.check_output(
                [cxx, "-print-resource-dir"],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
        except (OSError, subprocess.CalledProcessError):
            pass
        # Last resort: known CI path (may contain stale/wrong libxml2)
        candidates.append("/storage/Users/currentUser/usr/local/lib")
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""


    def source(self):
        # Skip download if source already populated (e.g. from cache or pre-copy)
        if os.path.exists(os.path.join(self.source_folder, "CMakeLists.txt")):
            self.output.info("Source already populated, skipping download")
            return
        # Download main archive (GitHub archive excludes git submodules)
        get(self, **self.conan_data["sources"], strip_root=True)
        # Download and inject each git submodule into the correct location
        for _name, sub in self.conan_data.get("submodules", {}).items():
            dest = os.path.join(self.source_folder, sub["destination"])
            os.makedirs(dest, exist_ok=True)
            tmp = os.path.join(self.source_folder, f".submodule-{_name}")
            get(self, url=sub["url"], sha256=sub.get("sha256", ""),
                destination=tmp, strip_root=True)
            # Copy contents from the extracted archive into the destination
            for root, dirs, files in os.walk(tmp):
                rel = os.path.relpath(root, tmp)
                dst_dir = dest if rel == "." else os.path.join(dest, rel)
                os.makedirs(dst_dir, exist_ok=True)
                for fn in files:
                    src_f = os.path.join(root, fn)
                    dst_f = os.path.join(dst_dir, fn)
                    if not os.path.exists(dst_f):
                        shutil.copy2(src_f, dst_f)
            shutil.rmtree(tmp, ignore_errors=True)
        # Inject fmt into spdlog (spdlog FetchContent downloads fmt from GitHub;
        # pre-inject to avoid network dependency during build)
        fmt_info = self.conan_data.get("fmt_source", {})
        if fmt_info:
            fmt_dest = os.path.join(self.source_folder, fmt_info["destination"])
            os.makedirs(fmt_dest, exist_ok=True)
            fmt_tmp = os.path.join(self.source_folder, ".submodule-fmt")
            get(self, url=fmt_info["url"], sha256=fmt_info.get("sha256", ""),
                destination=fmt_tmp, strip_root=True)
            for root, dirs, files in os.walk(fmt_tmp):
                rel = os.path.relpath(root, fmt_tmp)
                dst_dir = fmt_dest if rel == "." else os.path.join(fmt_dest, rel)
                os.makedirs(dst_dir, exist_ok=True)
                for fn in files:
                    src_f = os.path.join(root, fn)
                    dst_f = os.path.join(dst_dir, fn)
                    if not os.path.exists(dst_f):
                        shutil.copy2(src_f, dst_f)
            shutil.rmtree(fmt_tmp, ignore_errors=True)
            # Patch spdlog's fmtlib.cmake to use local fmt instead of FetchContent
            fmtlib_cmake = os.path.join(self.source_folder,
                "src/include/spdlog/cmake/fmtlib.cmake")
            if os.path.exists(fmtlib_cmake):
                with open(fmtlib_cmake, "r") as f:
                    content = f.read()
                content = content.replace(
                    "include(FetchContent)\n\nFetchContent_Declare(\n    fmt\n    DOWNLOAD_EXTRACT_TIMESTAMP FALSE\n    URL https://github.com/fmtlib/fmt/archive/refs/tags/11.1.4.tar.gz\n    URL_HASH SHA256=ac366b7b4c2e9f0dde63a59b3feb5ee59b67974b14ee5dc9ea8ad78aa2c1ee1e)\n\nFetchContent_GetProperties(fmt)\nif(NOT fmt_POPULATED)\n    # We do not require os features of fmt\n    set(FMT_OS OFF CACHE BOOL \"Disable FMT_OS\" FORCE)\n    FetchContent_MakeAvailable(fmt)\n    set_target_properties(fmt PROPERTIES FOLDER \"third-party\")\nendif()",
                    "# OHOS: use pre-injected fmt instead of FetchContent\nset(FMT_OS OFF CACHE BOOL \"Disable FMT_OS\" FORCE)\nadd_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/external/fmt-11.1.4 EXCLUDE_FROM_ALL)\nset_target_properties(fmt PROPERTIES FOLDER \"third-party\")")
                with open(fmtlib_cmake, "w") as f:
                    f.write(content)
                self.output.info("Patched spdlog fmtlib.cmake to use local fmt")

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS 基于 Linux 内核，CMake 不认识 OHOS 平台 → 显式声明
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 显式设置目标架构，避免 bundled zlib-ng 架构检测失败（默认 fallback 到 x86）
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Static build (avoid .so pollution on OHOS)
        tc.variables["BUILD_SHARED_LIBS"] = False
        # Disable all optional features — build only the core library
        tc.variables["GRK_BUILD_CODEC"] = False          # no CLI executables
        tc.variables["GRK_BUILD_DCI"] = False
        tc.variables["GRK_BUILD_CORE_EXAMPLES"] = False
        tc.variables["GRK_BUILD_CODEC_EXAMPLES"] = False
        tc.variables["GRK_BUILD_DOC"] = False
        tc.variables["BUILD_TESTING"] = False             # tests need test data
        tc.variables["GRK_BUILD_PLUGIN_LOADER"] = False   # no GPU plugin
        tc.variables["GRK_ENABLE_ASAN"] = False
        tc.variables["GRK_BUNDLE_STATIC_CORE"] = False
        tc.variables["GRK_ENABLE_LIBCURL"] = False        # no network features
        # Disable SWIG bindings (Python/Java/C#)
        tc.variables["GRK_BUILD_CORE_SWIG_BINDINGS"] = False
        tc.variables["GRK_BUILD_CSHARP_SWIG_BINDINGS"] = False
        tc.variables["GRK_BUILD_JAVA_SWIG_BINDINGS"] = False
        tc.variables["GRK_BUILD_PYTHON_TESTS"] = False
        # Disable pkg-config file generation (Conan manages this)
        tc.variables["GRK_BUILD_PKGCONFIG_FILES"] = False
        # Use bundled thirdparty deps where possible
        # libpng/libtiff disabled: bundled zlib-ng architecture detection fails on OHOS
        # libjpeg disabled: uses FetchContent from GitHub which times out on OHOS
        tc.variables["GRK_BUILD_LIBPNG"] = False
        tc.variables["GRK_BUILD_LIBTIFF"] = False
        tc.variables["GRK_BUILD_LCMS2"] = True
        tc.variables["GRK_BUILD_JPEG"] = False
        # aarch64 little-endian: CMake cross-compile cannot probe endianness
        tc.variables["CMAKE_C_BYTE_ORDER"] = "LITTLE_ENDIAN"
        tc.variables["CMAKE_CXX_BYTE_ORDER"] = "LITTLE_ENDIAN"
        # CMake minimum is 3.21 — set policy version minimum for bundled deps
        # that may declare older cmake_minimum_required
        os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Set LD_LIBRARY_PATH so lld finds libxml2.so.16 at runtime.
        # Conan's Environment API may not propagate to cmake subprocesses
        # reliably; use os.environ directly for robustness.
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            new_val = sdk_lib if not old else f"{sdk_lib}:{old}"
            os.environ["LD_LIBRARY_PATH"] = new_val
            self.output.info(f"Set LD_LIBRARY_PATH={new_val}")
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Copy bundled third-party static libs that grokj2k links against
        # but cmake.install() does not install. Search the entire build folder.
        packaged_libs = set()
        for root, _dirs, files in os.walk(self.build_folder):
            for fn in files:
                if fn.endswith(".a") and fn != "libgrokj2k.a":
                    if fn not in packaged_libs:
                        copy(self, fn, dst=os.path.join(self.package_folder, "lib"),
                             src=root)
                        packaged_libs.add(fn)
                        self.output.info(f"Packaged bundled library: {fn} from {root}")
        # License file
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        # grokj2k core lib + bundled third-party libs needed by consumers
        self.cpp_info.libs = ["grokj2k", "lcms2"]
        # Headers install to include/grok-20.3/
        # (GROK_INSTALL_SUBDIR = "grok-<major>.<minor>")
        self.cpp_info.includedirs = ["include/grok-20.3"]
        # CMake target name (upstream exports as GROK::grokj2k)
        self.cpp_info.set_property("cmake_target_name", "grokj2k::grokj2k")
        self.cpp_info.set_property("pkg_config_name", "libgrokj2k")
        # Static build defines
        self.cpp_info.defines = ["GRK_STATIC"]
        # pthreads required on UNIX (OHOS 无独立 libatomic，原子操作内置于编译器运行时)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
