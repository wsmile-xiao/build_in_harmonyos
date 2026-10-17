#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Htscodecs, htscodecs, 1.6.5, htscodecs 1.6.5, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class HtscodecsConan(ConanFile):
    name = "htscodecs"
    version = "1.6.5"
    description = "htscodecs 1.6.5"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # bzip2 provides the BZ2 codec within Arith streams; upstream configure
        # hard-fails without its development files (--disable-bz2 would degrade
        # data-stream compatibility and arith tests).
        self.requires("bzip2/1.0.8")

    def build_requirements(self):
        # v1.6.5 source (git archive) ships configure.ac without a generated
        # `configure`; bootstrap needs automake's aclocal AND libtool's m4
        # (configure.ac uses LT_INIT).  CI preinstalls autoconf but not
        # automake/aclocal, so `autoreconf -i -f` dies with `Can't exec
        # "aclocal"`; without libtool.m4 in ACLOCAL_PATH automake aborts with
        # `LIBTOOL is undefined`.  Self-contain the missing tools via
        # tool_requires (pdfsandwich/ocaml precedent).  NB: do NOT add
        # autoconf here — its conan package pulls its own perl in, whose XS
        # modules shadow the system perl and break the system autoreconf.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs;
        # configure's conftest runs compiled programs, which fail with
        # "Error loading shared library libbz2.so" unless LD_LIBRARY_PATH
        # points at dependency lib dirs.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def _apply_ohos_autotools_patch(self):
        """Patch autoreconf-generated config.guess/config.sub for HarmonyOS.

        Same edits as the framework's patch-autotools-ohos.pl (E007), applied
        self-contained here because `conan create` runs in a clean tree where
        configure must recognize `uname -s = HarmonyOS`.  This is the E007 /
        R8 "libc probe" exception: the patch only teaches the autotools triplet
        guesser about the OHOS platform, it does not stub library logic.
        """
        import os
        import re
        cg = os.path.join(self.source_folder, "config.guess")
        cs = os.path.join(self.source_folder, "config.sub")

        def rd(p):
            with open(p, "r", encoding="utf-8") as fh:
                return fh.read()

        def wr(p, s):
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(s)

        gc = rd(cg)
        if "__OHOS__" not in gc:
            gc = re.sub(
                r'(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)',
                r'\1\n#elif defined(__OHOS__)\n    LIBC=ohos',
                gc, count=1, flags=re.M)
        if "HarmonyOS" not in gc:
            block = (
                "    *:HarmonyOS:*:*)\n"
                '\tcase "$UNAME_MACHINE" in\n'
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n")
            gc = re.sub(r'(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)',
                        block + r'\1', gc, count=1, flags=re.M)
        wr(cg, gc)

        sc = rd(cs)
        if "ohos-linux" not in sc:
            sc = re.sub(
                r'(^(\s*)android-linux\)\s*\n(\s*)basic_machine=\$field1-unknown'
                r'\s*\n(\s*)basic_os=linux-android\s*\n(\s*);;\s*\n)',
                r'\1\2ohos-linux)\n\3basic_machine=$field1-unknown\n'
                r'\4basic_os=linux-ohos\n\5;;\n',
                sc, count=1, flags=re.M)
        if not re.search(r'gnu\*\s*\|\s*android\*\s*\|\s*ohos\*', sc):
            sc = re.sub(r'(gnu\*\s*\|\s*android\*)', r'\1 | ohos*',
                        sc, count=1)
        # kernel-OS validation list (validation gate, not just OS list).
        # NB: check for the "*)" pattern, not the bare string, because
        # basic_os=linux-ohos above already contains "linux-ohos".
        if not re.search(r'linux-ohos\*-\s*\)', sc):
            sc = re.sub(
                r'(linux-mlibc\*-\s*)\)',
                r'\1 | linux-ohos*-)',
                sc, count=1)
        wr(cs, sc)

        # E114: generated `configure`/`config.status` create a temp dir with
        # `umask 077 && mktemp -d ./confXXXXXX`, which on HMDFS yields an
        # unwritable drwx--S--- dir (subs1.awk: Permission denied).  Drop the
        # umask so the confXXXXXX temp dir keeps writable permissions.
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.exists(cfg):
            cc = rd(cfg)
            cc2 = cc.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
            cc2 = cc2.replace(
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null` &&')
            cc2 = cc2.replace(
                '(umask 077 && mkdir "$tmp")',
                'mkdir "$tmp" 2>/dev/null')
            if cc2 != cc:
                wr(cfg, cc2)
                self.output.info("E114: umask 077 removed from configure temp-dir creation")

        self.output.info("OHOS autotools patch applied (config.guess/config.sub)")

    def build(self):
        apply_conandata_patches(self)
        # v1.6.5 tag tarball is a git archive without a generated configure
        # script; bootstrap autotools when needed.
        import os
        if not os.path.exists("configure"):
            self.run("autoreconf -i -f", cwd=self.source_folder)
        self._apply_ohos_autotools_patch()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["htscodecs"]
