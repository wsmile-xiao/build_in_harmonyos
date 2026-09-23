#!/usr/bin/env python3
"""Conan recipe for drogon 1.9.13 — C++17 async HTTP web application framework.

Based on ConanCenter recipe with OHOS adaptation:
- R32: system_libs platform check includes OHOS
- UUID: conan uuid package (util-linux 2.40.1) mapped to drogon's bundled
  FindUUID (UUID_lib target); header layout fixed by 0001 patch
- Upstream DROGON_TEST suite (BUILD_TESTING=ON) executed in build() via ctest,
  with OHOS ELF signing (llvm-objcopy + binary-sign-tool) so the cross-built
  test executables can run on the HarmonyOS build host
- Database clients (postgres/mysql/sqlite/redis), drogon_ctl, brotli and
  yaml-cpp are disabled (non-essential dependencies trimmed; they are QUIET
  soft-deps upstream and compile to no-op stubs when absent)
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)


required_conan_version = ">=2.0"


class DrogonConan(ConanFile):
    name = "drogon"
    version = "1.9.13"
    description = "A C++17 based HTTP web application framework running on Linux/macOS/Unix/Windows"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/drogonframework/drogon"
    topics = ("http-server", "web-framework", "asynchronous-programming", "http-framework")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [False, True],
        "fPIC": [True, False],
        "with_orm": [True, False],
        "with_brotli": [True, False],
        "with_yaml_cpp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_orm": True,
        "with_brotli": False,
        "with_yaml_cpp": False,
    }

    # TLS test fixtures for the upstream CookieSameSite test (the upstream
    # test.sh copies them from the trantor submodule's test dir; with
    # USE_SUBMODULE=OFF we ship the same trantor test certificates here)
    exports_sources = "resources/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # trantor: drogon's network layer. drogon 1.9.13 does not use any of
        # the trantor 1.5.27/1.5.28 new APIs (forwardToTLSBuffer,
        # getCloseCallback), so the in-registry trantor 1.5.26 (within the
        # upstream CCI range >=1.5.25 <2) is used.
        self.requires("trantor/1.5.26", transitive_headers=True, transitive_libs=True)
        self.requires("jsoncpp/1.9.8", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/[>=1.2.11 <2]")
        # drogon's lib/src/Utilities.cc calls uuid_generate (util-linux libuuid)
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.requires("uuid/2.40.1")
        if self.options.get_safe("with_brotli"):
            self.requires("brotli/1.2.0")
        if self.options.get_safe("with_yaml_cpp"):
            self.requires("yaml-cpp/0.8.0")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_CTL"] = False              # drogon_ctl tool (needs host runtime)
        tc.cache_variables["BUILD_EXAMPLES"] = False
        tc.cache_variables["BUILD_DOC"] = False
        tc.cache_variables["BUILD_ORM"] = self.options.with_orm
        tc.cache_variables["BUILD_BROTLI"] = self.options.with_brotli
        tc.cache_variables["BUILD_YAML_CONFIG"] = self.options.get_safe("with_yaml_cpp", False)
        tc.cache_variables["BUILD_POSTGRESQL"] = False       # DB clients trimmed
        tc.cache_variables["BUILD_MYSQL"] = False
        tc.cache_variables["BUILD_SQLITE"] = False
        tc.cache_variables["BUILD_REDIS"] = False
        tc.cache_variables["BUILD_TESTING"] = True           # upstream DROGON_TEST suite
        tc.cache_variables["CMAKE_TRY_COMPILE_CONFIGURATION"] = str(self.settings.build_type)
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = True
        tc.cache_variables["USE_SUBMODULE"] = False          # use conan trantor
        if self.settings.os == "OHOS":
            # CMake has no built-in HarmonyOS platform module. Complete its
            # shared-linker contract so in-tree consumers record basename
            # SONAMEs and a build-only runtime path (jsoncpp precedent).
            for language in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"] = ":"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

        # OHOS: prepend the toolchain libc++ dir to the runtime library path
        # so the loader never resolves libc++_shared.so from an unrelated
        # search entry (e.g. an app bundle lib dir shipping an incompatible
        # build). Applied at the conanrun scope — the ctest invocations in
        # build() inherit it automatically.
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", self._toolchain_libcxx_dir())
        env.vars(self, scope="run").save_script("drogon_libcxx_runenv")

        deps = CMakeDeps(self)
        # drogon's CMakeLists does find_package(Jsoncpp) and links Jsoncpp_lib
        deps.set_property("jsoncpp", "cmake_file_name", "Jsoncpp")
        deps.set_property("jsoncpp", "cmake_target_name", "Jsoncpp_lib")
        # drogon's bundled cmake_modules/FindUUID.cmake expects package UUID
        # providing the UUID_lib target with util-linux libuuid semantics
        # (header layout fixed by 0001 patch: <uuid/uuid.h>)
        deps.set_property("uuid", "cmake_file_name", "UUID")
        deps.set_property("uuid", "cmake_target_name", "UUID_lib")
        if self.options.get_safe("with_brotli"):
            deps.set_property("brotli", "cmake_file_name", "Brotli")
            deps.set_property("brotli", "cmake_target_name", "Brotli_lib")
        if self.options.get_safe("with_yaml_cpp"):
            deps.set_property("yaml-cpp", "cmake_additional_variables_prefixes", ["YAML_CPP"])
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not can_run(self):
            self.output.warning(
                "The target cannot run on this build host; upstream tests "
                "must be executed by the native HarmonyOS validation worker."
            )
            return

        if self.settings.os == "OHOS":
            self._sign_build_artifacts()
            # CookieSameSite loads server.crt/server.key from its working
            # directory (upstream test.sh copies them from the trantor
            # submodule); ship the same trantor test certificates.
            # exports_sources lands next to src/ (base_source), and the ctest
            # working dir is the CMakeLists dir of the test target
            # (build/lib/tests).
            res_dir = os.path.normpath(os.path.join(self.source_folder, "..", "resources"))
            tests_bin_dir = os.path.join(self.build_folder, "lib", "tests")
            copy(self, "server.crt", src=res_dir, dst=tests_bin_dir)
            copy(self, "server.key", src=res_dir, dst=tests_bin_dir)
            # OHOS: run ctest through CONFIG_SHELL bash — /system/bin/sh (mksh)
            # fails to load dynamically linked test binaries (aa3d precedent).
            # The toolchain libc++ dir is prepended to LD_LIBRARY_PATH via the
            # drogon_libcxx_runenv script generated in generate().
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            cmd = (
                f"cd {shlex.quote(self.build_folder)} && "
                "ctest --output-on-failure --no-tests=error"
            )
            self.run(shlex.join([bash, "-c", cmd]), env="conanrun")
        else:
            self.run(
                shlex.join(
                    [
                        "ctest",
                        "--test-dir",
                        self.build_folder,
                        "--output-on-failure",
                        "--no-tests=error",
                    ]
                ),
                env="conanrun",
            )

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        # drop CMake package config files, keep only drogon's helper modules
        rm(self, "*", os.path.join(self.package_folder, "lib", "cmake"), recursive=True,
           excludes=["DrogonUtilities.cmake", "ParseAndAddDrogonTests.cmake"])

    def package_info(self):
        self.cpp_info.libs = ["drogon"]
        self.cpp_info.set_property("cmake_file_name", "Drogon")
        self.cpp_info.set_property("cmake_target_name", "Drogon::Drogon")
        self.cpp_info.set_property("pkg_config_name", "drogon")
        # drogon helper modules for creating views / tests at consumer side
        self.cpp_info.set_property(
            "cmake_build_modules",
            [os.path.join("lib", "cmake", "Drogon", "DrogonUtilities.cmake"),
             os.path.join("lib", "cmake", "Drogon", "ParseAndAddDrogonTests.cmake")])

        if self.settings.os == "Windows":
            self.cpp_info.system_libs.extend(["rpcrt4", "ws2_32", "crypt32", "advapi32", "shlwapi", "iphlpapi"])
        else:
            # dl is linked unconditionally on Linux-like platforms (CMakeLists: NOT WIN32 -> dl)
            self.cpp_info.system_libs.append("dl")
        # R32: OHOS is a Linux-like platform — pthread/m via libc
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
            self.cpp_info.system_libs.append("m")

    # ── OHOS ELF signing (jsoncpp precedent) ──────────────────────────────

    def _toolchain_libcxx_dir(self):
        """Directory containing the toolchain-matching libc++_shared.so.

        Derived from the compiler executable path (resolving symlinks, e.g.
        hnp/bin/clang++ -> ohos-sdk/llvm/bin/clang++ -> llvm/lib/<arch>/).
        """
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("cpp", "")
        compiler = os.path.realpath(compiler) if compiler else ""
        compiler_dir = os.path.dirname(compiler) if compiler else ""
        llvm_root = os.path.dirname(compiler_dir) if compiler_dir else ""
        candidates = []
        if llvm_root:
            candidates.extend(
                [
                    os.path.join(llvm_root, "lib", "aarch64-linux-ohos"),
                    os.path.join(llvm_root, "aarch64-linux-ohos", "lib"),
                    os.path.join(llvm_root, "lib"),
                ]
            )
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return os.path.normpath(cand)
        # realpath failed to resolve an SDK layout — fall back to the compiler
        # dir itself (an empty/invalid entry would shadow the system libc++)
        return compiler_dir or "/data/service/hnp/bin"

    def _sign_build_artifacts(self):
        patterns = (
            os.path.join(self.build_folder, "**", "unittest"),
            os.path.join(self.build_folder, "**", "cookie_same_site"),
            os.path.join(self.build_folder, "**", "real_ip_resolver"),
        )
        paths = [p for pat in patterns for p in glob.glob(pat, recursive=True) if os.path.isfile(p)]
        if not paths:
            raise ConanInvalidConfiguration(
                "OHOS upstream-test execution requires the unittest/cookie_same_site/real_ip_resolver binaries"
            )
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS upstream-test execution requires llvm-objcopy and binary-sign-tool"
            )
        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(shlex.join([objcopy, "--remove-section", ".codesign", temporary]))
            self.run(shlex.join([signer, "sign", "-inFile", temporary, "-outFile", temporary, "-selfSign", "1"]))
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if os.path.isfile(path)), "")
