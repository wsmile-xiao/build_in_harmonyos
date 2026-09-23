#!/usr/bin/env python3
"""Conan recipe for Yosys -- the Verilog RTL synthesis framework.

Build system: a CUSTOM Makefile (not autotools, not cmake).

ABC handling (the decisive detail):
  The official TAG archive (v0.66.tar.gz) ships an EMPTY abc/ submodule
  (directory entry only, 0 files) and an empty libs/cxxopts/.  Building in-tree
  ABC is therefore impossible from THIS tarball.  Note for accuracy: the
  separate GitHub release asset yosys-src.tar.gz (11,178,019 B) DOES inline
  abc/ (2316 files) and libs/cxxopts; this recipe deliberately stays on the
  official tag archive and consumes abc / cxxopts as conan packages instead
  (abc is already published in the OHOS repository and used by other recipes).
  Makefile:480-496 only adds the in-tree ABC to TARGETS when ABCEXTERNAL is
  empty; with ABCEXTERNAL set it merely defines -DABCEXTERNAL (Makefile:686-690)
  and yosys spawns that binary at runtime.  DISABLE_SPAWN=0 is mandatory in
  that branch (Makefile:493 raises otherwise).  So we keep ENABLE_ABC=1 and
  point ABCEXTERNAL at the conan abc package.

  abc is a HOST requirement (not a tool_require): yosys exec()s it at run time,
  so it belongs to the runtime closure.  package_info() additionally exports the
  documented ABC override (kernel/yosys.cc:652-657 prefers getenv("ABC") over
  the path compiled in by -DABCEXTERNAL), which keeps `synth` working after the
  package is uploaded and consumed on another machine.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class YosysConan(ConanFile):
    name = "yosys"
    version = "0.66"
    description = "Yosys Open SYnthesis Suite -- Verilog RTL synthesis framework"
    license = "ISC"
    homepage = "https://github.com/YosysHQ/yosys"
    url = "https://github.com/YosysHQ/yosys"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # README.md:80 -- TCL / readline / libffi are optional, ENABLE_* controlled
        self.requires("readline/8.3")
        self.requires("libffi/3.5.2")
        self.requires("tcl/8.6.16")
        self.requires("zlib/1.3.1")
        # header-only; the tag archive ships an EMPTY libs/cxxopts submodule
        self.requires("cxxopts/3.3.1.1")
        # consumed as an external runtime binary (see module docstring)
        self.requires("abc/0.0.0.20260511")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("yosys is supported on Linux/OHOS only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        env = Environment()
        # R5: OHOS has no /bin/sh
        env.define("CONFIG_SHELL", os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash"))
        # tclsh is invoked by the build system (TCL bindings), so the tcl
        # package bin/ must be on PATH even though tcl is a link dependency.
        tcl = self.dependencies.get("tcl")
        if tcl is not None and tcl.package_folder:
            env.prepend_path("PATH", os.path.join(tcl.package_folder, "bin"))
        # Makefile:441 calls a hardcoded `tclsh` (TCLSH= is not honoured), so put
        # a `tclsh` shim -> tclsh8.6 at the FRONT of PATH.
        _shim = self._tclsh_shim()
        if _shim:
            env.prepend_path("PATH", _shim)
        # yosys discovers tcl/readline/libffi through pkg-config; PkgConfigDeps
        # writes the .pc files but does NOT extend PKG_CONFIG_PATH (E468).
        PkgConfigDeps(self).generate()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("conanbuildenv-yosys")

    def _abc_bin(self):
        """abc is a HOST requirement: yosys spawns the binary at run time."""
        abc = self.dependencies.get("abc") or self.dependencies.build.get("abc")
        if abc is None or not abc.package_folder:
            raise ConanInvalidConfiguration("abc requirement is missing")
        for cand in (os.path.join(abc.package_folder, "bin", "abc"),
                     os.path.join(abc.package_folder, "bin", "yosys-abc")):
            if os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration("abc binary not found in the abc package")

    def _compiler_env(self):
        """CC/CXX/M4 as an environment prefix for make.

        yosys' Makefile sets CXX/CC itself (not `?=`), so the profile's
        tools.build:compiler_executables never reaches it and a cross build
        silently produced HOST objects (the link then died with
        `/usr/bin/ld: skipping incompatible .../libtcl8.6.so`).  R33: the
        values come from self.conf, never from bare shell variables.
        M4: the conan bison binary hardcodes /data/service/hnp/bin/m4 (verified
        with `strings`), so on any host where that device path is absent bison
        dies with "input/output error" (EIO) before generating the parser.
        Point M4 at a real m4 only when the device path is missing; on CI the
        path exists and this stays inert.
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        parts = []
        if compilers.get("c"):
            parts.append('CC="{}"'.format(compilers["c"]))
        if compilers.get("cpp"):
            parts.append('CXX="{}"'.format(compilers["cpp"]))
        if not os.path.exists("/data/service/hnp/bin/m4"):
            which_m4 = shutil.which("m4")
            if which_m4:
                parts.append('M4="{}"'.format(which_m4))
        return " ".join(parts)

    def _strip_cmd(self):
        """`make install` strips with $(STRIP), whose default is the HOST
        `strip` (Makefile:126).  Under cross-compilation that tool cannot read
        an aarch64 ELF and the install aborts with
            strip: Unable to recognise the format of the input file .../yosys
        Derive an LLVM strip sitting next to the configured C compiler (the
        OHOS SDK ships llvm-strip there); when there is none, leave the
        Makefile default alone so native builds keep stripping normally.
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            return ""
        cand = os.path.join(os.path.dirname(cc), "llvm-strip")
        return 'STRIP="{}"'.format(cand) if os.path.isfile(cand) else ""

    def _dep_flags(self):
        """Custom-Makefile projects get no automatic -I/-L from conan requires."""
        inc, libdir, libs = [], [], []
        # Iterate ALL host dependencies (not a fixed list) so transitive ones
        # are covered too: readline pulls in ncurses/tinfo, and without it the
        # link dies with `ld.lld: undefined symbol: PC / BC / UP / tgetflag`.
        for name, dep in self.dependencies.host.items():
            if dep is None or not dep.package_folder:
                continue
            for p in dep.cpp_info.includedirs:
                inc.append("-I" + p)
            for p in dep.cpp_info.libdirs:
                libdir.append("-L" + p)
            for lib in dep.cpp_info.libs:
                libs.append("-l" + lib)
        # flex is a build tool, but its FlexLexer.h is needed when compiling the
        # generated lexer (frontends/verilog/verilog_lexer.h:12).
        flex = self.dependencies.build.get("flex")
        if flex is not None and flex.package_folder:
            for p in flex.cpp_info.includedirs:
                inc.append("-I" + p)
            for p in flex.cpp_info.libdirs:
                libdir.append("-L" + p)
        return " ".join(inc), " ".join(libdir), " ".join(libs)

    def _tclsh(self):
        """The tcl conan package ships bin/tclsh8.6, not bin/tclsh."""
        tcl = self.dependencies.get("tcl")
        if tcl is None or not tcl.package_folder:
            return ""
        found = glob.glob(os.path.join(tcl.package_folder, "bin", "tclsh*"))
        return found[0] if found else ""

    def _bison_datadir(self):
        """The conan bison package keeps its skeleton in <pkg>/share/bison;
        without BISON_PKGDATADIR bison looks in /share/bison and dies with
        "cannot open: /share/bison/m4sugar/m4sugar.m4"."""
        bison = self.dependencies.build.get("bison")
        if bison is None or not bison.package_folder:
            return ""
        cand = os.path.join(bison.package_folder, "share", "bison")
        return cand if os.path.isdir(cand) else ""

    def _tclsh_shim(self):
        """Makefile:441 invokes a hardcoded `tclsh`; the tcl package ships
        bin/tclsh8.6.  Provide a `tclsh` shim on PATH (TCLSH= is not honoured)."""
        real = self._tclsh()
        if not real:
            return ""
        shim = os.path.join(self.generators_folder, "shim")
        os.makedirs(shim, exist_ok=True)
        p = os.path.join(shim, "tclsh")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write('#!/bin/sh\nexec "' + real + '" "$@"\n')
        os.chmod(p, 0o755)
        self.output.info("  [ok] tclsh shim -> " + real)
        return shim

    def build(self):
        apply_conandata_patches(self)
        # The tag archive has an EMPTY libs/cxxopts submodule, yet kernel/driver.cc
        # includes "libs/cxxopts/include/cxxopts.hpp" by in-tree path.  Materialise
        # the header from the conan package instead of patching upstream.
        cxxopts = self.dependencies.get("cxxopts")
        if cxxopts is not None and cxxopts.package_folder:
            dst = os.path.join(self.source_folder, "libs", "cxxopts", "include")
            os.makedirs(dst, exist_ok=True)
            copied = 0
            for hdr in glob.glob(os.path.join(cxxopts.package_folder, "include", "*.hpp")):
                shutil.copyfile(hdr, os.path.join(dst, os.path.basename(hdr)))
                copied += 1
            self.output.info("  [ok] materialised {} cxxopts header(s)".format(copied))
        # NOTE: there is no "config-clang" target in this Makefile -- CONFIG is a
        # plain variable (Makefile:2-7) and the default goal is "all" (Makefile:98).
        # Compiler selection comes from the conan profile env (CC/CXX).
        # Parallel build: yosys' Makefile is parallel-safe (upstream builds with
        # `make -j$(nproc)`), and the 342 translation units take 46-64 min at -j1
        # on the CI workers -- which overran the 3600s budget (build #51146);
        # `/system/bin/sh: .../make: Out of memory`), so cap at 4 to keep peak
        # RSS well inside the worker budget while still finishing in time.
        # Cap at 4: -j8 tripped the worker's memory limit (CI #51652:
        # yosys builds in-source: the Makefile lives in source_folder, while
        # basic_layout puts build() in its own folder.
        # Let yosys discover the dependencies itself via pkg-config (E468);
        # overriding CXXFLAGS on the make command line would drop its own -I.
        inc, libdir, libs = self._dep_flags()
        # Makefile:107 is `CXXFLAGS := $(CXXFLAGS) -Wall ... -I. ...`, so an
        # ENVIRONMENT prefix is read and preserved (a make command-line variable
        # would override it and drop -I.).  readline has no pkg-config branch in
        # the Makefile (only `LIBS += -lreadline`), hence the explicit -I/-L.
        # TCL_VERSION is `?=` in Makefile:441 and defaults to running `tclsh`;
        # passing it avoids executing the OHOS tclsh8.6 at build time (which on
        # WSL needs the tcl runtime closure).
        # BISON_PKGDATADIR points bison at the conan package skeleton.
        _jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        _jobs = max(1, min(_jobs or (os.cpu_count() or 1), 4))
        self.output.info("  [ok] make -j{}".format(_jobs))
        self.run('{} CXXFLAGS="{}" LIBS="{} {}" BISON_PKGDATADIR="{}" '
                 'make -j{} ENABLE_ABC=1 ABCEXTERNAL={} DISABLE_SPAWN=0 '
                 'TCL_VERSION=tcl8.6'.format(
                     self._compiler_env(), inc, libdir, libs,
                     self._bison_datadir(), _jobs, self._abc_bin()),
                 env="conanbuild", cwd=self.source_folder)

    def _resign(self, path):
        """OHOS clang/lld self-signs the ELF at link time (a .codesign section).
        Any later modification (strip/objcopy/patchelf) invalidates that
        signature and the kernel then refuses to exec the file with
        \"Operation not permitted\" — this is exactly what broke CI build
        #50968: `llvm-strip -S bin/yosys` in `make install` invalidated the
        section, and the packaged binary could not be executed.  Follow the
        established E077 flow: drop the stale section, re-sign, restore 0755.
        The tooling only exists on an OHOS device, so this is a no-op when
        cross-building on a plain Linux host."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if self.settings.os != "OHOS" or not os.path.exists(sign_tool):
            return
        tmp_signed = path + ".signed"
        # `|| true`: the section may be absent (e.g. a binary that was never
        # self-signed); re-signing an already-unsigned file is still valid.
        self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(
            objcopy, path), quiet=True)
        self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
            sign_tool, path, tmp_signed), quiet=True)
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def _resign_elf_binaries(self):
        """Re-sign every ELF in bin/ (yosys, yosys-filterlib); the helper
        scripts (yosys-config/yosys-smtbmc/yosys-witness) are skipped."""
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return
        for name in sorted(os.listdir(bindir)):
            p = os.path.join(bindir, name)
            if not os.path.isfile(p):
                continue
            try:
                with open(p, "rb") as fh:
                    is_elf = fh.read(4) == b"\x7fELF"
            except OSError:
                continue
            if is_elf:
                self._resign(p)
                self.output.info("  [ok] re-signed " + name)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # check-git-abc runs during `make install` too: the tarball is not a git
        # repo and abc/ is an empty submodule, so ABCEXTERNAL must be passed here
        # as well (otherwise: "not configured as a git repository, and 'abc'
        # folder is missing").
        inc, libdir, libs = self._dep_flags()
        self.run('{} {} CXXFLAGS="{}" LIBS="{} {}" BISON_PKGDATADIR="{}" '
                 'make install PREFIX={} ENABLE_ABC=1 ABCEXTERNAL={} '
                 'DISABLE_SPAWN=0 TCL_VERSION=tcl8.6'.format(
                     self._compiler_env(), self._strip_cmd(), inc, libdir, libs,
                     self._bison_datadir(), self.package_folder,
                     self._abc_bin()),
                 env="conanbuild", cwd=self.source_folder)
        # strip invalidated the link-time .codesign section; re-sign on device
        self._resign_elf_binaries()

    def package_info(self):
        # yosys is a pure CLI: it ships bin/ plus the runtime share/ data tree,
        # but no link libraries and no C headers, so leave libdirs/includedirs
        # empty instead of advertising directories that do not exist.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # ABCEXTERNAL bakes the *build-time* path into the binary; export the
        # consumer's own abc through the documented ABC override so `synth`
        # keeps working after the package leaves the build machine.
        abc = self.dependencies.get("abc")
        if abc is not None and abc.package_folder:
            for cand in (os.path.join(abc.package_folder, "bin", "abc"),
                         os.path.join(abc.package_folder, "bin", "yosys-abc")):
                if os.path.isfile(cand):
                    self.runenv_info.define("ABC", cand)
                    break

