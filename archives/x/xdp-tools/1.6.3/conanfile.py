#!/usr/bin/env python3
"""Conan recipe — xdp-tools 1.6.3 (custom shell configure + GNU Make).

SOURCE: upstream xdp-tools official release asset. mkarchive.sh bundles the
libbpf git submodule, but this recipe deliberately consumes the published
libbpf/1.5.1 conan package instead (FORCE_SYSTEM_LIBBPF=1), and gets libpcap
from the published libpcap/1.10.6 package (needed by xdp-dump).

OHOS build notes:
  * configure is a hand-written shell script (not autoconf). It finds a system
    libbpf through pkg-config and then runs 15 compile+link probes for
    individual libbpf symbols. None of the probes executes a program, so the
    script is cross-compilation friendly (no can_run needed).
  * XDP programs are compiled with clang -target bpf and (for the skeleton
    based tools) turned into headers with bpftool. Without a working bpftool
    the top Makefile only builds xdp-filter/xdp-loader/xdp-dump; that is
    upstream behaviour, not an adaptation defect.
  * configure only probes zlib/libelf/libpcap on the vendored-libbpf branch,
    which FORCE_SYSTEM_LIBBPF skips; libpcap's include/lib dirs are therefore
    injected explicitly via CFLAGS/LDFLAGS.
  * The in-tree lib/libxdp is built and installed together with the tools
    (upstream has no external-libxdp switch); the standalone libxdp/1.6.3
    package remains the canonical library.
  * musl has no public secure_getenv and upstream's fallback reads the
    musl-internal libc.secure; patched (see conandata.yml).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class XdpToolsConan(ConanFile):
    name = "xdp-tools"
    version = "1.6.3"
    description = "Command-line tools for XDP/eBPF (xdp-loader, xdp-filter, xdp-dump, ...)"
    license = "GPL-2.0-only AND LGPL-2.1-only AND BSD-2-Clause"
    homepage = "https://github.com/xdp-project/xdp-tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libbpf 1.5.0 is the upstream gitlink; 1.5.1 is the published patch
        # release of the same minor (static-only, pulls elfutils/zlib).
        self.requires("libbpf/1.5.1")
        # xdp-dump/Makefile hard-codes -lpcap.
        self.requires("libpcap/1.10.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- build environment (shared with the libxdp recipe) -----------------
    def _cc(self):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return exes.get("c") or "clang"

    @staticmethod
    def _pick(cc_dir, names, fallback):
        # prefer the LLVM tools shipped next to the configured compiler
        # (DevEco SDK in WSL; /data/service/hnp/bin on the OHOS device).
        if cc_dir:
            for n in names:
                cand = os.path.join(cc_dir, n)
                if os.path.exists(cand):
                    return cand
        for n in names:
            p = shutil.which(n)
            if p:
                return p
        return fallback

    def _bash(self):
        # OHOS /tmp is read-only; the shell must be bash (it honours TMPDIR for
        # here-documents) and TMPDIR must point at a writable directory.
        for c in (os.environ.get("CONFIG_SHELL"), "/data/service/hnp/bin/bash",
                  shutil.which("bash"), "/bin/bash"):
            if c and os.path.exists(c):
                return c
        return "bash"

    @staticmethod
    def _default_includes(cc):
        # The XDP programs are built with `clang -target bpf`, for which the
        # compiler does not apply its default sysroot search list. Ask the
        # configured compiler for its own include dirs (incl. the OHOS sysroot)
        # and hand them to the Makefile via ARCH_INCLUDES.
        try:
            p = subprocess.run([cc, "-E", "-Wp,-v", "-xc", "-"], input="",
                               text=True, capture_output=True, timeout=60)
        except Exception:
            return ""
        dirs, capture = [], False
        for line in (p.stderr or "").splitlines():
            if "include <...> search starts here" in line:
                capture = True
                continue
            if "End of search list" in line:
                break
            if capture:
                d = line.strip()
                if d.startswith("/") and os.path.isdir(d):
                    dirs.append(d)
        return " ".join("-I" + d for d in dirs)

    def _pcap_flags(self):
        # configure only runs check_pcap() on the vendored-libbpf branch, which
        # we skip; inject the dependency's resolved include/lib dirs instead.
        try:
            agg = self.dependencies["libpcap"].cpp_info.aggregated_components()
        except Exception:
            return "", ""
        cflags = " ".join("-I" + d for d in (getattr(agg, "includedirs", None) or []))
        ldflags = " ".join("-L" + d for d in (getattr(agg, "libdirs", None) or []))
        return cflags, ldflags

    def _env(self):
        cc = self._cc()
        cc_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        pcap_cflags, pcap_ldflags = self._pcap_flags()
        cflags = "-O2 -g" + (" " + pcap_cflags if pcap_cflags else "")
        env = {
            "CC": cc,
            "CLANG": self._pick(cc_dir, ["clang"], "clang"),
            "OBJCOPY": self._pick(cc_dir, ["llvm-objcopy", "objcopy"], "objcopy"),
            "READELF": self._pick(cc_dir, ["llvm-readelf", "readelf"], "readelf"),
            "M4": self._pick(cc_dir, ["m4"], "m4"),
            "PKG_CONFIG": self._pick(cc_dir, ["pkg-config"], "pkg-config"),
            "FORCE_SYSTEM_LIBBPF": "1",
            "EMACS": "emacs",
            "TMPDIR": tmpdir,
            "ARCH_INCLUDES": self._default_includes(cc),
            "PKG_CONFIG_PATH": self.generators_folder,
            "CFLAGS": cflags,
        }
        if pcap_ldflags:
            env["LDFLAGS"] = pcap_ldflags
        return env

    def _prefix(self):
        # Inline env assignments: the custom configure/Makefiles need these
        # in the process environment of the shell that runs them.
        return " ".join('%s="%s"' % (k, v) for k, v in self._env().items())

    def generate(self):
        # libbpf/1.5.1 declares pkg_config_name=libbpf; PkgConfigDeps also
        # resolves its static transitive deps (elfutils/zlib) in --libs.
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        p = self._prefix()
        self.run(p + ' "%s" configure' % self._bash(), cwd=self.source_folder)
        # OHOS only: bionic exposes the UAPI UDP header as struct
        # __kernel_udphdr and keeps struct udphdr in the libc-only
        # <netinet/udp.h>; tell the vendored parsing helper (patches/0007) to
        # restore the conventional UAPI name for bpf targets. HAVE_FEATURES is
        # the upstream mechanism (configure itself writes
        # HAVE_FEATURES+=BPFTOOL); lib/defines.mk:33 turns it into
        # -DHAVE_<feat> for both CFLAGS and BPF_CFLAGS. Gated on OHOS so the
        # recipe stays transparent on other platforms, and idempotent so a
        # repeated build does not append twice.
        if str(self.settings.os) == "OHOS":
            config_mk = os.path.join(self.source_folder, "config.mk")
            with open(config_mk, "r", encoding="utf-8") as fh:
                cfg = fh.read()
            if "OHOS_BPF" not in cfg:
                with open(config_mk, "a", encoding="utf-8") as fh:
                    fh.write("\n# conan recipe: OHOS bionic UAPI naming\nHAVE_FEATURES += OHOS_BPF\n")
        self.run(p + " make V=0 -j1", cwd=self.source_folder)

    def package(self):
        self.run(self._prefix() + ' make install V=0 PREFIX="%s"' % self.package_folder,
                 cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSES/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # OHOS: the SDK clang leaves only an unusable .codesign placeholder, so
        # the kernel refuses to exec the installed tools (EPERM / Error 126).
        # Re-sign every packaged executable on the device (E077/E077B pattern,
        # same as pan/0.165).  On a cross build the signing tool is absent and
        # qemu does not enforce codesign, so skip it there.
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elfs()

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS signing of %s" % path)
            return
        if os.path.isfile(objcopy):
            self.run('%s --remove-section .codesign "%s"' % (objcopy, path),
                     ignore_errors=True)
        signed = path + ".signed"
        self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, path, signed))
        if os.path.isfile(readelf):
            sec = subprocess.run([readelf, "-SW", signed],
                                 capture_output=True, text=True).stdout
            if sec.count(".codesign") != 1:
                raise ConanException("signed %s has invalid .codesign count" % path)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def _sign_ohos_elfs(self):
        sbin = os.path.join(self.package_folder, "sbin")
        if not os.path.isdir(sbin):
            return
        for name in sorted(os.listdir(sbin)):
            p = os.path.join(sbin, name)
            if os.path.isfile(p):
                self._sign_ohos_elf(p)

    def package_info(self):
        # The tools land in sbin/; the in-tree libxdp archive/headers are
        # installed next to them. Consumers that need the library should use
        # the standalone libxdp/1.6.3 package.
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
