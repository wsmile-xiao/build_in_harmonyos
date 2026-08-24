#!/usr/bin/env python3
"""Conan recipe — i686-elf-binutils 2.46.1 (Autotools, cross-toolchain).

GNU binutils configured as a cross-development toolchain that targets the
i686-elf (bare-metal) ABI. The assembler, linker and binary utilities
(i686-elf-as, i686-elf-ld, i686-elf-objdump, i686-elf-ar, ...) are
built to run on the HarmonyOS PC (aarch64) host and operate on i686 ELF
objects; they do not execute i686 code on the host.

R32: settings.os supports both Linux and OHOS.
R33: compiler and flags come from AutotoolsToolchain (ohos-aarch64 profile);
     no bare shell env vars (CC/CFLAGS/...) are used in build().
R38: produces executables -> commands.json declared, cpp_info.bindirs set.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    copy,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class I686ElfBinutilsConan(ConanFile):
    name = "i686-elf-binutils"
    version = "2.46.1"
    description = "GNU binutils cross-toolchain targeting i686-elf (bare-metal)"
    license = "GPL-3.0"
    homepage = "https://www.gnu.org/software/binutils/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "site-stty-fix.exp", self.recipe_folder, self.export_sources_folder)
        copy(self, "tmpfile-shim.c", self.recipe_folder, self.export_sources_folder)

    def build_requirements(self):
        # Upstream "make check" needs the DejaGNU harness (runtest) plus the
        # expect/tcl interpreters on the OHOS build host.  dejagnu/1.6.3 is
        # part of the official baseline; expect and tcl are additionally
        # declared as direct tool_requires so their package folders can be
        # resolved for TCL_LIBRARY / LD_LIBRARY_PATH in generate() (Conan
        # does not expose package_folder for transitive dependencies).
        self.tool_requires("dejagnu/1.6.3")
        self.tool_requires("expect/5.45.4")
        self.tool_requires("tcl/8.6.14")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # Build a cross-toolchain: the tools run on the build host (HarmonyOS
        # PC aarch64) and target the i686-elf bare-metal ABI. binutils
        # auto-prefixes every tool with "i686-elf-" when target != host.
        tc.configure_args.append("--target=i686-elf")

        # Build only static libraries (libbfd/libopcodes/...) so no .so is
        # shipped, keeping the toolchain self-contained and free of any
        # system-library collision (R26 spirit).
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")

        # gprofng relies on the Linux-specific SIGEV_THREAD_ID, which is not
        # available on HarmonyOS -> must be disabled.
        tc.configure_args.append("--disable-gprofng")

        # gdb/gdbserver/sim pull in heavy host dependencies (ncurses/python/...)
        # that are unnecessary for an assemble/link cross toolchain.
        tc.configure_args.append("--disable-gdb")
        tc.configure_args.append("--disable-gdbserver")
        tc.configure_args.append("--disable-sim")

        # No NLS/gettext, and do not let clang warnings fail the build.
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")

        tc.generate()

        # Build-scope env for the upstream DejaGNU testsuite: runtest is a
        # Tcl script and needs the expect interpreter and the tcl runtime
        # (TCL_LIBRARY / LD_LIBRARY_PATH).  Conan auto-injects tool_require
        # bin dirs into PATH; expect/tcl are direct tool_requires so their
        # package_folder is resolvable here (same pattern as the official
        # dejagnu recipe).
        # tool_requires live in the build context: access them via
        # self.dependencies.build[...] (self.dependencies[...] defaults to the
        # host context and would raise KeyError).
        deps = self.dependencies.build
        env = Environment()
        env.prepend_path("PATH", os.path.join(deps["expect"].package_folder, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(deps["tcl"].package_folder, "lib"))
        env.define("TCL_LIBRARY", os.path.join(deps["tcl"].package_folder, "lib", "tcl8.6"))
        env.vars(self, scope="build").save_script("i686_elf_check_env")

    def build(self):
        apply_conandata_patches(self)

        # The build-host clang passes linker-only options such as `-fuse-ld=lld`
        # on every invocation, including the configure preprocessor probes
        # (`$CC -E`). There the option is unused and clang prints a "argument
        # unused" warning on stderr; autoconf's legacy preprocess-mode header
        # check treats any stderr as failure and wrongly leaves
        # HAVE_LIMITS_H / HAVE_FCNTL_H / HAVE_SPAWN_H / ... unset. That breaks
        # libiberty (LONG_MIN in fibheap.c, O_* in pex-unix.c, posix_spawn ...).
        # Suppressing that single diagnostic gives the probes clean stderr so
        # the headers are detected correctly. Harmless when no such flag exists.
        os.environ["CPPFLAGS"] = (
            (os.environ.get("CPPFLAGS", "") + " -Wno-unused-command-line-argument").strip()
        )

        # musl ships mallinfo/mallinfo2 as linkable compatibility stubs but
        # does not define `struct mallinfo` / `struct mallinfo2` in <malloc.h>.
        # autoconf's link-only AC_CHECK_FUNCS therefore wrongly sets
        # HAVE_MALLINFO(_2) and ld's ldmain.c fails to compile on the incomplete
        # type. The functions are unusable on musl; ld just skips the optional
        # malloc statistics, so report them as absent.
        os.environ["ac_cv_func_mallinfo"] = "no"
        os.environ["ac_cv_func_mallinfo2"] = "no"

        autotools = Autotools(self)
        autotools.configure()
        # binutils is large; serial builds risk the CI timeout, so use modest
        # parallelism (capped to avoid memory pressure).
        jobs = min(os.cpu_count() or 2, 8)
        autotools.make(args=[f"-j{jobs}"])

        # ---- upstream official testsuite (DejaGNU make check, 379 .exp) ----
        # E272 migration: site-stty-fix.exp wraps expect spawn with -nottyinit
        # (/bin/stty missing on OHOS); tmpfile-shim.so via LD_PRELOAD restores
        # POSIX tmpfile() semantics (OHOS libc tmpfile() EACCES on the system
        # temp dir).  Both are test-environment compatibility files only.
        site_fix = os.path.join(self.build_folder, "site-stty-fix.exp")
        if not os.path.exists(site_fix):
            for src in (os.path.join(self.source_folder, "site-stty-fix.exp"),
                        os.path.join(self.build_folder, "..", "site-stty-fix.exp")):
                if os.path.exists(src):
                    self.run('cp -f "%s" "%s"' % (src, site_fix))
                    break
        shim_src = os.path.join(self.build_folder, "tmpfile-shim.c")
        shim_so = os.path.join(self.build_folder, "tmpfile-shim.so")
        if not os.path.exists(shim_src):
            for src in (os.path.join(self.source_folder, "tmpfile-shim.c"),
                        os.path.join(self.build_folder, "..", "tmpfile-shim.c")):
                if os.path.exists(src):
                    self.run('cp -f "%s" "%s"' % (src, shim_src))
                    break
        cc = None
        conf_ccs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        if conf_ccs:
            cc = conf_ccs.get("c") or conf_ccs.get("cc")
        elif os.environ.get("CC"):
            cc = os.environ["CC"]
        if not cc:
            raise RuntimeError("No C compiler found to build tmpfile-shim.so")
        if os.path.exists(shim_src):
            self.run('"%s" -shared -fPIC "%s" -o "%s"' % (cc, shim_src, shim_so),
                     cwd=self.build_folder)
        ldpreload = ("LD_PRELOAD=%s " % shim_so) if os.path.exists(shim_so) else ""
        if os.path.exists(site_fix):
            self.run("%sDEJAGNU=%s make -k -j1 check" % (ldpreload, site_fix),
                     env=["conanbuild", "i686_elf_check_env"],
                     cwd=self.build_folder)
        else:
            self.output.warn("site-stty-fix.exp not found; make check without DEJAGNU fix")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Cross-toolchain: the deliverables are the i686-elf-* executables
        # installed under bin/.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
