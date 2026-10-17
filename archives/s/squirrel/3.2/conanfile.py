#!/usr/bin/env python3
"""Conan recipe for the Squirrel 3.2 C/C++ VM and standard library."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


class SquirrelConan(ConanFile):
    name = "squirrel"
    version = "3.2"
    description = "Lightweight scripting language VM and standard library"
    license = "MIT"
    homepage = "http://www.squirrel-lang.org/"
    url = "https://github.com/albertodemichelis/squirrel"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration(
                f"Squirrel is validated only for Linux, OHOS, and Windows, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        fallback_compilers = None
        shared = bool(self.options.shared)
        # CMake 4 rejects the upstream 3.4 minimum unless the policy floor is
        # explicitly declared; this does not alter the project's source API.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["DISABLE_DYNAMIC"] = not shared
        tc.variables["DISABLE_STATIC"] = shared
        tc.variables["LONG_OUTPUT_NAMES"] = False
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if self.settings.os == "OHOS":
            configured = self.conf.get("tools.build:compiler_executables", default={}) or {}
            configured_c = str(configured.get("c", ""))
            llvm_root = os.environ.get("OHOS_NATIVE_LLVM", "").strip()
            if llvm_root and configured_c and not os.path.isfile(configured_c):
                # Local Windows verification may reuse the repository OHOS
                # profile whose /data/service compiler paths exist only on
                # the target worker. An explicit task environment can supply
                # an equivalent native LLVM root without entering the recipe.
                normalized_llvm_root = llvm_root.replace("\\", "/")
                fallback_compilers = (
                    f"{normalized_llvm_root}/clang.exe",
                    f"{normalized_llvm_root}/clang++.exe",
                    configured_c,
                    str(configured.get("cpp", "")),
                )
                tc.variables["CMAKE_C_COMPILER"] = fallback_compilers[0]
                tc.variables["CMAKE_CXX_COMPILER"] = fallback_compilers[1]
                target = os.environ.get("OHOS_TARGET_TRIPLE", "aarch64-linux-ohos").strip()
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target
                sysroot = os.environ.get("OHOS_NATIVE_SYSROOT", "").strip()
                if sysroot:
                    normalized_sysroot = sysroot.replace("\\", "/")
                    tc.variables["CMAKE_SYSROOT"] = normalized_sysroot
        make_program = os.environ.get("OHOS_NATIVE_MAKE", "").strip()
        if not make_program and self.settings.os == "OHOS":
            configured = self.conf.get("tools.build:compiler_executables", default={}) or {}
            configured_c = str(configured.get("c", ""))
            if configured_c and os.path.isfile(configured_c) and not configured_c.startswith("/data/"):
                make_program = shutil.which("make") or ""
        if make_program:
            tc.variables["CMAKE_MAKE_PROGRAM"] = make_program.replace("\\", "/")
        if not shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        if self.settings.os == "OHOS" and shared:
            for language in ("C", "CXX"):
                tc.variables[f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"] = "-Wl,-soname,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"] = "-Wl,-rpath,"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"] = ":"
                tc.variables[f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.generate()
        if fallback_compilers:
            self._normalize_compiler_toolchain(*fallback_compilers)
        self._normalize_sysroot_toolchain()

    def _normalize_compiler_toolchain(self, c_compiler, cxx_compiler, configured_c, configured_cxx):
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        with open(toolchain_file, encoding="utf-8") as handle:
            content = handle.read()
        if configured_cxx:
            content = content.replace(str(configured_cxx), str(cxx_compiler).replace("\\", "/"))
        content = content.replace(str(configured_c), str(c_compiler).replace("\\", "/"))
        with open(toolchain_file, "w", encoding="utf-8") as handle:
            handle.write(content)
        env_file = os.path.join(self.generators_folder, "conanbuildenv-release-armv8.sh")
        if os.path.isfile(env_file):
            with open(env_file, encoding="utf-8") as handle:
                env_content = handle.read()
            env_content = env_content.replace(
                'export SHELL="/data/service/hnp/bin/bash"', "unset SHELL"
            )
            env_content = env_content.replace(
                'export CONFIG_SHELL="/data/service/hnp/bin/bash"', "unset CONFIG_SHELL"
            )
            env_content = env_content.replace(
                'export PATH="/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin${PATH:+:$PATH}"',
                'export PATH="${PATH}"',
            )
            with open(env_file, "w", encoding="utf-8") as handle:
                handle.write(env_content)

    def _normalize_sysroot_toolchain(self):
        """Keep a DevEco sysroot containing spaces as one CMake value."""
        sysroot = self.conf.get("tools.build:sysroot", default=None)
        if not sysroot:
            return
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        with open(toolchain_file, encoding="utf-8") as handle:
            lines = handle.readlines()
        normalized = str(sysroot).replace("\\", "/")
        with open(toolchain_file, "w", encoding="utf-8") as handle:
            for line in lines:
                if line.startswith("set(CMAKE_SYSROOT ") and not line.startswith('set(CMAKE_SYSROOT "'):
                    handle.write(f'set(CMAKE_SYSROOT "{normalized}")\n')
                else:
                    handle.write(line)

    def build(self):
        if self.settings.os == "OHOS":
            self._configure_ohos_linker_runtime()
            # The repository profile supplies a target-side shell path. CMake
            # is invoked by Conan's host runner here, so let that runner use
            # its native shell while retaining the OHOS compiler toolchain.
            os.environ.pop("SHELL", None)
            os.environ.pop("CONFIG_SHELL", None)
            configured = self.conf.get("tools.build:compiler_executables", default={}) or {}
            configured_c = str(configured.get("c", ""))
            llvm_root = os.environ.get("OHOS_NATIVE_LLVM", "").strip()
            if llvm_root and configured_c and not os.path.isfile(configured_c):
                normalized_llvm_root = llvm_root.replace("\\", "/")
                self._normalize_compiler_toolchain(
                    f"{normalized_llvm_root}/clang.exe",
                    f"{normalized_llvm_root}/clang++.exe",
                    configured_c,
                    str(configured.get("cpp", "")),
                )
        alias_file = os.path.join(self.source_folder, "sq", "CMakeLists.txt")
        old_alias = "add_executable(squirrel::interpreter_static ALIAS sq)"
        new_alias = "add_executable(squirrel::interpreter_static ALIAS sq_static)"
        with open(alias_file, encoding="utf-8") as handle:
            if handle.read().count(old_alias) != 1:
                raise ConanInvalidConfiguration("unexpected static interpreter alias count")
        replace_in_file(self, alias_file, old_alias, new_alias)
        self._run_cmake_configure()
        self._run_cmake_build()
        if can_run(self):
            # The upstream project has no registered CTest cases; the packaged
            # consumer test exercises the public VM API instead.
            self.output.info("Squirrel upstream CMake project has no registered tests")

    def _configure_ohos_linker_runtime(self):
        """Expose the selected SDK's host-side lld runtime to CMake."""
        if os.name == "nt" or str(self.settings.os) != "OHOS":
            return

        configured = self.conf.get("tools.build:compiler_executables", default={}) or {}
        compiler = configured.get("cpp") or configured.get("c")
        candidates = []
        llvm_root = os.environ.get("OHOS_NATIVE_LLVM", "").strip()
        if llvm_root:
            candidates.append(os.path.join(llvm_root, "lib"))
            candidates.append(os.path.join(llvm_root, "..", "lib"))
        if compiler:
            compiler_dir = os.path.dirname(str(compiler))
            candidates.append(os.path.join(compiler_dir, "..", "lib"))
            sdk_parent = os.path.normpath(os.path.join(compiler_dir, ".."))
            for pattern in (
                os.path.join(sdk_parent, "ohos-sdk.org", "*", "ohos", "native", "llvm", "lib"),
                os.path.join(sdk_parent, "ohos-sdk", "*", "ohos", "native", "llvm", "lib"),
            ):
                candidates.extend(sorted(glob.glob(pattern)))

        selected = None
        for candidate in candidates:
            candidate = os.path.normpath(candidate)
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                selected = candidate
                break
        if not selected:
            return

        existing = [item for item in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if item]
        if selected not in existing:
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join([selected, *existing])
        self.output.info("Using OHOS linker host runtime: %s" % selected)

    def package(self):
        cmake_program = self.conf.get("tools.cmake:cmake_program", default="cmake")
        self.run(
            [cmake_program, "--install", self.build_folder],
            env=None,
            shell=False,
        )
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def _run_cmake_configure(self):
        """Invoke CMake without Conan's POSIX env-file wrapper on Windows."""
        cmake = CMake(self)
        toolchain_file = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        args = [
            cmake._cmake_program,
            "-G",
            cmake._generator,
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            f"-DCMAKE_INSTALL_PREFIX={self.package_folder}",
        ]
        args.extend(f"-D{key}={value}" for key, value in cmake._cache_variables.items())
        args.append(self.source_folder)
        self.run(args, env=None, shell=False)

    def _run_cmake_build(self):
        cmake_program = self.conf.get("tools.cmake:cmake_program", default="cmake")
        args = [cmake_program, "--build", self.build_folder]
        jobs = self.conf.get("tools.build:jobs", default=None)
        if jobs:
            args.extend(["--parallel", str(jobs)])
        self.run(args, env=None, shell=False)

    def package_info(self):
        libs = ["squirrel", "sqstdlib"] if self.options.shared else ["sqstdlib_static", "squirrel_static"]
        self.cpp_info.libs = libs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "squirrel")
        self.cpp_info.set_property("cmake_target_name", "squirrel::squirrel")
