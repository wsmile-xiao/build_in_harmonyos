#!/usr/bin/env python3
"""Conan recipe — ipsumdump 1.86

Summarizes TCP/IP dump files into a self-describing ASCII format.
Homepage: https://read.seas.harvard.edu/~kohler/ipsumdump/
License: MIT (Click license — BSD-like)
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import re
import stat


class IpsumdumpConan(ConanFile):
    name = "ipsumdump"
    version = "1.86"
    description = "Summarizes TCP/IP dump files into a self-describing ASCII format"
    license = "MIT"
    homepage = "https://read.seas.harvard.edu/~kohler/ipsumdump/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def requirements(self):
        # libpcap is already published in archive
        self.requires("libpcap/1.10.6")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # OHOS uses libc++, not libstdc++. Prevent -stdlib=libstdc++ from being
        # injected by the profile's compiler.libcxx setting.
        tc.extra_cxxflags.append("-stdlib=libc++")
        tc.generate()

    def _patch_ioc_dirshift(self):
        """Add _IOC_DIRSHIFT and related macros (may not be defined in all environments)."""
        # <sys/ioctl.h> doesn't always define _IOC_DIRSHIFT/_IOC_NONE/_IOC_READ/
        # _IOC_WRITE. Fix: add defines in llrpc.h before they're used.
        llrpc_h = os.path.join(self.source_folder, "libclick-2.1", "include", "click", "llrpc.h")
        if os.path.exists(llrpc_h):
            with open(llrpc_h) as fh:
                content = fh.read()
            if "#ifndef _IOC_DIRSHIFT" not in content:
                defines = (
                    "\n"
                    "/* Compat: _IOC_DIRSHIFT may not be defined by system headers */\n"
                    "#if !defined(_IOC_DIRSHIFT)\n"
                    "# define _IOC_NONE\t0U\n"
                    "# define _IOC_WRITE\t1U\n"
                    "# define _IOC_READ\t2U\n"
                    "# define _IOC_DIRSHIFT\t30\n"
                    "#endif\n\n"
                )
                # Insert after the include guard (#define CLICK_LLRPC_H)
                insert_point = "#define CLICK_LLRPC_H\n"
                if insert_point in content:
                    content = content.replace(insert_point, insert_point + defines, 1)
                    with open(llrpc_h, "w") as fh:
                        fh.write(content)
                    self.output.info("Patched llrpc.h: added _IOC_DIRSHIFT defines")
                else:
                    self.output.warning("Could not find insert point in llrpc.h")

    def _patch_config_guess_sub(self):
        """Patch config.guess and config.sub in libclick-2.1 for OHOS recognition."""
        click_dir = os.path.join(self.source_folder, "libclick-2.1")
        cg_file = os.path.join(click_dir, "config.guess")
        cs_file = os.path.join(click_dir, "config.sub")

        # config.guess: insert HarmonyOS case before NetBSD
        if os.path.exists(cg_file):
            with open(cg_file) as f:
                content = f.read()
            if "HarmonyOS" not in content:
                harmonyos_block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) echo aarch64-unknown-linux-ohos; exit ;;\n"
                    "\t    armv7*|armv8*) echo arm-unknown-linux-ohos; exit ;;\n"
                    "\t    x86_64|amd64)  echo x86_64-unknown-linux-ohos; exit ;;\n"
                    "\t    i?86)          echo i686-unknown-linux-ohos; exit ;;\n"
                    "\t    *)             echo ${UNAME_MACHINE}-unknown-linux-ohos; exit ;;\n"
                    "\tesac\n"
                    "\t;;\n\n"
                )
                content = content.replace(
                    "    *:NetBSD:*:*)",
                    harmonyos_block + "    *:NetBSD:*:*)",
                    1
                )
                with open(cg_file, "w") as f:
                    f.write(content)
                self.output.info("Patched config.guess for HarmonyOS")
                # Restore executable bit
                st = os.stat(cg_file)
                os.chmod(cg_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            else:
                self.output.info("config.guess already has HarmonyOS support")

        # config.sub: add ohos support in 4 places (each independent)
        if os.path.exists(cs_file):
            with open(cs_file) as f:
                content = f.read()
            c = content  # work on copy
            n_patches = 0

            # 1. maybe_os line
            if "linux-ohos* | ohos* | linux-uclibc*" not in c:
                c = c.replace(
                    "  linux-uclibc* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* |",
                    "  linux-ohos* | ohos* | linux-uclibc* | uclinux-uclibc* | uclinux-gnu* | kfreebsd*-gnu* |",
                )
                n_patches += 1

            # 2. aarch64 machine type (basic list)
            if "| aarch64 |" not in c:
                c = c.replace(
                    "| arc | arm | arm[bl]e | arme[lb] | armv[2345] | armv[345][lb] | avr | avr32",
                    "| aarch64 | aarch64_be | arc | arm | arm[bl]e | arme[lb] | arm64 | armv[2345] | armv[345][lb] | avr | avr32",
                )
                n_patches += 1

            # 2b. aarch64 machine type (pattern list)
            if "| aarch64-* |" not in c:
                c = c.replace(
                    "| arm-*  | armbe-* | armle-* | armeb-* | armv*-*",
                    "| aarch64-* | aarch64_be-* | arm-* | arm64-* | armbe-* | armle-* | armeb-* | armv*-*",
                )
                n_patches += 1

            # 3. OS validity list
            if "-ohos* | -gnu* | -bsd*" not in c:
                c = c.replace(
                    "\t-gnu* | -bsd* | -mach* | -minix* | -genix* | -ultrix* | -irix* \\",
                    "\t-ohos* | -gnu* | -bsd* | -mach* | -minix* | -genix* | -ultrix* | -irix* \\",
                )
                n_patches += 1

            # 4. kernel-os list
            if "| -linux-ohos* | -ohos* \\" not in c:
                c = c.replace(
                    "| -linux-newlib* | -linux-uclibc* \\",
                    "| -linux-newlib* | -linux-uclibc* | -linux-ohos* | -ohos* \\",
                )
                n_patches += 1

            if n_patches > 0:
                with open(cs_file, "w") as f:
                    f.write(c)
                st = os.stat(cs_file)
                os.chmod(cs_file, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                self.output.info(f"Patched config.sub for HarmonyOS ({n_patches} changes)")
            else:
                self.output.info("config.sub already has HarmonyOS support")

    def _patch_siocgstamp(self):
        """Add SIOCGSTAMP fallback define for OHOS."""
        fdev_file = os.path.join(self.source_folder, "src", "fromdevice.cc")
        if os.path.exists(fdev_file):
            with open(fdev_file) as f:
                content = f.read()
            if "SIOCGSTAMP" not in content or "define SIOCGSTAMP" not in content:
                # Insert after the sys/ioctl.h block
                insert_point = "# include <sys/ioccom.h>\n#endif\n"
                siocgstamp_block = (
                    "# include <sys/ioccom.h>\n#endif\n"
                    "\n"
                    "#ifndef SIOCGSTAMP\n"
                    "# define SIOCGSTAMP 0x80108906\n"
                    "#endif\n"
                )
                content = content.replace(insert_point, siocgstamp_block, 1)
                with open(fdev_file, "w") as f:
                    f.write(content)
                self.output.info("Added SIOCGSTAMP fallback define")
            else:
                self.output.info("SIOCGSTAMP already defined")

    def _patch_umask(self):
        """Fix umask 077 → 022 in configure for HMDFS compat (E002/E011)."""
        configure_file = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_file):
            with open(configure_file) as f:
                content = f.read()
            # Fix the mktemp umask pattern and mkdir umask pattern
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(configure_file, "w") as f:
                    f.write(content)
                self.output.info("Patched configure: umask 077→022 for HMDFS")
        # Also fix libclick configure
        lc_configure = os.path.join(self.source_folder, "libclick-2.1", "configure")
        if os.path.exists(lc_configure):
            with open(lc_configure) as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(lc_configure, "w") as f:
                    f.write(content)
                self.output.info("Patched libclick configure: umask 077→022")

    def _patch_install_man(self):
        """Disable install-man target in Makefile.in to avoid //share/man issue.

        Uses line-anchored regex to match the Makefile target 'install-man:'
        rather than a global substring replace.  Idempotent: once the sentinel
        '@echo man pages installed by recipe' is present, subsequent calls are
        a no-op.
        """
        mf = os.path.join(self.source_folder, "Makefile.in")
        if not os.path.exists(mf):
            return
        with open(mf) as f:
            content = f.read()
        # Idempotency guard: if already patched, skip.
        if "@echo man pages installed by recipe" in content:
            self.output.info("_patch_install_man already applied, skipping")
            return
        # Replace the 'install-man:' target with a no-op target, keeping a
        # disabled variant so that 'install: ... install-man' does not fail.
        content = re.sub(
            r"^install-man:",
            "install-man:\n\t@echo man pages installed by recipe\ninstall-man-disabled:",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        with open(mf, "w") as f:
            f.write(content)
        self.output.info("Patched Makefile.in: disabled install-man target")

    def build(self):
        # Apply all OHOS patches (inline: static patches don't work with apply_conandata_patches)
        self._patch_config_guess_sub()
        self._patch_siocgstamp()
        self._patch_umask()
        self._patch_ioc_dirshift()
        self._patch_install_man()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        # Manual packaging: copy binaries from build dir (make install fails on
        # man page path under OHOS HMDFS: //share/man/man1 Permission denied)
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for binary in ["ipsumdump", "ipaggcreate", "ipaggmanip"]:
            src = os.path.join(self.build_folder, "src", binary)
            if os.path.exists(src):
                copy(self, binary, src=os.path.join(self.build_folder, "src"),
                     dst=bindir)
        # Install man pages
        mandir = os.path.join(self.package_folder, "share", "man", "man1")
        os.makedirs(mandir, exist_ok=True)
        copy(self, "*.1", src=self.source_folder, dst=mandir)

    def package_info(self):
        self.cpp_info.libs = []
        # For application package: expose bin directory so test_package can find binaries
        self.cpp_info.bindirs = ["bin"]
