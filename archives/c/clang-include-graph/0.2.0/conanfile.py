#!/usr/bin/env python3
"""Conan recipe for clang-include-graph 0.2.0 (github.com/bkryza) — CLI tool
that analyzes a C++ project's include graph through libclang (application).

The upstream CMake project is built UNMODIFIED against conan
boost/1.91.0.1.3 (filesystem/graph/program_options/log/log_setup/
unit_test_framework/json via CMakeDeps) and links the libclang that ships
inside the on-device OHOS SDK toolchain (native/llvm, clang 15.0.4).

Key OHOS facts (probe-verified on the device, not assumed):
  * native/llvm ships a usable arm64 libclang.so (NEEDED only libc.so),
    clang-c/Index.h and llvm-config 15.0.4. There is no ohpcd clang recipe
    and conancenter is disabled, so libclang cannot be a conan dependency.
  * A code-signed aarch64 executable CAN dlopen that libclang.so at runtime
    and parse a translation unit with the C API.
  * libclang.so is an on-device SDK library, so no VirtualRunEnv entry covers
    it: the SDK lib dir is baked into every executable's RPATH. Boost shared
    libraries resolve through the conan run environment as usual.
  * OHOS loads only code-signed ELF, so the built binaries are signed with
    llvm-objcopy + binary-sign-tool (removing any prior .codesign section)
    before the upstream CTest gate and before packaging.
"""

import inspect
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, export_conandata_patches, get


class ClangIncludeGraphConan(ConanFile):
    name = "clang-include-graph"
    version = "0.2.0"
    description = (
        "Analyze C++ include graphs — a libclang based command line tool"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/bkryza/clang-include-graph"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Compiled Boost.Log/JSON/Test components (log, log_setup, json,
        # unit_test_framework) added by the boost/1.91.0.1.3 variant.
        self.requires("boost/1.91.0.1.3")

    def validate(self):
        # R32: settings.os check must be an explicit allow-list.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"clang-include-graph supports Linux and OHOS only, got "
                f"{self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    # ------------------------------------------------------------------ OHOS

    def _compiler_conf_path(self):
        # R33: take the compiler from Conan conf, never a bare env var.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or compilers.get("c") or ""

    def _ohos_llvm_root(self):
        """Return the on-device OHOS SDK native/llvm root that holds
        bin/llvm-config, lib/libclang.so and include/clang-c/Index.h.

        Candidates must contain the actual libclang shared library — some SDK
        layouts expose a top-level `bin/llvm-config` shim whose parent has no
        `lib/` (e.g. …/Cellar/ohos-sdk/26.0.0.18_1/), so `bin/llvm-config`
        alone is not a sufficient probe.  The real lib dir is always
        <root>/lib (…/native/llvm/lib) and is what gets baked into the
        executable RPATH, so it must exist.
        """
        compiler = os.path.realpath(self._compiler_conf_path())
        candidates = []
        if compiler:
            candidates.append(os.path.dirname(os.path.dirname(compiler)))
        candidates.extend([
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm",
            "/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/26.0.0.18_1"
            "/native/llvm",
        ])
        for root in candidates:
            if root and os.path.isfile(
                os.path.join(root, "bin", "llvm-config")
            ) and os.path.isfile(os.path.join(root, "lib", "libclang.so")):
                return root
        raise ConanInvalidConfiguration(
            "clang-include-graph needs the on-device OHOS SDK libclang "
            "(native/llvm with bin/llvm-config, lib/libclang.so and "
            "include/clang-c/Index.h); none found under the compiler conf "
            "path or the known SDK locations"
        )

    def _configure_flags(self):
        """CMake -D variables computed from the resolved OHOS environment."""
        variables = {
            # GitVersion.cmake falls back to 0.0.0-unknown when the source
            # tree is not a git checkout; pin the real upstream version.
            "GIT_VERSION": self.version,
        }
        if self.settings.os != "OHOS":
            return variables

        root = self._ohos_llvm_root()
        llvm_libdir = os.path.join(root, "lib")
        boost = self.dependencies["boost"]
        boost_include = os.path.join(boost.package_folder, "include")
        variables.update({
            # Upstream declares LLVM_PREFERRED_VERSION 16.0.0 but
            # FindLibClang.cmake never enforces it; pointing it at the SDK
            # llvm-config (clang 15.0.4) makes --cxxflags/--libdir/
            # --system-libs resolve against native/llvm.
            "LLVM_CONFIG_PATH": os.path.join(root, "bin", "llvm-config"),
            # lib-clang-include-graph is an OBJECT library: it compiles every
            # src/*.cc (Boost.JSON/Log/Program_options/asio headers) but only
            # the executables link the Boost targets, so the boost headers
            # cannot rely on target usage requirements. include_directories()
            # reads the legacy Boost_INCLUDE_DIRS variable which the conan
            # BoostConfig does not guarantee to set; surface the headers
            # through the global CXX flags instead.
            "CMAKE_CXX_FLAGS": f"-isystem {boost_include}",
            # libclang.so is not a conan dependency, so no run environment
            # provides it: bake the SDK lib dir into every executable RPATH.
            "CMAKE_EXE_LINKER_FLAGS": f"-Wl,-rpath,{llvm_libdir}",
        })
        return variables

    # ----------------------------------------------------------------- build

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables=self._configure_flags())
        cmake.build()
        if can_run(self):
            if self.settings.os == "OHOS":
                # OHOS loads only code-signed ELF; sign every built binary
                # (clang-include-graph + the nine upstream test executables)
                # before the CTest gate so libclang/boost load correctly.
                self._sign_ohos_elf_tree(self.build_folder)
            self._run_fail_closed(
                "ctest --output-on-failure --no-tests=error",
                env="conanrun",
                cwd=self.build_folder,
            )

    def package(self):
        executable = os.path.join(self.build_folder, "clang-include-graph")
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                f"built executable not found: {executable}"
            )
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        destination = os.path.join(bindir, "clang-include-graph")
        shutil.copy2(executable, destination)
        if self.settings.os == "OHOS":
            self._sign_elf_atomically(destination)
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # clang-include-graph is a CLI tool, not a library
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []

    # --------------------------------------------------- OHOS signing helpers

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _sign_ohos_elf_tree(self, root):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS tests require llvm-objcopy and binary-sign-tool"
            )
        for path in self._walk_elf_files(root):
            self._sign_elf_atomically(path)

    def _walk_elf_files(self, root):
        for directory, _, files in os.walk(root):
            for name in files:
                path = os.path.join(directory, name)
                if os.path.islink(path):
                    continue
                with open(path, "rb") as binary:
                    if binary.read(4) != b"\x7fELF":
                        continue
                yield path

    def _sign_elf_atomically(self, path):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS binary signing requires llvm-objcopy and "
                "binary-sign-tool"
            )
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self._run_fail_closed(f'"{objcopy}" --remove-section .codesign '
                                  f'"{temporary}"')
            self._run_fail_closed(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _run_fail_closed(self, command, **kwargs):
        parameters = inspect.signature(self.run).parameters
        if "ignore_errors" in parameters:
            kwargs["ignore_errors"] = False
        elif "check" in parameters:
            kwargs["check"] = True
        else:
            raise ConanInvalidConfiguration(
                "Unsupported ConanFile.run API: expected ignore_errors or check"
            )
        self.run(command, **kwargs)
