#!/usr/bin/env python3
"""Conan recipe — calc 3.0.1.0 (custom Makefile)

calc — C-style arbitrary precision calculator (lcn2/calc).
Build system: custom Makefile (no configure script), serial build only
(parallel make is NOT supported upstream; OHOS additionally has E074
SELinux FIFO constraint). Use `make -j1`.
Optional readline dependency for interactive history.

License: LGPL-2.1
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class CalcConan(ConanFile):
    name = "calc"
    version = "3.0.1.0"
    description = "C-style arbitrary precision calculator — arbitrary precision arithmetic system with a C-like language"
    license = "LGPL-2.1"
    homepage = "http://www.isthe.com/chongo/tech/comp/calc/"
    url = "https://github.com/lcn2/calc"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Export bundled readline headers for CI workers without system readline-devel
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def _get_sysroot(self):
        """Determine sysroot path via Conan conf, avoiding os.environ (R33)."""
        sysroot = self.conf.get("user.build:default_prefix", default=None, check_type=str)
        if not sysroot:
            sysroot = os.path.expanduser("~/usr/local")
        return sysroot

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"calc supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # OHOS: ensure man/gzip wrappers exist for doc generation chain
        bindir = self.build_folder
        man_wrapper = os.path.join(bindir, "man")
        if not os.path.isfile(man_wrapper):
            with open(man_wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("exec /data/service/hnp/bin/groff -Tascii -man \"$@\"\n")
            os.chmod(man_wrapper, 0o755)
        gzip_wrapper = os.path.join(bindir, "gzip")
        if not os.path.isfile(gzip_wrapper):
            with open(gzip_wrapper, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("ARGS=\"\"\n")
                f.write("for a in \"$@\"; do\n")
                f.write('  case "$a" in --best) ARGS="$ARGS -9";; --fast) ARGS="$ARGS -1";; *) ARGS="$ARGS $a";; esac\n')
                f.write("done\n")
                f.write("exec /usr/bin/gzip $ARGS\n")
            os.chmod(gzip_wrapper, 0o755)
        self.run(f"chmod 755 {man_wrapper} {gzip_wrapper}")

        # Set up readline include/lib paths (optional dependency).
        sysroot = self._get_sysroot()
        sys_inc = os.path.join(sysroot, "include")
        sys_lib = os.path.join(sysroot, "lib")

        cppflags = []
        ldflags = []
        use_readline = True

        if os.path.exists(os.path.join(sys_inc, "readline", "readline.h")):
            cppflags.append(f"-I{sys_inc}")
        else:
            bundled_inc = os.path.join(self.source_folder, "res", "headers")
            if os.path.isdir(bundled_inc):
                cppflags.append(f"-I{bundled_inc}")
            else:
                # readline headers unavailable — build without readline support
                use_readline = False
                self.output.info("readline headers not found; building WITHOUT readline support")

        if use_readline:
            readline_so = None
            lib_search_dirs = [sys_lib, os.path.join(sysroot, "lib", "external"), "/lib", "/usr/lib"]
            for lib_dir in lib_search_dirs:
                for name in ("libreadline.so", "libreadline.so.8"):
                    path = os.path.join(lib_dir, name)
                    if os.path.exists(path):
                        readline_so = path
                        ldflags.append(f"-L{lib_dir}")
                        break
                if readline_so:
                    break
            if not readline_so:
                use_readline = False
                self.output.info("libreadline not found; building WITHOUT readline support")

        # R9: Always use -j1, never -j$(nproc). calc does not support parallel make.
        # OHOS: target=Linux (uname -s returns HarmonyOS, Makefile.target needs Linux branch)
        #        LN=cp (HMDFS forbids hard links, E074)
        #        MAN/GZIP override (busybox gzip lacks --best; man not installed)
        base = f"make -j1 target=Linux CC=\"{cc}\" LCC=\"{cc}\" LN=\"cp\" "
        base += f"MAN=\"{man_wrapper}\" GZIP=\"{gzip_wrapper}\" "
        base += "calc-static-only BLD_TYPE=calc-static-only"
        if use_readline:
            cppflags_str = " ".join(cppflags) if cppflags else ""
            ldflags_str = " ".join(ldflags) if ldflags else ""
            base += f" CPPFLAGS=\"{cppflags_str}\" LDFLAGS=\"{ldflags_str}\""
        else:
            base += " USE_READLINE= READLINE_EXTRAS= READLINE_INCLUDE= READLINE_LIB="
        self.run(base)

    def package(self):
        # calc builds calc + cscript binaries and libcalc.a (static lib)
        copy(self, "calc", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cscript", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libcalc.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "calc.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)

    def package_info(self):
        # calc is a command-line tool; provide the static lib info for consumers
        self.cpp_info.libs = ["calc"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # Add bin to PATH so consumers (test_package) can find calc binary
        self.runenv_info.prepend_path("PATH", "bin")
        sysroot = self._get_sysroot()
        lib_external = os.path.join(sysroot, "lib", "external")
        if os.path.isdir(lib_external):
            self.runenv_info.append_path("LD_LIBRARY_PATH", lib_external)