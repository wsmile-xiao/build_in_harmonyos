#!/usr/bin/env python3
"""Conan recipe for mgen 5.02.c5.1.1 — NRL Multi-Generator network traffic tool.

mgen (Multi-Generator) is the NRL PROTocol Engineering Advanced Networking
(PROTEAN) tool for IP network performance tests and measurements using UDP
and TCP traffic. Upstream: https://github.com/USNavalResearchLaboratory/mgen

Version mapping: this recipe tracks upstream release V5.1.1 (MGEN_VERSION
"5.1.1" in include/mgenVersion.h, VERSION.TXT lineage 5.02c). The recipe
version 5.02.c5.1.1 follows the Debian source versioning
(5.02.c+really5.1.1) that distinguishes the 5.02c codebase from the 5.1.1
release on top of it.

Build notes:
  * Plain Makefile project (makefiles/Makefile.linux). No configure script,
    no CMake, no install target. `make -f Makefile.linux` builds the `mgen`
    and `mpmgr` binaries into makefiles/; protolib's static libprotokit.a is
    built first as a make prerequisite from the bundled protolib tree.
  * protolib is an upstream git submodule (pinned at 7264863 for V5.1.1) and
    is NOT part of the GitHub tag tarball, so source() fetches it as a second
    official GitHub archive into <source>/protolib (the exact layout the
    Makefiles expect: ../protolib relative to makefiles/).
  * Compiler/linker come from Conan conf tools.build:compiler_executables
    (R33) and are passed on the make command line, which also propagates to
    the protolib sub-make. CC names the C++ compiler (the Makefiles use
    $(CC) = g++ for .cpp files); the recipe passes the conf C++ compiler.
  * OHOS adaptation: the optional HAVE_PCAP/CLONE-from-pcap feature is
    disabled at build time by stripping -DHAVE_PCAP and -lpcap from
    makefiles/Makefile.linux via a plain text replace (no .patch file, so
    no hunk-context mismatch), so the build needs zero
    external dependencies. Rationale: resolving libpcap/1.10.6 from
    conancenter on an OHOS worker pulls the autotools chain
    (bison -> m4/flex) whose configure re-executes
    /data/service/hnp/bin/bash, which is inaccessible on the HarmonyOS PC
    worker (m4/1.4.19 configure[139] error 127 in preflight); the OHOS
    libpcap binary cannot be relied on for every profile, while the pcap
    feature is strictly optional upstream (all HAVE_PCAP code is #ifdef
    guarded) and OHOS raw-socket capture is restricted anyway. Core traffic
    patterns (PERIODIC/POISSON/BURST/JITTER) are unaffected; only the
    CLONE pcap-file replay pattern is unavailable. protolib itself never
    needed pcap (its Makefile.linux links only -ldl -lrt).
  * protolib's Makefile.common references -I/usr/include/libxml2 and
    -lxml2, but protoXml.cpp is NOT part of libprotokit.a (KIT_SRC), and the
    mgen link line does not use protolib's LIBS, so no libxml2 requires.

Upstream tests: mgen V5.1.1 ships NO automated test suite — no tests/ dir,
no check/test Makefile target, no TESTS/check_PROGRAMS, no ctest/gtest/
pytest wiring (see test_package/MANIFEST.yml for the full audit). build()
therefore runs no upstream suite and emits HMBS_UPSTREAM_TEST_RESULT with
status no_tests; test_package validates the packaged binaries as a runtime
consumer check.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MgenConan(ConanFile):
    name = "mgen"
    version = "5.02.c5.1.1"
    package_type = "application"

    description = "NRL Multi-Generator (MGEN): IP network performance test traffic generator"
    license = "BSD-2-Clause"  # NRL permissive notice in LICENSE (custom NRL text, see norm/1.5.9 precedent)
    homepage = "https://www.nrl.navy.mil/itd/ncs/products/mgen"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mgen", "traffic-generator", "network", "performance", "udp", "tcp")

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["mgen"], strip_root=True)
        get(self, **self.conan_data["sources"]["protolib"], strip_root=True,
            destination=os.path.join(self.source_folder, "protolib"))

    @staticmethod
    def _resolve_tool(configured, fallback):
        if configured and os.path.isfile(configured):
            return configured
        if configured:
            found = shutil.which(os.path.basename(configured))
            if found:
                return found
        return fallback

    @staticmethod
    def _target_triple(compiler):
        for flag in ("-print-target-triple", "-dumpmachine"):
            try:
                out = subprocess.run(
                    [compiler, flag], capture_output=True, text=True, timeout=10)
                if out.returncode == 0 and out.stdout.strip():
                    return out.stdout.strip()
            except Exception:
                continue
        return ""

    def build(self):
        # OHOS: strip the optional HAVE_PCAP feature with a plain text
        # replace instead of a .patch file (the tag-tarball bytes differ
        # from a git checkout, so hunk context mismatches fail to apply).
        # Only touches mgen's own makefiles/Makefile.linux; the variables
        # are file assignments, NOT command-line overrides, so nothing
        # leaks into the protolib sub-make (which keeps its own
        # SYSTEM_HAVES/SYSTEM_LIBS).
        mk_linux = os.path.join(self.source_folder, "makefiles", "Makefile.linux")
        with open(mk_linux, "r", encoding="utf-8", errors="replace") as f:
            mk_text = f.read()
        if "-DHAVE_PCAP" not in mk_text and "-lpcap" not in mk_text:
            raise RuntimeError(f"expected HAVE_PCAP/-lpcap markers not found in {mk_linux}")
        mk_text = mk_text.replace("-DHAVE_PCAP", "")
        mk_text = mk_text.replace("-lpcap", "")
        with open(mk_linux, "w", encoding="utf-8", newline="\n") as f:
            f.write(mk_text)
        self.output.info("disabled optional HAVE_PCAP/-lpcap for OHOS (zero external deps)")
        # OHOS musl sysroot compat: <sys/socket.h> (musl) and the kernel UAPI
        # <linux/socket.h> (pulled in by <linux/netlink.h>) both define
        # `struct sockaddr_storage` unconditionally, so any TU including both
        # fails with "redefinition of 'sockaddr_storage'"
        # (linuxRouteMgr.cpp via zebraRouteMgr.h). The kernel copy is not
        # needed here (netlink code only uses sockaddr_nl/nlmsghdr/rtmsg), so
        # hide it with a macro rename. Plain text replace (no .patch file) so
        # tag-tarball byte differences cannot break hunk context. Applied to
        # every protolib source that pulls <linux/netlink.h> (currently
        # include/unix/zebraRouteMgr.h + src/linux/linuxRouteMgr.cpp;
        # zebraRouteMgr.cpp is covered via the header).
        protolib_dir = os.path.join(self.source_folder, "protolib")
        patched = []
        for root, _dirs, files in os.walk(protolib_dir):
            for fname in files:
                if not fname.endswith((".h", ".cpp", ".c")):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                if "<linux/netlink.h>" not in text:
                    continue
                if "__hmbs_kernel_sockaddr_storage" in text:
                    patched.append(os.path.relpath(fpath, self.source_folder))
                    continue
                orig = text
                if "#include <linux/netlink.h>" in text:
                    text = text.replace(
                        "#include <linux/netlink.h>",
                        "#define sockaddr_storage __hmbs_kernel_sockaddr_storage\n"
                        "#include <linux/netlink.h>",
                        1,
                    )
                    if "#include <linux/rtnetlink.h>" in text:
                        text = text.replace(
                            "#include <linux/rtnetlink.h>",
                            "#include <linux/rtnetlink.h>\n"
                            "#undef sockaddr_storage",
                            1,
                        )
                    else:
                        text = text.replace(
                            "#define sockaddr_storage __hmbs_kernel_sockaddr_storage\n"
                            "#include <linux/netlink.h>",
                            "#define sockaddr_storage __hmbs_kernel_sockaddr_storage\n"
                            "#include <linux/netlink.h>\n"
                            "#undef sockaddr_storage",
                            1,
                        )
                if text != orig:
                    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
                        f.write(text)
                    patched.append(os.path.relpath(fpath, self.source_folder))
        if not patched:
            raise RuntimeError("expected <linux/netlink.h> sources not found in protolib")
        self.output.info(f"OHOS netlink header compat applied: {patched}")
        # R33: compilers from Conan conf, never bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = compilers.get("cpp") or compilers.get("c") or "clang++"
        cc_bin = self._resolve_tool(cxx, "clang++")

        bindir = os.path.dirname(cxx) if os.path.sep in (cxx or "") else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "llvm-ar")
        ranlib = compilers.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "llvm-ranlib")
        ar_bin = self._resolve_tool(ar, "llvm-ar")
        ranlib_bin = self._resolve_tool(ranlib, "llvm-ranlib")

        triple = self._target_triple(cc_bin)
        if triple and "ohos" not in triple:
            self.output.warning(f"compiler triple '{triple}' is not an OHOS target")
        self.output.info(f"using CC: {cc_bin} (triple: {triple or 'unknown'})")

        make_dir = os.path.join(self.source_folder, "makefiles")
        # CI hardening (build #70890 EAGAIN): protolib sub-make hit
        # `clang++: Resource temporarily unavailable` (fork/exec EAGAIN,
        # Error 127) after 12+ successful TUs — transient worker pressure,
        # not a source error. Build is already `-j1`; export MAKEFLAGS so a
        # sub-make invoked without $(MAKE) still stays serial.
        os.environ["MAKEFLAGS"] = "-j1"
        self.run(
            f'make -f Makefile.linux -j1 CC="{cc_bin}" CXX="{cc_bin}" '
            f'AR="{ar_bin}" RANLIB="{ranlib_bin}"',
            cwd=make_dir)

        for binary in ("mgen", "mpmgr"):
            path = os.path.join(make_dir, binary)
            if not os.path.isfile(path):
                raise RuntimeError(f"mgen build produced no '{binary}' binary in {make_dir}")

        # HMBS machine evidence: mgen V5.1.1 ships no automated test suite
        # (no check/test make target, no tests/ dir — see
        # test_package/MANIFEST.yml audit), so there is nothing to execute.
        marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make -f Makefile.linux (no check/test target upstream)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("mgen V5.1.1 has no automated test suite: no tests/ "
                       "directory, no check/test Makefile target, no "
                       "TESTS/check_PROGRAMS, no ctest/gtest/pytest wiring; "
                       "full audit in test_package/MANIFEST.yml"),
        }
        msg = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker)}"
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        make_dir = os.path.join(self.source_folder, "makefiles")
        for binary in ("mgen", "mpmgr"):
            copy(self, binary, src=make_dir,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tools, not a library (masscan/mac-robber precedent).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
