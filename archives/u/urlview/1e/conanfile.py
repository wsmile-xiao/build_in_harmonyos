import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UrlviewConan(ConanFile):
    name = "urlview"
    version = "1e"
    description = (
        "urlview scans text for URLs and lets the user pick one to open. "
        "urlview-ng is the maintained upstream of it: it replaces the 23-year-old "
        "autoconf mess of urlview 0.9 with a plain Makefile and fixes the Debian "
        "bug backlog, while keeping the same extractor/launcher behaviour."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sr.ht/~nabijaczleweli/urlview-ng"
    url = "https://sr.ht/~nabijaczleweli/urlview-ng"
    topics = ("url", "extractor", "launcher", "terminal", "ncurses", "cli")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # enter.h does `#include <ncurses.h>` and the OHOS sysroot ships no ncurses.h
        # (measured: `clang -fsyntax-only` -> fatal error: 'ncurses.h' file not found),
        # so ncurses is a hard dependency.  6.5 is the revision whose binary the
        # artifact repo actually serves for this profile (W0 evidence in notes.md).
        self.requires("ncurses/6.5")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ---- helpers ----------------------------------------------------------
    def _cc(self, which, probe):
        # R33: the compiler comes from the Conan conf, never from a shell variable.
        # Upstream defaults are `CC ?= cc` / `CXX ?= c++` and *neither* exists on a
        # HarmonyOS PC (measured: cc MISSING, c++ MISSING, only clang/clang++ are),
        # so without this injection the very first compile dies with rc=127.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get(which) or probe

    def _dep_flags(self):
        cpp, ld = [], []
        for dep in self.dependencies.host.values():
            info = dep.cpp_info.aggregated_components()
            cpp += ["-I%s" % d for d in info.includedirs]
            ld += ["-L%s" % d for d in info.libdirs]
            ld += ["-l%s" % lib for lib in info.libs]
        return " ".join(cpp), " ".join(ld)

    def _env(self):
        cppflags, ldflags = self._dep_flags()
        env = Environment()
        # Dependency flags must travel through the *environment*, not the make
        # command line: the upstream Makefile builds its own defines with
        # `CPPFLAGS += -DVERSION=... -DDEFAULT_REGEXP=...`, and a command-line
        # CPPFLAGS overrides that whole += chain (measured: with -DVERSION gone,
        # urlview.c:519 `sizeof(BRAND)` stops parsing).  Environment values are
        # what `+=` appends to.
        #
        # -DURLVIEW_NO_GETTEXT selects upstream's own identity-gettext branch.
        # The OHOS sysroot ships a <libintl.h> that is a macro-only stub: it
        # passes the __has_include probe, declares neither gettext() nor
        # bindtextdomain(), and there is no libintl to link against (all measured,
        # see notes.md).  No catalogue is installed either, so the identity
        # fallback is exactly upstream's intended no-gettext configuration.
        env.define("CPPFLAGS", (cppflags + " -DURLVIEW_NO_GETTEXT").strip())
        env.define("LDFLAGS", ldflags)
        # Pin the ncurses probe to a no-op so `$(CURSESCONF) --cflags` and
        # `--libs` both come back empty.  Left at its default (ncursesw6-config)
        # this build host resolves ~/.harmonybrew/bin/ncursesw6-config -- a host
        # copy that would leak host prefixes into the artifact and make W3 and CI
        # build different things.  Upstream's own comment sanctions this form.
        env.define("CURSESCONF", "echo #")
        return env

    def _make_vars(self):
        return [
            "CC=%s" % self._cc("c", "clang"),
            "CXX=%s" % self._cc("cpp", "clang++"),
            # Upstream: VERSION ?= $(shell git describe).  A release tarball has no
            # .git, so without this the version is compiled in empty (measured:
            # `make` prints "fatal: not a git repository").
            "VERSION=%s" % self.version,
            # Same story for the manual page date, which comes from `git log`.
            "SOURCE_DATE_EPOCH=0",
            # How upstream's own CI (.builds/sid+void.yml) runs without shellcheck.
            "SHELLCHECK=:",
            # No .mo files: msgfmt presence is build-host dependent, and the
            # install path for catalogues would have to be a runtime prefix.
            # Equivalent to Debian's own `pkg.urlview.noloc` build profile.
            "LOCALES=",
            # Empty prefix + DESTDIR=<package_folder> keeps every installed path
            # relative to the package, so no host prefix is baked into the binary
            # (R49).  Upstream defaults here would be PREFIX=/usr/local and
            # SYSTEM_INITFILE=/etc/urlview.conf.
            "PREFIX=",
        ]

    # ---- build ------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        vars_ = " ".join(self._make_vars())
        with self._env().vars(self, scope="build").apply():
            # 上游是裸 Makefile、只认源码目录，三条 make 都要钉在 source_folder：
            # 默认 cwd 是 build 子目录，那儿没有 Makefile（实测报
            # "make: *** No rule to make target 'all'. Stop."）。
            self.run('make -j1 %s all' % vars_, cwd=self.source_folder)
            # Upstream's own test entry point (same command its CI runs, modulo
            # SHELLCHECK=:): builds `quote` and asserts quotesub() twice.
            self.run('make -j1 %s check' % vars_, cwd=self.source_folder)

    def package(self):
        vars_ = " ".join(self._make_vars())
        with self._env().vars(self, scope="build").apply():
            self.run(
                'make install DESTDIR="%s" %s' % (self.package_folder, vars_),
                cwd=self.source_folder,
            )

    def package_info(self):
        # Command-line tool: nothing to link against.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share", "etc"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
