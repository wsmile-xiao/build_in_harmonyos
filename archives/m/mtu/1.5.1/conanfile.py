#!/usr/bin/env python3
"""Conan recipe for mtu 1.5.1 — MTU discovery/injection utility (CLI tool).

Upstream: https://github.com/ncopa/pingu (tag v1.5.1).
The `mtu` binary is one of the build targets of the pingu source tree
(src/mtu.c + src/icmp.c + src/netlink.c); this recipe builds and packages
only the `mtu` target. pingu itself (policy routing daemon, needs libev)
is not built.

Build system: hand-written Makefiles (no configure needed for the mtu
target; upstream `configure` only probes libev for the pingu daemon which
mtu does not link). The recipe invokes `make -C src mtu` directly with the
Conan-provided compiler, so there is no libev dependency (R36 clean).

Upstream ships no test suite (see test_package/MANIFEST.yml audit).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MtuConan(ConanFile):
    name = "mtu"
    version = "1.5.1"
    description = "Utility to discover and inject path MTU (from the pingu project)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ncopa/pingu"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mtu", "pmtu", "icmp", "netlink", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # No patch files: OHOS sockaddr_storage guard is applied
        # procedurally in source() via string replacement (immune to
        # unified-diff hunk offsets). Nothing to export.
        pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mtu/1.5.1 is adapted for Linux and OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._apply_ohos_sockaddr_guard()

    def _apply_ohos_sockaddr_guard(self):
        # OHOS musl sysroot: <sys/socket.h> and <linux/socket.h> both
        # define struct sockaddr_storage (E091 redefinition). Temporarily
        # rename the kernel-side symbol while including the linux headers.
        # Done here by exact string replacement instead of a unified-diff
        # patch file: the checked-in .patch drifted from the real upstream
        # header order (missed <sys/types.h>/<sys/ioctl.h> in netlink.c),
        # so `patch` rejected the hunk. Replacement is offset-independent.
        guard_begin = (
            "/* OHOS musl sysroot: <sys/socket.h> and <linux/socket.h> both\n"
            " * define struct sockaddr_storage. Temporarily rename the\n"
            " * kernel-side symbol while including the linux headers. */\n"
            "#define sockaddr_storage __linux_sockaddr_storage\n"
        )
        guard_end = "#undef sockaddr_storage\n"
        mtu_c = os.path.join(self.source_folder, "src", "mtu.c")
        with open(mtu_c, "r", encoding="utf-8", errors="replace") as f:
            mtu_text = f.read()
        old_mtu = "#include <linux/if.h>\n#include <linux/sockios.h>\n"
        if old_mtu not in mtu_text:
            raise Exception(
                "mtu.c linux header block not found for OHOS guard; "
                "refusing to guess (source may have changed)")
        mtu_text = mtu_text.replace(
            old_mtu, guard_begin + old_mtu + guard_end, 1)
        with open(mtu_c, "w", encoding="utf-8", newline="\n") as f:
            f.write(mtu_text)
        netlink_c = os.path.join(self.source_folder, "src", "netlink.c")
        with open(netlink_c, "r", encoding="utf-8", errors="replace") as f:
            nl_text = f.read()
        old_nl = (
            "#include <asm/types.h>\n"
            "#include <linux/netlink.h>\n"
            "#include <linux/rtnetlink.h>\n"
            "#include <linux/ip.h>\n"
        )
        if old_nl not in nl_text:
            raise Exception(
                "netlink.c linux header block not found for OHOS guard; "
                "refusing to guess (source may have changed)")
        nl_text = nl_text.replace(
            old_nl, guard_begin + old_nl + guard_end, 1)
        with open(netlink_c, "w", encoding="utf-8", newline="\n") as f:
            f.write(nl_text)
        self.output.info("OHOS sockaddr_storage define-guard applied")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _resolve_compiler(self, configured, names):
        # True device migrated clang from /data/service/hnp/bin to
        # ~/usr/local/bin but the shared profile still points at the old
        # path (make: /data/service/hnp/bin/clang: No such file).
        # Prefer the configured absolute path only when it exists,
        # otherwise resolve via PATH or the ~/usr/local/bin fallback.
        # Adapted from traildb/0.6 _resolve_compiler (same device issue).
        if configured and os.path.isabs(configured) and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def _compiler(self):
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        configured = comp.get("c")
        # CC env may also carry the stale absolute path; validate it the
        # same way instead of trusting it blindly.
        candidates = [configured, os.environ.get("CC")]
        for cand in candidates:
            resolved = self._resolve_compiler(cand, ("clang", "cc"))
            # _resolve_compiler falls back to which(); accept the first
            # candidate chain that yields an existing file.
            if resolved and os.path.isfile(resolved):
                return resolved
        return self._resolve_compiler(configured or os.environ.get("CC"),
                                      ("clang", "cc"))

    def build(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mtu/1.5.1 supports Linux and OHOS targets only, not %s" % self.settings.os
            )
        cc = self._compiler()
        self.output.info("HMBS diag compiler c=%s (configured=%s)" % (
            cc, (self.conf.get("tools.build:compiler_executables",
                               check_type=dict) or {}).get("c")))
        src_dir = os.path.join(self.source_folder, "src")
        # R33: compiler comes from the Conan conf, not a bare shell variable.
        # PINGU_VERSION/PACKAGE_VERSION are normally generated by configure;
        # the mtu target only uses PINGU_VERSION for -DPINGU_VERSION, so pass
        # it explicitly and skip configure (which would hard-require libev
        # for the pingu daemon that we do not build).
        # R9: -j1 for reproducibility on the OHOS worker.
        self.run(
            'make mtu -j1 CC="%s" PINGU_VERSION="1.5.1" PACKAGE_VERSION="1.5.1"'
            % cc,
            cwd=src_dir,
            env="conanbuild",
        )
        self._emit_no_tests_marker()

    def _emit_no_tests_marker(self):
        upstream = {
            "status": "no_tests",
            "framework": "make",
            "command": "make check (upstream registers no tests)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "pingu-1.5.1 audited: no tests/ or test/ directory in the "
                      "31KB tarball; src/Makefile and top Makefile define only "
                      "all/install/clean with no check/test target and no TESTS "
                      "registration; `configure --help` offers no test options; "
                      "see test_package/MANIFEST.yml audit",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "mtu", src=src_dir,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
