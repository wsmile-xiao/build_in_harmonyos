#!/usr/bin/env python3
"""Conan recipe for util-linux-login 2.42.2 — the login(1) PAM-based login program.

Builds ONLY the login binary (and nologin helper) from the util-linux suite.
All other programs are disabled via --disable-all-programs.
Requires linux-pam for PAM authentication headers and libraries.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class UtilLinuxLoginConan(ConanFile):
    name = "util-linux-login"
    version = "2.42.2"
    description = "login(1) PAM-based login program from util-linux"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/util-linux/util-linux"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("linux-pam/1.7.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "util-linux-login requires a POSIX environment with PAM support"
            )

    def source(self):
        data = self.conan_data["sources"][self.version]
        # cdn.kernel.org occasionally times out on the CI worker
        # (ConanConnectionError: Read timed out). Try primary URL then mirrors.
        primary = data["url"]
        mirrors = [
            "https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.2.tar.xz",
            "https://www.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.2.tar.xz",
        ]
        for url in [primary] + mirrors:
            try:
                get(self, url, sha256=data["sha256"], strip_root=True)
                return
            except Exception as e:
                self.output.warning(f"source download failed from {url}: {e}")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable ALL programs first, then selectively enable login and nologin
        tc.configure_args.append("--disable-all-programs")
        tc.configure_args.append("--enable-login")
        tc.configure_args.append("--enable-nologin")
        # Disable optional features that are not needed
        tc.configure_args.append("--without-systemd")
        tc.configure_args.append("--without-selinux")
        tc.configure_args.append("--without-audit")
        tc.configure_args.append("--disable-bash-completion")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-plymouth-support")
        # Disable features that require kernel-specific headers
        tc.configure_args.append("--without-cap-ng")
        tc.configure_args.append("--without-utempter")
        tc.configure_args.append("--disable-makeinstall-chown")
        tc.configure_args.append("--disable-makeinstall-setuid")
        # Inject PAM include/lib paths so AC_CHECK_HEADERS finds security/pam_appl.h.
        pam_root = self.dependencies["linux-pam"].package_folder
        pam_inc = os.path.join(pam_root, "include")
        pam_lib = os.path.join(pam_root, "lib")
        tc.extra_cflags.append("-I%s" % pam_inc)
        tc.extra_ldflags.append("-L%s" % pam_lib)
        tc.generate()
        # AutotoolsDeps injects linux-pam's include/lib into CPPFLAGS/LDFLAGS so
        # that AC_CHECK_HEADERS(security/pam_appl.h, ...) in configure succeeds.
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: autoconf configure/config.status 用 umask 077 建临时目录（confXXXXXX），
        # OHOS HMDFS 上 0700 目录被强制降权不可写 → 替换为 umask 022。
        for fname in ("configure",):
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                if "umask 077" in text:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(text.replace("umask 077", "umask 022"))
        # 预建可写 TMPDIR 并注入环境变量，确保 config.status 子进程继承。
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool .la files and pkgconfig (we don't ship libraries)
        la_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(la_dir):
            rm(self, "*.la", la_dir)
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        if os.path.isdir(pc_dir):
            rm(self, "*.pc", pc_dir)
        # Remove include files (we're shipping a binary, not a library)
        inc_dir = os.path.join(self.package_folder, "include")
        if os.path.isdir(inc_dir):
            shutil.rmtree(inc_dir)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = [bindir]
        # Add bin to PATH so login is accessible
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
