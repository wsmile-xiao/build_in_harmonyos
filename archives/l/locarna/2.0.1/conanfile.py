#!/usr/bin/env python3
"""Conan recipe — LocARNA 2.0.1 (Autotools).

LocARNA: a collection of tools for fast and high-quality pairwise and
multiple alignment of RNA sequences and structures (based on the Turner
free-energy model). C++14, autotools build.

OHOS adaptation (mirrors the validated ViennaRNA 2.7.2 pattern):
- config.guess/config.sub get defensive HarmonyOS recognition patches
  (non-fatal; the recipe forces explicit *-linux-gnu triplets via the
  libuuid pattern, so configure never receives an 'ohos' value).
- configure umask 077 -> 022 + TMPDIR pointed at the writable build
  folder (/tmp is read-only on OHOS).
- All adaptations of the pre-generated autotools files (config.sub/
  config.guess, configure, lib/Makefile.in) are applied from generate(),
  not build(), so no generated file is rewritten during build (R6).
- viennarna/2.7.2 is a hard dependency (RNAlib2 >= 2.5.1). Its shipped
  RNAlib2.pc has `prefix=/`, which on OHOS resolves to the host /lib; the
  recipe rewrites that prefix to the viennarna package folder and points
  PKG_CONFIG_PATH at the corrected .pc so configure's
  PKG_CHECK_MODULES([VRNA],[RNAlib2 >= 2.5.1]) resolves correctly.
- The lib/perl subdirectory is disabled. It installs MLocarna.pm and the
  MLocarna::* modules that drive the Perl front-end scripts; MLocarna.pm
  pulls in MLocarna::threaded, which does `use threads`, and the Perl
  runtime shipped with the OHOS PC image is built without thread support
  ("This Perl not built to support threads"). The Perl driver layer is
  therefore not viable on OHOS and is a separate deliverable.
- The integration test driver `test_programs` (bash/perl) is dropped from
  TESTS by overriding `TESTS=test_locarna_lib` on the `make check` command
  line (the pre-generated Makefile.in uses `$(am__EXEEXT_1) $(SCRIPTTESTS)`,
  so patching it is fragile). The upstream unit suite (Catch2, 22 test cases
  / 175 assertions: test_locarna_lib) runs and is parsed for the HMBS
  upstream-test marker.
- `make install` is driven through the bundled config/install-sh (via
  /bin/sh) to bypass the OHOS host `install` shim (Error 64 on the
  multi-file pkginclude header batch).
- The library + binaries are built static (--disable-shared) to avoid the
  OHOS shared-library loading pitfalls (R26).
- patches/0001-src-LocARNA-options.cc.patch fixes an AArch64-only portability
  bug in LocARNA::process_options(): it stores getopt_long()'s int return
  value in a `char`. On AArch64 `char` is unsigned, so EOF (-1) becomes 255
  and `while ((c = getopt_long(...)) != EOF)` never terminates -- every CLI
  invocation (including --help/--version) span at 100% CPU with no output.
  With the fix all eight tools (locarna, locarna_p, exparna_p, sparse,
  locarna_deviation, locarnap_fit, locarna_rnafold_pp, ribosum2cc) run
  normally and are shipped in bin/.
- On OHOS the non-ELF helper scripts that upstream also installs into bin/
  (mlocarna, locarnate, *.pl, ...) are pruned -- see _prune_non_elf_helpers().
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LocarnaConan(ConanFile):
    name = "locarna"
    version = "2.0.1"
    description = ("LocARNA - tools for fast and high-quality pairwise and multiple "
                   "alignment of RNA sequences and structures")
    license = "GPL-3.0-or-later"
    homepage = "https://s-will.github.io/LocARNA"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("viennarna/2.7.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.options.shared:
            # upstream builds a static libLocARNA and links the binaries -static;
            # on OHOS shared-library loading is unreliable (R26), so we keep it static.
            raise ConanInvalidConfiguration("LocARNA is built as a static library (shared is unsupported on OHOS)")

    def source(self):
        data = self.conan_data["sources"][self.version]
        # The CI mirror-fallback can rewrite a scalar `url:` into an ordered
        # list ({mirror,...,official}); accept both shapes.
        urls = data["url"] if isinstance(data["url"], list) else [data["url"]]
        for url in urls:
            try:
                get(self, url, sha256=data["sha256"], strip_root=True)
                return
            except Exception as e:
                self.output.warning(f"source download failed from {url}: {e}")
        raise ConanInvalidConfiguration("source download failed from all mirrors")

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        arch_triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        triplet = arch_triplets.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _prepare_autotools_env(self):
        """Writable TMPDIR + explicit AWK for configure (libuuid pattern)."""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "")
        bindir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        toolchain_awk = ""
        if bindir:
            for name in ("gawk", "awk"):
                candidate = os.path.join(bindir, name)
                if os.path.exists(candidate):
                    toolchain_awk = candidate
                    break
        awk = toolchain_awk or shutil.which("gawk") or shutil.which("awk")
        if not awk:
            raise ConanInvalidConfiguration("An awk implementation is required")
        os.environ["AWK"] = awk
        os.environ["ac_cv_prog_AWK"] = awk
        return awk

    def _fix_viennarna_pc(self):
        """LocARNA's configure requires RNAlib2.pc via PKG_CHECK_MODULES.

        The viennarna package ships RNAlib2.pc with `prefix=/`, which on OHOS
        resolves to the host /lib. Rewrite prefix to the real package folder and
        expose the corrected .pc on PKG_CONFIG_PATH so configure resolves
        RNAlib2 (>= 2.5.1) correctly.
        """
        vrna = self.dependencies["viennarna"].package_folder
        pc_src = os.path.join(vrna, "lib", "pkgconfig", "RNAlib2.pc")
        if not os.path.isfile(pc_src):
            raise ConanInvalidConfiguration("viennarna RNAlib2.pc not found")
        with open(pc_src, encoding="utf-8", errors="replace") as f:
            txt = f.read()
        txt = txt.replace("prefix=/", f"prefix={vrna}")
        pc_dir = os.path.join(self.build_folder, "vrna-pc")
        os.makedirs(pc_dir, exist_ok=True)
        with open(os.path.join(pc_dir, "RNAlib2.pc"), "w", encoding="utf-8") as f:
            f.write(txt)
        existing = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = (pc_dir + ":" + existing) if existing else pc_dir
        return pc_dir

    def generate(self):
        awk = self._prepare_autotools_env()
        pc_dir = self._fix_viennarna_pc()
        # R6: the OHOS adaptations of the pre-generated autotools files
        # (config.sub/config.guess, configure, lib/Makefile.in) happen here —
        # generate() runs after source() and before build(), so the source tree
        # is available and no generated file is rewritten inside build().
        self._apply_ohos_gnu_config_patches()
        self._patch_generated_build_files()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        host_triplet = self._gnu_triplet()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            # only build the static libLocARNA; fully static binaries avoid
            # the OHOS shared-library loading pitfalls (R26)
            "--disable-shared",
        ])
        tc.generate()
        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.prepend_path("PKG_CONFIG_PATH", pc_dir)
        # Ensure host build tools (pkg-config, gawk, awk, install) are resolvable
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.prepend_path("PATH", "/system/bin")
        env.vars(self, scope="build").save_script("conanlocarna_env")

    def _apply_ohos_gnu_config_patches(self):
        """Content-anchored, idempotent OHOS recognition for config/config.sub
        and config/config.guess (defensive; the recipe forces explicit
        *-linux-gnu triplets, so configure never receives an 'ohos' value).
        """
        sub_path = os.path.join(self.source_folder, "config", "config.sub")
        guess_path = os.path.join(self.source_folder, "config", "config.guess")

        def _rewrite(path, repls):
            applied = []
            if not os.path.isfile(path):
                return applied
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            orig = text
            for label, needle, replacement, marker in repls:
                if needle in text and marker not in text:
                    text = text.replace(needle, replacement, 1)
                    applied.append(label)
            if text != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            return applied

        sub_repls = [
            ("ohos basic-OS list", "android* | bsd*", "android* | ohos* | bsd*",
             "android* | ohos*"),
        ]
        guess_repls = [
            ("ohos config.guess branch",
             "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n",
             "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
             "    *:HarmonyOS:*:*)\n"
             "\tcase \"$UNAME_MACHINE\" in\n"
             "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
             "\t    *)             MACHINE=\"$UNAME_MACHINE\" ;;\n"
             "\tesac\n"
             "\techo ${MACHINE}-unknown-linux-ohos\n"
             "\texit ;;\n",
             "*:HarmonyOS:*:*"),
        ]
        _rewrite(sub_path, sub_repls)
        _rewrite(guess_path, guess_repls)

    def _patch_generated_build_files(self):
        """Content-anchored, idempotent OHOS fixes for pre-generated autotools
        files (called from generate(), see R6).

        - configure: E011 umask 077 -> 022 (confXXXXXX temp dirs become
          unwritable on OHOS HMDFS) and an ac_pwd getcwd fallback (E052).
        - lib/Makefile.in: drop the perl subdir.  MLocarna.pm pulls in
          MLocarna::threaded -> `use threads`, and the Perl shipped with the
          OHOS PC image is built without thread support, so the Perl driver
          layer is not viable here (see package()).
        """
        # E011: configure creates confXXXXXX temp dirs with umask 077 (0700); on
        # OHOS HMDFS those dirs are force-downgraded and become unwritable ->
        # use umask 022. Also patch autoconf's ac_pwd check to fall back to $PWD
        # when pwd (getcwd) fails in the HMDFS sandbox.
        fpath = os.path.join(self.source_folder, "configure")
        if os.path.isfile(fpath):
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            orig = text
            if "umask 077" in text:
                text = text.replace("umask 077", "umask 022")
            if 'ac_pwd=`pwd` && test -n "$ac_pwd" &&' in text:
                text = text.replace(
                    'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&',
                    1,
                )
            elif 'ac_pwd=`pwd`' in text and '|| ac_pwd="$PWD"' not in text:
                text = text.replace('ac_pwd=`pwd`', 'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"', 1)
            if text != orig:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info("patched configure: ac_pwd getcwd fallback + umask 077->022 (E011)")
        edits = [
            (os.path.join(self.source_folder, "lib", "Makefile.in"),
             [(r"SUBDIRS\s*=\s*perl\b", "SUBDIRS =")]),
        ]
        for makefile_in, regex_edits in edits:
            if not os.path.isfile(makefile_in):
                continue
            with open(makefile_in, encoding="utf-8", errors="replace") as f:
                text = f.read()
            orig = text
            for pattern, repl in regex_edits:
                text, n = re.subn(pattern, repl, text, count=1)
                if n:
                    self.output.info(f"patched {makefile_in}: {pattern!r} -> {repl!r}")
            if text != orig:
                with open(makefile_in, "w", encoding="utf-8") as f:
                    f.write(text)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_autotools_env()
        # HMDFS getcwd workaround (E052/shell_getcwd): set process cwd to
        # build_folder and pre-set $PWD so the shell pwd builtin falls back to
        # the logical path when getcwd() fails in the HMDFS sandbox.
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Layer 1: upstream unit test suite (Catch2 test_locarna_lib, 22 test
        # cases / 175 assertions). E553: override SHELL=/bin/sh on the make
        # check command line (correct fd inheritance for the automake driver).
        # Restrict TESTS to the Catch2 binary: the upstream integration driver
        # test_programs is a bash/perl script that cannot run on OHOS (no
        # /bin/bash, no perl). Overriding TESTS on the make command line is
        # more robust than patching the pre-generated Makefile.in.
        autotools.make(target="check", args=["-j1", "SHELL=/bin/sh", "TESTS=test_locarna_lib"])
        self._emit_upstream_test_marker()

    def _emit_upstream_test_marker(self):
        """Emit HMBS_UPSTREAM_TEST_RESULT from the automake `make check` that
        already ran in build().

        LocARNA's bundled Catch2 (single-header, no TAP reporter) emits a
        summary line "All tests passed (N assertions in M test cases)". We parse
        that line for the test-case count; the per-test .trs files carry the
        PASS/FAIL verdict. A Check/Catch2 failure makes `make check` return
        nonzero and abort build() before we reach here, so reaching here with
        zero FAIL means the whole suite passed.
        """
        logs = sorted(
            p for p in glob.glob(
                os.path.join(self.build_folder, "**", "*.log"), recursive=True)
            if not p.endswith("test-suite.log") and not p.endswith("testsuite.log")
        )
        test_cases = 0
        assertions = 0
        failed = 0
        for path in logs:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            m = re.search(r"(\d+)\s+assertions?\s+in\s+(\d+)\s+test cases?", text)
            if m:
                assertions = int(m.group(1))
                test_cases = int(m.group(2))
        trs = glob.glob(os.path.join(self.build_folder, "**", "*.trs"), recursive=True)
        for path in trs:
            with open(path, encoding="utf-8", errors="replace") as f:
                if ":test-result: FAIL" in f.read():
                    failed += 1
        passed = test_cases - failed
        discovered = test_cases
        executed = test_cases
        status = "passed" if (failed == 0 and test_cases > 0) else "failed"
        marker = {
            "status": status,
            "framework": "catch2",
            "command": "make check (test_locarna_lib)",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            # parsed from Catch2's "All tests passed (N assertions in M test
            # cases)" summary; kept in the marker so the assertion count has
            # tool-generated evidence (cf. reports/test-report.md)
            "assertions": assertions,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if status != "passed":
            raise RuntimeError("upstream make check failed")

    def _find_install_sh(self):
        """Locate the automake-bundled config/install-sh."""
        for attr in ("source_folder", "base_source_folder", "build_folder"):
            base = getattr(self, attr, None)
            if not base or not os.path.isdir(base):
                continue
            for dirpath, _dirnames, filenames in os.walk(base):
                if "install-sh" in filenames:
                    return os.path.join(dirpath, "install-sh")
        return None

    def package(self):
        install_sh = self._find_install_sh()
        if install_sh:
            # Drive `make install` with MKDIR_P/INSTALL* pointed at the bundled
            # install-sh (via /bin/sh) so the host install shim (which returns
            # Error 64 on the multi-file pkginclude header batch) is bypassed.
            # TMPDIR already points at <build_folder>/tmp (writable) via
            # _prepare_autotools_env().
            make_vars = (
                f'MKDIR_P="/bin/sh {install_sh} -c -d" '
                f'INSTALL="/bin/sh {install_sh} -c" '
                f'INSTALL_PROGRAM="/bin/sh {install_sh} -c" '
                f'INSTALL_DATA="/bin/sh {install_sh} -c -m 644"'
            )
            self.run(
                f'make install DESTDIR="{self.package_folder}" -j1 {make_vars}',
                cwd=self.build_folder,
            )
        else:
            autotools = Autotools(self)
            autotools.install()
        # remove libtool archives (stale absolute libdir paths)
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Upstream LocARNA-2.0.pc ships `prefix=/` (which resolves to the host
        # /lib on OHOS) and bakes this machine's build-time flags into
        # Libs:/Cflags: — the viennarna Conan cache dir and the shared
        # ~/usr/local prefix. Rewrite prefix to a relocatable ${pcfiledir}
        # expression, declare the ViennaRNA requirement the .pc is missing, and
        # drop the foreign absolute -L/-I flags, so the shipped .pc stays valid
        # after the package is relocated to another machine (E524). Conan
        # consumers normally use CMakeDeps/PkgConfigDeps (cpp_info + requires);
        # this file is the upstream convenience artifact.
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "LocARNA-2.0.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8", errors="replace") as f:
                pct = f.read()
            # `prefix=/` -> relocatable; ${pcfiledir} is the dir holding this .pc
            # (i.e. <prefix>/lib/pkgconfig), so ../.. is the package root.
            pct = pct.replace("prefix=/", "prefix=${pcfiledir}/../..")
            # libLocARNA-2.0.a keeps 8 undefined vrna_* symbols and 5 installed
            # public headers include <ViennaRNA/...>, so ViennaRNA is a public
            # requirement of the .pc (upstream omits it, relying on @LIBS@).
            if "Requires:" not in pct:
                pct = pct.replace("Libs:", "Requires: RNAlib2\nLibs:", 1)
            pct = self._strip_foreign_pc_flags(pct)
            with open(pc, "w", encoding="utf-8") as f:
                f.write(pct)
        if str(self.settings.os) == "OHOS":
            self._prune_non_elf_helpers()

    def _strip_foreign_pc_flags(self, pct: str) -> str:
        """Remove -L/-I flags from a .pc that point outside the package folder.

        Every absolute search path that is not inside this package (viennarna's
        Conan cache dir, the shared ~/usr/local prefix, ...) is build-machine
        specific and must not be shipped. Handles both the joined form
        (`-L/path`) and the space-separated form (`-L /path`) on Libs/Cflags and
        their .private variants.
        """
        pkg = os.path.abspath(self.package_folder)

        def _strip_line(line: str) -> str:
            # joined form: -L/abs or -I/abs
            line = re.sub(r"(-[LI])(/\S+)",
                          lambda m: m.group(0) if m.group(2).startswith(pkg) else "",
                          line)
            # space-separated form: -L /abs or -I /abs
            line = re.sub(r"(-[LI])\s+(/\S+)",
                          lambda m: m.group(0) if m.group(2).startswith(pkg) else "",
                          line)
            return " ".join(line.split())

        out = []
        for line in pct.splitlines():
            if re.match(r"^(Libs|Cflags)(\.private)?:", line):
                line = _strip_line(line)
            out.append(line)
        text = "\n".join(out)
        if pct.endswith("\n"):
            text += "\n"
        return text

    def _prune_non_elf_helpers(self):
        """Keep only the native ELF tools in bin/ on OHOS.

        Upstream `make install` also drops ~23 interpreter-driven helper
        scripts into bin/ (mlocarna, locarnate, locarna-motif-scan, exploc_p,
        locarna_mcc, dot2pp, pp2dot, mlocarna_nnames, the *.pl utilities,
        RNAz.pm/LocARNA_RNAz.pm and benchmark-plot.R). They need
        MLocarna.pm -> MLocarna::threaded -> `use threads`, and the Perl
        shipped with the OHOS PC image is built without thread support
        ("This Perl not built to support threads"); Rscript is absent too.
        Shipping executables that cannot start is worse than not shipping
        them (and each one costs up to 2x10s in the L2 bin/ smoke matrix),
        so on OHOS only the eight C++ tools remain in bin/.
        """
        bin_dir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bin_dir):
            return
        removed = []
        for entry in sorted(os.listdir(bin_dir)):
            path = os.path.join(bin_dir, entry)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as f:
                    is_elf = f.read(4) == b"\x7fELF"
            except OSError:
                is_elf = False
            if not is_elf:
                os.remove(path)
                removed.append(entry)
        if removed:
            self.output.info(
                "OHOS: removed %d non-ELF helper script(s) from bin/: %s"
                % (len(removed), ", ".join(removed)))

    def package_info(self):
        self.cpp_info.libs = ["LocARNA-2.0"]
        # Upstream installs headers under include/LocARNA-2.0/LocARNA/*.hh; both
        # the base include dir and the API-versioned subdir must be on the include
        # path so that `#include <LocARNA/sequence.hh>` resolves for CMakeDeps
        # (find_package) and PkgConfigDeps consumers alike.
        self.cpp_info.includedirs = ["include", "include/LocARNA-2.0"]
        self.cpp_info.libdirs = ["lib"]
        # The package also ships the eight command line tools in bin/ (see
        # patches/0001). Declare bindirs explicitly so the CLI capability is
        # visible to consumers/CI (R38/commands.json).
        self.cpp_info.bindirs = ["bin"]
        # libLocARNA-2.0.a does NOT embed ViennaRNA (it keeps undefined vrna_*
        # symbols and the installed public headers include <ViennaRNA/...>), so
        # the viennarna requirement is a real link/compile dependency of
        # consumers; math/pthread come from the C++ runtime usage.
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "LocARNA-2.0")
        self.cpp_info.set_property("cmake_file_name", "locarna")
        self.cpp_info.set_property("cmake_target_name", "locarna::locarna")
