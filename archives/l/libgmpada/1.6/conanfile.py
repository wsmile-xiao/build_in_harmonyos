#!/usr/bin/env python3
"""Conan recipe for libgmpada 1.6 -- the Ada binding to GMP.

Build-system notes
------------------
libgmpada ships a hand-written top-level `Makefile` (no configure/CMake/meson):
it invokes `gnatmake` for the Ada units, generates `src/gmp-h.ads` through the
C/C++ frontend (`--dump-ada-spec`), links `-lgnat` and `-lgmp`, and installs an
Ada source tree + ALI files + static/shared libraries.

Ada toolchain notes
-------------------
The only Ada toolchain published in ohpcd is `gcc-ada/9.5.0`, an OHOS/armv8
binary; the assembler/linker come from `binutils/2.46.0`, also OHOS/armv8 only.
There is therefore NO Linux cross compiler for Ada and this recipe can only be
built natively on OHOS (build == host), i.e. CI uses
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
A cross build is rejected explicitly in validate().

Static-only binding
-------------------
gcc-ada/9.5.0 installs the Ada runtime as NON-PIC static archives
(`adalib/libgnat.a`, `adalib/libgnarl.a`).  Linking them into the upstream
shared library therefore fails with

    libgnat.a(a-stream.o): relocation R_AARCH64_ADR_PREL_PG_HI21 against symbol
    ... can not be used when making a shared object; recompile with -fPIC

so only the static binding `libgmpada.a` can be produced (the shared target is
rejected in validate()); consumers link the static archive plus the Ada runtime
supplied by their own GNAT toolchain.

`gcc-ada` is built with `--enable-languages=c,ada`, so it provides `gcc` but
**no `g++`**.  Upstream defaults to `CXX := g++-<gnat_version>`; the C driver is
used instead.
"""
import glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                                export_conandata_patches, get)
from conan.tools.layout import basic_layout

# Upstream Makefile default LDFLAGS (Makefile:45-46), passed verbatim on the
# make command line; `-L<adalib>` is appended so that the explicit `-lgnat`
# resolves against gcc-ada's static Ada runtime.
_BASE_LDFLAGS = ("-Wl,--as-needed -Wl,--no-allow-shlib-undefined "
                 "-Wl,--no-copy-dt-needed-entries -Wl,--no-undefined")

# Upstream default ADAFLAGS (Makefile:32-33).
_ADAFLAGS = ("-g -O2 -gnataEfnoqQ -gnatVa -Wall -Wextra -gnatw.eH.Y "
             "-gnatyBdIoOSuxy")

class LibGmpAdaConan(ConanFile):
    name = "libgmpada"
    version = "1.6"
    description = "Ada binding to the GNU Multiple Precision arithmetic library (GMP)"
    license = "GPL-3.0-or-later"
    homepage = "http://nicolas.boulenguez.free.fr"
    url = "http://nicolas.boulenguez.free.fr"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The binding only uses the GMP C interface (-lgmp, <gmp.h>).
        self.requires("gmp/6.3.0")

    def build_requirements(self):
        # OHOS/armv8 binaries only: GNAT compiler + assembler/linker.
        self.tool_requires("gcc-ada/9.5.0")
        self.tool_requires("binutils/2.46.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libgmpada is supported on Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libgmpada is static-only on OHOS: gcc-ada's Ada runtime "
                "(adalib/libgnat.a, libgnarl.a) is non-PIC and cannot be linked "
                "into a shared object. Use shared=False.")
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "libgmpada requires a NATIVE OHOS build: the only Ada toolchain "
                "published in ohpcd (gcc-ada/9.5.0) and its binutils/2.46.0 are "
                "OHOS/armv8 binaries, so no Linux cross compiler exists. Use "
                "-pr:h=ci/conan/profiles/ohos-aarch64 "
                "-pr:b=ci/conan/profiles/ohos-aarch64")

    def layout(self):
        basic_layout(self)

    # ------------------------------------------------------------------ tools
    def _gcc_ada_folder(self):
        dep = self.dependencies.build.get("gcc-ada")
        return dep.package_folder if dep is not None else ""

    def _gcc_ada_tool(self, name):
        folder = self._gcc_ada_folder()
        path = os.path.join(folder, "bin", name) if folder else ""
        if path and os.path.isfile(path):
            return path
        return shutil.which(name) or name

    def _binutils_bin_dir(self):
        """Return the OHOS binutils directory that provides 'as' and 'ld'.

        gcc resolves the assembler through PATH.  The host /usr/bin/as cannot
        assemble the OHOS target produces ("as: unrecognized option -EL"), so
        the tool_requires binutils directory is put first explicitly instead of
        relying on the worker's /data/service/hnp/bin being in the profile.
        """
        dep = self.dependencies.build.get("binutils")
        if dep is None or not dep.package_folder:
            return ""
        candidates = [os.path.join(dep.package_folder, d)
                      for d in dep.cpp_info.bindirs]
        candidates.append(os.path.join(dep.package_folder, "bin"))
        for path in candidates:
            if path and os.path.isfile(os.path.join(path, "as")):
                return path
        return ""

    def _find_ohos_tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        sdk = os.path.dirname(ndk) if ndk else ""
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            # Also look in the OHOS SDK so the local W3 scaffold (WSL, where the
            # worker's /data/service/hnp does not exist) can sign and run.
            os.path.join(ndk, "llvm", "bin", name) if ndk else "",
            os.path.join(sdk, "toolchains", "lib", name) if sdk else "",
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    def _sign_file(self, path):
        """Sign an ELF in place so OHOS lets it be exec'd (E489/E517)."""
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "running the upstream demo on OHOS requires llvm-objcopy and "
                "binary-sign-tool")
        temporary = path + ".signing"
        shutil.copy2(path, temporary)
        self.run("{} --remove-section .codesign {}".format(
            shlex.quote(objcopy), shlex.quote(temporary)),
            cwd=self.source_folder, env="conanbuild")
        self.run("{} sign -inFile {} -outFile {} -selfSign 1".format(
            shlex.quote(signer), shlex.quote(temporary),
            shlex.quote(temporary)), cwd=self.source_folder, env="conanbuild")
        os.chmod(temporary, os.stat(path).st_mode)
        os.replace(temporary, path)
        self.output.info("  [ok] signed " + path)

    def _ada_libdir(self):
        # gcc-ada installs libgnat.a/libgnarl.a under
        # lib/gcc/<triplet>/<gcc-version>/adalib.  The version is the
        # COMPILER's (9.5.0), not this recipe's -- glob it instead of guessing.
        folder = self._gcc_ada_folder()
        if not folder:
            return ""
        for adalib in sorted(glob.glob(os.path.join(
                folder, "lib", "gcc", "*", "*", "adalib"))):
            if os.path.isfile(os.path.join(adalib, "libgnat.a")):
                return adalib
        return ""

    def _gmp_libdir(self):
        gmp = self.dependencies.get("gmp")
        if gmp is None:
            return ""
        dirs = [d for d in gmp.cpp_info.libdirs if d]
        return dirs[0] if dirs else ""

    def _gmp_includedir(self):
        gmp = self.dependencies.get("gmp")
        if gmp is None:
            return ""
        dirs = [d for d in gmp.cpp_info.includedirs if d]
        return os.path.join(gmp.package_folder, dirs[0]) if dirs else ""

    def _common_make_args(self):
        ada_libdir = self._ada_libdir()
        ldflags = _BASE_LDFLAGS
        if ada_libdir:
            ldflags += " -L" + ada_libdir
        args = [
            "GNATMAKE=" + self._gcc_ada_tool("gnatmake"),
            "CC=" + self._gcc_ada_tool("gcc"),
            "CXX=" + self._gcc_ada_tool("gcc"),
            # gcc-ada ships the Ada runtime as static libgnat.a/libgnarl.a;
            # libgnat references libgnarl, so it must follow on the link line.
            "LDLIBS=-L{} -lgmp -lgnarl".format(self._gmp_libdir()),
            "CPPFLAGS=-I{}".format(self._gmp_includedir()),
            "ADAFLAGS=" + _ADAFLAGS,
            "LDFLAGS=" + ldflags,
            # Conan-style install root; the .gpr is rewritten to relative
            # paths in package().
            "prefix=/",
        ]
        return args

    def _make_cmd(self, targets):
        parts = ["make"] + targets.split() + self._common_make_args()
        cmd = " ".join(shlex.quote(p) for p in parts)
        binutils_bin = self._binutils_bin_dir()
        if binutils_bin:
            cmd = "PATH={}:$PATH {}".format(shlex.quote(binutils_bin), cmd)
        return cmd

    def _generate_gmp_h_spec(self):
        """Generate src/gmp-h.ads the way the upstream Makefile intends to.

        The upstream rule is:

            src/gmp-h.ads: gmp-h.ads.sed
                echo '#include <gmp.h>' > obj/tmp.h
                cd obj && $(CXX) $(CPPFLAGS) $(CXXFLAGS) --dump-ada-spec tmp.h
                sed -f $< obj/*_gmp_h.ads > $@

        Two things break with the OHOS gcc-ada driver:

          * any invocation without -c/-S/-E/-fsyntax-only is classified as a
            LINK by the signed driver wrapper, so it tries to link tmp.h and
            dies with \"undefined reference to main\";
          * gcc-ada has no C++ frontend and its C driver names the dumped spec
            \"obj/gmp_h.ads\" with package \"gmp_h\", which neither the glob
            \"obj/*_gmp_h.ads\" nor the sed rule \"^package .*_gmp_h is$\" matches.

        Pre-generate the file in the build folder (kept out of the recipe) by
        running the dump and then applying the unmodified upstream sed after
        renaming the package to \"TMP_gmp_h\" so the upstream rule applies.
        """
        obj = os.path.join(self.source_folder, "obj")
        os.makedirs(obj, exist_ok=True)
        with open(os.path.join(obj, "tmp.h"), "w", encoding="utf-8") as fh:
            fh.write("#include <gmp.h>\n")
        cxx = self._gcc_ada_tool("gcc")
        inc = self._gmp_includedir()
        self.run("cd {} && {} -I{} -Wall -Wextra -fsyntax-only "
                 "--dump-ada-spec tmp.h".format(
                     shlex.quote(obj), shlex.quote(cxx), shlex.quote(inc)),
                 cwd=self.source_folder, env="conanbuild")
        dumped = sorted(glob.glob(os.path.join(obj, "*gmp_h.ads")))
        if not dumped:
            raise ConanException(
                "gcc --dump-ada-spec produced no gmp_h.ads under " + obj)
        sed = os.path.join(self.source_folder, "gmp-h.ads.sed")
        target = os.path.join(self.source_folder, "src", "gmp-h.ads")
        self.run("sed -e 's/^package gmp_h is$/package TMP_gmp_h is/' "
                 "-e 's/^end gmp_h;$/end TMP_gmp_h;/' {} | sed -f {} > {}".format(
                     shlex.quote(dumped[0]), shlex.quote(sed),
                     shlex.quote(target)),
                 cwd=self.source_folder, env="conanbuild")
        self.output.info("  [ok] generated src/gmp-h.ads from " + dumped[0])

    def _run_upstream_demo(self):
        """Build and run the upstream demo against the static binding.

        Upstream `make test` builds BOTH the shared and the static demo, but
        the shared variant is impossible on OHOS (non-PIC libgnat.a), so this
        reproduces only the static half against a staged install.
        """
        stage = os.path.join(self.source_folder, "demo-install")
        src_inc = os.path.join(stage, "usr", "share", "ada", "adainclude", "gmpada")
        ali_dir = os.path.join(stage, "usr", "lib", "ada", "adalib", "gmpada")
        lib_dir = os.path.join(stage, "usr", "lib")
        for path in (src_inc, ali_dir, lib_dir,
                     os.path.join(self.source_folder, "demo-static")):
            os.makedirs(path, exist_ok=True)
        copy(self, "*", src=os.path.join(self.source_folder, "src"), dst=src_inc)
        copy(self, "*.ali", src=os.path.join(self.source_folder, "obj-static"),
             dst=ali_dir)
        copy(self, "libgmpada.a", src=os.path.join(self.source_folder, "obj"),
             dst=lib_dir)

        ada_libdir = self._ada_libdir()
        ldflags = _BASE_LDFLAGS + (" -L" + ada_libdir if ada_libdir else "")
        gnatmake = self._gcc_ada_tool("gnatmake")
        demo = os.path.join(self.source_folder, "demo-static", "demo")
        cmd = ("{gnat} demo.adb -o {demo} -D {objdir} "
               "-aI{inc} -aO{ali} -cargs {adaflags} -gnata "
               "-largs {ldflags} {lib}/libgmpada.a -L{gmp} -lgmp -lgnarl").format(
                   gnat=shlex.quote(gnatmake), demo=shlex.quote(demo),
                   objdir=shlex.quote(os.path.join(self.source_folder, "demo-static")),
                   inc=shlex.quote(src_inc), ali=shlex.quote(ali_dir),
                   adaflags=_ADAFLAGS, ldflags=ldflags,
                   lib=shlex.quote(lib_dir),
                   gmp=shlex.quote(self._gmp_libdir()))
        binutils_bin = self._binutils_bin_dir()
        if binutils_bin:
            cmd = "PATH={}:$PATH {}".format(shlex.quote(binutils_bin), cmd)
        self.output.info("  [upstream] building the static demo")
        self.run(cmd, cwd=self.source_folder, env="conanbuild")
        if str(self.settings.os) == "OHOS":
            self._sign_file(demo)
        self.run(shlex.quote(demo), cwd=self.source_folder, env="conanbuild")
        self.output.info("  [upstream] demo-static/demo ran successfully")

    # ------------------------------------------------------------------ steps
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # tool_requires contribute gcc-ada/bin and binutils/bin to the build env.
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._generate_gmp_h_spec()
        # Static binding + the convenience project file.
        self.run(self._make_cmd("obj/libgmpada.a obj/gmpada.gpr"),
                 cwd=self.source_folder, env="conanbuild")
        if can_run(self):
            self._run_upstream_demo()
        else:
            self.output.warning("[libgmpada] cannot run tests on this host; "
                                "upstream demo not executed")

    def _rewrite_gpr(self):
        """Make the installed gmpada.gpr relocatable inside the package.

        Upstream's template bakes `$(SRC_DIR)/$(ALI_DIR)/$(SO_DIR)` (prefix=/,
        i.e. `/share/...` and `/lib`) and the build-time LDLIBS into the project
        file; rewrite to paths relative to the .gpr location and to the plain
        `-lgmp` a consumer can resolve through Conan.
        """
        gpr = os.path.join(self.package_folder, "share", "gpr", "gmpada.gpr")
        if not os.path.isfile(gpr):
            return
        with open(gpr, "r", encoding="utf-8") as fh:
            text = fh.read()
        text = text.replace('"/share/ada/adainclude/gmpada"',
                            '"../ada/adainclude/gmpada"')
        text = text.replace('"/lib/ada/adalib/gmpada"',
                            '"../../lib/ada/adalib/gmpada"')
        text = re.sub(r'for Library_Dir use "[^"]*";',
                      'for Library_Dir use "../../lib";', text)
        text = re.sub(r'for Linker_Options use \([^)]*\);',
                      'for Linker_Options use ("-lgmp");', text)
        text = re.sub(r'for Library_Kind use "[^"]*";',
                      'for Library_Kind use "static";', text)
        with open(gpr, "w", encoding="utf-8") as fh:
            fh.write(text)

    def package(self):
        copy(self, "gpl.txt.gz", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # Manual install: upstream's `make install` insists on both libraries
        # and would try to rebuild the impossible shared one.
        copy(self, "*", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "share", "ada",
                              "adainclude", "gmpada"))
        copy(self, "*.ali", src=os.path.join(self.source_folder, "obj-static"),
             dst=os.path.join(self.package_folder, "lib", "ada", "adalib",
                              "gmpada"))
        copy(self, "libgmpada.a", src=os.path.join(self.source_folder, "obj"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "gmpada.gpr", src=os.path.join(self.source_folder, "obj"),
             dst=os.path.join(self.package_folder, "share", "gpr"))
        self._rewrite_gpr()

    def package_info(self):
        self.cpp_info.libs = ["gmpada"]
        # Ada specs and bodies live under share/ada/adainclude (not include/).
        self.cpp_info.includedirs = ["share/ada/adainclude"]
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "gmpada")
        self.cpp_info.set_property("cmake_target_name", "gmpada::gmpada")
