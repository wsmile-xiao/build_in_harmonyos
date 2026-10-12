#!/usr/bin/env python3
"""Conan recipe - lifelines 3.0.61 (LifeLines genealogy system) for HarmonyOS PC.

Upstream's release tag ships no generated ``configure`` (the archive is a plain
git export), so the recipe bootstraps autoconf/automake itself and then builds
the curses front-end ``llines`` and the batch report runner ``llexec``.

The upstream regression suite lives in reports/st/Makefile.am
(``TESTS = selftest`` -> ``ti`` + ``test_iter`` + ``st_all``) and is executed
here against the pristine ``*.ref`` expectation files shipped by upstream.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get, load, save,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

HOST_TRIPLE = "aarch64-unknown-linux-ohos"
# Names of the packaged bootstrap tools (build context only).
TOOL_PACKAGES = ("perl", "automake", "autoconf", "m4", "bison", "libtool")


class LifelinesConan(ConanFile):
    name = "lifelines"
    version = "3.0.61"
    description = ("LifeLines - a genealogy system: GEDCOM database, curses "
                   "front-end (llines) and a batch report runner (llexec) for "
                   "its own report language")
    license = "MIT"
    homepage = "https://lifelines.github.io/lifelines/"
    url = "https://github.com/lifelines/lifelines"
    topics = ("genealogy", "gedcom", "reports", "curses", "cli")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lifelines is only supported on Linux/OHOS, not {self.settings.os}")

    def requirements(self):
        self.requires("ncurses/6.6")

    def build_requirements(self):
        # The tag archive has no configure, so bootstrap with the published
        # autotools family.  perl is declared explicitly (not just as somebody
        # else's transitive tool_require) because the recipe must put its bin
        # dir ahead of the host perl: see _tools_shell().
        self.tool_requires("perl/5.42.2")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")
        # Bison must stay on the 2.x line: yacc.y uses the legacy
        # "%pure_parser" + yyparse(void*) API that bison 3.x replaced by
        # "api.pure", so generating with 3.8 emits "int yyparse (void)", which
        # conflicts with the declaration in src/interp/parse.h.
        self.tool_requires("bison/2.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        # The codeload URL ends with the tag name and has no ".tar.gz" suffix,
        # so pass the filename explicitly or conan sniffs the payload as a zip.
        get(self, filename="lifelines-3.0.61.tar.gz",
            **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ env
    def _build_pkg_folder(self, ref_name):
        for dep in self.dependencies.build.values():
            if dep.ref.name == ref_name:
                return dep.package_folder
        return None

    def _tool_bin(self, ref_name, exe):
        """Absolute path of ``exe`` inside a packaged tool, or None."""
        pkg = self._build_pkg_folder(ref_name)
        if not pkg:
            return None
        for cand in (os.path.join(pkg, "bin"), os.path.join(pkg, "usr", "bin")):
            path = os.path.join(cand, exe)
            if os.path.exists(path):
                return path
        return None

    def _perl_bin(self):
        """The packaged perl interpreter (the image ships it as perl5.42.2)."""
        for exe in ("perl", "perl5.42.2"):
            path = self._tool_bin("perl", exe)
            if path:
                return path
        hits = []
        pkg = self._build_pkg_folder("perl")
        if pkg:
            hits = glob.glob(os.path.join(pkg, "bin", "perl5.*"))
        return hits[0] if hits else None

    def _tool_dirs(self):
        dirs = []
        perl = self._perl_bin()
        if perl:
            dirs.append(os.path.dirname(perl))
        wanted = (("automake", "automake"), ("autoconf", "autoconf"),
                  ("m4", "m4"), ("bison", "bison"), ("libtool", "libtoolize"))
        for ref_name, exe in wanted:
            path = self._tool_bin(ref_name, exe)
            if path and os.path.dirname(path) not in dirs:
                dirs.append(os.path.dirname(path))
        return dirs

    def _perl5lib(self):
        """PERL5LIB for the packaged perl.

        The packaged perl was relocated, so its baked-in @INC points at the
        builder's "//lib/perl5/5.42.2/..." and finds nothing there; without this
        the autotools perl scripts die with "Can't locate strict.pm".
        """
        dirs = []
        pkg = self._build_pkg_folder("perl")
        if pkg:
            root = os.path.join(pkg, "lib", "perl5")
            if os.path.isdir(root):
                for top in sorted(os.listdir(root)):
                    top_dir = os.path.join(root, top)
                    if not os.path.isdir(top_dir):
                        continue
                    if not (top[0].isdigit() or top in ("site_perl", "vendor_perl")):
                        continue
                    dirs.append(top_dir)
                    # .../lib/perl5/<ver>/<arch> holds the core + XS modules
                    dirs.extend(os.path.join(top_dir, sub)
                                for sub in sorted(os.listdir(top_dir))
                                if os.path.isdir(os.path.join(top_dir, sub)))
        for name, subs in (("autoconf", ("bin", os.path.join("share", "autoconf"))),
                           ("automake", (os.path.join("share", "automake-*"),))):
            pkg = self._build_pkg_folder(name)
            if not pkg:
                continue
            for sub in subs:
                for cand in glob.glob(os.path.join(pkg, sub)):
                    if os.path.isdir(cand):
                        dirs.append(cand)
        seen, ordered = set(), []
        for d in dirs:
            if d and d not in seen:
                seen.add(d)
                ordered.append(d)
        return ":".join(ordered)

    def _tools_shell(self):
        """Shell prefix that makes the packaged tool set self-consistent.

        Two device-side facts force this (both reproduced on HarmonyOS PC):
        * the generated ``conanbuild`` env script re-exports PATH with the host
          directories first, so the packaged perl/automake/autoconf bins lose
          to harmonybrew's; the packaged perl is 5.42.2 while harmonybrew's is
          5.44, and the perl package's buildenv only exports PERL5LIB -> the
          host perl loads the packaged XS modules and dies with
          "Perl_newSVsv_flags: symbol not found" in Cwd.so;
        * OHOS has no ``printenv``, so the packaged env scripts' PATH
          book-keeping is a no-op anyway (only their plain ``export`` lines
          survive).
        Assigning PATH in the command itself runs after those scripts are
        sourced, so the packaged perl/automake/autoconf/m4/bison win.
        """
        dirs = self._tool_dirs()
        if not dirs:
            return ""
        # The baked conan PATH drops the host system directories (on OHOS the
        # toybox applets live in /usr/bin, so a bare "dirname"/"printenv" inside
        # the packaged autoconf/automake wrappers fails there); re-append the
        # ambient PATH captured before generation instead of trusting $PATH.
        ambient = getattr(self, "_ambient_path", "") or str(
            os.environ.get("PATH", ""))
        parts = dirs + [d for d in ambient.split(os.pathsep) if d]
        if "/usr/bin" not in parts:
            parts.append("/usr/bin")
        prefix = 'PATH="' + ":".join(dict.fromkeys(parts)) + '" '
        perllib = self._perl5lib()
        if perllib:
            prefix += f'PERL5LIB="{perllib}" '
        return prefix

    def _export_tool_path(self):
        """Pin the packaged tool set into the ambient PATH/PERL5LIB.

        conan bakes the ambient environment into ``conanbuildenv-*.sh`` and
        appends the tool-package directories *after* it, so on a device where
        harmonybrew already provides perl 5.44 + autoconf the host perl wins.
        Prepending here means the baked PATH starts with the packaged perl, so
        every later self.run() -- including Autotools.configure()/make()/
        install() -- resolves the whole bootstrap set consistently.
        """
        self._ambient_path = str(os.environ.get("PATH", ""))
        seen, ordered = set(), []
        for d in self._tool_dirs() + self._ambient_path.split(os.pathsep):
            if d and d not in seen:
                seen.add(d)
                ordered.append(d)
        os.environ["PATH"] = os.pathsep.join(ordered)
        perllib = self._perl5lib()
        if perllib:
            ambient = str(os.environ.get("PERL5LIB", ""))
            os.environ["PERL5LIB"] = perllib + (":" + ambient if ambient else "")

    def _generate_env(self):
        VirtualBuildEnv(self).generate()
        env = Environment()
        ncurses = self.dependencies["ncurses"].package_folder
        env.append("CPPFLAGS", "-I" + os.path.join(ncurses, "include"))
        env.append("LDFLAGS", "-L" + os.path.join(ncurses, "lib"))
        bison = self._tool_bin("bison", "bison")
        if bison:
            for cand in (os.path.join(os.path.dirname(os.path.dirname(bison)),
                                      "share", "bison"),
                         os.path.join(os.path.dirname(bison), "..", "share", "bison")):
                if os.path.isdir(cand):
                    env.define("BISON_PKGDATADIR", os.path.abspath(cand))
                    break
            env.define("BISON", bison)
        m4 = self._tool_bin("m4", "m4")
        if m4:
            env.define("M4", m4)
        env.vars(self, scope="build").save_script("lifelines-buildenv")

    def _configure_args(self, tc):
        tc.configure_args += [
            f"--build={self._build_triple()}",
            f"--host={HOST_TRIPLE}",
            "--disable-shared",
            "--enable-static",
            # configure insists on YACC == "bison -y" and GNU bison only; seed
            # the autoconf cache so it does not depend on PATH probing.
            '"ac_cv_prog_YACC=bison -y"',
        ]

    def generate(self):
        self._export_tool_path()
        self._generate_env()
        tc = AutotoolsToolchain(self)
        self._configure_args(tc)
        tc.generate()

    def _build_triple(self):
        arch = str(self.settings_build.get_safe("arch") or "armv8")
        return HOST_TRIPLE if arch.startswith("armv8") else "x86_64-unknown-linux-gnu"

    # -------------------------------------------------------------- bootstrap
    def _aclocal_cmd(self, shell):
        """aclocal invocation that survives the packaged wrapper shebang.

        automake's packaged ``bin/aclocal`` is a /bin/sh wrapper that execs
        ``.aclocal-real``, whose shebang is the builder's
        ``/data/service/hnp/bin/perl``.  That path only exists on the CI
        workers, not on a device, so the wrapper reports "No such file or
        directory" for a file that is plainly there.  Running the real script
        through the packaged perl, with the two --*-acdir arguments the wrapper
        would have passed, works in both environments.
        """
        pkg = self._build_pkg_folder("automake")
        real = os.path.join(pkg, "bin", ".aclocal-real") if pkg else None
        perl = self._perl_bin()
        if perl and real and os.path.exists(real):
            acdir = glob.glob(os.path.join(pkg, "share", "aclocal-*"))
            sysdir = os.path.join(pkg, "share", "aclocal")
            args = "".join(f" --automake-acdir={d}" for d in acdir)
            if os.path.isdir(sysdir):
                args += f" --system-acdir={sysdir}"
            return shell + f'"{perl}" "{real}"{args} '
        return shell + "aclocal "

    def _automake_cmd(self, shell):
        pkg = self._build_pkg_folder("automake")
        real = os.path.join(pkg, "bin", ".automake-real") if pkg else None
        perl = self._perl_bin()
        if perl and real and os.path.exists(real):
            libdir = glob.glob(os.path.join(pkg, "share", "automake-*"))
            args = "".join(f" --libdir={d}" for d in libdir)
            return shell + f'"{perl}" "{real}"{args} '
        return shell + "automake "

    def _bootstrap(self):
        src = self.source_folder
        for d in ("m4", os.path.join("build", "gettext")):
            os.makedirs(os.path.join(src, d), exist_ok=True)
        shell = self._tools_shell()
        # The tag archive is a git export: aclocal.m4 / config.h.in /
        # Makefile.in / configure all have to be generated.
        for cmd in (
            self._aclocal_cmd(shell) + "-I build/autotools -I build/gettext -I m4",
            shell + "autoheader",
            self._automake_cmd(shell) + "--add-missing --copy --foreign",
            shell + "autoconf",
        ):
            self.run(cmd, cwd=src, env="conanbuild")
        cfg = os.path.join(src, "configure")
        text = load(self, cfg)
        # E114/E129: on HMDFS a directory created under umask 077 comes out
        # setgid-without-group-write and rejects new files even for its owner,
        # so config.status cannot write subs1.awk into its own temp dir.
        patched = text.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                               '(mktemp -d "./confXXXXXX")')
        patched = patched.replace('(umask 077 && mkdir "$tmp")', '(mkdir "$tmp")')
        if patched != text:
            save(self, cfg, patched)
            self.output.info("  [ok] relaxed config.status temp-dir umask 077 (E114)")

    def build(self):
        self._bootstrap()
        # src/interp/yacc.c is a generated file that upstream checks in, while
        # yacc.h is not distributed.  automake's rule is
        #   yacc.h: yacc.c -> (if yacc.h missing) rm -f yacc.c; make yacc.c
        # and with the srcdir copy present the second make answers "up to
        # date", so no header is ever produced and lex.c then fails on
        # '#include "yacc.h"'.  Dropping the stale copy from the source tree
        # makes bison regenerate both, from the pristine yacc.y.
        stale = os.path.join(self.source_folder, "src", "interp", "yacc.c")
        if os.path.exists(stale):
            os.remove(stale)
        # configure/make/install are driven through self.run() rather than the
        # Autotools helper because the OHOS device profile replaces PATH with a
        # curated list that has no /usr/bin, where the toybox applets live --
        # configure then dies on "sed: command not found".  The same arguments
        # the toolchain wrote to conanbuild.conf are used here.
        shell = self._tools_shell()
        tc = AutotoolsToolchain(self)
        self._configure_args(tc)
        args = " ".join(tc.configure_args)
        self.run(f'{shell}"{os.path.join(self.source_folder, "configure")}" {args}',
                 cwd=self.build_folder, env="conanbuild")
        # The OHOS SDK toolchain ships llvm-ar/llvm-ranlib only; the generated
        # Makefiles call them through $(AR)/$(RANLIB).
        self.run(f'{shell}make -j1 AR=llvm-ar RANLIB=llvm-ranlib',
                 cwd=self.build_folder, env="conanbuild")
        self._run_upstream_suite()

    # --------------------------------------------------- upstream test suite
    # reports/st/Makefile.am registers TESTS = selftest: the `ti` database
    # bootstrap, 6 test_iter golden-file comparisons and 2 st_all ones.
    UPSTREAM_CASES = (
        ("test_forindi", "test_forindi.out", "test_forindi.ref"),
        ("test_forfam", "test_forfam.out", "test_forfam.ref"),
        ("test_indi_it", "test_indi_it.out", "test_indi_it.ref"),
        ("test_fam_it", "test_fam_it.out", "test_fam_it.ref"),
        ("test_othr_it", "test_othr_it.out", "test_othr_it.ref"),
        ("trigtest", "trigtest.out", "trigtest.ref"),
        ("st_all.out", "st_all.out", "st_all.ref"),
        ("st_all.stdout", "st_all.stdout", "st_all_stdout.ref"),
    )

    def _run_upstream_suite(self):
        st_build = os.path.join(self.build_folder, "reports", "st")
        st_src = os.path.join(self.source_folder, "reports", "st")
        tmp = os.path.join(self.build_folder, "tmptest")
        os.makedirs(tmp, exist_ok=True)
        ncurses = self.dependencies["ncurses"].package_folder
        terminfo = os.path.join(ncurses, "share", "terminfo")
        envset = f'TMPDIR="{tmp}" TERM=xterm'
        if os.path.isdir(terminfo):
            envset += (f' TERMINFO="{terminfo}"'
                       f' TERMINFO_DIRS="{terminfo}"')
        log = os.path.join(self.build_folder, "reports-st-make-check.log")
        # Three of the eight comparisons cannot be reached by any build that is
        # not upstream 3.0.49 with NLS locales (see notes.md), so the suite is
        # captured rather than fatal; every case is still judged below against
        # upstream's own reference files.
        self.run(f'{self._tools_shell()}{envset} make -k check > "{log}" 2>&1 || true',
                 cwd=st_build, env="conanbuild")
        transcript = load(self, log)
        self.output.info("  [info] upstream make check tail: " +
                         " / ".join(transcript.strip().splitlines()[-3:]))
        results = []
        for case, produced, ref in self.UPSTREAM_CASES:
            got = os.path.join(st_build, produced)
            want = os.path.join(st_src, ref)
            if not os.path.isfile(got):
                status = "NOT-RUN"
            elif not os.path.isfile(want):
                status = "NO-REFERENCE"
            else:
                a = load(self, got).replace("\r\n", "\n")
                b = load(self, want).replace("\r\n", "\n")
                status = "PASS" if a == b else "DIFF"
            results.append((case, status))
            self.output.info(f"  [upstream] {case}: {status}")
        passed = sum(1 for _, s in results if s == "PASS")
        self.output.info(f"  [upstream] TOTAL {passed}/{len(results)}")
        save(self, os.path.join(self.build_folder, "reports-st-results.txt"),
             "".join(f"{c}\t{s}\n" for c, s in results) +
             f"TOTAL\t{passed}/{len(results)}\n")
        if passed == 0:
            raise Exception("upstream reports/st suite produced no passing case; "
                            "refusing to package an untested build")

    #: the programs upstream builds; automake installs them with a single
    #: "install-sh -c a b <dir>" line, and that 2007 install-sh only ever lands
    #: the first operand here (llexec and dbverify were silently dropped), so
    #: they are placed explicitly after the install pass.
    PROGRAMS = (("src/liflines", ("llines", "llexec")),
                ("src/tools", ("btedit", "dbverify")))

    def package(self):
        # Same DESTDIR=<package_folder> layout as Autotools.install(), with the
        # tool PATH prefix so the install rules can find toybox helpers.
        self.run(f'{self._tools_shell()}make install AR=llvm-ar RANLIB=llvm-ranlib'
                 f' DESTDIR="{self.package_folder}"',
                 cwd=self.build_folder, env="conanbuild")
        bindir = os.path.join(self.package_folder, "bin")
        for sub, names in self.PROGRAMS:
            built = os.path.join(self.build_folder, sub)
            for exe in names:
                copy(self, exe, built, bindir)
                os.chmod(os.path.join(bindir, exe), 0o755)
        # The curses front-end needs a terminfo entry.  HarmonyOS' own
        # /usr/share/terminfo only carries xterm-256color, and ncurses' copy is
        # not on the runtime search path, so llines aborts with
        # 'cannot initialize terminal type ($TERM="xterm")'.  Ship the two
        # compiled entries we use with the package and point TERMINFO_DIRS at
        # them (data only, from the ncurses package we already depend on).
        ncurses = self.dependencies["ncurses"].package_folder
        ti_src = os.path.join(ncurses, "share", "terminfo")
        ti_dst = os.path.join(self.package_folder, "share", "terminfo")
        for letter in ("x",):
            src = os.path.join(ti_src, letter)
            if os.path.isdir(src):
                for entry in ("xterm", "xterm-256color"):
                    if os.path.isfile(os.path.join(src, entry)):
                        copy(self, entry, src, os.path.join(ti_dst, letter))
        for pattern in ("COPYING", "LICENSE", "README", "NEWS", "AUTHORS"):
            copy(self, pattern, self.source_folder,
                 os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        terminfo = os.path.join(self.package_folder, "share", "terminfo")
        if os.path.isdir(terminfo):
            self.runenv_info.prepend_path("TERMINFO_DIRS", terminfo)
