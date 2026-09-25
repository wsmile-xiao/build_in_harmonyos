#!/usr/bin/env python3
"""Conan recipe for libdeflate 1.26 on HarmonyOS."""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibdeflateConan(ConanFile):
    name = "libdeflate"
    version = "1.26"
    description = "Optimized DEFLATE/deflate/zlib/gzip compression library"
    license = "MIT"
    homepage = "https://github.com/ebiggers/libdeflate"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib is needed only by libdeflate's upstream comparison tests.
        # Keep it private so it does not become a consumer runtime dependency.
        self.requires("zlib/1.3.1", visible=False)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            filename="libdeflate-1.26.tar.gz",
            **self.conan_data["sources"],
            strip_root=True,
        )

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        candidates = []
        if cc:
            try:
                resource_dir = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
            except (OSError, subprocess.CalledProcessError):
                pass
            compiler = os.path.realpath(cc)
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
            )
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    def _llvm_tools(self):
        ar = shutil.which("ar")
        ranlib = shutil.which("ranlib")
        if ar and ranlib:
            return ar, ranlib
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        if not cc:
            return "llvm-ar", "llvm-ranlib"
        tool_dir = os.path.dirname(os.path.realpath(cc))
        ar = os.path.join(tool_dir, "llvm-ar")
        ranlib = os.path.join(tool_dir, "llvm-ranlib")
        if not os.path.isfile(ranlib):
            ranlib = ar
        return ar, ranlib

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if ndk:
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        if cc:
            native_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.realpath(cc)))
            )
            candidates.append(
                os.path.join(native_root, "build", "cmake", "ohos.toolchain.cmake")
            )
        candidates.extend(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
            )
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain"
        )

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        sdk_lib = self._sdk_llvm_libdir()
        if not sdk_lib:
            raise ConanInvalidConfiguration(
                "Cannot locate OHOS SDK llvm/lib containing libxml2.so.16"
            )
        zlib = self.dependencies.host["zlib"]
        zlib_root = zlib.package_folder
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler_c = compilers.get("c")
        if not compiler_c:
            raise ConanInvalidConfiguration(
                "OHOS test runner requires tools.build:compiler_executables.c"
            )
        ar, ranlib = self._llvm_tools()

        # Run every upstream-supported test group from a disposable source copy.
        # run_tests.sh removes its local build/ directory, which otherwise
        # contains Conan's active build folder under cmake_layout.
        test_env = (
            'CC="{0}" AR="{1}" RANLIB="{2}" '
            'CMAKE_PREFIX_PATH="{3}" ZLIB_ROOT="{3}" '
            'LD_LIBRARY_PATH="{4}:{3}/lib:$LD_LIBRARY_PATH"'
        ).format(compiler_c, ar, ranlib, zlib_root, sdk_lib)
        upstream_test_src = os.path.join(self.build_folder, "upstream-tests")
        shutil.rmtree(upstream_test_src, ignore_errors=True)
        shutil.copytree(
            self.source_folder,
            upstream_test_src,
            ignore=shutil.ignore_patterns("build"),
        )
        try:
            self.run(
                "{} bash scripts/run_tests.sh".format(test_env),
                env="conanbuild",
                cwd=upstream_test_src,
            )
        finally:
            shutil.rmtree(upstream_test_src, ignore_errors=True)

        # Build only the library for the Conan package. The upstream gzip CLI is
        # exercised above but is intentionally not installed as a tool package.
        build_dir = os.path.join(self.build_folder, "build-ohos")
        cmake_args = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_AR=\"{}\"".format(ar),
            "-DCMAKE_RANLIB=\"{}\"".format(ranlib),
            "-DLIBDEFLATE_BUILD_SHARED_LIB={}".format("ON" if self.options.shared else "OFF"),
            "-DLIBDEFLATE_BUILD_STATIC_LIB={}".format("OFF" if self.options.shared else "ON"),
            "-DLIBDEFLATE_BUILD_GZIP=OFF",
            "-DLIBDEFLATE_BUILD_TESTS=OFF",
        ]
        cmake = 'cmake -B "{}" -S "{}" {}'.format(
            build_dir, self.source_folder, " ".join(cmake_args)
        )
        self.run('LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" {}'.format(sdk_lib, cmake),
                 env="conanbuild")
        self.run('LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" cmake --build "{}"'.format(
            sdk_lib, build_dir
        ), env="conanbuild")

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        sdk_lib = self._sdk_llvm_libdir()
        self.run('LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" cmake --install "{}" --prefix "{}"'.format(
            sdk_lib, build_dir, self.package_folder
        ), env="conanbuild")
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # HarmonyOS shared objects must be signed after removing the SDK placeholder section.
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or compilers.get("cpp")
        native_root = ""
        if cc:
            native_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.realpath(cc)))
            )
        sdk_root = os.path.dirname(native_root) if native_root else ""
        objcopy_candidates = [
            os.environ.get("OHOS_LLVM_OBJCOPY", ""),
            shutil.which("llvm-objcopy") or "",
            os.path.join(native_root, "llvm", "bin", "llvm-objcopy") if native_root else "",
            "/data/service/hnp/bin/llvm-objcopy",
        ]
        signer_candidates = [
            os.environ.get("OHOS_BINARY_SIGN_TOOL", ""),
            shutil.which("binary-sign-tool") or "",
            os.path.join(sdk_root, "toolchains", "lib", "binary-sign-tool") if sdk_root else "",
            "/data/service/hnp/bin/binary-sign-tool",
        ]
        objcopy = next((path for path in objcopy_candidates if path and os.path.isfile(path)), "")
        signer = next((path for path in signer_candidates if path and os.path.isfile(path)), "")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS llvm-objcopy/binary-sign-tool unavailable; preserving the SDK-generated code-signature section"
            )
            return
        for so in sos:
            if os.path.islink(so):
                continue
            self.run('"{oc}" --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('"{sg}" sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["deflate"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libdeflate")
        self.cpp_info.set_property("cmake_target_name", "libdeflate::libdeflate")
        self.cpp_info.set_property("pkg_config_name", "libdeflate")
