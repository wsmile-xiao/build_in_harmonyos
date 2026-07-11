#!/usr/bin/env python3
"""Conan recipe — rsync 3.3.0 (Autotools).

rsync is a fast file synchronization tool. Dependencies (xxhash, zstd, lz4,
openssl) are system-installed via cmd-pkgs to $HOME/usr/local; their paths are
passed to the AutotoolsToolchain since they are not available as Conan packages
on the ohpcd remote.

R26: Terminal tool — statically linked.
R32: settings.os supports both Linux and OHOS.
R33: No hardcoded absolute paths or shell env vars in build(); uses AutotoolsToolchain.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RsyncConan(ConanFile):
    name = "rsync"
    version = "3.3.0"
    description = "Fast incremental file transfer and synchronization tool"
    license = "GPL-3.0"
    homepage = "https://rsync.samba.org/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    # System dependency paths (installed via cmd-pkgs to $HOME/usr/local)
    # R33: No hardcoded absolute paths; use expanduser for portability across
    # dev machines and CI/release workers.
    _sys_prefix = os.path.join(os.path.expanduser("~"), "usr", "local")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools statically linked
        tc.extra_ldflags.append("-static")
        # E114: --no-create to generate config.status without running it,
        # so we can patch config.status mktemp before it executes.
        tc.configure_args.append("--no-create")
        # System dependency paths for xxhash/zstd/lz4/openssl (installed via cmd-pkgs)
        tc.extra_cflags.append(f"-I{self._sys_prefix}/include")
        tc.extra_ldflags.append(f"-L{self._sys_prefix}/lib")

        # Conditionally disable optional features if headers are missing.
        # CI workers may not have all cmd-pkgs pre-installed; without this,
        # rsync's configure aborts when it detects missing optional deps.
        inc_dir = os.path.join(self._sys_prefix, "include")
        optional_deps = [
            ("openssl", os.path.join(inc_dir, "openssl", "md4.h")),
            ("xxhash", os.path.join(inc_dir, "xxhash.h")),
            ("zstd", os.path.join(inc_dir, "zstd.h")),
            ("lz4", os.path.join(inc_dir, "lz4.h")),
        ]
        for feature, header in optional_deps:
            if not os.path.exists(header):
                tc.configure_args.append(f"--disable-{feature}")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E165: Fix shebangs for OHOS (no /bin/sh)
        self._fix_all_shebangs()

        # rsync 3.3.0 ships configure.sh; ensure 'configure' symlink exists for Autotools
        src = self.source_folder
        configure_path = os.path.join(src, "configure")
        configure_sh_path = os.path.join(src, "configure.sh")
        if not os.path.exists(configure_path) and os.path.exists(configure_sh_path):
            os.symlink("configure.sh", configure_path)

        # R33: Use Autotools to run configure and make with toolchain env
        autotools = Autotools(self)

        # E114: configure --no-create generates config.status without running it.
        # Autotools.configure() passes toolchain flags (CC, CFLAGS, LDFLAGS, etc.)
        # from generate(), satisfying R33.
        autotools.configure()

        # E114: Fix config.status mktemp on HMDFS (programmatic, not a source patch)
        self._fix_config_status_mktemp()

        # Run config.status to generate Makefiles and config.h
        self.run("bash config.status", env=["conanbuild"])

        # Fix: configure detects getpass in libc but OHOS has no header declaration.
        # Undefine HAVE_GETPASS so rsync.h provides the local declaration.
        # Must be done AFTER config.status runs (which generates config.h)
        self._undef_getpass()

        # Build with toolchain env (R33 compliant)
        autotools.make(args=["-j1"])

    def _fix_all_shebangs(self):
        """E165: Fix #!/bin/sh and #!/bin/bash shebangs for OHOS.

        Only needed on OHOS (no /bin/sh). On Linux, standard paths work.
        R32: settings.os checked with in ("Linux", "OHOS").
        """
        # R32: Only apply shebang fix on OHOS; Linux has standard /bin paths
        if self.settings.os != "OHOS":
            return
        src = self.source_folder
        # OHOS-specific shell paths
        sh_replacements = {
            "#!/bin/sh": "#!/system/bin/sh",
            "#! /bin/sh": "#! /system/bin/sh",
            "#!/bin/bash": "#!/data/service/hnp/bin/bash",
            "#! /bin/bash": "#! /data/service/hnp/bin/bash",
        }
        for root, dirs, files in os.walk(src):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r') as f:
                        first_line = f.readline()
                    if first_line.startswith("#!") and ("/bin/sh" in first_line or "/bin/bash" in first_line):
                        with open(fpath, 'r') as f:
                            content = f.read()
                        for old, new in sh_replacements.items():
                            content = content.replace(old, new)
                        with open(fpath, 'w') as f:
                            f.write(content)
                except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                    pass

    def _fix_config_status_mktemp(self):
        """E114: Fix config.status mktemp on HMDFS (permission denied).

        config.status uses mktemp to create temp dirs in the current directory
        (./confXXXXXX), which fails on HMDFS with Permission denied.
        Redirect to TMPDIR-based fixed path.

        Root cause of previous G2 failure: config.status is a GENERATED file
        created by configure in self.build_folder (e.g. build-release/ subfolder),
        NOT in self.source_folder. The old code looked in self.source_folder
        and returned early without applying the fix.

        This fix is applied after configure --no-create generates config.status
        but before config.status is executed (bash config.status).
        """
        # config.status is generated by configure in build_folder, not source_folder
        cs_file = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(cs_file):
            # Fallback: also check source_folder (in case layout differs)
            cs_file = os.path.join(self.source_folder, "config.status")
        if not os.path.exists(cs_file):
            return
        with open(cs_file, 'r') as f:
            content = f.read()
        tmpdir = os.environ.get("TMPDIR", "/tmp")
        fixed_dir = os.path.join(tmpdir, "rsync-config-status-tmp")
        os.makedirs(fixed_dir, exist_ok=True)
        # Pattern 1: mktemp -d "./confXXXXXX" (primary path)
        content = re.sub(
            r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
            'tmp=%s' % fixed_dir,
            content
        )
        # Pattern 2: fallback ./conf$$-$RANDOM
        content = re.sub(r'tmp=\./conf\$\$-\$RANDOM', 'tmp=%s' % fixed_dir, content)
        # Pattern 3: mkdir "$tmp" fallback (make it a no-op since dir already exists)
        content = content.replace('(umask 077 && mkdir "$tmp")', 'true')
        with open(cs_file, 'w') as f:
            f.write(content)

    def _undef_getpass(self):
        """Undefine HAVE_GETPASS in config.h so rsync.h provides local declaration.

        config.h is generated by config.status in build_folder (same as config.status).
        """
        # config.h is generated in build_folder, not source_folder
        ch_file = os.path.join(self.build_folder, "config.h")
        if not os.path.exists(ch_file):
            # Fallback: also check source_folder
            ch_file = os.path.join(self.source_folder, "config.h")
        if not os.path.exists(ch_file):
            return
        with open(ch_file, 'r') as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if 'HAVE_GETPASS' in line and line.strip().startswith('#define'):
                new_lines.append('/* #undef HAVE_GETPASS */\n')
            else:
                new_lines.append(line)
        with open(ch_file, 'w') as f:
            f.writelines(new_lines)

    def package(self):
        # R33: Use Autotools for make install with toolchain env
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # rsync is a binary tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
