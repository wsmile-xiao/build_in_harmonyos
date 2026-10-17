#!/usr/bin/env python3
"""Conan recipe for libx11 1.8.13.

X.Org libX11 — the core X11 client-side protocol library.  Pure autotools;
the official X.Org release tarball ships a pre-generated configure script
so no autoreconf is needed at build time.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libx11Conan(ConanFile):
    name = "libx11"
    version = "1.8.13"
    description = "X.Org libX11 — core X11 client-side protocol library"
    license = "X11-distribute-modifications-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libx11"
    url = "https://gitlab.freedesktop.org/xorg/lib/libx11"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libx11 supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("xorgproto/2025.1")
        self.requires("libxau/1.0.11")
        self.requires("libxcb/1.17.0")
        self.requires("xtrans/1.4.0")
        self.requires("xcb-proto/1.17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess from 2018 cannot recognise HarmonyOS; supply triplet.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Disable optional docs / formatting tools.
        tc.configure_args.append("--disable-docs")
        tc.configure_args.append("--without-xmlto")
        tc.configure_args.append("--without-fop")
        tc.configure_args.append("--without-xsltproc")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        configure_path = os.path.join(self.source_folder, "configure")
        if str(self.settings.os) == "OHOS" and os.path.exists(configure_path):
            # E002/HMDFS: autoconf temp dirs with umask 077 fail on OHOS
            # because config.status cannot execute subs1.awk inside them.
            replace_in_file(self, configure_path, "umask 077", "umask 022", strict=False)
            # /bin/bash does not exist on HarmonyOS — replace shebang with the
            # full path to the bash shipped under /data/service/hnp/bin/.
            for pattern in ("#! /bin/sh", "#!/bin/sh", "#! /bin/bash", "#!/bin/bash"):
                replace_in_file(
                    self,
                    configure_path,
                    pattern,
                    "#!/data/service/hnp/bin/bash",
                    strict=False,
                )
            # clang on HarmonyOS predefines `unix` even with -undef -ansi,
            # which makes configure's RAWCPP check fail with "I don't know
            # what to do."  On HarmonyOS, stdin redirect (`< file`) to
            # clang -E produces empty output (platform shell/pipe bug).
            # Fix 1: replace all ` < conftest.$ac_ext` with
            #         ` conftest.$ac_ext` (file arg, not stdin).
            # Fix 2: add a -Uunix elif branch for clang's persistent
            #         `unix` builtin definition.
            with open(configure_path, "r", encoding="utf-8") as fh:
                cfg_text = fh.read()
            cfg_text = cfg_text.replace(
                " < conftest.$ac_ext",
                " conftest.$ac_ext",
            )
            with open(configure_path, "w", encoding="utf-8") as fh:
                fh.write(cfg_text)
            replace_in_file(
                self,
                configure_path,
                (
                    "\telse\n"
                    "\t\tas_fn_error $? \"${RAWCPP} defines unix with or without -undef.  I don't know what to do.\" \"$LINENO\" 5"
                ),
                (
                    "\telif test `${RAWCPP} -undef -Uunix conftest.$ac_ext | grep -c 'unix'` -eq 1 ; then\n"
                    "\t\tRAWCPPFLAGS=\"-undef -Uunix\"\n"
                    "\t\t{ printf \"%s\\n\" \"$as_me:${as_lineno-$LINENO}: result: yes, with -Uunix\" >&5\n"
                    "printf \"%s\\n\" \"yes, with -Uunix\" >&6; }\n"
                    "\telse\n"
                    "\t\tas_fn_error $? \"${RAWCPP} defines unix with or without -undef.  I don't know what to do.\" \"$LINENO\" 5"
                ),
                strict=False,
            )
        # Fix stale .la files in dependency package folders.
        # libtool .la files record absolute paths to other .la files
        # (e.g. libxcb.la → libXau.la → /conan2/p/b/.../p/lib/libXau.la).
        # These build-folder paths are cleaned after `conan create`,
        # so libtool fails with "is not a valid libtool archive".
        # Fix: rewrite dependency_libs to drop non-existent .la refs.
        self._fix_dep_la_files()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # ── Upstream official tests ──
        # libX11 ships a Perl-based compose-check test in nls/.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._patch_libtool_libdir()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _patch_libtool_libdir(self):
        import re

        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            new_content = re.sub(
                r"^libdir='.*'$",
                f"libdir='{lib_dir}'",
                content,
                flags=re.MULTILINE,
            )
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def _fix_dep_la_files(self):
        """Rewrite dependency_libs in dependency .la files to remove
        references to non-existent build-folder .la paths."""
        import re

        for dep in self.dependencies.values():
            dep_lib = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for entry in os.listdir(dep_lib):
                if not entry.endswith(".la"):
                    continue
                la_path = os.path.join(dep_lib, entry)
                with open(la_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                # Remove any .la file references in dependency_libs
                # that point to non-existent paths.
                new_content = content
                for match in re.finditer(
                    r"(\S+\.la)", new_content
                ):
                    la_ref = match.group(1)
                    if not os.path.isfile(la_ref):
                        new_content = new_content.replace(la_ref, "")
                # Clean up any double spaces left behind.
                new_content = re.sub(r"  +", " ", new_content)
                if new_content != content:
                    with open(la_path, "w", encoding="utf-8") as handle:
                        handle.write(new_content)

    def package_info(self):
        self.cpp_info.libs = ["X11"]
        self.cpp_info.set_property("cmake_file_name", "libx11")
        self.cpp_info.set_property("cmake_target_name", "libx11::libx11")
        self.cpp_info.set_property("pkg_config_name", "x11")
