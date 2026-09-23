#!/usr/bin/env python3
"""Conan recipe for dhcpoptinj 0.5.3 — DHCP option injector (direct cc).

Upstream: https://github.com/misje/dhcpoptinj (tag 0.5.3,GPL-3.0)
Binary: sbin/dhcpoptinj (netfilter NFQUEUE based DHCP mangler).

OHOS adaptation:
- libnfnetlink 1.0.2, libmnl 1.0.5, libnetfilter_queue 1.0.5 are all
  built inline from netfilter.org tarballs (additional_sources),
  installed into build-folder prefixes and consumed via -I/-L
  + PKG_CONFIG_PATH (no shared /usr/local pollution, R49).
  Prefixes are populated by pure-Python staging (.libs/*.a + include/
  + generated .pc), not `make install`: on HMFS the install shim lands
  nothing and libtool's post-install chmod then hard-fails (same class
  as the buildtorrent 0.9.1 install-sh fallback-copy precedent).
  Inline vendoring avoids the conancenter libnfnetlink/1.0.2 recipe whose
  validate() rejects os=OHOS ("only supported on Linux"), which breaks
  the dependency graph on HarmonyOS even though an OHOS-adapted recipe
  exists locally (remote resolution prefers the conancenter revision).
- HMDFS compat: umask 077 -> 022 fix for autotools configure scripts,
  stub config.guess/config.sub (report aarch64-unknown-linux-gnu),
  compat_fixup.h for OHOS socket header conflicts.
- Shell compat (2026-09-11 preflight): profile CONFIG_SHELL points at
  /data/service/hnp/bin/bash which is inaccessible on the worker
  (configure[157] re-exec -> Error 127); recipe forces
  CONFIG_SHELL=SHELL=/bin/sh (HMBS-injected) and runs
  `sh ./configure` per ADAPTATION_GUIDE §8.
- nfnetlink header compat (2026-09-11 preflight): staged
  libnfnetlink/linux_nfnetlink.h redefines nfnetlink_groups /
  NFNLGRP_* / nfgenmsg vs OHOS sysroot <linux/netfilter/nfnetlink.h>
  (10 errors in libnetfilter_queue nlmsg.lo); nfnl_wrapper shadows it
  and forwards to the system header (fprobe-ulog/1.2 precedent).
- Upstream has no test suite (no tests/ dir, no ctest, .travis only builds),
  so build() does not call cmake.test(); the no-tests audit lives in
  test_package/MANIFEST.yml (upstream_tests_exist: false).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.layout import basic_layout


class DhcpoptinjConan(ConanFile):
    name = "dhcpoptinj"
    version = "0.5.3"
    description = "DHCP option injector (NFQUEUE based)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/misje/dhcpoptinj"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("dhcp", "netfilter", "nfqueue")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dhcpoptinj is built for Linux/OHOS only"
            )

    def requirements(self):
        pass  # all netfilter deps are vendored inline (see build())

    def build_requirements(self):
        # libnetfilter_queue's configure uses PKG_CHECK_MODULES(LIBMNL)
        # which hard-requires a pkg-config binary; the HMBS worker image
        # has none in PATH (2026-09-11 preflight: "The pkg-config script
        # could not be found"). Precedent: burp2/2.1.0, capt_agent/6.4.4.
        self.tool_requires("pkgconf/3.0.5")

    def generate(self):
        # No CMakeToolchain: upstream is 5 C files + find_library; CMake 4.4
        # has no Platform/HarmonyOS module so project() compiler check fails
        # (see build()). Direct cc needs only VirtualBuildEnv (pkgconf).
        VirtualBuildEnv(self).generate()
        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.vars(self).save_script("dhcpoptinj_env")

    def _create_compat_header(self):
        save(
            self,
            os.path.join(self.build_folder, "compat_fixup.h"),
            """/* compat_fixup.h - Fix header conflicts on HarmonyOS */
#ifndef _COMPAT_FIXUP_H
#define _COMPAT_FIXUP_H
#include <sys/socket.h>
#define _UAPI_LINUX_SOCKET_H
#ifndef __KERNEL_SA_FAMILY_T
#define __KERNEL_SA_FAMILY_T
typedef unsigned short __kernel_sa_family_t;
#endif
#endif
""",
        )

    def _create_nfnl_wrapper(self, wrapper_dir):
        """Create wrapper header for libnfnetlink to resolve OHOS SDK conflict.

        Precedent: fprobe-ulog/1.2. The vendored
        libnfnetlink/linux_nfnetlink.h is a stale copy of the kernel
        header and redefines nfnetlink_groups / NFNLGRP_* / nfgenmsg
        already provided by the OHOS sysroot
        <linux/netfilter/nfnetlink.h> (true error in this preflight:
        10 redefinition errors in libnetfilter_queue-1.0.5/src/nlmsg.lo).
        The wrapper shadows the stale header via -I priority and
        forwards to the system header, then pulls the compat header
        for the remaining compat definitions.
        """
        wrapper_path = os.path.join(wrapper_dir, "libnfnetlink", "linux_nfnetlink.h")
        os.makedirs(os.path.dirname(wrapper_path), exist_ok=True)
        save(
            self,
            wrapper_path,
            '/* Wrapper: forward to system kernel header to avoid conflicts */\n'
            '#ifndef _UAPI_NFNETLINK_H\n'
            '#include <linux/netfilter/nfnetlink.h>\n'
            '#endif\n'
            '#include <libnfnetlink/linux_nfnetlink_compat.h>\n',
        )

    def _create_config_guess_sub(self, dest_dir):
        save(
            self,
            os.path.join(dest_dir, "config.guess"),
            '#!/bin/sh\necho "aarch64-unknown-linux-gnu"\nexit 0\n',
        )
        try:
            os.chmod(os.path.join(dest_dir, "config.guess"), 0o755)
        except OSError:
            self.output.warning("chmod config.guess ignored (HMBS_CAP_CHMOD=0)")
        save(
            self,
            os.path.join(dest_dir, "config.sub"),
            '#!/bin/sh\necho "$1"\nexit 0\n',
        )
        try:
            os.chmod(os.path.join(dest_dir, "config.sub"), 0o755)
        except OSError:
            self.output.warning("chmod config.sub ignored (HMBS_CAP_CHMOD=0)")

    def _fix_umask(self, file_path):
        try:
            replace_in_file(self, file_path, "umask 077", "umask 022")
        except Exception as e:
            self.output.warning(f"Failed to fix umask in {file_path}: {e}")

    def _build_autotools_dep(self, name, src_dir, prefix, extra_env=""):
        ba = os.path.join(src_dir, "build-aux")
        if os.path.isdir(ba):
            shutil.copy(os.path.join(src_dir, "config.guess"), ba)
            shutil.copy(os.path.join(src_dir, "config.sub"), ba)
        cfg = os.path.join(src_dir, "configure")
        if os.path.isfile(cfg):
            self._fix_umask(cfg)
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        # Preflight 2026-09-11: profile exports
        # CONFIG_SHELL=/data/service/hnp/bin/bash, but that path is
        # inaccessible on this worker, and autoconf configure re-execs
        # itself via $CONFIG_SHELL (-> line 157 Error 127). HMBS injects
        # SHELL=/bin/sh and reports shell=/bin/sh, so force both vars to
        # the working shell and invoke configure through it (GUIDE §8).
        shell = "/bin/sh" if os.path.isfile("/bin/sh") else "sh"
        self.run(
            f'cd "{src_dir}" && '
            f"CC=clang {extra_env} "
            f'TMPDIR="{tmp_dir}" CONFIG_SHELL="{shell}" SHELL="{shell}" '
            f'"{shell}" ./configure --prefix="{prefix}" --disable-shared --enable-static && '
            f"make -j1",
            env="conanbuild",
        )
        self._stage_autotools_dep(name, src_dir, prefix)

    def _stage_autotools_dep(self, name, src_dir, prefix):
        """Stage an inline autotools dep without `make install`.

        Preflight 2026-09-11 (libnfnetlink): `make install` goes through
        install-sh + libtool's post-install `chmod 644`, but on HMFS the
        install shim lands nothing (HMBS_CAP_CHMOD=0) so chmod hard-fails
        with "No such file or directory" and the build aborts — same
        "install-sh在HMFS未落盘" class as the buildtorrent 0.9.1
        package() fallback-copy precedent. Only static archives, public
        headers and generated .pc files are needed downstream, so copy
        them with pure-Python file ops into the build-folder prefix.
        """
        libdir = os.path.join(prefix, "lib")
        pcdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(pcdir, exist_ok=True)
        staged_libs = []
        for root, _dirs, files in os.walk(src_dir):
            if os.path.basename(root) != ".libs":
                continue
            for fname in files:
                if fname.endswith(".a"):
                    dst = os.path.join(libdir, fname)
                    shutil.copyfile(os.path.join(root, fname), dst)
                    staged_libs.append(dst)
        src_inc = os.path.join(src_dir, "include")
        staged_headers = 0
        if os.path.isdir(src_inc):
            for root, _dirs, files in os.walk(src_inc):
                rel = os.path.relpath(root, src_inc)
                dest_dir = (
                    os.path.join(prefix, "include")
                    if rel == "."
                    else os.path.join(prefix, "include", rel)
                )
                os.makedirs(dest_dir, exist_ok=True)
                for fname in files:
                    if fname.endswith(".h"):
                        shutil.copyfile(
                            os.path.join(root, fname),
                            os.path.join(dest_dir, fname),
                        )
                        staged_headers += 1
        staged_pc = []
        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                if fname.endswith(".pc") and not fname.endswith(".pc.in"):
                    dst = os.path.join(pcdir, fname)
                    shutil.copyfile(os.path.join(root, fname), dst)
                    staged_pc.append(dst)
        self.output.info(
            "staged %s: %d lib(s), %d header(s), %d pc file(s) into %s"
            % (name, len(staged_libs), staged_headers, len(staged_pc), prefix)
        )
        if not staged_libs:
            raise ConanInvalidConfiguration(
                "manual staging of %s found no static archive under %s"
                % (name, src_dir)
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        self._create_compat_header()
        compat_h = os.path.join(self.build_folder, "compat_fixup.h")

        cflags_base = f"-fPIC -O2 -include {compat_h}"

        # --- libnfnetlink (inline; avoids conancenter recipe that rejects OHOS) ---
        nfnl_prefix = os.path.join(self.build_folder, "deps", "libnfnetlink")
        os.makedirs(nfnl_prefix, exist_ok=True)
        get(
            self,
            **self.conan_data["additional_sources"]["libnfnetlink"],
            destination=self.build_folder,
            strip_root=False,
        )
        nfnl_src = os.path.join(self.build_folder, "libnfnetlink-1.0.2")
        self._create_config_guess_sub(nfnl_src)
        nfnl_include = os.path.join(nfnl_prefix, "include")
        nfnl_libdir = os.path.join(nfnl_prefix, "lib")
        self._build_autotools_dep(
            "libnfnetlink",
            nfnl_src,
            nfnl_prefix,
            extra_env=f'CFLAGS="{cflags_base}"',
        )

        # --- libmnl (inline) ---
        libmnl_prefix = os.path.join(self.build_folder, "deps", "libmnl")
        os.makedirs(libmnl_prefix, exist_ok=True)
        get(
            self,
            **self.conan_data["additional_sources"]["libmnl"],
            destination=self.build_folder,
            strip_root=False,
        )
        libmnl_src = os.path.join(self.build_folder, "libmnl-1.0.5")
        self._create_config_guess_sub(libmnl_src)
        self._build_autotools_dep(
            "libmnl",
            libmnl_src,
            libmnl_prefix,
            extra_env=f'CFLAGS="{cflags_base}"',
        )

        # --- libnetfilter_queue (inline, needs libmnl + libnfnetlink) ---
        # OHOS sysroot already ships <linux/netfilter/nfnetlink.h>; the
        # staged libnfnetlink/linux_nfnetlink.h would redefine
        # nfnetlink_groups / NFNLGRP_* / nfgenmsg (10 errors in nlmsg.lo).
        # Shadow it with the nfnl_wrapper (fprobe-ulog/1.2 precedent) via
        # -I priority so downstream includes resolve to the forwarder.
        wrapper_dir = os.path.join(self.build_folder, "nfnl_wrapper")
        self._create_nfnl_wrapper(wrapper_dir)
        nfq_prefix = os.path.join(self.build_folder, "deps", "libnetfilter_queue")
        os.makedirs(nfq_prefix, exist_ok=True)
        get(
            self,
            **self.conan_data["additional_sources"]["libnetfilter_queue"],
            destination=self.build_folder,
            strip_root=False,
        )
        nfq_src = os.path.join(self.build_folder, "libnetfilter_queue-1.0.5")
        self._create_config_guess_sub(nfq_src)
        nfq_cflags = (
            f"{cflags_base} -I{wrapper_dir} -I{libmnl_prefix}/include -I{nfnl_include}"
        )
        nfq_extra = (
            f'CFLAGS="{nfq_cflags}" '
            f'LDFLAGS="-L{libmnl_prefix}/lib -L{nfnl_libdir}" '
            f'LIBMNL_CFLAGS="-I{libmnl_prefix}/include" '
            f'LIBMNL_LIBS="-L{libmnl_prefix}/lib -lmnl" '
            f'LIBNFNETLINK_CFLAGS="-I{wrapper_dir} -I{nfnl_include}" '
            f'LIBNFNETLINK_LIBS="-L{nfnl_libdir} -lnfnetlink" '
            f'PKG_CONFIG_PATH="{libmnl_prefix}/lib/pkgconfig:{nfnl_prefix}/lib/pkgconfig" '
        )
        self._build_autotools_dep("libnetfilter_queue", nfq_src, nfq_prefix, nfq_extra)

        # --- dhcpoptinj (direct cc; bypass CMake 4.4/HarmonyOS platform check) ---
        # 2nd strategy cycle: the previous three rounds all stayed on the
        # CMakeToolchain + project() path (1: POLICY_MINIMUM=3.5, 2:
        # SYSTEM_NAME=Linux override, 3: toolchain-append for CFLAGS) and all
        # still die at CMakeLists.txt:19 project() with "C compiler
        # identification is unknown" for /data/service/hnp/bin/clang. That
        # proves the root cause is not flag passing but the platform mapping
        # itself: forcing Linux discards the OHOS sysroot/target flags the
        # wrapper needs, while keeping HarmonyOS has no Platform module on
        # CMake 4.4. Upstream is only 5 C files + find_library(netfilter_queue)
        # (see upstream CMakeLists), so compile directly with the same PATH
        # clang that already built the inline autotools deps (fprobe-ulog/1.2
        # precedent: no CMakeToolchain for the main package). This also
        # sidesteps the cmake_minimum_required(3.0) floor without patching.
        srcs = ["config.c", "dhcp.c", "dhcpoptinj.c", "ipv4.c", "options.c"]
        src_abs = " ".join(
            f'"{os.path.join(self.source_folder, "src", _s)}"' for _s in srcs
        )
        out_bin = os.path.join(self.build_folder, "dhcpoptinj")
        cflags = (
            "-std=c99 -O2 -fPIC "
            "-D_POSIX_SOURCE -D_DEFAULT_SOURCE -D_FORTIFY_SOURCE=2 "
            "'-DDHCPOPTINJ_VERSION=\"0.5.3\"' "
            f'-include "{compat_h}" '
            f'-I"{wrapper_dir}" -I"{nfq_prefix}/include" '
            f'-I"{libmnl_prefix}/include" -I"{nfnl_include}" '
            f'-I"{os.path.join(self.source_folder, "src")}"'
        )
        ldflags = (
            f'-L"{nfq_prefix}/lib" '
            f'-L"{libmnl_prefix}/lib" -L"{nfnl_libdir}"'
        )
        self.run(
            f'clang {cflags} {src_abs} {ldflags} '
            f"-lnetfilter_queue -lmnl -lnfnetlink -o \"{out_bin}\"",
            env="conanbuild",
        )
        # NOTE: upstream provides no test suite (no tests/ dir, no ctest
        # registration; .travis.yml only runs cmake + make). Intentionally
        # no cmake.test() call; audit in test_package/MANIFEST.yml.

    def package(self):
        copy(
            self,
            "dhcpoptinj",
            src=os.path.join(self.build_folder),
            dst=os.path.join(self.package_folder, "sbin"),
        )
        # Fallback: cmake single-config output may land under build/ subdir.
        if not os.path.isfile(os.path.join(self.package_folder, "sbin", "dhcpoptinj")):
            for root, _, files in os.walk(self.build_folder):
                if "dhcpoptinj" in files and root.endswith("build"):
                    copy(self, "dhcpoptinj", src=root,
                         dst=os.path.join(self.package_folder, "sbin"))
                    break

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
