#!/usr/bin/env python3
"""Conan recipe - tiledb 2.30.1 (cmake)

TileDB is an open-source, array database for fast analytical queries over
multidimensional, heterogeneous data. This recipe builds the core C++ library
(libtiledb.so) and the C API, with all optional cloud integrations (S3/Azure/GCS/
serialization/WebP/tools) disabled, tests disabled (rapidcheck absent from
registry), using the OHOS NDK toolchain and forcing C++20.

Build: CMake at source root with OHOS NDK ohos.toolchain.cmake. R32: os in
("Linux", "OHOS"). C++20 forced because tiledb 2.30.1 hard-requires concepts
(requires) and std::span, which OHOS libc++ (clang 15) provides only under -std=c++20.
"""
import os
import glob

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get, copy, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeDeps, cmake_layout


class TileDBConan(ConanFile):
    name = "tiledb"
    version = "2.30.1"
    description = "TileDB - open-source, array database for fast analytical queries"
    license = "MIT"
    homepage = "https://github.com/TileDB-Inc/TileDB"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        # R32: platform detection must use in ("Linux", "OHOS")
        if self.settings.os in ("Linux", "OHOS"):
            if self.options.shared:
                self.options.rm_safe("fPIC")

    def requirements(self):
        # 9 mandatory third-party deps + fmt (transitively required by spdlog for
        # <fmt/format.h> used directly by tiledb headers). All consumable via
        # conan download --only-recipe from the ohpcd remote (verified R36).
        self.requires("blosc2/3.2.3")
        self.requires("bzip2/1.0.8.2")
        self.requires("lz4/1.10.0.3")
        self.requires("openssl/3.5.6.1.2")
        self.requires("nlohmann_json/3.12.0")
        self.requires("spdlog/1.17.0")
        self.requires("fmt/12.2.0")
        self.requires("zlib/1.3.1.2")
        self.requires("zstd/1.5.7.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    # `patches/*.patch` 保留 patches/ 子目录结构，与 conandata.yml 的
    # patch_file: "patches/xxx.patch" 一致（apply_conandata_patches 把
    # patch_file 相对 export_sources_folder 解析）。
    exports_sources = "conandata.yml", "patches/*.patch"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Emit CMakeDeps config files so find_package(blosc2/fmt/...) resolve.
        # (No CMakeToolchain: build() drives CMake with the OHOS NDK toolchain.)
        CMakeDeps(self).generate()

    def _ohos_toolchain(self):
        # Self-discover OHOS NDK ohos.toolchain.cmake (same approach as zstd/1.5.7.1).
        ut = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + (
            [os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else []
        )
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
            )
        )
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME, or configure "
            "tools.cmake.cmaketoolchain:user_toolchain in profile [conf]"
        )

    def build(self):
        # Patch files are exported to export_sources_folder via `exports_sources`
        # (see class attr); apply_conandata_patches resolves patch_file against
        # that folder, so the headers' `a/ b/` prefixes resolve at -p1.
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        # Derive llvm-ar from toolchain dir; OHOS SDK lacks llvm-ranlib -> shim.
        build_cmake_dir = os.path.dirname(toolchain)  # .../build/cmake
        ndk_build = os.path.dirname(build_cmake_dir)  # .../build
        llvm_bin = os.path.join(os.path.dirname(os.path.dirname(ndk_build)), "llvm", "bin")
        cmake_ar = os.path.join(llvm_bin, "llvm-ar")
        ranlib_wrapper = os.path.join(self.build_folder, "llvm-ranlib-shim")
        with open(ranlib_wrapper, "w") as f:
            f.write('#!/data/service/hnp/bin/bash\nexec {} s "$@"\n'.format(cmake_ar))
        os.chmod(ranlib_wrapper, 0o755)

        bdir = os.path.join(self.build_folder, "build-ohos")
        # CMakeDeps wrote the dep *-config.cmake files into the build-folder
        # generators dir. The conan CMake helper needs CMakeToolchain (which we
        # cannot use — tiledb must build with the OHOS NDK toolchain), so drive
        # cmake manually. CMake 4.1 needs explicit <pkg>_DIR (CONFIG mode does
        # not search CMAKE_PREFIX_PATH for these), so point each dep at the
        # generators dir directly.
        # cmake_layout(src_folder=".") makes build_folder = <b>/build/Release, and
        # CMakeDeps writes the config files into build_folder/generators.
        generators = os.path.join(self.build_folder, "generators")
        # <pkg>_DIR must match the name tiledb passes to find_package() and the
        # config filename CMakeDeps wrote (Blosc2Config.cmake vs bzip2-config.cmake).
        # Only CONFIG-mode deps need _DIR; MODULE-mode (BZip2/LZ4/ZLIB) are fed via
        # the <PKG>_LIBRARIES/<PKG>_INCLUDE_DIR cache vars injected below.
        dep_dirs = {
            "Blosc2": generators,
            "nlohmann_json": generators,
            "spdlog": generators,
            "zstd": generators,
            "fmt": generators,
        }
        # find_package(OpenSSL) uses the MODULE finder, which needs OPENSSL_ROOT_DIR
        # (the package root containing lib/ and include/), not the CMakeDeps dir.
        try:
            openssl_root = os.path.join(
                self.dependencies["openssl"].cpp_info.aggregated_components().includedirs[0],
                "..",
            )
            openssl_root = os.path.abspath(os.path.normpath(openssl_root))
            mod_defs_openssl = [
                "-DOPENSSL_ROOT_DIR={}".format(openssl_root),
                "-DOPENSSL_INCLUDE_DIR={}".format(
                    self.dependencies["openssl"].cpp_info.aggregated_components().includedirs[0]
                ),
                # OHOS openssl 包只提供静态库 libssl.a/libcrypto.a（无 .so），
                # 用真实存在的 .a 作为 imported target 的 IMPORTED_LOCATION。
                "-DOPENSSL_CRYPTO_LIBRARY={}".format(
                    os.path.join(
                        self.dependencies["openssl"].cpp_info.aggregated_components().libdirs[0],
                        "libcrypto.a",
                    )
                ),
                "-DOPENSSL_SSL_LIBRARY={}".format(
                    os.path.join(
                        self.dependencies["openssl"].cpp_info.aggregated_components().libdirs[0],
                        "libssl.a",
                    )
                ),
            ]
        except Exception as e:
            self.output.warning("OHOS openssl resolve failed: {}".format(e))
            mod_defs_openssl = []
        # MODULE-mode Find-modules (FindBZip2/FindLZ4/FindZLIB) need these cache
        # vars; resolved from the Conan package dirs of the static .a libs.
        def _dep_prefix(dep):
            for d in self.dependencies.get(dep, []):
                return d.cpp.aggregated_components().includedirs[0] if d else None
            return None
        mod_defs = []
        for var, dep, libname in (
            ("BZIP2", "bzip2", "bz2"),
            ("LZ4", "lz4", "lz4"),
            ("ZLIB", "zlib", "z"),
        ):
            try:
                d = self.dependencies[dep]
                # Conan 2.29: access via the cpp_info aggregator (ConanFileInterface
                # itself carries no .cpp attribute).
                inc = d.cpp_info.aggregated_components().includedirs[0]
                libdir = d.cpp_info.aggregated_components().libdirs[0]
                libfile = os.path.join(libdir, "lib{}.a".format(libname))
                # Find modules (FindBZip2/FindLZ4/FindZLIB) build their ::targets
                # from the *_LIBRARY_RELEASE var (not *_LIBRARIES), so inject that.
                mod_defs += [
                    "-D{}_INCLUDE_DIR={}".format(var, inc),
                    "-D{}_LIBRARIES={}".format(var, libfile),
                    "-D{}_LIBRARY_RELEASE={}".format(var, libfile),
                ]
                self.output.info("OHOS mod: {} -> {}".format(var, libfile))
            except Exception as e:
                self.output.warning("OHOS mod resolve {} failed: {}".format(var, e))
        defs = " ".join([
            '-DCMAKE_PREFIX_PATH={}'.format(generators),
        ] + [
            '-D{name}_DIR={val}'.format(name=n, val=v) for n, v in dep_dirs.items()
        ] + mod_defs + mod_defs_openssl + [
            '-DCMAKE_TOOLCHAIN_FILE={}'.format(toolchain),
            '-DCMAKE_AR={}'.format(cmake_ar),
            '-DCMAKE_RANLIB={}'.format(ranlib_wrapper),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_CXX_STANDARD=20",
            "-DCMAKE_CXX_STANDARD_REQUIRED=ON",
            # OHOS 适配：OHOS toolchain 注入 --gcc-toolchain=<sdk>/llvm，OHOS 目标下该
            # 参数未被消费，clang 报 -Wunused-command-line-argument；tiledb 的
            # TILEDB_WERROR 把该告警升级为硬错误。关掉 WERROR 让编译可继续
            # （其余告警保留）。
            "-DTILEDB_WERROR=OFF",
            "-DTILEDB_S3=OFF",
            "-DTILEDB_AZURE=OFF",
            "-DTILEDB_GCS=OFF",
            "-DTILEDB_SERIALIZATION=OFF",
            "-DTILEDB_WEBP=OFF",
            "-DTILEDB_TOOLS=OFF",
            "-DTILEDB_TESTS=OFF",
            "-DTILEDB_ALLOW_REGEX_CHAR_PATH=ON",
            "-DCMAKE_BUILD_WITH_INSTALL_RPATH=OFF",
        ])
        self.run(
            'cmake -G "Unix Makefiles" -B {bdir} -S {sdir} {defs}'.format(
                bdir=bdir, sdir=self.source_folder, defs=defs
            )
        )
        self.run('cmake --build {bdir} -- -j$(nproc)'.format(bdir=bdir))

    def _conan_deps_prefix(self):
        # CMakeDeps is generated in build()/generate(); point CMake at the
        # aggregated include dirs of each dep (absolute paths into the cache).
        prefixes = []
        for dep in ("blosc2", "bzip2", "lz4", "openssl", "nlohmann_json",
                    "spdlog", "fmt", "zlib", "zstd"):
            try:
                d = self.dependencies[dep]
                inc = d.cpp.aggregated_components().includedirs
                if inc:
                    prefixes.append(os.path.abspath(inc[0]))
            except Exception:
                pass
        # Dedup parent dirs (includedirs are <prefix>/include).
        seen = set()
        out = []
        for p in prefixes:
            par = os.path.dirname(p)
            if par not in seen:
                seen.add(par)
                out.append(par)
        return os.pathsep.join(out)

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run(
            'cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder)
        )
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # HarmonyOS PC requires code signing for .so loaded via dlopen. Strip any
        # invalid self-sign and re-sign with binary-sign-tool -selfSign 1 (ML-0043).
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "TileDB")
        self.cpp_info.set_property("cmake_target_name", "TileDB::tiledb_shared")
