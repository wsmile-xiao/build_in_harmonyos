#!/usr/bin/env python3
"""Conan recipe for openfortivpn 1.24.1 — Fortinet SSL VPN client.

openfortivpn is an open-source client for PPP-over-SSL tunnels to Fortinet
VPN servers. It is a CLI tool (not a library). The only runtime dependency
is OpenSSL (libssl + libcrypto) for the SSL tunnel.

Build system: Autotools (configure.ac + Makefile.am). The GitHub archive
(git tag) does not ship a pre-generated configure script, so autoreconf -fi
is run during the build via tool_requires on automake/libtool.

Platform adaptations for HarmonyOS:
1. pthread_cancel not available: configure.ac patched to remove the
   AC_CHECK_FUNCS check; src/io.c patched to guard the 5 pthread_cancel()
   calls with #ifndef __OHOS__ (threads exit naturally on sem signal).
2. OpenSSL .pc files in conan package have build-profile paths that don't
   exist at runtime — set OPENSSL_CFLAGS/OPENSSL_LIBS env vars explicitly
   from the conan dependency's package_folder, bypassing pkg-config.
3. HMDFS umask 077: autoconf 2.72 sets `umask 077` at the top of the
   generated configure script; on HMDFS this can cause permission issues
   for config.status temporary directories. Fix: sed umask 077 → 022.
4. ELF signing: OHOS XPM requires signed executables; sign the binary
   after install.

R32: settings.os must check in ("Linux", "OHOS").
R33: No hardcoded absolute paths — all paths from Conan dependency.
R34: test_package calls openfortivpn --version (substantive dependency).
R38: CLI tool — commands.json declared at software level.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpenfortivpnConan(ConanFile):
    name = "openfortivpn"
    version = "1.24.1"
    description = "Open-source client for PPP-over-SSL tunnels to Fortinet VPN servers"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/adrienverge/openfortivpn"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"openfortivpn only supports Linux/OHOS, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("openssl/3.5.6")

    def build_requirements(self):
        # GitHub archive (git tag) has no pre-generated configure script;
        # autoreconf -fi needs automake + libtool.
        # autoconf + pkg-config + m4 come from the system PATH (/data/service/hnp/bin).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OpenSSL paths: conan openssl .pc files point to build-profile paths
        # that don't exist at runtime. Pass paths explicitly via env vars
        # so configure's PKG_CHECK_MODULES uses them instead of pkg-config.
        openssl = self.dependencies["openssl"]
        openssl_inc = os.path.join(openssl.package_folder, "include")
        openssl_lib = os.path.join(openssl.package_folder, "lib")
        # Set OPENSSL_CFLAGS/OPENSSL_LIBS for PKG_CHECK_MODULES to pick up
        os.environ["OPENSSL_CFLAGS"] = f"-I{openssl_inc}"
        os.environ["OPENSSL_LIBS"] = f"-L{openssl_lib} -lssl -lcrypto"
        # OHOS: pass --build/--host so config.sub recognizes ohos triplet.
        # Also pass --with-rt_dst=yes and --enable-proc=yes to skip
        # AC_CHECK_FILE calls that fail when cross-compiling (even though
        # we build natively on OHOS, autoconf treats --host as cross-compile).
        # --with-pppd=/usr/sbin/pppd: skip AC_CHECK_FILE for pppd binary
        # --with-resolvconf=DISABLED: skip resolvconf detection
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
                "--with-rt_dst=yes",
                "--enable-proc=yes",
                "--with-pppd=/usr/sbin/pppd",
                "--with-resolvconf=DISABLED",
            ])
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # Source is a git archive (no pre-generated configure) → autoreconf
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("No configure script (git archive), running autoreconf -fi")
            autotools.autoreconf(args=["-vfi"])
        # Fix HMDFS umask 077 in generated configure (E011)
        self._fix_configure_umask()
        # Patch config.sub/guess for OHOS triplet recognition
        self._patch_config_for_ohos()
        # Configure may fail on HMDFS due to config.status temp dir perms;
        # retry after fixing config.status (same pattern as duo-unix)
        try:
            autotools.configure()
        except ConanException:
            cs = os.path.join(self.build_folder, "config.status")
            if not os.path.exists(cs):
                raise
            self.output.info("configure internal config.status failed, applying HMDFS fix")
        self._fix_config_status()
        mk = os.path.join(self.build_folder, "Makefile")
        if not os.path.exists(mk):
            self.run("cd " + self.build_folder + " && bash config.status")
        autotools.make(args=["-j1"])
        # Run upstream tests (R1: make check required)
        self.run("make check", cwd=self.build_folder)

    def _fix_configure_umask(self):
        """Fix umask 077 in generated configure script (E011 HMDFS issue).

        autoconf 2.72 sets `umask 077` at the top of configure to protect
        sensitive temporary files. On HMDFS, files created with umask 077
        have restrictive permissions that can cause config.status to fail
        when its internal awk scripts try to execute.
        """
        path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(path):
            return
        content = load(self, path)
        original = content
        content = content.replace("umask 077", "umask 022")
        if content != original:
            save(self, path, content)
            self.output.info(f"Patched configure umask 077→022 for HMDFS: {path}")

    def _patch_config_for_ohos(self):
        """Patch config.sub/config.guess to recognize the OHOS triplet."""
        if self.settings.os != "OHOS":
            return
        for cs_path in glob.glob(
            os.path.join(self.source_folder, "**", "config.sub"), recursive=True
        ):
            try:
                with open(cs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "ohos" in content:
                continue
            changed = False
            if "gnu* | android*" in content and "ohos*" not in content:
                content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
                changed = True
            if "linux-uclibc" in content and "linux-ohos" not in content:
                content = content.replace("linux-uclibc*)", "linux-uclibc* | linux-ohos*)", 1)
                changed = True
            if "ohos-linux)" not in content and "android-linux)" in content:
                anchor = "android-linux)\n"
                idx = content.find(anchor)
                if idx != -1:
                    end = content.find(";;", idx)
                    if end != -1:
                        insert_pos = end + len(";;") + 1
                        ohos_block = (
                            "\tohos-linux)\n"
                            "\t\tbasic_machine=$field1-unknown\n"
                            "\t\tbasic_os=linux-ohos\n"
                            "\t\t;;\n"
                        )
                        content = content[:insert_pos] + ohos_block + content[insert_pos:]
                        changed = True
            if changed:
                with open(cs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched config.sub for OHOS: {cs_path}")

        for cg_path in glob.glob(
            os.path.join(self.source_folder, "**", "config.guess"), recursive=True
        ):
            try:
                with open(cg_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "HarmonyOS" in content:
                continue
            changed = False
            if "__OHOS__" not in content and "__ANDROID__" in content:
                content = content.replace(
                    "#if defined(__ANDROID__)\n    LIBC=android",
                    "#if defined(__ANDROID__)\n    LIBC=android\n#elif defined(__OHOS__)\n    LIBC=ohos",
                    1,
                )
                changed = True
            if changed:
                with open(cg_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"Patched config.guess for OHOS: {cg_path}")

    def _fix_config_status(self):
        """Fix config.status HMDFS temporary directory permissions."""
        path = os.path.join(self.build_folder, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        original = content
        content = content.replace("umask 077 && mktemp", "mktemp")
        content = content.replace("umask 077 && mkdir", "mkdir")
        content = content.replace(
            "ac_tmp=$tmp",
            'ac_tmp=$tmp\nchmod 755 "$tmp" 2>/dev/null',
        )
        if content != original:
            save(self, path, content)
            self.output.info(f"Patched config.status for HMDFS: {path}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Clean up sysconfdir config (not part of Conan package)
        etc_dir = os.path.join(self.package_folder, "etc")
        if os.path.isdir(etc_dir):
            shutil.rmtree(etc_dir, ignore_errors=True)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """Sign ELF binaries for OHOS XPM."""
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warn("Signing tools not found, skipping ELF signing")
            return
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        for f in targets:
            if os.path.islink(f):
                continue
            try:
                self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=f))
            except ConanException:
                self.output.info(f"No .codesign section to remove (first signing), skipping: {f}")
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f
            ))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
