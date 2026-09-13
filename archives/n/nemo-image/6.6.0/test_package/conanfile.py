#!/usr/bin/env python3
"""Consumer test for nemo-image 6.6.0 (extension module package).

Exercises the packaged artifacts through GModule — the exact mechanism
the Nemo file manager uses to load its extensions (R34 / real-artifact
test):

- Contract smoke (11 assertions): g_module_open() of the extension
  module (verifies the DT_NEEDED chain libnemo-extension.so.1 → glib
  proxy libintl → gtk3 closure), resolution of the three Nemo extension
  entry points (nemo_module_initialize / list_types / shutdown), a real
  nemo_module_list_types() call reporting the converter GObject type,
  the full host-driven type registration (a minimal GTypeModule
  subclass is passed to nemo_module_initialize(); the registered type
  is then asserted to implement both the NemoMenuProvider and
  NemoNameAndDescProvider interfaces via g_type_is_a — AI review P3),
  g_module_open() of the vendored libnemo-extension.so, and resolution
  of the six ABI symbols the module's code actually calls
  (nemo_file_info_get_mime_type / get_uri_scheme / list_copy,
  nemo_menu_item_new, the two provider get_type registrations).

Upstream nemo-image-converter ships no automated tests (N=0, see
MANIFEST.yml); the assertions above are the adapted-side tests carried
by this package.
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class NemoImageTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R33: compiler from the Conan toolchain configuration.  The glib
        # dependency of the tested package provides the cflags/libs via
        # its consumer generators (VirtualRunEnv + glib's own
        # glib-2.0.pc through PkgConfigDeps of the tested package); the
        # test needs glib/gmodule/gobject headers and link libs, which
        # are reachable through the glib requirement declared
        # transitively (gobject is required for the GTypeModule host the
        # conformance check drives, AI review P3).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanException(
                "CC missing from tools.build:compiler_executables")
        glib = self.dependencies["glib"]
        glib_lib = os.path.join(glib.package_folder, "lib")
        glib_inc = os.path.join(glib.package_folder, "include",
                                "glib-2.0")
        glib_inc2 = os.path.join(glib.package_folder, "lib",
                                 "glib-2.0", "include")
        src = os.path.join(self.source_folder, "test_module.c")
        out = os.path.join(self.build_folder, "test_module")
        # env includes conanbuild: the ohos-aarch64 profile buildenv injects
        # LD_LIBRARY_PATH pointing at the OHOS SDK llvm/lib dir, where the
        # linker (lld) finds its runtime dependency libxml2.so.16.  Without
        # it the compile fails on CI workers with
        # "Error loading shared library libxml2.so.16 (needed by lld)"
        # (lld's own RUNPATH is $ORIGIN/../lib, unreachable when lld is
        # invoked as a clang subprocess from a different PATH entry).
        self.run(
            f'"{cc}" "{src}" -o "{out}" '
            f'-I"{glib_inc}" -I"{glib_inc2}" '
            f'-L"{glib_lib}" -lglib-2.0 -lgmodule-2.0 -lgobject-2.0 '
            f'-Wl,-rpath,"{glib_lib}"',
            env=["conanbuild", "conanrun"])

    def test(self):
        package_folder = self.dependencies["nemo-image"].package_folder
        # The test binary resolves libnemo-extension.so through the
        # packaged lib directory (DT_NEEDED soname libnemo-extension.so.1
        # is provided by the lib/libnemo-extension.so.1 symlink).
        libdir = os.path.join(package_folder, "lib")
        if not os.path.isdir(libdir):
            raise ConanException(f"package lacks lib directory: {libdir}")
        module = os.path.join(
            package_folder, "lib", "nemo", "extensions-3.0",
            "libnemo-image-converter.so")
        if not os.path.isfile(module):
            raise ConanException(f"extension module missing: {module}")

        binary = os.path.join(self.build_folder, "test_module")
        # LD_LIBRARY_PATH: packaged lib dir first (vendored
        # libnemo-extension.so.1), then the platform c++ runtime location
        # (gtk's OHOS closure needs libc++_shared.so which the platform
        # ships under /system/lib64).
        self.run(
            f'LD_LIBRARY_PATH="{libdir}:/system/lib64:$LD_LIBRARY_PATH" '
            f'"{binary}" "{package_folder}"',
            env=["conanrun"])
