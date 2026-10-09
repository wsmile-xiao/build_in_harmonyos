#!/usr/bin/env python3
"""Conan recipe for miniupnpd 2.3.10 — lightweight UPnP IGD / PCP / NAT-PMP daemon.

Build route: upstream hand-written `./configure` + GNU `Makefile.linux_nft`,
run out-of-source in the Conan build folder. No source patches are needed:
every OHOS difference below is handled by configure flags / CPPFLAGS / PATH.

OHOS adaptation points (first-hand evidence in notes.md and reports/):

* `uname -s` prints `HarmonyOS`, upstream's OS case only knows the BSD/Linux/
  Darwin/SunOS names → use configure's own cross-build switch
  `--host-os=Linux --host-os-version=<rel> --host-machine=aarch64`.
* `--host-os-version` must be numeric. The real release string is
  "HongMeng Kernel 1.12.0"; upstream's Linux branch does `awk -F.` + `[ ... ]`
  arithmetic on it and a value with spaces makes the test emit
  `[: Kernel: missing )` (observed on device), so 1.12.0 (the actual kernel
  version component) is passed instead.
* OHOS SDK <linux/socket.h> redefines `struct sockaddr_storage` that
  <sys/socket.h> already defines → add
  `-D_UAPI_LINUX_SOCKET_H -D__kernel_sa_family_t=sa_family_t` to CPPFLAGS
  (same workaround as libnftnl/1.3.1, knowledge entry E119).
* Firewall backend = nftables. The Linux default (iptables) needs
  <xtables.h> + <libiptc/libiptc.h> from iptables, for which the ohpcd
  remote has no recipe; nftables' libnftnl + libmnl both have prebuilt
  OHOS binaries (armv8 / clang 15 / Release).
* Upstream `testgetifaddr.sh` shells out to `command -v ip`. OHOS toybox is
  built without the `ip` applet, but busybox (shipped in $PATH as
  /data/service/hnp/bin/busybox) does provide it, so build() exposes a
  task-local bin dir containing an `ip` → busybox link on PATH. The upstream
  test script itself is not modified.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (get, copy, apply_conandata_patches,
                              export_conandata_patches)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# Upstream `make check` registers exactly these four validate targets
# (miniupnpd-2.3.10/check.mk: validateupnppermissions, validategetifaddr,
#  validatessdppktgen, validateversion).
_CHECK_TARGETS = (
    "validateupnppermissions",
    "validategetifaddr",
    "validatessdppktgen",
    "validateversion",
)

# Test programs the platform build produces (Makefile.linux_nft TESTS=1) but
# which `make check` does not drive; each is run standalone with the
# parameters its own main() documents.
_STANDALONE_CASES = (
    ("testupnpdescgen", "./testupnpdescgen"),
    ("testgetifstats", "./testgetifstats lo"),
    ("testgetroute", "./testgetroute 127.0.0.1"),
    ("testasyncsendto", "./testasyncsendto"),
)


class MiniupnpdConan(ConanFile):
    name = "miniupnpd"
    version = "2.3.10"
    description = "Lightweight UPnP IGD & PCP/NAT-PMP daemon"
    license = "BSD-3-Clause"
    homepage = "https://miniupnp.tuxfamily.org/"
    url = "https://github.com/miniupnp/miniupnp"
    topics = ("upnp", "igd", "nat-pmp", "pcp", "ssdp", "daemon")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("libnftnl/1.3.1")

    def export_sources(self):
        # Required by conan-verify G1 (and harmless with `patches: {}`): the
        # patch machinery is declared so a future version can add patches
        # without touching the recipe skeleton.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # configure() calls `pkg-config --exists libnftnl libmnl` to decide
        # whether to put -I/-L/-l for the nftables backend into config.mk.
        # Without the generated .pc files upstream silently falls back to
        # "Warning: no libnftnl or libmnl pkg-config found" and compilation
        # dies later on `libmnl/libmnl.h: file not found`.
        PkgConfigDeps(self).generate()
        pc_path = self.generators_folder
        old = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = (pc_path + os.pathsep + old) if old else pc_path
        self.output.info("PKG_CONFIG_PATH=%s" % os.environ["PKG_CONFIG_PATH"])

    # ---------------------------------------------------------------- helpers
    def _cc(self):
        # R33: compiler comes from the Conan conf, never from ${CC}/${CFLAGS}.
        comp = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        cc = (comp.get("c") or "").strip()
        if not cc or not os.path.isfile(cc):
            cc = shutil.which("clang") or "clang"
        self.output.info("CC=%s" % cc)
        return cc

    def _ensure_ip_tool(self):
        """Upstream testgetifaddr.sh needs `ip`; OHOS toybox has no ip applet.

        busybox (present in the HNP tool bundle) does provide it, so expose it
        under a task-local bin dir instead of editing the upstream test.
        """
        if shutil.which("ip"):
            self.output.info("ip tool: found on PATH (%s)" % shutil.which("ip"))
            return
        tools_dir = os.path.join(self.build_folder, ".tools")
        os.makedirs(tools_dir, exist_ok=True)
        busybox = shutil.which("busybox")
        if not busybox:
            self.output.warning("ip tool: neither `ip` nor `busybox` found; "
                                "upstream testgetifaddr.sh will exit 1")
            return
        link = os.path.join(tools_dir, "ip")
        if not os.path.exists(link):
            os.symlink(busybox, link)
        os.environ["PATH"] = tools_dir + os.pathsep + os.environ.get("PATH", "")
        self.output.info("ip tool: exposed %s -> %s (OHOS toybox has no ip applet)"
                         % (link, busybox))

    def _ensure_writable_tmp(self):
        # Device /tmp is read-only; configure uses mktemp in the build dir but
        # child tools still honour TMPDIR.
        cand = (os.environ.get("TMPDIR") or os.environ.get("TMP") or "")
        if not cand or not os.path.isdir(cand) or not os.access(cand, os.W_OK):
            cand = os.path.join(self.build_folder, "tmp")
            os.makedirs(cand, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = cand
        self.output.info("TMPDIR=%s" % cand)

    def _run(self, cmd, cwd=None, timeout=1800, label=None, keep=None):
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(cmd, shell=True, cwd=cwd or self.build_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout)
        out = proc.stdout or ""
        if out.strip():
            if keep:
                # `make check` rebuilds every object first (upstream writes
                # .depend/%.d after the .o, so the depfile is always newer),
                # which buries the four validate verdicts under thousands of
                # compiler lines. Keep the verdict lines verbatim so the
                # evidence copy shows each target's result.
                import re as _re
                verdicts = [l for l in out.splitlines()
                            if _re.search(keep, l)]
                self.output.info("check verdict lines:\n" + "\n".join(verdicts))
            self.output.info(out[-6000:])
        if proc.returncode != 0:
            raise ConanException("%s failed (rc=%s): %s\n%s"
                                 % (label or cmd, proc.returncode, cmd, out[-4000:]))
        return out

    def _case(self, label, cmd, cwd=None, timeout=600):
        self.output.info("+ [%s] %s" % (label, cmd))
        try:
            proc = subprocess.run(cmd, shell=True, cwd=cwd or self.build_folder,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=timeout)
            rc, out = proc.returncode, proc.stdout or ""
        except subprocess.TimeoutExpired as exc:
            rc, out = 124, "TIMEOUT after %ss\n%s" % (timeout, exc.output or "")
        self.output.info("--- [%s] rc=%s ---\n%s" % (label, rc, out[-3000:]))
        return rc, out

    # ------------------------------------------------------------------ build
    def build(self):
        self._ensure_writable_tmp()
        self._ensure_ip_tool()
        # OHOS SDK UAPI headers: <linux/netfilter.h> pulls <linux/socket.h>
        # which re-declares struct sockaddr_storage (E119). Exported in the
        # environment so both configure's child processes and GNU make (which
        # appends to an environment-origin CPPFLAGS) see it.
        os.environ["CPPFLAGS"] = (os.environ.get("CPPFLAGS", "") +
                                  " -D_UAPI_LINUX_SOCKET_H "
                                  "-D__kernel_sa_family_t=sa_family_t").strip()
        cc = self._cc()
        # Export CC for every make invocation: upstream's `%.o` rule writes
        # `.depend/%.d` after the object file, so the depfile ends up newer
        # than the object and GNU make rebuilds everything from `make check`
        # onwards. Without an explicit CC those rebuilds fall back to make's
        # built-in `cc`, which does not exist on OHOS (make: cc: No such file
        # or directory -> Error 127).
        os.environ["CC"] = cc
        src = self.source_folder

        # 1. configure — cross branch, nftables backend (see module docstring)
        self._run('sh "%s/configure" --host-os=Linux --host-os-version=1.12.0 '
                  '--host-machine=aarch64 --firewall=nftables' % src,
                  label="configure")
        for required in ("config.h", "config.mk", "Makefile", ".configure.cache"):
            if not os.path.isfile(os.path.join(self.build_folder, required)):
                raise ConanException("configure did not produce %s" % required)

        # 2. build everything upstream builds with TESTS=1 (daemon + 11 tests)
        self._run("make CC=\"%s\" -j1" % cc, label="make")

        # 3. layer 1 — the upstream test suite, verbatim `make check`
        self._run('make CC="%s" check' % cc, label="make check",
                  keep=r"touch validate|test OK|tests OK|test FAILED|"
                       r"\./miniupnpd --version|^miniupnpd |backend|"
                       r"make(?:\[\d+\])?: \*\*\*")

        # 4. layer 1b — upstream test programs `make check` does not drive
        cases = []
        for label, cmd in _STANDALONE_CASES:
            rc, out = self._case(label, cmd)
            cases.append({"case": label, "cmd": cmd, "rc": rc,
                          "passed": rc == 0})
            if rc != 0:
                raise ConanException("upstream test %s failed (rc=%s)" % (label, rc))

        passed = len(_CHECK_TARGETS) + sum(1 for c in cases if c["passed"])
        result = {
            "status": "passed",
            "framework": "upstream-makefile",
            "command": "make check (4 validate targets: %s) + standalone: %s"
                       % (",".join(_CHECK_TARGETS),
                          "; ".join("%s=%s" % (c["case"], c["cmd"]) for c in cases)),
            # N = candidate-max census: all 23 upstream test*.c programs in the
            # 2.3.10 source tree (see reports/upstream-tests.md for the
            # per-item attribution of the 16 that are not executed here).
            "discovered": 23,
            "executed": passed,
            "passed": passed,
            "failed": 0,
            "skipped": 23 - passed,
            "cases": cases,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s"
                         % json.dumps(result, separators=(",", ":")))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------------- package
    def package(self):
        copy(self, "miniupnpd", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "miniupnpd.conf", src=os.path.join(self.source_folder),
             dst=os.path.join(self.package_folder, "share", "miniupnpd"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # netfilter_nft helper scripts installed by upstream `make install`
        copy(self, "*.sh", src=os.path.join(self.source_folder,
                                            "netfilter_nft", "scripts"),
             dst=os.path.join(self.package_folder, "share", "miniupnpd"))
        try:
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("pkg_config_name", "miniupnpd")
