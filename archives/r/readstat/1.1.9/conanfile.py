#!/usr/bin/env python3
"""Conan recipe for readstat 1.1.9 — C library for reading/writing SPSS, SAS and Stata data files.

Upstream: https://github.com/WizardMac/ReadStat (tag v1.1.9, tarball sha256 89af7c785a7a…).

Build system: Autotools only (configure.ac + Makefile.am; the VS17/ directory is an
MSVC project and there is no CMake build in the tarball).

HarmonyOS PC adaptations
------------------------
* The GitHub tag archive ships **no** pre-generated `configure`, so `autoreconf -fi`
  runs first.  It needs three tools the CI worker does not have on PATH:
  automake (aclocal/automake), libtool (libtoolize) and gettext's m4 macros —
  `configure.ac` uses `LT_INIT` *and* `AM_ICONV`, and `AM_ICONV` is defined in
  gettext's `iconv.m4`, which lives in `<gettext>/share/aclocal` and is NOT on the
  default aclocal search path (hnp gettext only ships `nls.m4` in share/aclocal).
  Declared as tool_requires; their ACLOCAL_PATH/`_lt_pkgdatadir`/PERL5LIB exports
  come from the workspace OHOS recipes (libtool needs `_lt_pkgdatadir` to find its
  baked `@datadir@`, see libtool/2.5.4 recipe).  `autoconf` itself is taken from
  the SDK/HNP: declaring conan `autoconf` would pull an OHOS-built perl whose XS
  modules crash HNP perl (`Perl_my_cxt_init`, device-facts §一.23).
* `config.guess` cannot recognise `uname` = `HarmonyOS`, so `--build`/`--host` are
  pinned to `aarch64-unknown-linux-gnu` (same compatible-tuple strategy as
  epeg/aldo; matches the `*linux*` case in configure.ac that adds `-lm`).
* HMDFS temp-dir family (device-facts §一.13/E011): the generated `configure`
  creates its `config.status` scratch dirs with `(umask 077 && …)` and
  `mktemp -d "./confXXXXXX"`, which on HMDFS land as mode-2700 directories the
  build user cannot write into (`can't create ./confXXXXXX/subs1.awk: Permission
  denied`).  Normalised at build time to umask 022 / `${TMPDIR:-.}` — same
  standard fix as E0678/symphony/integrit, no patch file needed.
* `zlib` is optional upstream (`AC_CHECK_LIB(z, deflate)`), but the upstream test
  suite writes and reads ZSAV (`RT_FORMAT_SAV_COMP_ZLIB`, part of `RT_FORMAT_SPSS`
  in `src/test/test_readstat.h`), so a build without HAVE_ZLIB cannot pass
  `make check`.  zlib/1.3.1.1 is in the registry (OHOS binary present), so it is
  required explicitly instead of silently picking up the SDK's system copy
  (R26/G3: no undeclared system library).
  `libxlsxwriter`/`libcsv` are optional readers/writers that are NOT part of the
  upstream test surface (`RT_FORMAT_*` covers dta/sav/por/sas/xport only) and are
  absent from the registry → left disabled (no loss of test coverage).
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ReadstatConan(ConanFile):
    name = "readstat"
    version = "1.1.9"
    description = (
        "ReadStat: MIT-licensed C library and command line tools for reading "
        "(and writing) SAS, Stata and SPSS data files"
    )
    license = "MIT"
    homepage = "https://github.com/WizardMac/ReadStat"
    url = "https://github.com/WizardMac/ReadStat"
    topics = ("sas", "stata", "spss", "statistics", "data-format")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Optional upstream (HAVE_ZLIB) but required to run the upstream ZSAV
        # test cases; also keeps the SDK system libz out of the package (R26).
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # GitHub tag archive ships no configure → autoreconf needs
        # aclocal/automake (aclocal finds LT_INIT/AM_ICONV macros through the
        # ACLOCAL_PATH these recipes export) and libtoolize.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # iconv.m4 / gettext.m4 (AM_ICONV) + autopoint.  MUST be 0.22.5.1:
        # the 0.22.5 package in the registry ships only include/lib/share/locale
        # (no bin/, no share/aclocal → "possibly undefined macro: AM_ICONV",
        # round-1 G2 failure), while 0.22.5.1 ships bin/autopoint + share/aclocal
        # + share/gettext — same recipe avahi-compat-libdns_sd uses.
        self.tool_requires("gettext/0.22.5.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("readstat supports Linux and OHOS only")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── OHOS build helpers ────────────────────────────────────────────────

    @staticmethod
    def _gnu_build_triplet(conanfile):
        arch = str(conanfile.settings.arch)
        if arch in ("armv8", "armv8.3", "aarch64"):
            return "aarch64-unknown-linux-gnu"
        if arch == "x86_64":
            return "x86_64-unknown-linux-gnu"
        raise ConanInvalidConfiguration(f"Unsupported arch for readstat: {arch}")

    def _patch_hmdfs_tempdirs(self):
        """E011 family: normalise autoconf's temp-dir handling on HMDFS.

        Applied to the freshly generated `configure` before running it; prints
        verifiable counters so a silent no-op (fix function pointing at a
        missing file) is visible in the build log.
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            self.output.warning(f"configure not found at {configure}; skip HMDFS temp-dir fix")
            return 0
        before = 0
        for old, new in (
            ("umask 077", "umask 022"),
            ('mktemp -d "./confXXXXXX"', 'mktemp -d "${TMPDIR:-.}/confXXXXXX"'),
            ("tmp=./conf$$-$RANDOM", "tmp=${TMPDIR:-.}/conf$$-$RANDOM"),
        ):
            try:
                content = open(configure, encoding="utf-8", errors="ignore").read()
            except OSError as exc:  # pragma: no cover - defensive
                self.output.warning(f"cannot read configure: {exc}")
                return 0
            if old in content:
                replace_in_file(self, configure, old, new)
                before += 1
        residual = open(configure, encoding="utf-8", errors="ignore").read()
        n_umask077 = residual.count("umask 077")
        self.output.info(
            f"[hmdfs] configure temp-dir fixes applied={before} "
            f"residual_umask077={n_umask077}"
        )
        return before

    def _gettext_pkg(self):
        return self.dependencies.build["gettext"].package_folder

    def _iconv_macro_dirs(self):
        """Dirs holding gettext's m4 macro set (iconv.m4 defines AM_ICONV).

        Candidates: the conan gettext package (0.22.5.1 ships share/aclocal,
        0.22.5 does not) plus the HNP gettext that ships the same macro set
        under share/gettext/m4.  Hard-fails with the full candidate list so a
        broken macro path shows up in generate() instead of as autoconf's
        "possibly undefined macro: AM_ICONV" deep inside autoreconf.
        """
        gettext_pkg = self._gettext_pkg()
        candidates = [
            os.path.join(gettext_pkg, "share", "aclocal"),
            os.path.join(gettext_pkg, "share", "gettext", "m4"),
            os.path.join(gettext_pkg, "share", "gettext", "aclocal"),
        ]
        for pattern in (
            "/data/service/hnp/*/*/share/gettext/m4",
            "/data/service/hnp/*/*/share/aclocal",
        ):
            candidates.extend(sorted(glob.glob(pattern)))
        found = [d for d in candidates if os.path.isfile(os.path.join(d, "iconv.m4"))]
        if not found:
            raise ConanInvalidConfiguration(
                "AM_ICONV macro (iconv.m4) not found in any candidate dir:\n  "
                + "\n  ".join(candidates)
            )
        self.output.info("[aclocal] AM_ICONV macro dirs: " + ", ".join(found))
        return found

    def _gettext_datadir(self):
        """share/gettext of the tool_require, for autopoint/gettextize."""
        gettext_pkg = self._gettext_pkg()
        datadir = os.path.join(gettext_pkg, "share", "gettext")
        if os.path.isfile(os.path.join(datadir, "ABOUT-NLS")):
            return datadir
        for cand in sorted(glob.glob("/data/service/hnp/*/*/share/gettext")):
            if os.path.isfile(os.path.join(cand, "ABOUT-NLS")):
                return cand
        self.output.warning(f"gettext data files not found under {gettext_pkg}")
        return ""

    def generate(self):
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            # LT_INIT([disable-static]) only flips the default; ask explicitly.
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        else:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        if str(self.settings.os) == "OHOS":
            triplet = self._gnu_build_triplet(self)
            tc.configure_args.extend([f"--build={triplet}", f"--host={triplet}"])

        # Pin the toolchain flags instead of inheriting whatever the CI worker
        # exports (R33 / CFLAGS leakage precedent), and neutralise one warning
        # the upstream `-Werror` would otherwise turn fatal: clang 15 enables
        # -Wstrict-prototypes by default while upstream still declares
        # `static void print_version()` style prototypes (E063: keep the
        # disable precise to that one category).
        #
        # MUST go through `extra_cflags` — `AutotoolsToolchain.cflags` is a
        # read-only @property that recomputes `build_type_flags + extra_cflags`
        # on every access, so `tc.cflags.extend(...)` silently mutates a
        # temporary (round-2 evidence: configure summary printed `CFLAGS: -O3`
        # with no user flags and the -Werror failure came straight back).
        tc.extra_cflags.extend(["-O3", "-pipe", "-DNDEBUG", "-Wno-strict-prototypes"])
        tc.extra_cxxflags.extend(["-O3", "-pipe", "-DNDEBUG"])

        env = tc.environment()

        # AM_ICONV (gettext's iconv.m4) is NOT on aclocal's default search
        # path — conan gettext does not export ACLOCAL_PATH and hnp's
        # share/aclocal only carries nls.m4, so `autoreconf` dies with
        # "possibly undefined macro: AM_ICONV".  Collect every candidate dir
        # (conan gettext package + HNP gettext, same image on device and CI
        # worker) and refuse to continue when none of them has iconv.m4 —
        # that fails fast with a readable message instead of the autoconf one.
        for _d in self._iconv_macro_dirs():
            env.prepend_path("ACLOCAL_PATH", _d)
        gettext_datadir = self._gettext_datadir()
        if gettext_datadir:
            # autopoint/gettextize bake their data dir at gettext build time;
            # the env override keeps them relocatable (avahi precedent, R19).
            env.define("gettext_datadir", gettext_datadir)

        # HMDFS /tmp is read-only (device-facts §一.1): keep autoconf scratch
        # files inside the build tree.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)

        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)

        # 1) No pre-generated configure in the tag archive → bootstrap.
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            self.run("autoreconf -fi", cwd=self.source_folder,
                     env=["conanbuild", "conanautotoolstoolchain"])
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "autoreconf -fi did not produce configure; see build log"
            )

        # 2) HMDFS temp-dir normalisation (must precede ./configure).
        self._patch_hmdfs_tempdirs()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream official test suite (src/test, automake TESTS): 4 programs
        # (test_readstat / test_dta_days / test_sav_date / test_double_decimals).
        autotools.make(args=["check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["readstat"]
        self.cpp_info.system_libs = ["m"]
        # readstat/extract_metadata are installed to bin/ by `make install`
        # (bin_PROGRAMS) — declares them for consumers and, per R38/L0k, makes
        # the software-level commands.json mandatory (archives/r/readstat/).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "readstat")
        self.cpp_info.set_property("cmake_target_name", "readstat::readstat")
        self.cpp_info.set_property("pkg_config_name", "readstat")
