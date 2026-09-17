#!/usr/bin/env python3
"""Conan recipe for nrpe 4.1.3 — Nagios Remote Plugin Executor.

Autotools daemon + client adapted for HarmonyOS PC (aarch64-linux-ohos).
Hard dependency: openssl (SSL transport). The bundled AX_NAGIOS_GET_SSL macro
probes explicit --with-ssl(-inc/-lib) paths (Homebrew: "Set both or it still
looks for /usr/lib"), so the openssl conan dependency is provisioned into a
private build_folder/prefix (R49, no shared /usr/local pollution) and injected
through configure args. tcp wrappers (libwrap) is optional and not published on
ohpcd → --disable-tcpd. nrpe installs into sbin/ and libexec/, folded to bin/
per Conan convention (R38 commands.json declares both binaries).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

_PY = "/data/service/hnp/bin/python3"


def _copy_tree(src, dst):
    """Recursively copy a directory tree (HMDFS: no symlink support → real copies)."""
    if not os.path.isdir(src):
        return
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            _copy_tree(s, d)
        else:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            if not os.path.exists(d):
                shutil.copy2(s, d)


def _identity():
    """Resolve current user/group name via python (no `id`(1) on OHOS).

    Returns (user, group). Falls back to numeric uid/gid strings when the
    euid has no /etc/passwd entry (e.g. sandbox uid 20020082).
    """
    try:
        out = subprocess.check_output(
            [_PY, "-c",
             "import os,pwd,grp;"
             "u=os.geteuid(); g=os.getegid();"
             "un=pwd.getpwuid(u).pw_name if u in (p.pw_uid for p in pwd.getpwall()) else str(u);"
             "gn=grp.getgrgid(g).gr_name if g in (x.gr_gid for x in grp.getgrall()) else str(g);"
             "print(un,gn)"],
            text=True).strip().split()
        if len(out) == 2:
            return out[0], out[1]
    except Exception:
        pass
    return "0", "0"


class NrpeConan(ConanFile):
    name = "nrpe"
    version = "4.1.3"
    description = "NRPE 4.1.3 - Nagios Remote Plugin Executor (daemon + check_nrpe client)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nagios.org/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openssl is the hard dependency for the SSL transport (published in
        # the configured registry; recipe availability verified during adaptation)
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prefix(self):
        # R49: dependency injection target = private build_folder/prefix (never
        # the shared /usr/local — CI workers share /storage/Users/currentUser/usr/local).
        return os.path.join(self.build_folder, "prefix")

    def generate(self):
        prefix = self._prefix()
        # Provision openssl headers/libs into the private prefix.
        ssl_pkg = self.dependencies["openssl"].package_folder
        _copy_tree(os.path.join(ssl_pkg, "include"), os.path.join(prefix, "include"))
        _copy_tree(os.path.join(ssl_pkg, "lib"), os.path.join(prefix, "lib"))
        user, group = _identity()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # config.guess cannot recognize HarmonyOS (uname -s = HarmonyOS) and the
            # bundled config.sub lacked ohos — patched (0001), pin triplet explicitly.
            "--build=aarch64-linux-ohos",
            "--host=aarch64-linux-ohos",
            # SSL: explicit paths (AX_NAGIOS_GET_SSL probes ssl-inc/ssl-lib dirs).
            f"--with-ssl={prefix}",
            f"--with-ssl-inc={prefix}/include",
            f"--with-ssl-lib={prefix}/lib",
            "--enable-ssl",
            "--enable-command-args",
            # tcp wrappers (libwrap) not published on ohpcd → trim.
            "--disable-tcpd",
            # OHOS /etc/passwd has no nagios user; install(1) -o nagios would fail
            # for non-root. Use the current build user (Homebrew does the same).
            f"--with-nrpe-user={user}",
            f"--with-nrpe-group={group}",
            f"--with-nagios-user={user}",
            f"--with-nagios-group={group}",
            # Keep every path private; nrpe's get_paths macro rewrites an
            # unset libexecdir to /usr/nagios — must pin it explicitly.
            f"--with-piddir={prefix}/var/run",
            f"--with-logdir={prefix}/var/log",
            f"--with-pipedir={prefix}/var/run",
            f"--libexecdir={prefix}/libexec",
            f"--sysconfdir={prefix}/etc",
        ])
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1: Conan's default -j{N} creates a GNU make jobserver FIFO under
        # $TMPDIR, which HMDFS rejects ("jobserver mkfifo ... Operation not
        # permitted"). Serial make avoids the jobserver entirely.
        # NB: top-level Makefile's default target only prints a help list —
        # the real build target is "all".
        autotools.make(args=["all", "-j1"])

    def package(self):
        autotools = Autotools(self)
        # The OHOS install-sh may not provide chown even when the build user is
        # root; package files need no ownership metadata, so disable the recipe's
        # default -o/-g install flags at make time.
        # -j1 for the same HMDFS jobserver reason as above.
        autotools.install(args=["-j1", "NRPE_INSTALL_OPTS=", "NAGIOS_INSTALL_OPTS="])
        # Upstream installs nrpe into $(sbindir) and check_nrpe into
        # $(pluginsdir)=<libexec>/plugins; Conan convention (and the CI
        # application negative test) expects executables under bin/.
        # NB: --libexecdir=<absolute private prefix> makes DESTDIR staging land
        # under package_folder/<abs-path>/libexec/... — walk recursively to
        # collect every binary into bin/ (HMDFS symlink issues make a
        # hardcoded nested-path copy fragile).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wanted = {"nrpe", "check_nrpe", "nrpe-uninstall"}
        for root, _dirs, files in os.walk(self.package_folder):
            if os.path.abspath(root) == os.path.abspath(bin_dir):
                continue
            for name in files:
                if name in wanted:
                    os.replace(os.path.join(root, name), os.path.join(bin_dir, name))
        # prune empty directories left behind (best-effort)
        for root, dirs, _files in os.walk(self.package_folder, topdown=False):
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError:
                    pass
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
