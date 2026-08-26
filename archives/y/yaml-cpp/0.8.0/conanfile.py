#!/usr/bin/env python3
"""Conan recipe for yaml-cpp 0.8.0 (CMake).

A YAML parser and emitter in C++ matching the YAML 1.2 spec.
Homepage: https://github.com/jbeder/yaml-cpp
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class YamlCppConan(ConanFile):
    name = "yaml-cpp"
    version = "0.8.0"
    description = "A YAML parser and emitter in C++ matching the YAML 1.2 spec."
    license = "MIT"
    homepage = "https://github.com/jbeder/yaml-cpp"
    url = "https://github.com/jbeder/yaml-cpp"
    topics = ("yaml", "parser", "emitter", "serialization")
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

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: settings.os checks must use `in ("Linux", "OHOS")`,
        # not `== "Linux"`, so OHOS targets are accepted.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yaml-cpp is validated only for Linux and OHOS, "
                f"not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The GitHub archive extracts to `yaml-cpp-0.8.0/`; strip_root
        # collapses it so the sources sit at the root of the source folder.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # yaml-cpp 0.8.0 has cmake_minimum_required(VERSION 3.4), which
        # CMake 4.x rejects (compatibility with < 3.5 removed). Must use
        # cache_variables so it becomes a -D flag on the cmake command line;
        # a toolchain-file-only set() is not read before cmake_minimum_required.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # Build only the library; disable tests/tools/contrib/format/install-to-etc
        # so the package stays a self-contained library artifact.
        tc.variables["YAML_CPP_BUILD_TESTS"] = False
        tc.variables["YAML_CPP_BUILD_TOOLS"] = False
        tc.variables["YAML_CPP_BUILD_CONTRIB"] = False
        tc.variables["YAML_CPP_FORMAT_SOURCE"] = False
        tc.variables["YAML_CPP_INSTALL"] = True

        # BUILD_SHARED_LIBS must follow options.shared, not be hardcoded True:
        # hardcoding it would let a consumer's `-o shared=False` silently fail
        # (conan computes a different package_id while the artifact is still a
        # shared lib, and cpp_info.libs names no longer match the output).
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)

        # Static builds respect -fPIC so consumers can link the .a into DSOs.
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
                self.options.get_safe("fPIC", True)
            )

        if self.settings.os == "OHOS":
            # CMake ships a Platform/OHOS.cmake module (which just includes
            # Platform/Linux) but Conan's CMakeToolchain defaults
            # CMAKE_SYSTEM_NAME to "HarmonyOS" — a name CMake has no platform
            # file for. The mismatch leaves platform variables (notably
            # CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG) empty, so shared libraries
            # are built without DT_SONAME, and the linker bakes absolute paths
            # into consumers' DT_NEEDED. Fix the name + processor here, with an
            # os guard so other profiles (e.g. os=Linux/x86_64) keep CMake's
            # native platform detection intact.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = (
                "aarch64"
            )
            # Install to lib/ (not lib64/) so cpp_info.libdirs and test_package
            # find the artifacts where they expect them.
            tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Ship the license alongside the binaries (good practice + CI checks).
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        # OHOS XPM requires dlopen'd .so and exec'd ELFs to be code-signed,
        # otherwise loading/execution fails with Permission denied. Signing is
        # content-hash based (stored in a .codesign section), so any post-sign
        # byte mutation (strip/patchelf/objcopy/relink) invalidates it.
        # yaml-cpp installs only a library, so only the lib/ tree needs signing.
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_libraries()

    def package_info(self):
        self.cpp_info.libs = ["yaml-cpp"]
        self.cpp_info.set_property("cmake_file_name", "yaml-cpp")
        self.cpp_info.set_property("cmake_target_name", "yaml-cpp::yaml-cpp")
        self.cpp_info.set_property("pkg_config_name", "yaml-cpp")

    # ------------------------------------------------------------------
    # OHOS code-signing helpers
    # ------------------------------------------------------------------
    def _sign_shared_libraries(self):
        """Code-sign every real ELF .so under lib/ for OHOS execution."""
        targets = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            recursive=True,
        )
        targets += glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
            recursive=True,
        )
        # Deduplicate and skip symlinks: only sign the real ELF the link
        # points at, otherwise the same file gets signed twice.
        paths = sorted(
            {
                p
                for p in targets
                if os.path.isfile(p) and not os.path.islink(p)
            }
        )
        if not paths:
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            # Release worker signs the package; a non-OHOS build host has
            # neither tool, so warn rather than fail.
            self.output.warning(
                "HarmonyOS execution requires llvm-objcopy and "
                "binary-sign-tool; release worker must sign the package"
            )
            return

        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        """Sign one ELF in-place via a temp copy (atomic replace)."""
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            # Drop any pre-existing .codesign so the new hash is clean.
            self.run(
                shlex.join(
                    [objcopy, "--remove-section", ".codesign", temporary]
                )
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                )
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        """Locate an OHOS host tool: beside the compiler, in /data/service/hnp/bin, or on PATH."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next(
            (path for path in candidates if os.path.isfile(path)), "",
        )
