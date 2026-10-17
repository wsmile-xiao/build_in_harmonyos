#!/usr/bin/env python3
"""Conan recipe for scintilla 5.6.1 — HarmonyOS native code editor component.

Scintilla is a source code editing component. The upstream build depends on
GTK; for HarmonyOS we provide a complete platform layer (PlatOHOS.cxx +
ScintillaOHOS.cxx) using the OHOS Native Drawing API.

Build system: custom CMakeLists.txt (ohos/CMakeLists.txt).
Output: libscintilla_core.a (static) + libscintilla_ohos.so (shared).
"""
import os
import shutil
import glob

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class ScintillaConan(ConanFile):
    name = "scintilla"
    version = "5.6.1"
    description = "Cross-platform source code editor component library for HarmonyOS"
    license = "LicenseRef-Scintilla-License"
    homepage = "https://www.scintilla.org/"
    url = "https://www.scintilla.org/"
    topics = ("editor", "scintilla", "text", "ohos", "native-drawing")
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

    # Export the FINAL platform layer files (not patches — avoids context mismatch)
    exports_sources = (
        "PlatOHOS.cxx",
        "ScintillaOHOS.cxx",
        "ScintillaOHOS.h",
        "ohos/CMakeLists.txt",
    )

    def export_sources(self):
        # Standard pattern: export conandata patches (none for scintilla, but
        # required by conan-verify G1 and CI pre-commit hooks)
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def _get_ohos_sdk(self):
        """Locate the OHOS SDK native directory."""
        base = "/data/service/hnp/ohos-sdk.org"
        candidates = sorted(glob.glob(os.path.join(base, "ohos-sdk_*", "ohos", "native")))
        if candidates:
            return candidates[-1]
        return os.path.join(base, "ohos-sdk_26.0.0.18", "ohos", "native")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        sdk = self._get_ohos_sdk()

        # Tell the CMakeLists.txt where the OHOS SDK is
        tc.variables["OHOS_NDK_NATIVE"] = sdk

        # Point SCI_SRC_DIR at the extracted scintilla source (strip_root removes
        # the top-level "scintilla/" dir, so core sources are at <src>/src/)
        tc.variables["SCI_SRC_DIR"] = os.path.join(self.source_folder, "src")

        # ── Critical fix: add C++ standard library include path ──────────
        # The OHOS clang does not find <string>, <vector>, <cstdint>, etc. by
        # default. We must add the SDK's LLVM C++ headers directory.
        cpp_stdlib_inc = os.path.join(sdk, "llvm", "include", "c++", "v1")
        sysroot_inc = os.path.join(sdk, "sysroot", "usr", "include")

        # Method 1: CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES — CMake appends
        # these to every C++ compile command's include search path.
        tc.variables["CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES"] = (
            f"{cpp_stdlib_inc};{sysroot_inc}"
        )
        tc.variables["CMAKE_C_STANDARD_INCLUDE_DIRECTORIES"] = sysroot_inc

        # Method 2: extra_cxxflags — Conan toolchain appends these to CXXFLAGS
        tc.extra_cxxflags.append(f"-isystem{cpp_stdlib_inc}")
        tc.extra_cxxflags.append(f"-isystem{sysroot_inc}")
        tc.extra_cflags.append(f"-isystem{sysroot_inc}")

        # Method 3: CMAKE_CXX_FLAGS as fallback
        existing_cxx = tc.variables.get("CMAKE_CXX_FLAGS", "")
        tc.variables["CMAKE_CXX_FLAGS"] = (
            existing_cxx + f" -isystem {cpp_stdlib_inc} -isystem {sysroot_inc}"
        )

        # ── Linker: add OHOS system library search path ───────────────────
        arch = "aarch64"
        sdk_lib = os.path.join(sdk, "sysroot", "usr", "lib", f"{arch}-linux-ohos")
        tc.extra_exelinkflags.append(f"-L{sdk_lib}")
        tc.extra_sharedlinkflags.append(f"-L{sdk_lib}")

        tc.generate()

        # Method 4: also set env var CPLUS_INCLUDE_PATH as last resort
        self.buildenv_info.append("CPLUS_INCLUDE_PATH", cpp_stdlib_inc)
        self.buildenv_info.append("C_INCLUDE_PATH", sysroot_inc)

    def _inject_linker_env(self):
        """Ensure lld (invoked by clang) can load its libxml2.so.16 dependency.

        lld needs libxml2.so.16 from the SDK's llvm/lib dir. On workers where
        lld's RUNPATH ($ORIGIN/../lib) fails to resolve, an explicit
        LD_LIBRARY_PATH makes the musl loader find it (knowledge E120/E132).
        Without this, CMake's compiler test fails at link time with
        "Error loading shared library libxml2.so.16".

        Note: this must be set via os.environ in build(), NOT via
        buildenv_info — VirtualBuildEnv does not aggregate the recipe's own
        buildenv_info, so that would silently do nothing.
        """
        llvm_lib = os.path.join(self._get_ohos_sdk(), "llvm", "lib")
        if os.path.isdir(llvm_lib):
            current = os.environ.get("LD_LIBRARY_PATH", "")
            parts = [p for p in current.split(os.pathsep) if p]
            if llvm_lib not in parts:
                parts.insert(0, llvm_lib)
                os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(parts)

    def build(self):
        self._inject_linker_env()
        # Apply conandata patches (none for scintilla — platform files via exports_sources)
        apply_conandata_patches(self)

        # Copy exported platform files into ohos/ where CMakeLists.txt expects them
        ohos_dir = os.path.join(self.source_folder, "ohos")
        os.makedirs(ohos_dir, exist_ok=True)
        for f in ("PlatOHOS.cxx", "ScintillaOHOS.cxx", "ScintillaOHOS.h"):
            src = os.path.join(self.source_folder, f)
            dst = os.path.join(ohos_dir, f)
            if os.path.isfile(src):
                shutil.copy2(src, dst)

        cmake = CMake(self)
        cmake.configure(build_script_folder=ohos_dir)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # Also install the root-level platform header for consumers
        from conan.tools.files import copy
        copy(self, "ScintillaOHOS.h",
             src=os.path.join(self.source_folder, "ohos"),
             dst=os.path.join(self.package_folder, "include", "scintilla_ohos"))

    def package_info(self):
        # Always include both libraries: scintilla_core (static, core+PlatOHOS)
        # and scintilla_ohos (shared, ScintillaOHOS with BN_Sci_* C API).
        # The shared library links scintilla_core via --whole-archive so it's
        # self-contained; consumers linking the shared lib get all symbols.
        if self.options.shared:
            self.cpp_info.libs = ["scintilla_ohos"]
        else:
            # Static build: link both — scintilla_ohos.so has BN_Sci_* exports,
            # scintilla_core.a has the core engine. System libs resolve the rest.
            self.cpp_info.libs = ["scintilla_ohos", "scintilla_core"]

        # OHOS system libraries that scintilla links against
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = [
                "native_drawing",
                "hilog_ndk.z",
                "pasteboard",
                "udmf",
                "ohinputmethod",
            ]

        self.cpp_info.set_property("cmake_file_name", "scintilla")
        self.cpp_info.set_property("cmake_target_name", "scintilla::scintilla")

        # Include path for the platform header
        self.cpp_info.includedirs.append("include/scintilla_ohos")

        # SDK library path for linking OHOS system libs
        sdk = self._get_ohos_sdk()
        sdk_lib = os.path.join(sdk, "sysroot", "usr", "lib", "aarch64-linux-ohos")
        self.cpp_info.libdirs.append(sdk_lib)

        # Runtime: OHOS system libs are in the SDK sysroot; add to LD_LIBRARY_PATH
        self.runenv_info.append("LD_LIBRARY_PATH", sdk_lib)
