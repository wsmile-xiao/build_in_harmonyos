#!/usr/bin/env python3
"""Conan recipe — libiptcdata 1.0.5 (autotools)

libiptcdata is a pure-C library for parsing, viewing, modifying and saving
IPTC (International Press Telecommunications Council) metadata stored in
multimedia files such as JPEG images. The core library has no runtime
dependencies; the optional Python bindings, gtk-doc reference and the `iptc`
command-line tool are disabled here to keep the port to the OHOS core
library only.

Upstream: https://github.com/ianw/libiptcdata  (tag release_1_0_5)
License:  LGPL-2.0-or-later  (COPYING — GNU Library GPL v2)
"""
import glob as _glob
import os as _os

from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibiptcdataConan(ConanFile):
    name = "libiptcdata"
    version = "1.0.5"
    description = "C library for manipulating IPTC metadata stored in multimedia files"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/ianw/libiptcdata"
    url = "https://github.com/ianw/libiptcdata"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The bundled config.guess/sub is 2018-02-24 vintage and does not
        # recognize the `*-linux-ohos` triplet (config.sub: "system `ohos'
        # not recognized"). libiptcdata's configure performs no OHOS-specific
        # probing, so a known-good linux triplet is accepted and produces an
        # identical build. This mirrors the approach used by libconfini/1.16.4
        # and libdatrie/0.2.13 and avoids a config.sub patch entirely.
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # Core library only: disable the optional Python bindings, the gtk-doc
        # reference manual and NLS. The core libiptcdata C library then has no
        # runtime dependencies (i18n.h falls back to identity macros when
        # ENABLE_NLS is undefined), so no gettext/iconv is pulled in.
        tc.configure_args.append("--disable-python")
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--disable-nls")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # The release tarball ships a pre-generated `configure`, so no
        # autoreconf bootstrap is needed.
        #
        # ── OHOS-compatibility modification of upstream configure ──
        # configure's config.status uses `(umask 077 && mktemp -d "./confXXXXXX")`
        # to create a private temp dir, writes subs1.awk into it, then the
        # config.status subshell reads it back. On the OHOS PC HMDFS-backed
        # filesystem, umask 077 makes subs1.awk unreadable to the subshell:
        #   ./config.status: line 837: ./confXXXX/subs1.awk: Permission denied
        #   config.status: error: could not setup config files machinery
        #
        # Five non-source-modification approaches were tried and ALL failed:
        #   1. os.umask(0o022) before configure        — subshell re-sets 077
        #   2. shell `umask 022` before configure      — subshell re-sets 077
        #   3. TMPDIR=dir with chmod 0777              — HMDFS ignores chmod
        #   4. CONFIG_SHELL wrapper (export -f umask) — RC=126 exec failure
        #   5. BASH_ENV umask() function override      — not sourced by config.status
        # The subshell explicitly sets `umask 077`, overriding any inherited
        # or env-level umask. The only fix is to change `umask 077` → `umask 022`
        # in the configure script itself.
        #
        # This is an OHOS-compatibility minimal modification of the upstream
        # build script (configure). It is NOT "zero source modification" —
        # the upstream configure IS modified (in-place text replacement at
        # build time, not a separate .patch file). This is disclosed honestly.
        for _cfg in _glob.glob(_os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # Remove libtool .la archives: they bake in an absolute libdir
        # (/lib under our prefix=/), which misleads downstream libtool into
        # looking for `//lib/libiptcdata.la`. Link info is already provided
        # via the .pc file and cpp_info.
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["iptcdata"]
        self.cpp_info.set_property("cmake_file_name", "libiptcdata")
        self.cpp_info.set_property("cmake_target_name", "libiptcdata::libiptcdata")
        self.cpp_info.set_property("pkg_config_name", "libiptcdata")
