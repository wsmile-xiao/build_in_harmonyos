#!/usr/bin/env python3
"""test_package for mstpd 0.2.0 — consumer test plus capability probe.

What runs here:
  1. _check_package_layout(): the installed artifacts are really in the package.
  2. build(): compiles test_probe.c, a small C consumer of the same syscall
     surface mstpd needs at runtime (netlink route socket, PF_PACKET raw
     socket, abstract AF_UNIX bind, sysfs class/net enumeration, epoll,
     bridge ioctls).  It records rc/errno per call instead of guessing.
  3. test(): executes the packaged mstpd / mstpctl binaries through
     test_mstpd.sh (R34 — real binaries are run, no print-only shell).

All evidence goes to an absolute directory handed over through
MSTPD_TEST_OUT, so the framework's second (negative) conan test pass cannot
clobber the first pass output.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class MstpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep generators and compiled helpers out of the archive source dir.
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def _pkg(self):
        return self.dependencies[self.tested_reference_str].package_folder

    # Upstream installs the helper scripts into $(libexecdir)/mstpctl-utils
    # (Makefile.am:44) and configure.ac:34 deliberately pins libexecdir='/lib'
    # as soon as exec_prefix is empty -- which configure.ac:11 makes true for
    # every build ("no standard macro to override the default exec_prefix").
    # So the packaged location is lib/mstpctl-utils, never libexec/...: the
    # generated build-release/Makefile reports `libexecdir = /lib`.  The list
    # below is the built package's own conanmanifest.txt contents, so any file
    # that stops being installed fails this test.
    UTILS = ("ifquery", "ifupdown.sh", "mstp_config_bridge",
             "mstpctl-utils-functions.sh", "mstpctl_restart_config")

    def _check_package_layout(self):
        pkg = self._pkg()
        checks = [
            ("mstpd daemon", os.path.join(pkg, "bin", "mstpd")),
            ("mstpctl CLI", os.path.join(pkg, "bin", "mstpctl")),
            ("bridge-stp hook", os.path.join(pkg, "bin", "bridge-stp")),
            ("mstp_restart alias", os.path.join(pkg, "bin", "mstp_restart")),
            ("mstpctl-utils dir", os.path.join(pkg, "lib", "mstpctl-utils")),
            ("man page mstpctl.8", os.path.join(pkg, "share", "man", "man8", "mstpctl.8")),
            ("man page mstpctl-utils-interfaces.5",
             os.path.join(pkg, "share", "man", "man5", "mstpctl-utils-interfaces.5")),
            ("config bridge-stp.conf", os.path.join(pkg, "etc", "bridge-stp.conf")),
            ("bash completion mstpctl",
             os.path.join(pkg, "etc", "bash_completion.d", "mstpctl")),
        ]
        for script in self.UTILS:
            checks.append(("mstpctl-utils/" + script,
                           os.path.join(pkg, "lib", "mstpctl-utils", script)))
        # lexists, not exists: install-exec-hook creates the two restart
        # aliases as symlinks whose targets are the DEPLOYED path
        # $(sbindir)/bridge-stp (i.e. /bin/bridge-stp under --prefix=/), which by
        # construction cannot resolve inside a staged conan package folder.  The
        # packaged directory entry is what is asserted here; the resolution
        # behaviour is captured (not judged) by test_mstpd.sh.
        missing = [name for name, path in checks if not os.path.lexists(path)]
        if missing:
            raise ConanException("missing mstpd artifacts: " + ", ".join(missing))

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        cc = shutil.which(os.environ.get("CC", "clang")) or "clang"
        src = os.path.join(self.source_folder, "test_probe.c")
        exe = os.path.join(self.build_folder, "test_probe")
        # -D__MUSL__: the OHOS sysroot defines struct sockaddr_storage in both
        # sys/socket.h (inside #ifndef __MUSL__) and linux/socket.h (unguarded),
        # so any consumer touching netlink headers needs the guard (E091).
        self.run(cc + " -o " + exe + " " + src + " -Wall -D__MUSL__")
        # 目录名带进程号：框架 L1e 会对同一 test_package 再起一轮负照，
        # 两轮证据不得复用同一个输出目录。
        out = os.path.join(self.build_folder, "out-%d" % os.getpid())
        os.makedirs(out, exist_ok=True)
        self._out = out
        self._probe = exe

    def test(self):
        self._check_package_layout()
        # The preflight wrapper may export CONFIG_SHELL as /bin/sh, and
        # /system/bin/sh (mksh) cannot exec ELF binaries, so prefer the SDK
        # bash explicitly (same lesson as archives/a/adcli/0.9.2).
        bash = ("/data/service/hnp/bin/bash"
                if os.path.exists("/data/service/hnp/bin/bash")
                else (os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"))
        # Absolute paths only: the test script must never write relative to
        # the current working directory.
        os.environ["MSTPD_TEST_OUT"] = getattr(self, "_out", self.build_folder)
        os.environ["MSTPD_PROBE"] = getattr(self, "_probe", "")
        os.environ["MSTPD_BINDIR"] = os.path.join(self._pkg(), "bin")
        script = os.path.join(self.source_folder, "test_mstpd.sh")
        self.run(bash + " " + script, env="conanrun")
