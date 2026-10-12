#!/usr/bin/env python3
"""Conan recipe - tasksh 1.2.0 (Tasksh, the Taskwarrior shell).

Build system: CMake (cmake_minimum_required 2.8).

Dependencies:
  - readline/8.3  (GNU Readline, line editing + history; REQUIRED by upstream
                   cmake/Modules/FindReadline.cmake). Packaged static, and its
                   terminal-cursor symbols (tputs / tgetent / ...) resolve to
                   ncurses, so the static link line must carry -lncursesw.

HarmonyOS notes:
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 is passed on the cmake command line:
    CMake >= 3.31 warns and CMake >= 4.0 hard-errors on
    "cmake_minimum_required (VERSION 2.8)".
  - cmake/CXXSniffer.cmake keys the platform off CMAKE_SYSTEM_NAME. Under the
    OHOS toolchain CMAKE_SYSTEM_NAME is not "Linux", so none of the
    LINUX/DARWIN/... branches match and the file falls through to its final
    `else()` arm, which sets UNKNOWN. That is harmless: the only consumers of
    those variables are the `#cmakedefine` lines in cmake.h.in, and the sources
    have no `#ifdef LINUX` / `#ifdef UNKNOWN` branches.
  - `if (EXISTS ${CMAKE_SOURCE_DIR}/.git/index)` is false inside a Conan
    source folder, so HAVE_COMMIT stays undefined and commit.h is used as
    shipped in the release tarball.
  - The release tarball ships no test/ directory, so
    `add_subdirectory (test EXCLUDE_FROM_ALL)` is skipped by upstream's own
    `if (EXISTS ...)` guard.
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class TaskshConan(ConanFile):
    name = "tasksh"
    version = "1.2.0"
    description = "Tasksh - a shell wrapper around the Taskwarrior command-line task manager"
    license = "MIT"
    homepage = "https://taskwarrior.org/docs/tools/tasksh.html"
    url = "https://github.com/GothenburgBitFactory/taskshell"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream requires GNU Readline unconditionally
        # (find_package (Readline REQUIRED)).
        self.requires("readline/8.3", transitive_headers=True, transitive_libs=True)
        # readline is packaged static; its terminfo/cursor symbols live in
        # ncurses. Requires it explicitly so the static link line can name
        # libncursesw.a by absolute path (FindReadline only probes for a library
        # literally called "ncurses", which this platform does not ship).
        self.requires("ncurses/6.6", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMakeLists.txt declares cmake_minimum_required (VERSION 2.8).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Point FindReadline at the Conan-provided static Readline explicitly
        # instead of relying on system search paths.
        readline = self.dependencies["readline"]
        tc.variables["READLINE_INCLUDE_DIR"] = readline.cpp_info.includedirs[0]
        tc.variables["READLINE_readline_LIBRARY"] = os.path.join(
            readline.cpp_info.libdirs[0], "libreadline.a")
        tc.variables["READLINE_ncurses_LIBRARY"] = self._ncurses_library()

        # OHOS-specific compiler/linker flags for raw clang (without wrapper).
        # The CI profile uses /data/service/hnp/bin/clang directly which needs
        # explicit sysroot, libc++ includes, target triple, and resource directory.
        # The local WSL profile uses a wrapper script (/opt/lpk-fixed/clang) that
        # injects these flags automatically. This method ensures the recipe works
        # with both setups by adding the flags when they're not already present.
        if self.settings.os == "OHOS":
            self._setup_ohos_toolchain(tc)

        tc.generate()

    def _setup_ohos_toolchain(self, tc):
        """Configure OHOS-specific flags for the CMake toolchain.

        The CI runner uses /data/service/hnp/bin/clang which is the native
        aarch64 OHOS clang. It requires explicit sysroot, libc++ includes,
        target triple, and resource directory. The local WSL profile uses a
        wrapper script (/opt/lpk-fixed/clang) that injects these flags
        automatically. This method ensures the recipe works with both setups
        by adding the flags when they're not already present.
        """
        # Detect sysroot (for system headers like bits/alltypes.h)
        sysroot = self._detect_ohos_sysroot()
        if sysroot:
            tc.variables["CMAKE_SYSROOT"] = sysroot
            # Add OHOS system includes (bits/alltypes.h etc.)
            ohos_inc = os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos")
            if os.path.isdir(ohos_inc):
                # Escape quotes for CMake string: \" becomes literal " in CMake
                tc.extra_cxxflags.append(f'-isystem \\"{ohos_inc}\\"')

        # Detect libc++ include path (for <string>, <vector>, etc.)
        libcxx_inc = self._detect_ohos_libcxx_include()
        if libcxx_inc:
            # Escape quotes for CMake string
            tc.extra_cxxflags.append(f'-isystem \\"{libcxx_inc}\\"')

        # Detect compiler resource dir (for compiler builtin headers)
        resource_dir = self._detect_ohos_resource_dir()
        if resource_dir:
            tc.extra_cxxflags.append(f'-resource-dir \\"{resource_dir}\\"')

        # Target triple for OHOS
        tc.extra_cxxflags.append("--target=aarch64-linux-ohos")

        # Predefine OHOS macros (needed for libcxx-ohos)
        tc.extra_cxxflags.append("-D__OHOS__=1")
        tc.extra_cxxflags.append("-D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE")

        # Static libc++ linking (match wrapper script behavior)
        ohos_sdk_libdir = self._detect_ohos_sdk_libdir()
        if ohos_sdk_libdir:
            # Escape quotes for CMake string
            tc.extra_exelinkflags.append(f'-L\\"{ohos_sdk_libdir}\\"')
            tc.extra_exelinkflags.append("-fuse-ld=lld")
            tc.extra_exelinkflags.append("-lc++abi")
            tc.extra_exelinkflags.append("-lc++")
            tc.extra_exelinkflags.append("-lunwind")

    def _detect_ohos_sysroot(self):
        """Detect OHOS sysroot path (contains usr/include/aarch64-linux-ohos)."""
        # 1. Check explicit conf
        sysroot = self.conf.get("tools.build:sysroot")
        if sysroot and os.path.isdir(os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos")):
            return sysroot

        # 2. Check environment variable
        sysroot = os.environ.get("OHOS_SYSROOT")
        if sysroot and os.path.isdir(os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos")):
            return sysroot

        # 3. Local DevEco Studio sysroot (WSL)
        local_sysroot = "/mnt/c/Users/13909/ohos-sysroot"
        if os.path.isdir(os.path.join(local_sysroot, "usr", "include", "aarch64-linux-ohos")):
            return local_sysroot

        # 4. CI SDK path
        ci_sysroot = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm"
        if os.path.isdir(os.path.join(ci_sysroot, "usr", "include", "aarch64-linux-ohos")):
            return ci_sysroot

        # 5. Try to get from compiler's resource dir
        cxx = self.conf.get("tools.build:compiler_executables", {}).get("cpp")
        if cxx and os.path.isfile(cxx):
            try:
                result = subprocess.run(
                    [cxx, "-print-resource-dir"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    resource_dir = result.stdout.strip()
                    # resource_dir is .../llvm/lib/clang/15.0.4, sysroot is parent of llvm
                    llvm_dir = os.path.dirname(os.path.dirname(os.path.dirname(resource_dir)))
                    candidate = os.path.join(llvm_dir, "usr", "include", "aarch64-linux-ohos")
                    if os.path.isdir(candidate):
                        return llvm_dir
            except Exception:
                pass

        return None

    def _detect_ohos_libcxx_include(self):
        """Detect libc++ include path (contains c++/v1/string etc.)."""
        # 1. Local DevEco Studio libcxx-ohos
        local_libcxx = "/mnt/d/apps/DevEco Studio/sdk/default/openharmony/native/llvm/include/libcxx-ohos/include/c++/v1"
        if os.path.isdir(local_libcxx) and os.path.isfile(os.path.join(local_libcxx, "string")):
            return local_libcxx

        # 2. CI SDK libcxx-ohos
        ci_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/include/libcxx-ohos/include/c++/v1"
        if os.path.isdir(ci_libcxx) and os.path.isfile(os.path.join(ci_libcxx, "string")):
            return ci_libcxx

        # 3. Derive from sysroot
        sysroot = self._detect_ohos_sysroot()
        if sysroot:
            derived = os.path.join(sysroot, "include", "libcxx-ohos", "include", "c++", "v1")
            if os.path.isdir(derived) and os.path.isfile(os.path.join(derived, "string")):
                return derived

        # 4. Try compiler's built-in include path
        cxx = self.conf.get("tools.build:compiler_executables", {}).get("cpp")
        if cxx and os.path.isfile(cxx):
            try:
                result = subprocess.run(
                    [cxx, "-print-search-dirs"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if line.startswith("libraries:"):
                            paths = line.split("=", 1)[1].split(":")
                            for p in paths:
                                # Look for libcxx-ohos include relative to lib/clang
                                if p.endswith("/lib/clang/15.0.4"):
                                    base = os.path.dirname(os.path.dirname(os.path.dirname(p)))
                                    candidate = os.path.join(base, "include", "libcxx-ohos", "include", "c++", "v1")
                                    if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "string")):
                                        return candidate
            except Exception:
                pass

        return None

    def _detect_ohos_resource_dir(self):
        """Detect compiler resource directory (contains builtin headers)."""
        # 1. Local DevEco Studio
        local_resource = "/mnt/d/apps/DevEco Studio/sdk/default/openharmony/native/llvm/lib/clang/15.0.4"
        if os.path.isdir(local_resource) and os.path.isfile(os.path.join(local_resource, "include", "stddef.h")):
            return local_resource

        # 2. CI SDK
        ci_resource = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/clang/15.0.4"
        if os.path.isdir(ci_resource) and os.path.isfile(os.path.join(ci_resource, "include", "stddef.h")):
            return ci_resource

        # 3. Try to get from compiler
        cxx = self.conf.get("tools.build:compiler_executables", {}).get("cpp")
        if cxx and os.path.isfile(cxx):
            try:
                result = subprocess.run(
                    [cxx, "-print-resource-dir"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    resource_dir = result.stdout.strip()
                    if os.path.isdir(resource_dir) and os.path.isfile(os.path.join(resource_dir, "include", "stddef.h")):
                        return resource_dir
            except Exception:
                pass

        return None

    def _detect_ohos_sdk_libdir(self):
        """Detect OHOS SDK lib directory (aarch64-linux-ohos) for static libc++."""
        # 1. Local DevEco Studio
        local_libdir = "/mnt/d/apps/DevEco Studio/sdk/default/openharmony/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(local_libdir) and os.path.isfile(os.path.join(local_libdir, "libc++.a")):
            return local_libdir

        # 2. CI SDK
        ci_libdir = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(ci_libdir) and os.path.isfile(os.path.join(ci_libdir, "libc++.a")):
            return ci_libdir

        # 3. Derive from sysroot
        sysroot = self._detect_ohos_sysroot()
        if sysroot:
            derived = os.path.join(sysroot, "lib", "aarch64-linux-ohos")
            if os.path.isdir(derived) and os.path.isfile(os.path.join(derived, "libc++.a")):
                return derived

        return None

    def _ncurses_library(self):
        ncurses = self.dependencies["ncurses"]
        for libdir in ncurses.cpp_info.libdirs:
            for name in ("libncursesw.a", "libncurses.a"):
                candidate = os.path.join(libdir, name)
                if os.path.isfile(candidate):
                    return candidate
        raise ConanInvalidConfiguration(
            "ncurses static library (libncursesw.a) not found in "
            f"{list(ncurses.cpp_info.libdirs)}")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Static libreadline.a references terminfo entry points that only
        # ncurses provides; FindReadline looks for a library named "ncurses",
        # which does not exist on this platform (the wide-character build is
        # libncursesw.a). Name it explicitly on the link line.
        ncurses_libdir = self.dependencies["ncurses"].cpp_info.libdirs[0]
        cmake.configure(variables={
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            "CMAKE_EXE_LINKER_FLAGS": f"-L{ncurses_libdir} -lncursesw",
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]