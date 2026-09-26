#!/usr/bin/env python3
"""Conan recipe — libxdp 1.6.3 (xdp-tools, custom shell configure + GNU Make).

SOURCE: upstream xdp-tools official release asset. Its mkarchive.sh bundles the
libbpf git submodule, but this recipe deliberately consumes the published
libbpf/1.5.1 conan package instead (FORCE_SYSTEM_LIBBPF=1).

OHOS build notes:
  * configure is a hand-written shell script (not autoconf). It finds a system
    libbpf through pkg-config and then runs 15 compile+link probes for
    individual libbpf symbols. None of the probes executes a program, so the
    script is cross-compilation friendly (no can_run needed).
  * libxdp's embedded XDP programs are compiled with clang -target bpf and
    then embedded with ld -r --format=binary + llvm-objcopy --rename-section.
    Both are supported by the OHOS SDK LLVM 15.
  * musl has no public secure_getenv and upstream's fallback reads the
    musl-internal libc.secure; patched (see conandata.yml).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class LibxdpConan(ConanFile):
    name = "libxdp"
    version = "1.6.3"
    description = "Library for loading XDP programs (xdp-tools)"
    license = "LGPL-2.1-only OR BSD-2-Clause"
    homepage = "https://github.com/xdp-project/xdp-tools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libxdp 1.6.3 pins libbpf 1.5.0 (gitlink 09b9e831...); 1.5.1 is the
        # published patch release of the same minor. It is a static-only
        # package and pulls elfutils/zlib transitively.
        self.requires("libbpf/1.5.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---- build environment -------------------------------------------------
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
        # and hand them to the Makefile via ARCH_INCLUDES, so the BPF compile
        # finds <linux/types.h> from the sysroot too.
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

    def _env(self):
        cc = self._cc()
        cc_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        return {
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
        }

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
        self.run(p + " make libxdp V=0", cwd=self.source_folder)

    def package(self):
        # install straight into the package folder so the generated
        # libxdp.pc gets the correct absolute prefix.
        self.run(self._prefix() + ' make libxdp_install V=0 PREFIX="%s"' % self.package_folder,
                 cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSES/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["xdp"]
        self.cpp_info.includedirs = ["include"]     # headers land in include/xdp/
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libxdp")
        # public header <xdp/libxdp.h> includes <bpf/libbpf.h>: propagate the
        # libbpf include dirs/libs to consumers (both static and shared).
        self.cpp_info.requires = ["libbpf::libbpf"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]