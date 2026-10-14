#!/usr/bin/env python3
"""Conan recipe for the xwininfo 1.1.7 X11 window inspection utility."""

import glob
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XwininfoConan(ConanFile):
    name = "xwininfo"
    version = "1.1.7"
    description = "X11 utility for displaying information about windows"
    license = ("MIT", "MIT-open-group", "HPND-sell-variant")
    homepage = "https://gitlab.freedesktop.org/xorg/app/xwininfo"
    url = homepage
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Match the current X.Org client-tool track. xwininfo uses XCB for the
        # protocol and Xlib headers/library for cursorfont.h and x11 metadata.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libxcb/1.16", transitive_headers=True, transitive_libs=True)
        # Runtime closure for libX11/libxcb on the HarmonyOS device.
        self.requires("libxau/1.0.11", run=True)
        self.requires("libxdmcp/1.1.5", run=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def _dep_dirs(self, name, header_only=False):
        dep = self.dependencies[name]
        include_dir = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
        if header_only:
            return include_dir, None
        lib_dir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        return include_dir, lib_dir

    def generate(self):
        # The package provides a generated configure script, so avoid
        # autoreconf. Preseed PKG_CHECK_MODULES with the exact Conan package
        # paths: this keeps the build independent of any X11 stack on the host.
        toolchain = AutotoolsToolchain(self)
        xcb_include, xcb_lib = self._dep_dirs("libxcb")
        x11_include, x11_lib = self._dep_dirs("libx11")
        proto_include, _ = self._dep_dirs("xorgproto", header_only=True)

        # This release's config.sub recognizes linux-ohos. Pass the native
        # HarmonyOS AArch64 tuple explicitly instead of relying on config.guess.
        toolchain.configure_args.extend(
            [
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
                f"--x-includes={x11_include}",
                f"--x-libraries={x11_lib}",
                "XWININFO_CFLAGS=-I{} -I{} -I{}".format(
                    xcb_include, x11_include, proto_include
                ),
                "XWININFO_LIBS=-L{} -lxcb-shape -lxcb".format(xcb_lib),
                "XLIB_CFLAGS=-I{} -I{}".format(x11_include, proto_include),
                "XLIB_LIBS=-L{} -lX11".format(x11_lib),
            ]
        )
        toolchain.generate()

    def _rewrite_configure(self):
        """Keep generated configure usable when HMFS cannot resolve getcwd()."""
        for configure in glob.glob(os.path.join(self.source_folder, "configure")):
            try:
                with open(configure, "r", encoding="utf-8", errors="ignore") as handle:
                    content = handle.read()
            except OSError:
                continue

            content = content.replace("umask 077", "umask 022")
            pwd_check = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
            if pwd_check in content:
                content = content.replace(
                    pwd_check,
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&',
                    1,
                )
            with open(configure, "w", encoding="utf-8") as handle:
                handle.write(content)

    def build(self):
        # Conan caches on this HMFS device may not support getcwd() through
        # their parent path. Run configure from the accessible build folder.
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder

        self._rewrite_configure()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream registers no test programs in Makefile.am. Run the generated
        # check target anyway; it must succeed with zero discovered tests.
        autotools.make(target="check")
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
            '"framework":"Automake/Meson",'
            '"command":"make check",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,'
            '"skipped":0,'
            '"reason":"Makefile.am registers no TESTS/check_PROGRAMS; meson.build has no test()"}'
        )

    def _sign_elf(self, path):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
            self.run(f'"{sign_tool}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._sign_elf(os.path.join(self.package_folder, "bin", "xwininfo"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
