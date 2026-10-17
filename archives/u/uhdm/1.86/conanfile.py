#!/usr/bin/env python3
"""Conan recipe — uhdm 1.86 (CMake, C++17, OHOS aarch64).

UHDM (Universal Hardware Data Model): C++17 VPI library (libuhdm) plus CLI
tools (uhdm-cmp/uhdm-dump/uhdm-hier/uhdm-lint).

Build-time code generation:
  - capnpc/capnpc-c++ from tool_requires capnproto/1.3.0 generate the model
    C++ sources (UHDM_USE_HOST_CAPNP=ON — upstream third_party/capnproto
    submodule, pinned at 1.1-dev, is NOT built).
  - python3 + orderedmultidict (pip, build-only) run generate.py.

The upstream gtest suites (17 binaries / 43 ctest cases) were executed in the
exploratory phase on OHOS aarch64: 43/43 passed (see notes.md); the shipped
package is tests-free (UHDM_BUILD_TESTS=OFF, third_party/googletest skipped).

R26 not applicable (no system-name library collision). R38 applies: CLI tools
declared in software-level archives/u/uhdm/commands.json. R49 (E524): pip
code-gen deps resolve into the build_folder private prefix, never the shared
machine environment.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save

# Upstream applies target_compile_options(uhdm PUBLIC "SHELL:-include
# uhdm/config.h") so that consumers compile the installed headers with
# uhdm/config.h force-included (defines O_BINARY etc.). CMakeDeps cannot carry
# raw compile options, so this build module re-applies it to the imported
# target after CMakeDeps defines it.
_UHDM_BUILD_MODULES = """\
# Conan build module for uhdm — force-include config.h like upstream does.
if(TARGET uhdm::uhdm)
  target_compile_options(uhdm::uhdm INTERFACE "SHELL:-include uhdm/config.h")
endif()
"""


class UhdmConan(ConanFile):
    name = "uhdm"
    version = "1.86"
    description = "Universal Hardware Data Model — C++17 VPI library and CLI tools"
    license = "Apache-2.0"
    homepage = "https://github.com/chipsalliance/UHDM"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # Static by default: the upstream CMake default (no BUILD_SHARED_LIBS),
    # and on this platform the runtime-robust choice — CMake does not know
    # HarmonyOS (E092) so no SONAME is emitted and a shared libuhdm.so makes
    # the shipped tools unrunnable (DT_NEEDED embeds the relative build path
    # "lib/libuhdm.so", loader fails at runtime). The only dependency
    # (capnproto) is static in the registry anyway.
    default_options = {"shared": False}

    # capnpc-c++ code generator — build-time only, never linked into the package.
    tool_requires = ("capnproto/1.3.0",)

    def requirements(self):
        # capnproto is ALSO a host dependency: the installed generated headers
        # (include/uhdm/uhdm_capnp_*.h) include capnp headers, and a static
        # libuhdm.a references capnp/kj symbols that consumers must link.
        # The tool_requires above covers only the capnpc code generator
        # (standard protobuf/protoc dual-declaration pattern).
        self.requires("capnproto/1.3.0")

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Skip upstream third_party submodules: capnproto comes from the
        # registry (1.1-dev submodule would need the E543-66FA CXX_EXTENSIONS
        # workaround); upstream gtest suites are not part of the package.
        tc.variables["UHDM_USE_HOST_CAPNP"] = True
        tc.variables["UHDM_BUILD_TESTS"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # The UHDM_USE_HOST_CAPNP branch only calls find_package(CapnProto) and
        # never sets CAPNP_EXECUTABLE/CAPNPC_CXX_EXECUTABLE (CMakeLists.txt
        # L57-66); the consumer must provide them. The registry capnproto
        # package is static + fPIC (default options), safe for a shared libuhdm.
        capnp_bin = os.path.join(self.dependencies.build["capnproto"].package_folder, "bin")
        tc.cache_variables["CAPNP_EXECUTABLE"] = os.path.join(capnp_bin, "capnp")
        tc.cache_variables["CAPNPC_CXX_EXECUTABLE"] = os.path.join(capnp_bin, "capnpc-c++")
        # E092 platform gap: CMake does not know HarmonyOS, so the platform
        # defaults that normally enable SONAME are not applied. Verified: a
        # CMAKE_SONAME cache variable (UNINITIALIZED, FORCE) lands in
        # CMakeCache.txt but no -Wl,-soname reaches link.txt, so shared
        # libuhdm.so gets no SONAME and consumers embed the relative build
        # path "lib/libuhdm.so" in DT_NEEDED (relocation failure at
        # runtime). Static is the default (see default_options); for
        # explicit shared=True builds force -soname via linker flags so
        # DT_NEEDED carries the proper basename "libuhdm.so".
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-soname,libuhdm.so"
        tc.generate()

        # R49 (E524): code-gen python deps resolve into the build_folder
        # private prefix — never the shared /usr/local or machine site-packages.
        # save_script registers the script in the "build" scope; conan
        # aggregates it into the conanbuild env that the CMake helper
        # activates by default (configure/build/test).
        buildenv = Environment()
        buildenv.define("PYTHONPATH", os.path.join(self.build_folder, "pydeps"))
        buildenv.vars(self).save_script("conanbuild_pythonpath")

        # E002/E544-E3AD: /tmp is read-only on OHOS — deterministic private tmp.
        tmpenv = Environment()
        tmpenv.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        tmpenv.vars(self).save_script("conanbuild_tmpdir")

    def build(self):
        apply_conandata_patches(self)
        # Build-only python dep of generate.py. The community index
        # (pypi.cnb.cool) is preconfigured by ci/conan/setup.sh; --no-deps +
        # pinned versions is the adb-enhanced/2.8.0 repo precedent.
        pydeps = os.path.join(self.build_folder, "pydeps")
        self.run(
            f'python3 -m pip install --no-deps --target "{pydeps}" '
            f'"orderedmultidict==1.0.2" "six==1.17.0"'
        )
        os.makedirs(os.path.join(self.build_folder, "tmp"), exist_ok=True)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        save(self, os.path.join(self.package_folder, "cmake",
                                "uhdm_build_modules.cmake"),
             _UHDM_BUILD_MODULES)

    def package_info(self):
        self.cpp_info.libs = ["uhdm"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        # A static libuhdm.a defers capnp/kj symbol resolution to the
        # consumer; the generated public headers also include capnp headers.
        # The capnp component carries its own kj edge (link order handled).
        self.cpp_info.requires = ["capnproto::capnp"]
        self.cpp_info.set_property(
            "cmake_build_modules",
            [os.path.join("cmake", "uhdm_build_modules.cmake")])
