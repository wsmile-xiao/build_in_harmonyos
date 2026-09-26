#!/usr/bin/env python3
"""Conan recipe for memlockd 1.3.1 (upstream single-TU C++ build, plain Makefile, no deps)."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, chmod
from conan.tools.files import export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MemlockdConan(ConanFile):
    name = "memlockd"
    version = "1.3.1"
    description = (
        "Daemon that keeps a configured list of system files resident through "
        "mmap()+mlock() (plus mlockall() for itself), so an administrator can still "
        "log in on a machine that is paging heavily."
    )
    license = "GPL-3.0-only"
    homepage = "https://doc.coker.com.au/projects/memlockd/"
    url = "https://doc.coker.com.au/projects/memlockd/"
    topics = ("daemon", "memory", "mlock", "mlockall", "tool")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # The upstream Makefile compiles in place (`memlockd.cpp -o memlockd`).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _cxx(self):
        """R33: take the C++ driver from the profile conf, verify it is executable,
        and only then fall back to a PATH lookup (the CI profile pins an absolute
        hnp path whose reachability varies with device state)."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        home_cxx = os.path.expanduser("~/usr/local/bin/clang++")
        for cand in ((compilers or {}).get("cpp"), shutil.which("clang++"),
                     shutil.which("c++"), shutil.which("g++"), home_cxx):
            if cand and os.access(cand, os.X_OK):
                return cand
        raise ConanInvalidConfiguration(
            "no executable C++ compiler (checked profile conf, PATH clang++/c++/g++, "
            "~/usr/local/bin/clang++)")

    def build(self):
        apply_conandata_patches(self)
        # Makefile:8 builds `memlockd` from `$(CXX) $(WFLAGS) $(CXXFLAGS) $(LDFLAGS)`.
        # WFLAGS (-Wall -W -Wshadow -Wpointer-arith -Wcast-align -Wwrite-strings
        # -Wcast-qual -pedantic -ffor-scope) is accepted verbatim by OHOS clang 15.0.4
        # (probe: rc=0, zero diagnostics on memlockd.cpp), so no patch is needed.
        # CXX is passed on the command line so it overrides anything the environment
        # carries; there is no configure step and no install target.
        Autotools(self).make(args=["-j1", f'CXX="{self._cxx()}"'], target="all")

    def package(self):
        pkg = self.package_folder
        copy(self, "memlockd", src=self.build_folder,
             dst=os.path.join(pkg, "bin"))
        chmod(self, os.path.join(pkg, "bin", "memlockd"), 0o755)
        # Upstream hard-codes the config path as /etc/memlockd.cfg (memlockd.cpp:39)
        # and /etc here is a symlink into the read-only /system/etc, so the sample
        # config ships under res/ and is selected at runtime with -c.
        copy(self, "memlockd.cfg", src=self.source_folder,
             dst=os.path.join(pkg, "res"))
        copy(self, "memlockd.8", src=self.source_folder,
             dst=os.path.join(pkg, "share", "man", "man8"))
        copy(self, "memlockd.cpp", src=self.source_folder,
             dst=os.path.join(pkg, "res", "source"))
        self._sign_bins()

    def _sign_bins(self):
        """OHOS kernels only exec ELFs carrying a valid .codesign section; the
        clang+lld link leaves the placeholder empty (abx/0.1 precedent)."""
        signer = (shutil.which("binary-sign-tool")
                  or os.environ.get("OHOS_BINARY_SIGN_TOOL", ""))
        if not signer or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool not found on PATH (set OHOS_BINARY_SIGN_TOOL)")
        path = os.path.join(self.package_folder, "bin", "memlockd")
        out = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", out,
                        "-selfSign", "1"], check=True, timeout=60)
        os.chmod(out, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(out, path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.builddirs = []
        self.cpp_info.frameworkdirs = []
        self.cpp_info.appdirs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
