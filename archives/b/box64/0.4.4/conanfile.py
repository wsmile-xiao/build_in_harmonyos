#!/usr/bin/env python3
"""Conan recipe for box64 0.4.4 (HarmonyOS PC / aarch64, musl host).

box64 emulates x86_64 Linux userspace on ARM64.  This recipe builds the
ARM64 + Dynarec configuration for OHOS.  Upstream has no OHOS/musl host
support; the adaptation lives in patches/ (full problem -> root cause -> fix
table in notes.md).  The important runtime facts baked in:

* box64's malloc/mmap/dlopen family wrappers must stay local in .dynsym:
  OHOS musl resolves libc's own PLT through the executable and would call the
  not-yet-initialised wrappers, crashing before main().  The adapted
  CMakeLists.txt generates a version script and adds -no-pie on OHOS.
* musl-fts / musl-obstack come from the OpenHarmonyPCDeveloper registry and
  are injected into the CMakeLists find hooks through BOX64_FTS_* /
  BOX64_OBSTACK_* variables (no shared /usr/local prefix, R49).
* The package is self-contained: the two compat shared objects are bundled
  into <package>/lib and resolved via the binary's $ORIGIN/../lib RUNPATH.
* OHOS needs signed ELF images; cmake --install rewrites RUNPATH and thereby
  invalidates the linker self-signature, so the shipped host ELF files are
  re-signed after install (bindirs / libdirs only, never x86_64 guest libs).

R38: box64 is a CLI tool -> software-level archives/b/box64/commands.json.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# OHOS host code signatures (see notes.md); x86_64 guest files are skipped.
_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"
_SIGNER = "/data/service/hnp/bin/binary-sign-tool"
_AARCH64 = 0xB7


class Box64Conan(ConanFile):
    name = "box64"
    version = "0.4.4"
    description = ("x86_64 Linux userspace emulator for ARM64 "
                   "(HarmonyOS PC build with ARM64 Dynarec)")
    license = "MIT"
    homepage = "https://github.com/ptitSeb/box64"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("musl-fts/1.2.7")
        self.requires("musl-obstack/1.2.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ──────────────────────────────────────────────────────────

    def _inject_dep(self, tc, dep_name, prefix, libname, header):
        """Point the CMakeLists find_library/find_path hooks at the exact
        dependency paths (box64 does not use CMakeDeps/find_package)."""
        dep = self.dependencies[dep_name]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        incdir = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        lib = None
        for candidate in ("lib%s.so" % libname, "lib%s.a" % libname):
            path = os.path.join(libdir, candidate)
            if os.path.exists(path):
                lib = path
                break
        if lib is None:
            raise ConanException("%s: no lib%s.{so,a} under %s"
                                 % (dep_name, libname, libdir))
        tc.variables["%s_LIBRARY" % prefix] = lib
        tc.variables["%s_INCLUDE_DIR" % prefix] = incdir
        self.output.info("%s: library=%s include=%s" % (dep_name, lib, incdir))

    @staticmethod
    def _is_host_elf(path):
        try:
            with open(path, "rb") as fh:
                head = fh.read(20)
        except OSError:
            return False
        return (len(head) >= 20 and head[:4] == b"\x7fELF"
                and head[18] == _AARCH64)

    # ── build phases ─────────────────────────────────────────────────────

    def generate(self):
        tc = CMakeToolchain(self)
        # Dependency paths are consumed by CMakeLists after project(), so
        # toolchain variables are fine for them.
        self._inject_dep(tc, "musl-fts", "BOX64_FTS", "fts", "fts.h")
        self._inject_dep(tc, "musl-obstack", "BOX64_OBSTACK", "obstack",
                         "obstack.h")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # ARM64/ARM_DYNAREC/NOGIT must be CMake command-line -D arguments:
        # box64's option() chain runs before project() (the toolchain is only
        # read at project()), so toolchain cache variables land too late and
        # are silently reset to OFF.  -D cache entries exist before the
        # CMakeLists body runs, matching the documented bare build.
        cmake.configure(cli_args=["-DARM64=ON", "-DARM_DYNAREC=ON",
                                  "-DNOGIT=ON", "-DNOLOADADDR=OFF"])
        # The OHOS build host is shared with other heavy workloads (and CI
        # workers are small): keep the parallelism bounded at 4.
        cmake.build(build_tool_args=["-j4"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._bundle_compat_libs()
        self._sign_host_elfs()

    def _bundle_compat_libs(self):
        """Bundle the musl-fts/musl-obstack SONAMEs next to bin/box64 so the
        executable is relocatable and self-contained at runtime."""
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        for dep_name, soname in (("musl-fts", "libfts.so.0"),
                                 ("musl-obstack", "libobstack.so.1")):
            dep = self.dependencies[dep_name]
            libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
            src = os.path.join(libdir, soname)
            if not os.path.isfile(src):
                raise ConanException("%s: %s not found in %s"
                                     % (dep_name, soname, libdir))
            dst = os.path.join(lib_dst, soname)
            shutil.copyfile(os.path.realpath(src), dst)
            self.output.info("bundled %s -> %s" % (soname, dst))

    def _sign_host_elfs(self):
        """Re-sign the aarch64 ELF files we ship (bin/ + lib/).

        cmake --install rewrites RUNPATH, which invalidates the linker's
        self-signature; OHOS refuses to exec/dlopen unsigned images.  The
        x86_64 guest payload (x64lib, tests/box64-bash) is never signed.
        """
        if not os.path.exists(_SIGNER):
            raise ConanException("binary-sign-tool not found: %s" % _SIGNER)
        targets = []
        for sub in ("bin", "lib"):
            subdir = os.path.join(self.package_folder, sub)
            if not os.path.isdir(subdir):
                continue
            for name in sorted(os.listdir(subdir)):
                path = os.path.join(subdir, name)
                if (os.path.isfile(path) and not os.path.islink(path)
                        and self._is_host_elf(path)):
                    targets.append(path)
        for path in targets:
            self.run('%s --remove-section .codesign "%s" 2>/dev/null || true'
                     % (_OBJCOPY, path))
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (_SIGNER, path, path))
            self.output.info("signed %s" % os.path.relpath(path, self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # R38: CLI application package -> no library components
        self.cpp_info.libs = []
