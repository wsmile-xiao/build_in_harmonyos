#!/usr/bin/env python3
"""Conan recipe for the EROFS userspace utilities."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ErofsUtilsConan(ConanFile):
    name = "erofs-utils"
    version = "1.9.3"
    description = "Userspace tools for the EROFS filesystem"
    license = "GPL-2.0-or-later AND MIT"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/xiang/erofs-utils.git"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 1.9.3 tarball does not contain pre-generated autotools files
        # (unlike 1.9.2). Bootstrap with autoreconf -fi in build().
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _patch_ohos_triple(self, path):
        """Add HarmonyOS recognition to a config.guess/config.sub so configure
        does not need --build/--host (E007)."""
        import re
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        original = data
        if "config.guess" in os.path.basename(path):
            if "__OHOS__" not in data and "#if defined(__ANDROID__)" in data:
                data = data.replace(
                    "#if defined(__ANDROID__)\n    LIBC=android",
                    "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    1,
                )
            if "HarmonyOS" not in data and "    *:NetBSD:*:*)" in data:
                block = (
                    '    *:HarmonyOS:*:*)\n'
                    '\tcase "$UNAME_MACHINE" in\n'
                    '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                    '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                    '\tesac\n'
                    '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                    '\t;;\n\n'
                    '    *:NetBSD:*:*)'
                )
                data = data.replace("    *:NetBSD:*:*)", block, 1)
        else:
            if "ohos*" not in data and "gnu* | android*" in data:
                data = data.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            if "linux-ohos" not in data:
                data, _ = re.subn(
                    r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', data
                )
        if data != original:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            self.output.info(f"E007: patched {os.path.basename(path)} for OHOS")

    def _drop_umask_077(self, path):
        """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
        creates a drwx--S--- temp dir that is not writable even by its owner.
        Replace every `umask 077` occurrence (any quoting/spacing variant) with
        `umask 022` so config.status can create its temp dir."""
        import re
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        pattern = re.compile(r'umask\s+077')
        data, count = pattern.subn('umask 022', data)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        if count:
            self.output.info(f"E114: replaced {count} umask 077 -> 022 in {path}")

    def _fix_config_status(self, build_folder):
        """Fix config.status: remove umask 077 for temp dir (HMDFS permission).

        config.status is a generated file (not in source tarball), so it
        cannot be patched via conandata.yml. This fix must be applied inline
        after configure generates it.
        """
        path = os.path.join(build_folder, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null'
        )
        save(self, path, content)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-multithreading",
                "--disable-lz4",
                "--disable-lzma",
                "--without-zlib",
                "--without-libdeflate",
                "--without-libzstd",
                "--without-qpl",
                "--without-xxhash",
                "--without-libcurl",
                "--without-openssl",
                "--without-libxml2",
                "--without-json-c",
                "--without-libnl3",
                "--disable-ublk",
                "--disable-s3",
                "--disable-oci",
                "--disable-fanotify",
                "--disable-fuse",
                "--without-uuid",
                "--without-selinux",
            ]
        )
        # E007: do not pass --build/--host/--target to configure; instead patch
        # config.guess/config.sub in build() to recognize HarmonyOS natively.
        tc.generate()

    def build(self):
        # 1.9.3 tarball lacks pre-generated autotools files; bootstrap now.
        # E114: umask 000 needed for config.status temp dir creation on HMDFS.
        os.umask(0)
        self.run("umask 000 && autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        if str(self.settings.os) == "OHOS":
            # Patch config.guess/config.sub to recognize OHOS natively (E007 compliant)
            for fn in ["config/config.guess", "config/config.sub"]:
                p = os.path.join(self.source_folder, fn)
                if os.path.isfile(p):
                    self._patch_ohos_triple(p)
            self._drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        if not os.path.isfile(os.path.join(self.build_folder, "config.status")) \
                or not os.path.isfile(os.path.join(self.build_folder, "Makefile")):
            raise ConanInvalidConfiguration(
                "erofs-utils configure failed: config.status/Makefile missing. "
                "Check config.log in the build folder."
            )
        if str(self.settings.os) == "OHOS":
            # Fix config.status (generated file - cannot be a source patch)
            self._fix_config_status(self.build_folder)
            # If config.status failed during configure, re-run it manually
            cs_path = os.path.join(self.build_folder, "config.status")
            mk_path = os.path.join(self.build_folder, "Makefile")
            if os.path.exists(cs_path) and not os.path.exists(mk_path):
                self._fix_config_status(self.build_folder)
                self.run("cd " + self.build_folder + " && bash config.status")
        # E074: parallel make hits HMDFS jobserver fifo EPERM;
        # also disable autotools regeneration (ACLOCAL/AUTOMAKE/AUTOCONF=true)
        # to prevent make from re-running configure which would produce an
        # unpatched config.status (E114 HMDFS Permission denied).
        autotools.make(args=["-j1", "ACLOCAL=true", "AUTOMAKE=true", "AUTOCONF=true", "AUTOHEADER=true"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["ACLOCAL=true", "AUTOMAKE=true", "AUTOCONF=true", "AUTOHEADER=true"])
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = []
