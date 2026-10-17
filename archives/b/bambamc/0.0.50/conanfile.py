#!/usr/bin/env python3
"""Conan recipe for bambamc 0.0.50 — OHOS (aarch64-linux-ohos) adaptation.

bambamc is German Tischler's lightweight C implementation of name-collating
BAM file input and BAM file output (SAM/BAM decoding, BGZF gzip layer on top
of zlib).

Adaptation notes
----------------
* The official tag tarball ships **no generated `configure`** (upstream keeps
  `Makefile.in`/`configure` out of the repository), so `build()` bootstraps with
  `autoreconf -fiv` first.
* `configure.in` uses `PKG_PROG_PKG_CONFIG` / `PKG_CHECK_MODULES`, which are
  defined in pkg-config's `pkg.m4`.  That file is not on aclocal's implicit
  search path in this toolchain, so the macro stayed unexpanded and the
  generated `configure` died with a shell syntax error.  The recipe carries
  `m4-pkg.m4` and copies it to `<source>/m4/pkg.m4` **before** `autoreconf`
  (configure.in declares `AC_CONFIG_MACRO_DIR([m4])`, so autoreconf passes
  `-I m4` to aclocal).  Same approach as the merged libfyaml 0.9.6 recipe.
* `config.guess`/`config.sub` are produced by autoreconf and cannot recognise
  HarmonyOS, so the two committed patches re-add the OHOS detection the repo
  standard requires (E007/E072); they are applied **after** `autoreconf`, which
  would otherwise overwrite them.  No `--build`/`--host` triplets are used
  (native compilation).
* autoconf's `config.status` template creates its temp directory under
  `umask 077`; on HMDFS that directory is not writable by its own creator and
  configuration aborts with "could not setup config files machinery"
  (E011/E110/E114/E136).  The freshly generated `configure` is normalised to
  `umask 022` before it is executed.
* Upstream's only test programs (`bamreadertest`, `bamwritertest`) are
  assert-based self-checking binaries.  Conan's Release profile injects
  `-DNDEBUG`, which would compile every assertion away; upstream's own default
  (`--enable-fast=no`) leaves them enabled, so `NDEBUG` is dropped here.
* `zlib/1.3.1.1` is used deliberately: `zlib/1.3.1`, `zlib/1.3.1.1` and
  `zlib/1.3.2` all resolve to the *same* package_id on the OHOS profile
  (`6b129b068851896169fae42d399fa922d239ce8a`), but only the latter two inject
  `CFLAGS="-fPIC -O2"`.  `zlib/1.3.1`'s `libz.a` is therefore not PIC
  (`zutil.o` reaches the global `z_errmsg` through
  `R_AARCH64_ADR_PREL_PG_HI21`), which makes `ld.lld` refuse to absorb it into
  a shared object.  Package_id does not encode CFLAGS, so the variant has to be
  probed with `readelf -r`, not chosen by ref name.
"""
import gzip
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

UPSTREAM_HOMEPAGE = "https://github.com/gt1/bambamc"


class BambamcConan(ConanFile):
    name = "bambamc"
    version = "0.0.50"
    description = ("Lightweight C implementation of name collating BAM file input "
                   "and BAM file output")
    license = "GPL-3.0-or-later"
    homepage = UPSTREAM_HOMEPAGE
    url = UPSTREAM_HOMEPAGE
    topics = ("bam", "sam", "bioinformatics", "name-collation", "bgzf")

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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bambamc {self.version} is validated for Linux/OHOS only, got {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)
        # pkg.m4 (pkg-config 0.29.2, serial 12) carried with the recipe: the
        # OHOS/CI toolchain does not expose it on aclocal's search path.
        copy(self, "m4-pkg.m4", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        # See the module docstring: 1.3.1.1 is the PIC variant; zlib/1.3.1 shares
        # the same package_id but is not PIC.
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # The clean CI sandbox has autoconf/autoreconf/m4 on PATH
        # (/data/service/hnp/bin) but no aclocal/automake/libtoolize, which
        # autoreconf needs to bootstrap this tarball.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # zlib is probed by configure via PKG_CHECK_MODULES; AutotoolsToolchain
        # prepends the generators folder to PKG_CONFIG_PATH so the .pc that
        # PkgConfigDeps writes here is the one configure resolves.
        PkgConfigDeps(self).generate()
        # AutotoolsToolchain does not translate dependency cpp_info into
        # CPPFLAGS/LDFLAGS; AutotoolsDeps does, and src/Makefile.am only ever
        # consumes CPPFLAGS (ZLIBCPPFLAGS from the .pc is never referenced),
        # so without this the compile of <zlib.h> consumers would not find the
        # header.
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Upstream's test programs are assert-based; upstream default is
        # --enable-fast=no (asserts on). Keep them on so the test run is real.
        tc.ndebug = None
        tc.configure_args.append("--enable-static")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        # 1) pkg.m4 has to be in m4/ before autoreconf, otherwise
        #    PKG_CHECK_MODULES stays unexpanded and configure fails.
        shutil.copy(os.path.join(self.export_sources_folder, "m4-pkg.m4"),
                    os.path.join(self.source_folder, "m4", "pkg.m4"))

        autotools = Autotools(self)
        # 2) bootstrap: the tag tarball carries no generated configure
        autotools.autoreconf()
        # 3) OHOS triplets in the freshly generated config.guess/config.sub
        #    (must come after autoreconf, which rewrites both files)
        apply_conandata_patches(self)
        # 4) HMDFS workaround (E011/E110/E114/E136)
        self._normalise_config_status_umask()

        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _normalise_config_status_umask(self):
        """autoconf's config.status template uses `umask 077 && mktemp -d`.

        On HMDFS the resulting directory ends up not writable by its creator
        and config.status aborts.  Rewrite the generated configure before it
        runs; fail loudly if the expected pattern is gone.
        """
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if "umask 077" not in content:
            raise ConanInvalidConfiguration(
                "expected 'umask 077' in the generated configure (E011 workaround anchor missing)")
        content = content.replace("umask 077", "umask 022")
        with open(cfg, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(cfg, 0o755)
        self.output.info("  [ok] configure: config.status temp dir umask normalised to 022")

    def _run_upstream_tests(self):
        """Build artefacts of upstream's own test programs and run them.

        Upstream registers no autotools test suite (`make check` has an empty
        TESTS list); `bamreadertest` and `bamwritertest` are its only test
        entry points and are built as noinst_PROGRAMS by `make`.
        """
        src_dir = os.path.join(self.build_folder, "src")
        bam_out = os.path.join(self.build_folder, "bamwritertest.bam")
        writer = os.path.join(src_dir, "bamwritertest")
        reader = os.path.join(src_dir, "bamreadertest")

        self.run('"%s" > "%s" 2> "%s"' % (writer, bam_out,
                                          os.path.join(self.build_folder, "bamwritertest.err")),
                 cwd=self.build_folder)
        self.run('"%s" < "%s" > "%s" 2> "%s"' % (reader, bam_out,
                                                 os.path.join(self.build_folder, "bamreadertest.fastq"),
                                                 os.path.join(self.build_folder, "bamreadertest.err")),
                 cwd=self.build_folder)

        size = os.path.getsize(bam_out)
        if size == 0:
            raise ConanInvalidConfiguration("bamwritertest produced an empty BAM file")
        with open(bam_out, "rb") as handle:
            head = handle.read(2)
        if head != b"\x1f\x8b":
            raise ConanInvalidConfiguration(
                "bamwritertest output is not a BGZF stream (bad gzip magic)")
        with gzip.open(bam_out, "rb") as handle:
            magic = handle.read(4)
        if magic != b"BAM\x01":
            raise ConanInvalidConfiguration(
                "bamwritertest output does not decompress to a BAM header")
        self.output.info("  [ok] upstream tests: bamwritertest %d bytes BGZF/BAM, bamreadertest rc=0"
                         % size)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "GPLv3", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        self._relocate_pkgconfig()

    def _relocate_pkgconfig(self):
        """Drop build-machine paths the autotools flow bakes into bambamc.pc.

        configure expands ZLIBPKGLIBS (taken from the zlib .pc) into `Libs:`,
        which would embed the packaging machine's cache path. `Requires: zlib`
        already carries the dependency, so the absolute -L entry is removed.
        """
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "bambamc.pc")
        if not os.path.isfile(pc):
            return
        kept = []
        changed = False
        with open(pc, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("Libs:") and "-L/" in line:
                    prefix = line.split("-L/", 1)[0].rstrip()
                    kept.append(prefix + " -lbambamc\n")
                    changed = True
                else:
                    kept.append(line)
        if changed:
            with open(pc, "w", encoding="utf-8") as handle:
                handle.writelines(kept)
            self.output.info("  [ok] bambamc.pc: removed build-machine -L path")

    def package_info(self):
        self.cpp_info.libs = ["bambamc"]
        # no libm symbols in the archive (checked with `nm -u libbambamc.a`);
        # zlib is carried by the transitive requirement, not as a system lib.
        self.cpp_info.set_property("pkg_config_name", "bambamc")
