#!/usr/bin/env python3
"""Conan recipe — vvenc 1.14.0 (Fraunhofer Versatile Video Encoder, H.266/VVC).

OpenHarmony / HarmonyOS PC (aarch64) adaptation.

Three platform findings drive the recipe, all reproduced with minimal
reproducers on an OHOS PC worker:

* E092 — CMake has no Platform/HarmonyOS module.  The OHOS-adapted Conan maps
  ``os=OHOS`` to ``CMAKE_SYSTEM_NAME=HarmonyOS`` when build and host profiles
  differ, and the worker itself also reports ``CMAKE_HOST_SYSTEM_NAME=HarmonyOS``
  (``uname`` -> HarmonyOS), so ``CMAKE_SYSTEM_NAME`` resolves to an unknown
  platform.  The Linux platform semantics are then lost: no ``-Wl,-soname``
  flag, no rpath base, and dependents record build-tree relative paths in
  ``DT_NEEDED``.  Pinning ``CMAKE_SYSTEM_NAME=Linux`` in the preset restores
  ``Platform/Linux.cmake``.  The value goes through ``cache_variables`` so that
  Conan emits it as a ``-D`` argument; the toolchain's generic-system block is
  guarded by ``if(NOT DEFINED CMAKE_SYSTEM_NAME)`` and therefore no longer
  injects ``HarmonyOS``.
* E050 — HMDFS cannot reliably create or follow symbolic links.  CMake
  realises a versioned shared library with a symlink chain
  (``libvvenc.so -> libvvenc.so.<abi> -> libvvenc.so.<abi>.<patch>``); the
  exec-time loader then fails to resolve ``DT_NEEDED="libvvenc.so.1.14"`` for
  every consumer ("Error loading shared library libvvenc.so.1.14"), while
  in-process ``dlopen`` still succeeds.  ``VVENC_ENABLE_VERSIONED_SONAME=OFF``
  emits a single unversioned real file whose SONAME is ``libvvenc.so``.
* E504 — the OHOS loader rejects an ELF whose embedded code signature no longer
  matches its bytes.  The OHOS clang/lld toolchain signs every artifact it
  links (adding ``.note.ohos.ident`` and a ``.codesign`` section), but CMake's
  install step rewrites ``DT_RUNPATH`` in place: a single ``RPATH_CHANGE`` of
  21 bytes in ``.dynstr``.  That invalidates the signature, and the installed
  ``libvvenc.so`` then fails for every consumer with
  ``Error loading shared library libvvenc.so: Permission denied`` (EACCES) --
  ``ctypes``/``dlopen`` reports exactly the same.  Note the build tree copy
  stays loadable, which is why the in-build ``ctest`` suite passes while
  ``test_package`` fails.  vvenc sets ``CMAKE_INSTALL_RPATH`` itself
  (``$ORIGIN`` and ``$ORIGIN/../lib``) whenever shared libraries are enabled,
  so the rewrite always happens.  Building the binaries with the install RPATH
  already in place (``CMAKE_BUILD_WITH_INSTALL_RPATH=ON``) makes CMake find the
  RPATH already correct at install time and skip the rewrite entirely: the
  installed file is byte-identical to the linked one, the signature stays
  valid, and no external signing tool is required.  This keeps upstream's
  relocatable-RPATH intent, unlike ``CMAKE_SKIP_INSTALL_RPATH`` which would
  drop it.  Verified: build-tree and installed checksums match, and both
  ``CDLL`` and ``vvencapp --help`` succeed from the installed prefix.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class VvencConan(ConanFile):
    name = "vvenc"
    version = "1.14.0"
    description = ("vvenc is the Fraunhofer Versatile Video Encoder: an H.266/VVC "
                   "encoder library (libvvenc) plus the vvencapp and vvencFFapp "
                   "command line tools")
    license = "BSD-3-Clause-Clear"
    homepage = "https://github.com/fraunhoferhhi/vvenc"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"

        # E092: CMake ships no Platform/HarmonyOS module; force the Linux branch
        # so the platform semantics (SONAME flag, rpath base, CMAKE_UNIX) are
        # available.  Emitted as -D through the preset, which makes the
        # toolchain's guarded generic-system block skip its HarmonyOS injection.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # E050: emit one unversioned real artifact instead of a symlink chain
        # that HMDFS cannot follow.
        tc.cache_variables["VVENC_ENABLE_VERSIONED_SONAME"] = "OFF"

        # Keep the artifacts (lib/, bin/) inside the build tree instead of
        # writing them next to the sources (upstream default is ON).
        tc.cache_variables["VVENC_TOPLEVEL_OUTPUT_DIRS"] = "OFF"

        tc.cache_variables["VVENC_ENABLE_INSTALL"] = "ON"
        # Install vvencapp as well as the full-feature vvencFFapp.
        tc.cache_variables["VVENC_INSTALL_FULLFEATURE_APP"] = "ON"

        # E504: upstream sets CMAKE_INSTALL_RPATH ($ORIGIN and $ORIGIN/../lib)
        # for shared builds, so CMake would otherwise rewrite DT_RUNPATH in
        # place at install time.  That single in-place edit invalidates the
        # HarmonyOS code signature that clang/lld embedded when it linked the
        # library, and the OHOS loader then refuses the installed .so with
        # EACCES.  Linking against the install RPATH up front makes the install
        # step a plain copy, so the signature survives and the artifact stays
        # loadable.  Using the install RPATH (rather than skipping it) keeps
        # the library relocatable for downstream consumers.
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "ON"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream ships an official ctest suite (test/vvenclibtest,
        # test/vvencinterfacetest and the vvencapp/vvencFFapp tool tests).
        # Run it here so that conan create exercises the upstream tests.
        if not self.conf.get("tools.build:skip_test", default=False, check_type=bool):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["vvenc"]
        # The package ships the vvencapp and vvencFFapp command line tools.
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
