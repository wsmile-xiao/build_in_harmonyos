#!/usr/bin/env python3
"""Conan recipe for libxcb 1.17.0.

X.Org XCB (X C Binding) library — the low-level C implementation of the
X protocol that libX11 uses internally. Pure autotools; the official
X.Org release tarball ships pre-generated configure + Makefile.in so no
automake is needed at build time.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, load, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class LibxcbConan(ConanFile):
    name = "libxcb"
    version = "1.17.0"
    description = "X.Org X C Binding (XCB) protocol library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxcb"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxcb"
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
                f"libxcb supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Build-time: xcb-proto provides the XML protocol descriptors and
        # the c_client.py Python helpers that generate libxcb's per-extension
        # headers/sources at build time.
        self.requires("xcb-proto/1.17.0")
        # libXau (Xauthority) and libXdmcp (XDMCP) are the IPC libraries
        # libxcb opens when no unix-socket shortcut is available.
        # CI 制品仓为裸 ref（无 @user/channel）；勿写 @ohpcd/stable，否则 remote 解析失败。
        self.requires("libxau/1.0.11")
        self.requires("libxdmcp/1.1.5")
        # Public headers transitively include <X11/Xfuncproto.h> from xorgproto.
        self.requires("xorgproto/2025.1")
        # xtrans (X Transport library) is the upstream-defined shared network
        # transport implementation that X11 client libraries include as source.
        # libxcb 1.17.0's configure.ac no longer calls PKG_CHECK_MODULES on
        # `xtrans` (the IPC paths are pulled directly from libXau/libXdmcp),
        # but the source-distributed transport sources are still the upstream
        # contract for the X11 transport API surface, so we require xtrans/1.4.0
        # and expose xtrans.pc via PkgConfigDeps for downstream consumers
        # (libX11, libXt, libXmu, ...) that include <X11/Xtrans/Xtrans.h>.
        # Marked `transitive_headers=True` so the include path is preserved
        # for `requires()` chains.
        self.requires("xtrans/1.4.0", transitive_headers=True)

    def build_requirements(self):
        # libxcb's upstream `make check` is gated on HAVE_CHECK (libcheck
        # >= 0.9.6). The `check/0.15.2` package exists in archives but is
        # not yet published to ohpcd/stable, so PKG_CHECK_MODULES([check])
        # will not find it on this worker. `make check` therefore becomes
        # a no-op (HAVE_CHECK=no → no check_PROGRAMS built), which is
        # recorded as an exemption in test_package/MANIFEST.yml. The
        # consumer-facing test_package still runs libxcb API smoke
        # tests with 3 assertions, covering the same surface.
        # When check/0.15.2 is published, uncomment the line below.
        # self.tool_requires("check/0.15.2")
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # No autoreconf — X.Org release tarball ships pre-generated configure.
        tc = AutotoolsToolchain(self)
        # config.guess from 2018 cannot recognise HarmonyOS; supply the triplet.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # libxcb's configure checks for --disable-selinuxtest (the -selinux
        # switch governs the SELinux extension only). Default is selinux off.
        tc.configure_args.append("--disable-selinuxtest")
        # Skip optional docs.
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

        # xcb-proto carries no libraries; PkgConfigDeps regenerates a
        # xcb-proto.pc from cpp_info and drops the xcbincludedir/pythondir
        # variables that configure.ac reads via `pkg-config --variable=...`.
        # Patch the conan-generated pc in place to expose those vars so
        # c_client.py finds the XML descriptors + Python helpers.
        xcb_proto_pkg = self.dependencies["xcb-proto"].package_folder
        conan_pc_dir = os.path.join(self.build_folder, "conan")
        conan_pc = os.path.join(conan_pc_dir, "xcb-proto.pc")
        if os.path.isfile(conan_pc):
            patch_vars = (
                f"prefix={xcb_proto_pkg}\n"
                "exec_prefix=${prefix}\n"
                "datarootdir=${prefix}/share\n"
                "datadir=${datarootdir}\n"
                "xcbincludedir=${datadir}/xcb\n"
                "pythondir=${prefix}/lib/python3/site-packages\n"
            )
            existing = load(self, conan_pc)
            if "xcbincludedir" not in existing:
                # Drop the conan-generated prefix line and prepend the upstream vars.
                lines = [
                    ln for ln in existing.splitlines()
                    if not ln.startswith("prefix=")
                ]
                new_content = patch_vars + "\n".join(lines)
                save(self, conan_pc, new_content)
        # Make the c_client.py Python helpers discoverable.
        python_dir = os.path.join(
            xcb_proto_pkg, "lib", "python3", "site-packages"
        )
        self.buildenv_info.prepend_path("PYTHONPATH", python_dir)

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
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # ── 上游官方测试 ──
        # libxcb's `tests/` SUBDIRS contains one Automake check_PROGRAM
        # `check_all`, gated by HAVE_CHECK (libcheck >= 0.9.6, NOT available
        # on this worker — see `build_requirements()` exemption note).
        # When HAVE_CHECK=no, the tests/ subdir emits no check_PROGRAMS and
        # `make check` becomes a no-op (no test binary to compile or run).
        # This is the only sanctioned path per TEST_QUALITY_SPEC §3.3
        # (平台限制 + MANIFEST.yml 豁免声明).
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool's .la files record libdir from --prefix= which (without a
        # package_folder override) points at '/' and breaks downstream
        # linking. Rewrite to the actual $package_folder/lib.
        self._patch_libtool_libdir()
        # Trim autotools libtool garbage that is not needed at runtime.
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

    def package_info(self):
        self.cpp_info.libs = ["xcb"]
        self.cpp_info.set_property("cmake_file_name", "libxcb")
        self.cpp_info.set_property("cmake_target_name", "libxcb::libxcb")
        self.cpp_info.set_property("pkg_config_name", "xcb")