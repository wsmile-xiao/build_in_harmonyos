#!/usr/bin/env python3
"""Conan recipe — lexd 1.3.5 (Apertium lexicon compiler).

lexd compiles lexicons in an hfst-lexc-like format into ATT transducers,
specialised for non-suffixational morphologies (prefixes, alternations,
sieves, filters). It replaces the ``hfst-twolc`` step in the Apertium
machine-translation pipeline and is a pure C++17 program: the only artifact is
``bin/lexd`` (plus ``share/man/man1/lexd.1`` and ``lib/pkgconfig/lexd.pc``).

Build system: autotools (configure.ac + Makefile.am). The release tarball
ships NO pre-generated ``configure`` and no ``autogen.sh``, and the two ways of
producing one are both unavailable in this environment:

  * ``autoreconf`` via tool_requires would drag perl/5.42.2 (a dependency of
    autoconf/automake in the ohpcd registry) into the build context. That perl
    is musl-linked and crashes outright — verified locally: ``qemu-aarch64
    perl -e 'print 1'`` -> "uncaught target signal 11 (Segmentation fault)";
    apertures/3.9.12 documents the same ABI breakage on the native worker.
  * the CI worker's own autotools are incomplete (autoconf only, no
    automake/aclocal/m4), which is why lttoolbox/3.7.6 solved the identical
    problem by vendoring the autoreconf products.

So ``patches/autotools/`` carries the products of a single ``autoreconf -fi``
run over the unmodified tarball (configure, aclocal.m4, Makefile.in,
src/Makefile.in and the automake aux scripts). They are copied into the source
tree in ``source()`` and nothing is regenerated at build time, so the OHOS
worker needs no autotools and no perl — the same build path runs identically
locally and in CI.

Dependencies (per configure.ac):
  - lttoolbox >= 3.7.1 (pkg-config)  -> Conan lttoolbox/3.7.6
  - icu-uc, icu-io (pkg-config)      -> Conan icu4c/77 (the same package
                                         lttoolbox/3.7.6 requires, so the graph
                                         holds a single ICU)
  - utf8cpp/utf8.h or utf8.h         -> Conan utf8cpp/4.1.1
  - getopt_long (AC_CHECK_FUNCS, libc)

The three PKG_CHECK_MODULES calls are satisfied by passing
``<PKG>_CFLAGS``/``<PKG>_LIBS`` to configure as command-line assignments built
from Conan's dependency model: pkg.m4 skips the pkg-config lookup entirely when
both are set. That is deliberate and avoids two known traps — the registry's
``.pc`` files were installed with ``--prefix=/`` and make pkg-config emit
``-I/include``/``-L/lib`` (E355), and relying on an ambient system ``pkg-config``
binary is not portable across the worker (E468). icu4c/77's ``cpp_info`` already
carries its ``m``/``pthread`` system libs but does not model ``libicuio``, which
``configure`` hard requires via ``PKG_CHECK_MODULES([ICU_IO], [icu-io])``, so
``-licuio`` is added explicitly.

OHOS-specific build handling (all knowledge-graph driven, no source patch):
  * E007/E205  config.guess cannot identify ``uname -s = HarmonyOS``; the
    build triplet is passed explicitly via ``--build=aarch64-unknown-linux-ohos``.
    ``--host`` is deliberately NOT passed, so configure does not fall into
    cross-compiling mode and skip AC_RUN_IFELSE probes.
  * E114       autoconf's generated configure uses ``umask 077 && mktemp -d``;
    on HMDFS the resulting ``drwx--S---`` directory is not writable.
  * E041/E248  the vendored Makefile.in/aclocal.m4 are current, so the
    maintainer rebuild rules are neutered (``ACLOCAL=':'`` …) rather than
    letting make shell out to automake, which the worker does not have.
  * E074       ``make -j1`` — the parallel jobserver fifo fails with EPERM on
    HMDFS.
  * in-source build: tests/feature/Makefile is a hand-written (not
    automake-generated) Makefile that reaches the binary through the relative
    path ../../src/lexd, so the suite only works when srcdir == builddir.

Upstream tests (R51): ``make check`` expands to 6 flag variants x 38 registered
cases (36 positive + 2 negative) = 228 executions. The positive oracle is
``hfst-txt2fst | hfst-fst2strings -X obey-flags -c 10 | sort -u`` diffed
against ``*.strings.gold``; HFST (and its Foma dependency) is not published in
the ohpcd repository, so that half cannot run here and is NOT silently
skipped: it is reported as excluded in notes.md/MANIFEST.yml and covered
instead by the consumer test (test_package/att_check.py reproduces the same
gold comparison with a self-contained ATT reader). The 2 negative cases need
nothing but lexd's exit status, so build() runs all 6 variants for real.

R26: lexd links the Conan-provided static liblttoolbox.a / libicu*.a; no
system-named shared library is introduced.
R32: recipe supports both Linux and OHOS.
"""
import hashlib
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# The six check targets of upstream's top-level `make check` and the lexd flags
# each one applies. Upstream derives the flag string with
# `LEXD_TEST_FLAGS="$(echo '$*' | grep -v plain | sed 's/^\|-/ --/g')"`, which
# yields e.g. " --minimize --tags" for the minimize-tags target. We spell the
# equivalent explicit set instead: lexd sets flags=true for both -m and -t
# (src/lexd.cc), so "--flags --tags --minimize" produces the byte-identical
# transducer (verified for all 36 fixtures x 6 variants by test_package).
UPSTREAM_VARIANTS = (
    ("plain", ""),
    ("flags", "--flags"),
    ("minimize-tags", "--flags --tags --minimize"),
    ("tags", "--flags --tags"),
    ("minimize", "--flags --minimize"),
    ("single", "--single"),
)

# pkg.m4 variable prefixes that configure.ac derives from the three
# PKG_CHECK_MODULES() calls.
PKG_PREFIXES = ("LTTOOLBOX", "ICU_UC", "ICU_IO")


def _drop_umask_077(path):
    """E114: on HMDFS `umask 077 && mktemp -d` yields an unwritable drwx--S---.

    Drop the umask so config.status can create its scratch directory.
    """
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        data = handle.read()
    patched = data.replace("(umask 077 && mktemp -d", "(mktemp -d")
    patched = patched.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    if patched != data:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(patched)


class LexdConan(ConanFile):
    name = "lexd"
    version = "1.3.5"
    description = ("lexd — Apertium lexicon compiler for non-suffixational "
                   "morphologies (ATT transducer output)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/apertium/lexd"
    url = ""  # CI fills this
    topics = ("apertium", "lexicon", "morphology", "transducer", "att",
              "nlp", "morphological-analyser", "compiler")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lexd is validated on Linux/OHOS, not " + str(self.settings.os))

    # ------------------------------------------------------------------ deps
    def requirements(self):
        # configure.ac: PKG_CHECK_MODULES([LTTOOLBOX], [lttoolbox >= 3.7.1])
        self.requires("lttoolbox/3.7.6", transitive_headers=True)
        # configure.ac: PKG_CHECK_MODULES([ICU_UC]/[ICU_IO], [icu-uc]/[icu-io]).
        # icu4c/77 is the same package lttoolbox/3.7.6 requires, so only one
        # ICU lands in the graph. (icu/76.1 would add a second, ABI-incompatible
        # ICU: the compile then sees icu_77 headers while -licuuc resolves to
        # the 76.1 archive, and every UnicodeString symbol ends up undefined.)
        self.requires("icu4c/77", transitive_headers=True)
        # configure.ac: AC_CHECK_HEADER([utf8cpp/utf8.h]) / [utf8.h];
        # lttoolbox's public header ustring.h includes <utf8.h> directly.
        self.requires("utf8cpp/4.1.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)
        # patches/autotools/ holds the `autoreconf -fi` products for the
        # untouched tarball. They are a vendored build input, not a patch, so
        # export_conandata_patches() does not carry them: copy them here so
        # they reach the exported source folder (see source()).
        autotools_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if os.path.isdir(autotools_src):
            autotools_dst = os.path.join(self.export_sources_folder, "patches", "autotools")
            for root, _dirs, files in os.walk(autotools_src):
                rel = os.path.relpath(root, autotools_src)
                dst = autotools_dst if rel == "." else os.path.join(autotools_dst, rel)
                os.makedirs(dst, exist_ok=True)
                for name in files:
                    copy(self, name, root, dst)

    # ---------------------------------------------------------------- source
    def _copy_vendored_autotools(self, destination):
        """Copy patches/autotools/** over the extracted tree.

        Done in source() (not build()): it runs right after get() extracts the
        tarball, so the files are baked into the cached source folder that
        build() sees. lttoolbox/3.7.6 hit the same trap — copying in build()
        let Conan's source-folder management restore a stale top-level
        configure between configure() and make().
        """
        src = os.path.join(self.export_sources_folder, "patches", "autotools")
        if not os.path.isdir(src):
            src = os.path.join(self.recipe_folder, "patches", "autotools")
        if not os.path.isdir(src):
            return 0
        copied = 0
        for root, _dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dst = destination if rel == "." else os.path.join(destination, rel)
            os.makedirs(dst, exist_ok=True)
            for name in files:
                shutil.copy2(os.path.join(root, name), os.path.join(dst, name))
                # automake aux scripts must stay executable
                mode = os.stat(os.path.join(root, name)).st_mode
                os.chmod(os.path.join(dst, name), mode | 0o111
                         if name in ("configure", "install-sh", "missing", "depcomp")
                         else mode)
                copied += 1
        return copied

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        count = self._copy_vendored_autotools(self.source_folder)
        if count == 0:
            self.output.warning("no vendored autotools found; build() will need "
                                "a working autoreconf on the build host")
        else:
            self.output.info("Vendored autotools products copied: %d files" % count)

    # --------------------------------------------------------------- generate
    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # E007/E205: config.guess has no HarmonyOS branch, and the OHOS
            # triplet is what config.sub accepts. Only --build is passed so
            # configure stays in native mode (no --host => no cross mode).
            tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()
        # build() invokes ./configure directly (it needs the dependency flags on
        # the command line, see _compute_dependency_flags), so the toolchain's
        # own configure arguments -- notably the E007/E205 --build triplet --
        # must be replayed there. Drop the prefix/bindir/libdir entries and the
        # CC/CXX ones: build() passes those explicitly.
        skip = ("CC=", "CXX=", "--prefix=", "--bindir=", "--sbindir=",
                "--libdir=", "--includedir=", "--oldincludedir=")
        self._toolchain_configure_args = [str(arg) for arg in tc.configure_args
                                          if not str(arg).startswith(skip)]
        self._dependency_flags = self._compute_dependency_flags()
        for key in sorted(self._dependency_flags):
            self.output.info("configure {}={}".format(
                key, self._dependency_flags[key]))

    def _compute_dependency_flags(self):
        """Dependency flags derived from Conan's dependency model.

        Two things are solved here:

        * pkg.m4 skips its pkg-config lookup when both ``<PKG>_CFLAGS`` and
          ``<PKG>_LIBS`` are already set, so handing configure those variables
          satisfies the three ``PKG_CHECK_MODULES`` calls without a system
          pkg-config binary — and without the registry's ``prefix=/`` .pc files
          (E355: pkg-config would emit ``-I/include``/``-L/lib``, E468: the
          worker has no pkg-config to rely on).
        * The values are passed to ``./configure`` as ``VAR=value`` command-line
          assignments rather than only through ``os.environ``: the build runs
          under ``env="conanbuild"``, and the generated conanbuild script owns
          CPPFLAGS/LDFLAGS, so an environment-only export can be silently
          shadowed (observed: a CI-profile run lost ``-I<utf8cpp>/include`` and
          configure aborted with "You don't have utfcpp installed").

        Returns: dict of shell variable name -> value.
        """
        cppflags, ldflags, pkg_flags = [], [], {}
        for _ref, dep in self.dependencies.items():
            if dep.package_folder is None:
                continue
            cflags = ["-I{}".format(d) for d in dep.cpp_info.includedirs]
            libs = ["-L{}".format(d) for d in dep.cpp_info.libdirs]
            if dep.ref.name == "icu4c":
                # configure.ac requires icu-io (u_vfprintf & friends live in
                # libicuio) but icu4c's cpp_info only models the uc/i18n/data
                # trio, so add -licuio in front — the static archives resolve
                # left to right and libicuio itself needs the trio.
                libs.append("-licuio")
            libs += ["-l{}".format(lib) for lib in dep.cpp_info.libs]
            libs += ["-l{}".format(lib) for lib in dep.cpp_info.system_libs]
            pkg_flags[dep.ref.name] = (cflags, libs)
            cppflags += cflags
            ldflags += [f for f in libs if f.startswith("-L")]

        # lttoolbox's ustring.h does `#include <utf8.h>` while the utfcpp
        # package ships it as include/utf8cpp/utf8.h. Add those
        # sub-directories, but never ICU's include/unicode/utf8.h, which is a
        # different header with clashing UTF8_* macros.
        for _ref, dep in self.dependencies.items():
            if dep.ref.name != "utf8cpp":
                continue
            for inc in dep.cpp_info.includedirs:
                if not os.path.isdir(inc):
                    continue
                for sub in sorted(os.listdir(inc)):
                    subdir = os.path.join(inc, sub)
                    if (sub != "unicode" and os.path.isdir(subdir)
                            and os.path.isfile(os.path.join(subdir, "utf8.h"))):
                        flag = "-I{}".format(subdir)
                        if flag not in cppflags:
                            cppflags.append(flag)

        exports = {
            "LTTOOLBOX_CFLAGS": pkg_flags["lttoolbox"][0],
            "LTTOOLBOX_LIBS": pkg_flags["lttoolbox"][1],
            "ICU_UC_CFLAGS": pkg_flags["icu4c"][0],
            "ICU_UC_LIBS": pkg_flags["icu4c"][1],
            "ICU_IO_CFLAGS": pkg_flags["icu4c"][0],
            "ICU_IO_LIBS": pkg_flags["icu4c"][1],
            "CPPFLAGS": cppflags,
            "LDFLAGS": ldflags,
        }
        return {key: " ".join(values) for key, values in exports.items() if values}

    # ------------------------------------------------------------------ build
    def _compiler(self, key, fallback):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict) or {}
        return executables.get(key) or fallback

    def build(self):
        # Nothing in patches/ today besides the vendored autotools products
        # (already applied in source()); keep the hook so future adaptations
        # declare real patches in conandata.yml.
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            # Local fallback only: the release tarball ships no configure and
            # the CI worker has no automake, so the vendored products above are
            # the normal path.
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        _drop_umask_077(configure)
        # E041/E248: the Makefile.in/aclocal.m4 in the tree are current, so the
        # maintainer rules must not re-run automake (absent on the worker).
        # Neutering them is a no-op for a correct tree and prevents Error 127.
        for var in ("ACLOCAL", "AUTOMAKE", "AUTOCONF", "AUTOHEADER", "AUTOM4TE"):
            os.environ[var] = ":"
        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        # Flags travel as VAR=value argv assignments: conanbuild.sh owns
        # CPPFLAGS/LDFLAGS in the environment, so env-only injection is not
        # reliable (see _compute_dependency_flags).
        assignments = ['CC="{}"'.format(cc), 'CXX="{}"'.format(cxx)]
        for key in sorted(self._dependency_flags):
            assignments.append('{0}="{1}"'.format(key, self._dependency_flags[key]))
        # E007/E205: without this, config.guess cannot identify HarmonyOS on the
        # build host and configure aborts before compiling anything.
        self.run("{} ./configure {} --prefix=\"{}\"".format(
            " ".join(assignments), " ".join(self._toolchain_configure_args),
            self.package_folder),
            cwd=self.source_folder, env="conanbuild")
        # E074: parallel make hits the HMDFS jobserver fifo with EPERM.
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream test cases that do not need the HFST binaries.

        ``make check`` runs 6 flag variants x (36 positive + 2 negative)
        cases. The positive oracle is
        ``hfst-txt2fst <lexd-output> | hfst-fst2strings -X obey-flags -c 10 |
        sort -u`` diffed against ``*.strings.gold``; neither hfst-txt2fst nor
        hfst-fst2strings is published in the ohpcd repository (and HFST's own
        Foma dependency is not published either), so the positive half is
        reported as excluded instead of being silently skipped. The 2
        negative cases only need lexd's exit status, so all 6 variants run.
        """
        feature_dir = os.path.join(self.source_folder, "tests", "feature")
        produced = 0
        # (variant, path) so the 6 variants do not collide: they all emit the
        # same two basenames (negtest-col0.lexd.txt.error, …).
        evidence = []
        for variant, flags in UPSTREAM_VARIANTS:
            out_dir = os.path.join(feature_dir, "out-{}".format(variant))
            cmd = 'make -C "{}" O="{}" LEXD_TEST_FLAGS="{}" check-neg'.format(
                feature_dir, out_dir, flags)
            self.output.info("Upstream negative tests [{}]: {}".format(variant, cmd))
            self.run(cmd, cwd=self.source_folder, env="conanbuild")
            if not os.path.isdir(out_dir):
                continue
            names = sorted(f for f in os.listdir(out_dir)
                           if f.endswith(".lexd.txt.error"))
            produced += len(names)
            for name in names:
                evidence.append((variant, name, os.path.join(out_dir, name)))
        # 6 variants x 2 negative cases; both must have produced an error file.
        expected = 2 * len(UPSTREAM_VARIANTS)
        if produced != expected:
            raise RuntimeError(
                "upstream negative tests incomplete: produced {} of {} expected "
                "error files".format(produced, expected))
        # Read the real artifacts and digest them: the marker must describe
        # evidence that exists, not just a hand-written number. test_package
        # re-hashes the packaged copies, so a fabricated marker cannot pass.
        digest = hashlib.sha256()
        samples = []
        shipped = []
        for variant, name, path in evidence:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            if not text.strip():
                raise RuntimeError("upstream error file is empty: %s" % path)
            if "Error on line" not in text:
                raise RuntimeError("upstream error file has no lexd diagnostic: "
                                   "%s -> %r" % (path, text[:120]))
            digest.update(text.encode("utf-8"))
            shipped.append("{}__{}".format(variant, name))
            if len(samples) < 2:
                samples.append(text.strip().splitlines()[0])
        result = {
            "status": "passed",
            "framework": "make-check(negative subset)",
            "command": "make -C tests/feature O=out-<variant> "
                       "LEXD_TEST_FLAGS='<flags>' check-neg",
            "discovered": 6 * 38,
            "executed": produced,
            "passed": produced,
            "failed": 0,
            "skipped": 6 * 36,
            "error_files": len(evidence),
            "error_file_order": shipped,
            "error_sha256": digest.hexdigest(),
            "error_samples": samples,
            "reason": ("2 negative cases (negtest-col0, negtest-trailing-bracket) "
                       "x 6 upstream flag variants executed; the 36 positive "
                       "cases need hfst-txt2fst/hfst-fst2strings, which are not "
                       "published in the ohpcd registry (HFST and its Foma "
                       "dependency are absent), so they are covered instead by "
                       "the consumer test in test_package/att_check.py, which "
                       "reproduces the same *.strings.gold comparison"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False)
        # Keep the error artifacts next to the marker so package() can ship
        # them as inspectable evidence, with the variant in the file name.
        evidence_dir = os.path.join(self.build_folder, "upstream-errors")
        os.makedirs(evidence_dir, exist_ok=True)
        for variant, name, path in evidence:
            shutil.copy2(path, os.path.join(
                evidence_dir, "{}__{}".format(variant, name)))

    # ---------------------------------------------------------------- package
    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")
        # Conan convention: drop the empty dirs autotools' install leaves.
        for empty in ("share/info", "share/licenses", "lib", "include"):
            candidate = os.path.join(self.package_folder, empty)
            if os.path.isdir(candidate) and not os.listdir(candidate):
                os.rmdir(candidate)
        # Ship the upstream test evidence (marker + the 12 real .error files)
        # under share/lexd/, not in the package root: it is an audit trail, not
        # a delivered artifact, and test_package re-hashes the error files so a
        # hand-written marker cannot pass.
        copy(self, "upstream_test_result.json",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "share", "lexd"))
        copy(self, "*",
             src=os.path.join(self.build_folder, "upstream-errors"),
             dst=os.path.join(self.package_folder, "share", "lexd", "upstream-errors"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
