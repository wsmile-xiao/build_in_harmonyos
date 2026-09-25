#!/usr/bin/env python3
"""Conan recipe — l2tpns 2.5.0 (L2TP LNS daemon, raw Makefile, no configure).

l2tpns is a layer-2 tunneling protocol network server (LNS) for Linux:
it terminates L2TP/PPPoE tunnels, authenticates against RADIUS and exposes
a Cisco-like CLI (libcli) on tcp/23. Upstream ships a hand-written Makefile
that builds two executables (l2tpns daemon, nsctl control tool) plus 8
dlopen(3)ed CLI plugins (*.so).

OHOS adaptations (see patches/ and notes.md):
  - cli.c/cluster.c need <fcntl.h> for F_GETFL/F_SETFL/O_NONBLOCK/O_DIRECTORY
    (glibc leaks those through <sys/file.h>, musl does not);
  - struct msghdr positional initializer broken under OHOS musl (int
    msg_iovlen + int pad member) -> designated initializers;
  - ohos_compat.h (force-included via EXTRA_CFLAGS=-include) skips uapi
    blocks duplicated by the sanitized OHOS kernel headers and provides
    __kernel_sa_family_t / __packed (E119 family, cf. batctl);
  - Makefile gains an $(EXTRA_CFLAGS) hook and a direct -DHAVE_EPOLL
    (upstream probes `uname -r | perl`, fragile on perl-less workers);
  - l2tpns.LIBS is overridden: musl provides dlopen/dlsym in libc, so the
    standalone -ldl is dropped; libcli is linked through an explicit static
    archive path (no -l lookup, no runtime rpath against the conan cache);
  - `make install` is never invoked (hardcodes install -o root -g root,
    gzip on manpages and mknod /dev/net/tun; E108); artifacts are collected
    with Conan copy() instead.

Official upstream: https://code.ffdn.org/l2tpns/l2tpns (2.5.0 = commit
372e5c0d29de77f5958fd55b81801f58e9eb52e0; archive pinned to the Debian
original tarball of that commit because code.ffdn.org is unreachable from
the porting network — see conandata.yml and notes.md).
License: GPL-2.0-only
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class L2tpnsConan(ConanFile):
    name = "l2tpns"
    version = "2.5.0"
    description = (
        "High-performance L2TP network server (LNS): l2tpns daemon, "
        "nsctl control tool and 8 CLI plugins"
    )
    license = "GPL-2.0-only"
    homepage = "https://code.ffdn.org/l2tpns/l2tpns"
    url = "https://code.ffdn.org/l2tpns/l2tpns"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Upstream Makefile builds in-source; keep the downloaded sources in
    # place so `make` (run with cwd=source_folder) produces artifacts there.
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # -lcli: the Cisco-like CLI library the daemon links (upstream
        # l2tpns.LIBS=-lcli -ldl). Static by default (libcli default
        # shared=False): the final binary keeps a libc-only DT_NEEDED set,
        # so nothing needs an rpath against the conan cache at runtime.
        # The 8 plugins are dlopen(RTLD_NOW)'ed and carry libc-only
        # undefined symbols, so they stay loadable regardless.
        self.requires("libcli/1.10.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _is_usable_executable(self, path):
        # Absolute paths must exist and be executable (preflight toolchain
        # may move: the profile conf can point at a stale clang that no
        # longer exists -> make then fails with "No such file or
        # directory"). Bare names resolve via PATH, so accept them.
        if not path:
            return False
        path = str(path)
        if not os.path.isabs(path):
            return True
        return os.path.isfile(path) and os.access(path, os.X_OK)

    def _resolve_tool(self, key, fallbacks):
        # R33: compiler paths come from Conan conf, never from bare shell
        # env vars. Conf values are only used when the absolute path is
        # actually usable; stale profile paths fall back to PATH lookup.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get(key)
        if self._is_usable_executable(cand):
            if os.path.isabs(str(cand)):
                return str(cand)
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        # Known OHOS absolute locations (profile PATH order) before giving up.
        for abs_path in ("/data/service/hnp/bin/clang",
                         "/storage/Users/currentUser/usr/local/bin/clang"):
            if fallbacks and os.path.basename(abs_path) in fallbacks:
                if self._is_usable_executable(abs_path):
                    return abs_path
        if self._is_usable_executable(cand):
            return str(cand)
        return fallbacks[0]

    def build(self):
        apply_conandata_patches(self)

        cc = self._resolve_tool("c", ["clang", "cc"])
        if not cc:
            raise ConanInvalidConfiguration("A C compiler is required to build l2tpns")

        # libcli include/lib locations straight from the dependency package.
        # Explicit link closure (implement-policy #5): the static archive is
        # passed as an absolute link input guarded by isfile, never through
        # implicit default-search-path resolution.
        dep = self.dependencies.get("libcli")
        if dep is None:
            raise ConanInvalidConfiguration("libcli dependency missing from the graph")
        incdir = os.path.join(str(dep.package_folder), "include")
        libdir = os.path.join(str(dep.package_folder), "lib")
        if not os.path.isfile(os.path.join(incdir, "libcli.h")):
            raise ConanInvalidConfiguration(
                "libcli package is missing include/libcli.h")
        libcli_a = os.path.join(libdir, "libcli.a")
        if os.path.isfile(libcli_a):
            # Static: absolute archive as a direct link input.
            libs_arg = libcli_a
        else:
            # Shared libcli variant: -L/-lcli (binary then needs a runtime
            # path; keep the default static option to avoid this branch).
            libs_arg = "-L{} -lcli".format(libdir)

        args = [
            "CC={}".format(cc),
            # INCLUDES is the upstream Makefile's own -I slot (it feeds
            # CPPFLAGS together with DEFINES). Extend INCLUDES rather than
            # overriding CPPFLAGS so the -DLIBDIR/-DETCDIR defines survive
            # the command-line override.
            '"INCLUDES=-I. -I{}"'.format(incdir),
            '"LDFLAGS=-L{}"'.format(libdir),
            # Upstream hardcodes l2tpns.LIBS=-lcli -ldl. musl (OHOS)
            # provides dlopen/dlsym in libc itself, so the standalone libdl
            # is dropped and libcli comes from the explicit archive above.
            '"l2tpns.LIBS={}"'.format(libs_arg),
            # Force-include the OHOS uapi/musl clash shims into every TU
            # (see patches/0004-ohos_compat.h.patch and notes.md).
            '"EXTRA_CFLAGS=-include ohos_compat.h"',
            # R9: always single-job make on OHOS workers — the platform
            # SELinux policy forbids user processes from creating FIFOs, so
            # GNU make's FIFO-based jobserver cannot pass tokens and
            # parallel make hangs or errors out.
            "-j1",
        ]
        # `all` = programs + plugins + doc; docs/Makefile degrades to a
        # no-op when pandoc is absent, so this is safe on every worker.
        self.run("make all {}".format(" ".join(args)), cwd=self.source_folder)

    def package(self):
        sf = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")
        plugdir = os.path.join(self.package_folder, "lib", "l2tpns")

        copy(self, "l2tpns", sf, bindir)
        copy(self, "nsctl", sf, bindir)
        copy(self, "COPYING", sf, os.path.join(self.package_folder, "licenses"))

        plugins = (
            "autosnoop.so", "autothrottle.so", "garden.so", "sessionctl.so",
            "setrxspeed.so", "snoopctl.so", "stripdomain.so", "throttlectl.so",
        )
        for plugin in plugins:
            copy(self, plugin, sf, plugdir)

        # Fail loudly on missing artifacts instead of shipping a broken
        # package (make install is never invoked: upstream install target
        # hardcodes install -o root -g root, gzip of manpages and
        # mknod /dev/net/tun — E108, not usable on OHOS CI).
        for artifact in ("l2tpns", "nsctl"):
            if not os.path.isfile(os.path.join(bindir, artifact)):
                raise ConanInvalidConfiguration(
                    "l2tpns build did not produce bin/{}".format(artifact))
        for plugin in plugins:
            if not os.path.isfile(os.path.join(plugdir, plugin)):
                raise ConanInvalidConfiguration(
                    "l2tpns build did not produce lib/l2tpns/{}".format(plugin))

    def package_info(self):
        # Application package: nothing to link against; deliver the two
        # executables on PATH. Plugins ship under lib/l2tpns (they are
        # dlopen()ed from PLUGINDIR at daemon runtime, never -l linked).
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
