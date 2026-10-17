#!/usr/bin/env python3
"""Conan test_package for miniupnpd 2.3.10 (consumer-view verification).

Two layers, both substantive (R34):

1. `miniupnpd --version` — the packaged binary really executes and reports the
   packaged version (also the L2 smoke test).
2. `ohos_netprobe` — a HarmonyOS-specific network capability probe compiled
   here and run here. It exercises the kernel interfaces miniupnpd needs at
   runtime (SSDP multicast join + round trip, rtnetlink iface watcher and
   route query, SIOCGIF* ioctls, /proc/net inputs) and inventories the
   capability-gated ones (NETLINK_NETFILTER / AF_PACKET / raw socket / uuid
   proc node). Its 22 required checks are the "鸿蒙特有测试" assertions.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class MiniupnpdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ---------------------------------------------------------------- helpers
    def _cc(self):
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        cc = (comp.get("c") or "").strip()
        if not cc or not os.path.isfile(cc):
            cc = subprocess.run("command -v clang || command -v cc",
                                shell=True, executable="/bin/sh",
                                capture_output=True, text=True).stdout.strip()
        if not cc:
            raise ConanException("no C compiler available for ohos_netprobe")
        return cc

    def _capture(self, cmd, timeout=120):
        proc = subprocess.run(cmd, shell=True, cwd=self.build_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout)
        return proc.returncode, proc.stdout or ""

    def _probe_dir(self):
        """Directory for the compiled probe.

        Conan runs test_package's build() with build_folder == this source
        directory, so a binary written next to ohos_netprobe.c would land in
        the PR surface as an untracked blob. Prefer the task TMPDIR
        (workspace tmp, writable, outside the worktree) and fall back to a
        sub-directory that only exists at run time.
        """
        for base in (os.environ.get("TMPDIR"), os.environ.get("TMP")):
            if base and os.path.isdir(base) and os.access(base, os.W_OK):
                d = os.path.join(base, "miniupnpd-2.3.10-probe")
                os.makedirs(d, exist_ok=True)
                return d
        d = os.path.join(self.build_folder, ".probe-build")
        os.makedirs(d, exist_ok=True)
        return d

    def _assert(self, cond, msg, counters):
        counters["total"] += 1
        if cond:
            counters["passed"] += 1
            self.output.info("assertion %d OK: %s" % (counters["total"], msg))
        else:
            raise ConanException("assertion %d FAILED: %s"
                                 % (counters["total"], msg))

    # ------------------------------------------------------------------ build
    def build(self):
        # Compile the probe with the same toolchain the package was built
        # with; it is deliberately self-contained (no link against miniupnpd,
        # which ships no library) so it also works on a plain consumer host.
        cc = self._cc()
        src = os.path.join(self.build_folder, "ohos_netprobe.c")
        self._probe_out = os.path.join(self._probe_dir(), "ohos_netprobe")
        self.run('"%s" -O1 -Wall -o "%s" "%s"'
                 % (cc, self._probe_out, src))

    # ------------------------------------------------------------------- test
    def test(self):
        counters = {"total": 0, "passed": 0}
        bindirs = self.dependencies["miniupnpd"].cpp_info.bindirs
        bin_dir = bindirs[0] if bindirs else os.path.join(
            self.dependencies["miniupnpd"].package_folder, "bin")
        binary = os.path.join(bin_dir, "miniupnpd")
        pkg_folder = self.dependencies["miniupnpd"].package_folder

        # A1 — the packaged binary runs (non-zero rc raises)
        self.run('"%s" --version' % binary)

        # A2 — it reports exactly the packaged version
        rc, out = self._capture('"%s" --version' % binary)
        first = out.strip().splitlines()[0] if out.strip() else ""
        toks = first.split()
        self._assert(rc == 0, "miniupnpd --version rc=0", counters)
        # upstream prints "miniupnpd <ver> <build date>" (validateversion in
        # check.mk compares `cut -d' ' -f-2`), so compare the first two fields
        self._assert(toks[:2] == ["miniupnpd", "2.3.10"],
                     "version line starts with 'miniupnpd 2.3.10' (got %r)" % first,
                     counters)
        self._assert("netfilter(nftables)" in out,
                     "built with the nftables backend (got %r)" % out[:80],
                     counters)

        # A3 — packaged payload present (config sample + licence)
        conf = os.path.join(pkg_folder, "share", "miniupnpd", "miniupnpd.conf")
        lic = os.path.join(pkg_folder, "licenses", "LICENSE")
        self._assert(os.path.isfile(conf) and os.path.getsize(conf) > 0,
                     "packaged miniupnpd.conf present and non-empty", counters)
        self._assert(os.path.isfile(lic) and os.path.getsize(lic) > 0,
                     "packaged LICENSE present and non-empty", counters)

        # A4..A(n) — HarmonyOS network-stack probe (鸿蒙特有测试)
        probe = os.path.join(self._probe_dir(), "ohos_netprobe")
        if not os.path.isfile(probe):
            raise ConanException("probe binary missing: %s" % probe)
        rc, out = self._capture('"%s"' % probe, timeout=180)
        self.output.info("ohos_netprobe rc=%s\n%s" % (rc, out))
        m = re.search(r"^OHOS_NETPROBE required=(\d+) required_pass=(\d+) "
                      r"info=(\d+)$", out, re.M)
        if not m:
            raise ConanException("ohos_netprobe produced no OHOS_NETPROBE "
                                 "summary line:\n%s" % out[-2000:])
        required, passed, info_n = (int(m.group(1)), int(m.group(2)),
                                    int(m.group(3)))
        self._assert(rc == 0, "ohos_netprobe exit code 0", counters)
        self._assert(required >= 1,
                     "probe declares %d required checks" % required, counters)
        self._assert(passed == required,
                     "all %d required network checks pass (got %d/%d)"
                     % (required, passed, required), counters)
        # every required check must have been reported individually
        lines = [l for l in out.splitlines() if "\tPASS\t" in l or "\tFAIL\t" in l]
        self._assert(len(lines) == required,
                     "probe reported %d per-check lines == required %d"
                     % (len(lines), required), counters)
        self._assert(info_n >= 1,
                     "probe inventoried %d capability-gated interfaces" % info_n,
                     counters)

        self.output.info("test_package assertions: %d/%d passed"
                         % (counters["passed"], counters["total"]))
        if counters["passed"] != counters["total"]:
            raise ConanException("assertion accounting mismatch")
