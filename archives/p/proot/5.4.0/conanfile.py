#!/usr/bin/env python3
"""Conan recipe for proot 5.4.0 — chroot, mount --bind, and binfmt_misc
without privilege/setup.

proot is a single-binary C program built by a hand-written GNUmakefile.  It
uses ptrace(2) to intercept the syscalls of the guest programs it runs, so the
whole "guest rootfs" machinery lives in user space and needs no privilege.
The binary links against libtalloc (hierarchical memory pools, published in
this repository as talloc/2.4.4) and the vendored uthash headers; the
optional CARE companion tool is not built.

OHOS adaptations (patches in conandata.yml):
  - src/path/binding.h: the OHOS C library ships a FreeBSD-derived
    <sys/queue.h> from which the CIRCLEQ_* family has been removed (FreeBSD
    dropped it in 2018).  proot uses circular queues for its binding lists,
    so the standard definitions are provided when the C library does not
    (feature detection only, no platform macro — R8/PF5 clean).
  - src/path/temp.c: get_current_dir_name() is a GNU extension the OHOS C
    library does not provide; the portable getcwd() form (already used by the
    upstream __ANDROID__ branch) is used on such C libraries.
  - src/extension/portmap/portmap.c: <linux/net.h> pulls in <linux/socket.h>,
    whose kernel-side struct sockaddr_storage collides with the C library's
    definition in <sys/socket.h> on musl-based systems such as the OHOS one;
    the kernel-side struct is renamed while the UAPI headers are included
    (glibc builds are unaffected).  Same class as knowledge E091.
  - test/ptrace-2.c (upstream test support): uses the glibc-only
    `enum __ptrace_request`, absent from the OHOS C library; the parameter
    type falls back to `int` there (the same fix is applied by the Alpine
    Linux package of proot to this upstream test).

The version banner is pinned with VERSION=<release> on the make command line:
upstream derives it from `git describe`, which cannot work from a release
tarball (the Alpine Linux package does the same).

Platform capability boundary (recorded in reports/test-report.md): the OHOS
kernel refuses ptrace(2) for unprivileged processes, so invocations that need
a tracee fail with "ptrace(TRACEME): Permission denied" before execve.  This
is kernel policy that no user-space patch can bypass; the consumer tests in
test_package/ verify the full CLI surface that remains usable, and the
upstream suite results are recorded truthfully in reports/test-report.md.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class ProotConan(ConanFile):
    name = "proot"
    version = "5.4.0"
    description = (
        "chroot, mount --bind, and binfmt_misc without privilege/setup "
        "(user-space implementation based on ptrace)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://proot-me.github.io"
    url = "https://github.com/proot-me/proot"
    topics = ("proot", "chroot", "ptrace", "container", "cli", "utility")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: check the OHOS family, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "proot requires a Linux-like target (Linux or OHOS), not {0}".format(
                    self.settings.os
                )
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("talloc/2.4.4")

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()

    @staticmethod
    def _executable(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def _resolve_tool(self, cc, tool_name):
        """Locate a target-capable binutils clone for the embedded loader.

        proot embeds its ELF loader into the binary with objcopy/objdump, so
        those tools must understand the target architecture.  The OHOS
        toolchain provides the LLVM variants next to the cross compiler and
        in the CI worker's HNP layout; look there first, then on PATH.
        Returns None when nothing is found — `make` then falls back to its
        own default (plain objcopy/objdump/strip resolved from its PATH).
        """
        candidates = []
        if cc and os.path.sep in cc:
            for base in (os.path.dirname(cc), os.path.dirname(os.path.realpath(cc))):
                candidates.append(os.path.join(base, tool_name))
        candidates.append(os.path.join("/data/service/hnp/bin", tool_name))
        candidates += glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/" + tool_name
        )
        candidates += glob.glob(
            os.path.expanduser("~/.harmonybrew/opt/ohos-sdk@*/native/llvm/bin/" + tool_name)
        )
        for p in os.environ.get("PATH", "").split(os.pathsep):
            if p:
                candidates.append(os.path.join(p, tool_name))
        for candidate in candidates:
            if self._executable(candidate):
                return candidate
        return None

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # R33: the compiler comes from the Conan conf, never from shell
        # environment variables.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        # VERSION: upstream derives it from `git describe`, which cannot work
        # from a release tarball; pin the release version explicitly.
        cmd = [
            "make", "-C", "src", "proot", "-j1", "V=1",
            "CC={0}".format(cc),
            "VERSION={0}".format(self.version),
        ]
        for var, tool in (
            ("OBJCOPY", "llvm-objcopy"),
            ("OBJDUMP", "llvm-objdump"),
            ("STRIP", "llvm-strip"),
        ):
            path = self._resolve_tool(cc, tool)
            if path is not None:
                cmd.append("{0}={1}".format(var, path))
        # The GNUmakefile locates talloc through pkg-config; point it at the
        # .pc generated by Conan only, so no host package can leak in.
        prelude = 'PKG_CONFIG_PATH="{0}" PKG_CONFIG_LIBDIR="{0}" '.format(
            self.generators_folder
        )
        self.run(prelude + " ".join(cmd), cwd=self.source_folder)

    def package(self):
        # Upstream `make install` relies on install(1), which OHOS does not
        # provide, so the artifacts are copied explicitly.
        copy(self, "proot", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
