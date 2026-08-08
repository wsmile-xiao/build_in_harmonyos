#!/usr/bin/env python3
"""Conan recipe — arm-none-eabi-binutils 2.46.1 (HarmonyOS PC)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv
import os
import shutil
import subprocess


class ArmnoneeabibinutilsConan(ConanFile):
    name = "arm-none-eabi-binutils"
    version = "2.46.1"
    description = "GNU Binutils for arm-none-eabi cross development (HarmonyOS PC)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/binutils/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "site-stty-fix.exp", self.recipe_folder, self.export_sources_folder)
        copy(self, "tmpfile-shim.c", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--target=arm-none-eabi")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")
        tc.configure_args.append("--disable-gdb")
        tc.configure_args.append("--disable-gdbserver")
        tc.configure_args.append("--disable-libdecnumber")
        tc.configure_args.append("--disable-readline")
        tc.configure_args.append("--disable-sim")
        # Bypass config.guess detection on OHOS
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Note: umask 077 → umask 022 for HMDFS compatibility is applied via
        # patches/0004-configure-umask.patch (declared in conandata.yml).
        # No runtime sed rewriting of generated configure files.
        autotools = Autotools(self)
        autotools.configure(build_script_folder=self.source_folder)
        autotools.make(args=["-j1"])
        # Run upstream DejaGNU testsuite with OHOS spawn stty fix.
        # Makefile is generated in build_folder (out-of-tree configure), so
        # make check must run there. site-stty-fix.exp is exported to the
        # build folder via export_sources + layout; fall back to source if absent.
        # Ensure site-stty-fix.exp is present in the build folder (where
        # make check runs), then inject it via DEJAGNU.
        site_fix = os.path.join(self.build_folder, "site-stty-fix.exp")
        if not os.path.exists(site_fix):
            for src in (os.path.join(self.source_folder, "site-stty-fix.exp"),
                        os.path.join(self.build_folder, "..", "site-stty-fix.exp")):
                if os.path.exists(src):
                    self.run("cp -f \"%s\" \"%s\"" % (src, site_fix))
                    break
        # OHOS libc tmpfile() ignores TMPDIR and hits EACCES on the system
        # temp dir, breaking libctf ctf_link_write (ctf-compressed test).
        # Build a minimal tmpfile() shim and inject via LD_PRELOAD so the
        # upstream testsuite runs unmodified. No test expectation changes.
        shim_src = os.path.join(self.build_folder, "tmpfile-shim.c")
        shim_so = os.path.join(self.build_folder, "tmpfile-shim.so")
        if not os.path.exists(shim_src):
            for src in (os.path.join(self.source_folder, "tmpfile-shim.c"),
                        os.path.join(self.build_folder, "..", "tmpfile-shim.c")):
                if os.path.exists(src):
                    self.run("cp -f \"%s\" \"%s\"" % (src, shim_src))
                    break
        cc = None
        # Prefer the compiler Conan toolchain configured via conf.
        # Profile sets tools.build:compiler_executables as a JSON dict
        # (e.g. {"c": ".../clang", "cpp": ".../clang++"}).
        conf_ccs = self.conf_info.get("tools.build:compiler_executables", check_type=dict)
        if conf_ccs:
            cc = conf_ccs.get("c") or conf_ccs.get("cc")
        elif os.environ.get("CC"):
            cc = os.environ["CC"]
        else:
            # Fallback: a clang/cc discoverable on PATH. Never use a
            # machine-specific absolute path.
            cc = shutil.which("clang") or shutil.which("cc")
        if not cc:
            raise RuntimeError(
                "No C compiler found to build tmpfile-shim.so: "
                "tools.build:compiler_executables is unset, CC is unset, and "
                "neither 'clang' nor 'cc' is discoverable on PATH."
            )
        if os.path.exists(shim_src):
            compile_cmd = "\"%s\" -shared -fPIC \"%s\" -o \"%s\"" % (cc, shim_src, shim_so)
            rc = subprocess.call(compile_cmd, shell=True, cwd=self.build_folder)
            if rc != 0 or not os.path.exists(shim_so):
                raise RuntimeError(
                    "B20-FIX: failed to build tmpfile-shim.so (rc=%s, cc=%s); "
                    "testsuite cannot run without it" % (rc, cc)
                )
            self.output.info("B20-FIX: built tmpfile-shim.so with %s" % cc)
        if os.path.exists(site_fix):
            # NOTE: Conan 2.x self.run(env=[...]) treats list items as env-file
            # generator names, NOT literal VAR=value assignments. Use a shell
            # prefix so DEJAGNU and LD_PRELOAD propagate to all children.
            self.output.info("B20-FIX: injecting DEJAGNU=%s" % site_fix)
            ldpreload = "LD_PRELOAD=%s " % shim_so if os.path.exists(shim_so) else ""
            self.run("%sDEJAGNU=%s make -k -j1 check" % (ldpreload, site_fix),
                     cwd=self.build_folder)
        else:
            self.output.warn("B20-FIX: site-stty-fix.exp NOT FOUND in build folder")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
