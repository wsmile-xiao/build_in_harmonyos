#!/usr/bin/env python3
"""Conan recipe — ViennaRNA 2.7.2 (Autotools).

The ViennaRNA Package: a C code library (RNAlib, libRNA) and several
stand-alone programs (RNAfold, RNAcofold, RNAalifold, ...) for the
prediction and comparison of RNA secondary structures.

OHOS adaptation:
- config/config.sub + config/config.guess get HarmonyOS ('ohos' OS) / the
  'aarch64-linux-ohos' host triplet recognition patches (E072/E205).
- configure umask 077 -> 022 (E011: HMDFS 0700 temp dirs are unwritable)
  + TMPDIR pointed at the writable build folder (/tmp is read-only on OHOS).
- build/host triplets derived from Conan settings.
- The scripting language interfaces (Python/Perl/SWIG) and the optional
  numeric add-ons (GSL, MPFR) and the libsvm classifiers (-lstdc++) are
  disabled: they are separate deliverables / require host toolchains that
  are out of scope for a C-library + programs package and would pull in
  extra runtime dependencies.
- The C-library unit tests (Check framework, 10 programs) and the
  executable-program tests (RNAfold/RNAcofold/RNAalifold, 9 TAP scripts)
  are enabled and run via `make check` (19 tests registered in TESTS).
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ViennarnaConan(ConanFile):
    name = "viennarna"
    version = "2.7.2"
    description = ("The ViennaRNA Package — a C code library and several stand-alone "
                   "programs for the prediction and comparison of RNA secondary structures")
    license = "LicenseRef-ViennaRNA"  # custom license, see license.txt
    homepage = "https://www.tbi.univie.ac.at/RNA/"
    url = ""
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.options.shared:
            # upstream libRNA_la_LDFLAGS forces -static: only a static lib is produced
            raise ConanInvalidConfiguration("ViennaRNA is built as a static library (upstream forces -static)")

    def requirements(self):
        # Check framework, only used to build/link the C-library unit tests
        # (configure: PKG_CHECK_MODULES([CHECK], [check >= 0.9.4]))
        self.requires("check/0.15.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

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

    def generate(self):
        awk = self._prepare_autotools_env()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        host_triplet = self._gnu_triplet()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"AWK={awk}",
            f"ac_cv_prog_AWK={awk}",
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            # scripting interfaces are separate deliverables, not the C-library package
            "--without-python",
            "--without-perl",
            "--without-swig",
            # optional numeric dependencies / classifiers kept off for a lean build
            "--without-gsl",
            "--disable-mpfr",
            "--without-svm",  # avoids the -lstdc++ linkage on OHOS (libc++)
            # sub-packages (RNAforester / Kinfold / RNAlocmin) not part of this package
            "--without-forester",
            "--without-kinfold",
            "--without-rnalocmin",
            # toolchain flags that can destabilize the OHOS clang build
            "--disable-lto",
            "--disable-openmp",
            "--disable-vectorize",
            "--disable-simd",
            # reference manual build (doc/doxygen) requires doxygen +
            # sphinx-build + pdflatex, none of which are present on the OHOS
            # build host. --without-doc alone does NOT clear the
            # WITH_REFERENCE_MANUAL automake conditional (configure keeps
            # with_doc enabled and only disables the *_pdf/*_html sub-drivers),
            # so doc/doxygen's noinst_DATA `xml/*` still ends up in all-am
            # with no rule to build it -> "No rule to make target 'xml/*'".
            # patches/0003-Makefile.in-no-doc.patch drops doc/doxygen and doc
            # from the top-level SUBDIRS so make never enters them. Keep
            # --without-doc anyway (harmless) so configure does not try to
            # regenerate the manuals.
            "--without-doc",
            # C-library unit tests stay ON (default): our check/0.15.2 requirement
            # satisfies PKG_CHECK_MODULES([CHECK], [check >= 0.9.4]).
        ])
        tc.generate()
        # autoconf temp files must not land in /tmp (read-only on OHOS)
        env = Environment()
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.vars(self, scope="build").save_script("conavrna_tmpdir")

    def _apply_ohos_gnu_config_patches(self):
        """Content-anchored, idempotent OHOS recognition for config/config.sub
        and config/config.guess.

        The old 0001/0002 unified diffs were keyed to the exact line offsets /
        context of the official tarball's config scripts, so any drifted or
        newer-generation config.sub/config.guess in the source archive made the
        patch application abort with "source file is different" and killed the
        whole build. Here we key on stable substrings that exist across config
        script generations (2023-era and 2024+ forms), which lets the edits
        apply regardless of minor drift, and we never abort if an anchor is
        missing.

        The recipe forces explicit --build/--host = *-unknown-linux-gnu triplets
        (libuuid pattern), so configure/config.sub never receive an 'ohos' value;
        these edits are defensive OHOS recognition kept for consistency with the
        repo convention (libuuid keeps a config.guess patch) and for any future
        use of an OHOS triplet. Consequently a missing anchor is only logged as a
        warning, not treated as a build failure.
        """
        sub_path = os.path.join(self.source_folder, "config", "config.sub")
        guess_path = os.path.join(self.source_folder, "config", "config.guess")

        def _rewrite(path, repls):
            """Apply content-anchored, idempotent replacements.

            Each repl is (label, needle, replacement, marker): apply only if
            ``needle`` is present AND ``marker`` (something that only exists
            once the edit is in place) is absent, so re-runs never duplicate.
            Returns the labels that were applied this call.
            """
            applied = []
            if not os.path.isfile(path):
                self.output.warning("_apply_ohos_gnu_config_patches: no such file: %s" % path)
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

        # config.sub — OHOS must be recognized as (a) a basic OS and (b) a valid
        # linux kernel-OS combination. Both are mandatory (knowledge
        # DRAFT-autotools-config-sub-silent-ohos-triplet: only one of the two
        # leaves the triplet silently normalized to *-linux-gnu-ohos or rejected).
        sub_repls = [
            # basic OS list: 'android* | bsd* ...' -> add ohos* after android*
            ("ohos basic-OS list", "android* | bsd*", "android* | ohos* | bsd*",
             "android* | ohos*"),
            # old-generation kernel-OS combo list (ViennaRNA 2.7.2 ships this): the
            # 'linux-...*' line with no trailing '-' (e.g. 'linux-newlib* \').
            ("ohos kernel-combo old-gen",
             "linux-android* | linux-newlib* \\\n",
             "linux-android* | linux-newlib* | linux-ohos* \\\n",
             "linux-android* | linux-newlib* | linux-ohos*"),
            # new-generation kernel-OS combo list (2024+ config.sub, trailing '-'
            # tokens): 'linux-newlib*- \' -> add linux-ohos*-
            ("ohos kernel-combo new-gen",
             "linux-newlib*- \\\n",
             "linux-newlib*- | linux-ohos*- \\\n",
             "linux-newlib*- | linux-ohos*-"),
        ]
        # config.guess — add a HarmonyOS detection branch after the main case
        # selector, in the same echo+exit style the old 0002 patch used.
        guess_repls = [
            ("ohos config.guess branch",
             "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n",
             "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
             "    *:HarmonyOS:*:*)\n"
             "\tcase \"$UNAME_MACHINE\" in\n"
             "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
             "\t    armv7*|armv8*) MACHINE=arm ;;\n"
             "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
             "\t    i?86)          MACHINE=i686 ;;\n"
             "\t    *)             MACHINE=\"$UNAME_MACHINE\" ;;\n"
             "\tesac\n"
             "\techo ${MACHINE}-unknown-linux-ohos\n"
             "\texit ;;\n",
             "*:HarmonyOS:*:*"),
        ]

        sub_done = _rewrite(sub_path, sub_repls)
        guess_done = _rewrite(guess_path, guess_repls)
        if sub_done:
            self.output.info("patched config/config.sub for ohos: %s" % ", ".join(sub_done))
        else:
            self.output.info(
                "config/config.sub already carries (or could not anchor) OHOS recognition; "
                "recipe uses explicit *-linux-gnu triplets so this is non-fatal")
        if guess_done:
            self.output.info("patched config/config.guess for ohos: %s" % ", ".join(guess_done))
        else:
            self.output.info(
                "config/config.guess already carries (or could not anchor) OHOS recognition; "
                "recipe uses explicit *-linux-gnu triplets so this is non-fatal")

    def build(self):
        apply_conandata_patches(self)
        self._apply_ohos_gnu_config_patches()
        self._prepare_autotools_env()
        # HMDFS getcwd workaround (E052/shell_getcwd): conan cache parent
        # directories are inaccessible to getcwd() on HMDFS, causing bash's
        # pwd to fail with "working directory cannot be determined".
        # Triple fallback (same as aribb24/libuuid pattern):
        # ① set process cwd to build_folder; ② pre-set $PWD so shell pwd
        # builtin falls back to logical path when getcwd() fails.
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        # E011: configure creates confXXXXXX temp dirs with umask 077 (0700);
        # on OHOS HMDFS those dirs are force-downgraded and become unwritable
        # -> use umask 022 so config.status can write its helper files.
        # Also patch autoconf's ac_pwd check to fallback to $PWD when pwd
        # (getcwd) fails in the HMDFS sandbox.
        fpath = os.path.join(self.source_folder, "configure")
        if os.path.isfile(fpath):
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            orig = text
            if "umask 077" in text:
                text = text.replace("umask 077", "umask 022")
            # autoconf >= 2.70 style: ac_pwd=`pwd` && test -n "$ac_pwd" &&
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
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Layer 1: upstream native test suite. make check registers 19 tests
        # (10 C-library Check programs + 9 executable-program TAP scripts).
        # The .ts -> .c checkmk-generated sources are already shipped in the
        # tarball, and the check framework comes from our check requirement.
        # E553: the OHOS PC bash 5.3 (hnp port, injected as $(SHELL) via the
        # conan profile buildenv) has an fd-3 inheritance defect: in the
        # automake tap-driver.sh group-command pipeline
        #   { (test) | awk '{ print | "cat >&3" }' } 3>"$logfile"
        # the fd 3 redirection is not propagated into the pipeline elements,
        # so awk's 'cat >&3' fails with "3: Bad file descriptor" / "Broken
        # pipe" and tap-driver flags every TAP test "missing test plan" ERROR
        # (RNAfold/general.log Error 1 killed the whole make check). Override
        # SHELL=/bin/sh (mksh, correct fd inheritance) on the make check
        # command line; a command-line assignment wins over the Makefile
        # builtin and the env aggregate without changing the Makefile or the
        # global profile.
        autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])
        self._emit_upstream_test_marker()

    def _emit_upstream_test_marker(self):
        """Emit HMBS_UPSTREAM_TEST_RESULT from the automake 'make check' that
        already ran in build().

        The ViennaRNA `make check` suite is a mix of two frameworks:
          * 9 executable TAP scripts (RNAfold/RNAcofold/RNAalifold) that emit
            83 TAP `ok`/`not ok` result lines (the official TAP-assertion
            count, 14+3+21+2+14+6+17+2+4 = 83), and
          * 10 Check-framework C programs (energy_evaluation, constraints, ...)
            that report in check's own non-TAP format.
        The HMBS rule4 evidence gate measures this `make check` at the
        TAP-assertion unit and its real-device ground truth is therefore
        discovered=83, executed=83, passed=83 (0 failed, 0 skipped) — as seen
        in the preflight "上游测试：发现 83，执行 83，通过 83". This matches the
        declared upstream_test_total=83 (autotools_tests / TAP-assertion
       口径, see test_package/MANIFEST.yml).

        The counts come from ONE deterministic log source: the per-test
        `<test>.log` files that automake's tap-driver writes, which contain the
        verbatim TAP result lines of the executable scripts. We count the
        `ok`/`not ok` TAP result lines (the exact unit the rule4 gate uses);
        we never count stdout or derive numbers by subtraction. The 10
        Check-framework programs emit no TAP `ok` lines; a Check failure would
        make `make check` return nonzero and abort build() before we reach
        here, so emitting "passed" here implies the whole suite passed.
        """
        # Collect the per-test .log files written by tap-driver under the
        # tests build directory (recursively, to cover tests/RNAfold/*.log
        # etc.). We deliberately exclude test-suite.log (the aggregate) so the
        # counts come from the per-test logs only.
        logs = sorted(
            p for p in glob.glob(
                os.path.join(self.build_folder, "**", "*.log"), recursive=True)
            if not p.endswith("test-suite.log") and not p.endswith("testsuite.log")
        )
        if not logs:
            self.output.error(
                "no per-test *.log files found under build_folder after make check; searched: "
                + os.path.join(self.build_folder, "**", "*.log")
            )
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "failed",
                "framework": "automake",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "no per-test .log files found after make check",
            }))
            raise RuntimeError("upstream make check produced no per-test .log files")

        # Count the raw TAP result lines emitted by the executable scripts.
        # tap-driver copies every `ok`/`not ok` line verbatim into the test's
        # .log (a trailing "PASS <test> (exit status: 0)" line is not a TAP
        # result and is excluded by the anchors). `not ok` lines start with
        # "not ok", so the `^ok\b` pattern cannot also match them (no
        # double-count, no subtraction). TAP `ok ... # SKIP` results are
        # counted as skipped, not passed.
        passed = 0
        failed = 0
        skipped = 0
        for path in logs:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("not ok") and line[6:7] in (" ", "\t", "\n", ""):
                        failed += 1
                    elif line.startswith("ok") and line[2:3] in (" ", "\t", "\n", ""):
                        if "# SKIP" in line or "# skip" in line:
                            skipped += 1
                        else:
                            passed += 1
        # Identity: executed = passed + failed; discovered = executed + skipped.
        executed = passed + failed
        discovered = executed + skipped
        status = "passed" if (failed == 0 and discovered > 0) else "failed"
        marker = {
            "status": status,
            "framework": "automake",
            "command": "make check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if status != "passed":
            self.output.error(
                "upstream make check not fully passed; TAP results: passed=%d failed=%d"
                % (passed, failed))
            raise RuntimeError("upstream make check failed")

    def _find_install_sh(self):
        """Locate the automake-bundled config/install-sh.

        The OHOS host PATH is fronted by an `install` shim that mishandles
        autotools' install argument forms (postgresql-18.3 draft E574-family);
        here `make install` fails in install-pkgincludeHEADERS with
        `Error 64` while copying the ~40 RNAlib headers to include/ViennaRNA.
        Point the INSTALL* variables at the bundled install-sh instead, which
        parses the automake multi-file header batches correctly (new automake
        install-sh installs every file in a batch, unlike the vintage X11R5
        single-file one).
        """
        for attr in ("source_folder", "base_source_folder", "build_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base or not os.path.isdir(base):
                continue
            for dirpath, _dirnames, filenames in os.walk(base):
                if "install-sh" in filenames:
                    return os.path.join(dirpath, "install-sh")
        return None

    def package(self):
        install_sh = self._find_install_sh()
        if install_sh:
            # Same approach as cracklib2/2.9.6 and cyrus-sasl/2.1.28.1 on
            # OHOS: drive `make install` with MKDIR_P/INSTALL/INSTALL_PROGRAM/
            # INSTALL_DATA pointed at the bundled install-sh (via /bin/sh) so
            # the host install shim (which returns Error 64 on the multi-file
            # pkginclude header batch) is bypassed. Use /bin/sh, NOT
            # /system/bin/sh: old libtool (ViennaRNA 2.7.2 era) only
            # recognizes `/bin/sh .../install-sh -c` as an install command and
            # otherwise mis-parses install-sh itself as a file to install.
            # TMPDIR already points at <build_folder>/tmp (writable, OHOS /tmp
            # is read-only) via _prepare_autotools_env().
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
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["RNA"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # libRNA.a contains dlib C++ objects (bundled), so consumers must link
        # the C++ standard library; RNAlib2.pc links pthread + lm.
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("pkg_config_name", "RNAlib2")
        self.cpp_info.set_property("cmake_file_name", "viennarna")
        self.cpp_info.set_property("cmake_target_name", "viennarna::viennarna")
