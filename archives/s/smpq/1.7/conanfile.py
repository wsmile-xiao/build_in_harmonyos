#!/usr/bin/env python3
"""Conan recipe for smpq 1.7 — StormLib MPQ archiving utility.

HarmonyOS (aarch64) adaptation.  smpq is a small C command line tool that
links against StormLib; its CMakeLists locates the library through the
``STORMLIB_INCLUDE_DIR`` / ``STORMLIB_LIBRARY`` variables (with a
``find_path``/``find_library`` fallback) and then ``try_compile``s check.c to
reject StormLib < 9.14.  This recipe therefore points both variables straight
at the Conan-provided ``stormlib/9.40`` package instead of relying on a
system-wide install.

CMake notes:
* ``WITH_KDE=OFF`` — the KDE4 kio_smpq plugin (``find_package(KDE4 REQUIRED)``)
  is a desktop-integration extra irrelevant to a headless packaging flow and
  KDE4 is not available for OHOS.
* ``WITH_CMD=ON`` — builds the ``smpq`` console application plus the man page
  generator (``mangen``), which is the deliverable.
* The project declares only ``project(SMPQ)`` without a language list, so the
  try_compile probe compiles C — fine on this toolchain.

R32: settings.os must check in ("Linux", "OHOS").
R38: application with bin/ → software-level commands.json is provided.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SmpqConan(ConanFile):
    name = "smpq"
    version = "1.7"
    description = "StormLib MPQ archiving utility (create/extract/list MPQ archives)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/notmgn/smpq"
    url = "https://github.com/notmgn/smpq"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    # Informational for an application package; kept for pipeline uniformity.
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("stormlib/9.40")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        dep = self.dependencies["stormlib"]
        # Resolve to absolute paths: the upstream CMakeLists uses the values
        # verbatim (include_directories / target_link_libraries) and only
        # falls back to find_path/find_library when they are unset.
        inc_dir = None
        for d in dep.cpp_info.includedirs:
            full = d if os.path.isabs(d) else os.path.join(
                dep.package_folder or "", d)
            if os.path.isdir(full):
                inc_dir = full
                break
        lib_file = None
        for libdir in dep.cpp_info.libdirs:
            full_dir = libdir if os.path.isabs(libdir) else os.path.join(
                dep.package_folder or "", libdir)
            for name in ("libstorm.a", "libstorm.so", "storm.lib"):
                cand = os.path.join(full_dir, name)
                if os.path.isfile(cand):
                    lib_file = cand
                    break
            if lib_file:
                break
        if not inc_dir or not lib_file:
            raise ConanInvalidConfiguration(
                "stormlib package does not expose StormLib.h / libstorm "
                "(include=%s lib=%s)" % (inc_dir, lib_file))

        tc = CMakeToolchain(self)
        tc.variables["STORMLIB_INCLUDE_DIR"] = inc_dir
        tc.variables["STORMLIB_LIBRARY"] = lib_file
        tc.variables["WITH_CMD"] = True
        tc.variables["WITH_KDE"] = False
        # smpq links StormLib through a raw library path, so CMake never sees
        # the dependency's transitive requirements.  StormLib is a C++ static
        # library whose objects need zlib/bzip2 plus the C++ runtime
        # (__gxx_personality_v0).  Those must be resolved AFTER libstorm.a on
        # the link line: CMAKE_EXE_LINKER_FLAGS lands *before* the objects, so
        # the archive's undefined symbols would stay unresolved.  The
        # *_STANDARD_LIBRARIES variable is emitted after the target's
        # libraries, which is exactly the position needed.  No quoting: an
        # embedded `"` makes CMake pass the whole flag string as one argument.
        extra = []
        seen_dirs = []
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                full = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder or "", libdir)
                if os.path.isdir(full) and full not in seen_dirs:
                    seen_dirs.append(full)
                    extra.append("-L%s" % full)
            for lib in dep.cpp_info.libs:
                extra.append("-l%s" % lib)
        extra.extend(["-lc++", "-lm", "-ldl", "-lpthread"])
        tc.variables["CMAKE_C_STANDARD_LIBRARIES"] = " ".join(extra)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
