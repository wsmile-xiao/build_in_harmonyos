#!/usr/bin/env python3
"""Conan recipe — noweb 2.13 (Norman Ramsey's literate-programming toolbox).

noweb is a pure-C + shell/awk command-line tool set (notangle / noweb /
noweave / noroots / ...) built with a plain GNU-Make project (no configure).
Installation puts the public commands in `bin/` and the pipeline pieces
(markup/nt/finduses/... C binaries plus shell+awk helpers) in `lib/noweb/`.

OHOS / HarmonyOS-PC notes:
  * The Makefile's `install-code` runs `strip` on the C helpers.  On this
    platform an ELF stripped of its .symtab / .codesign metadata is refused
    by the loader (Permission denied at exec), so patch 0001 removes the
    strip step and we keep the unstripped binaries.
  * The C tools call libc tmpfile(), which always uses /tmp — read-only on
    OHOS.  Patches 0006/0007 add a TMPDIR-aware anonymous-temp helper.
  * The distribution references `nawk`; OHOS only ships `awk`/`gawk`
    (patches 0002-0005, 0008-0012, 0015, 0024 rename to plain awk).
  * Standard --version/--help were added to the command wrappers
    (patches 0013-0023); upstream only knows `-gitversion`.
  * Wrappers embed an absolute LIB dir (upstream design).  package() rewrites
    the baked prefix into a `$0`-relative lookup so the package stays usable
    from the Conan cache.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import (
    get,
    copy,
    apply_conandata_patches,
    export_conandata_patches,
)


class NowebConan(ConanFile):
    name = "noweb"
    version = "2.13"
    description = (
        "noweb — a simple, extensible tool for literate programming "
        "(Norman Ramsey); provides notangle/noweb/noweave/noroots and friends"
    )
    license = "BSD-2-Clause"
    homepage = "https://www.cs.tufts.edu/~nr/noweb"
    url = ""  # CI fills this
    topics = ("literate-programming", "noweb", "notangle", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Upstream is an in-source GNU-Make project (no configure/VPATH) —
        # build directly in the source folder, like no-more-secrets.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler must come from the Conan toolchain conf, never
        # from an undefined ${CC} shell variable (empty on release workers).
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp.get("c") or os.environ.get("CC") or "clang"

        src = os.path.join(self.source_folder, "src")
        # R49: private staging prefix inside the conan build folder.
        prefix = os.path.join(self.build_folder, "prefix")
        os.makedirs(os.path.join(prefix, "bin"), exist_ok=True)
        os.makedirs(os.path.join(prefix, "lib"), exist_ok=True)

        # CPPFLAGS=/LDFLAGS= are passed empty on purpose so that nothing is
        # silently pulled from the host environment (R33).
        self.run(
            f"make -C {src} CC={cc} CPPFLAGS= LDFLAGS= boot",
            cwd=src,
        )
        self.run(
            f"make -C {src} CC={cc} CPPFLAGS= LDFLAGS= all",
            cwd=src,
        )
        bin_dir = os.path.join(prefix, "bin")
        lib_dir = os.path.join(prefix, "lib", "noweb")
        self.run(
            f"make -C {src} CC={cc} install-code "
            f"BIN={bin_dir} LIB={lib_dir} ELISP=/dev/null",
            cwd=src,
        )

    def package(self):
        prefix = os.path.join(self.build_folder, "prefix")
        # public command wrappers (bin/) + pipeline pieces (lib/noweb/)
        copy(self, "*", src=os.path.join(prefix, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(prefix, "lib", "noweb"),
             dst=os.path.join(self.package_folder, "lib", "noweb"))
        # install-code does not install man/tex/emacs pieces; ship the license.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # Make the installed wrappers relocatable: the upstream install bakes
        # an absolute LIB dir at install time.  bin/ and lib/noweb are
        # siblings, so rewrite the baked absolute prefix into a $0-relative
        # resolution at package time.
        self._relocate_libdir()

    def _relocate_libdir(self):
        """Rewrite `LIB=<abs lib dir>` assignments baked by `make install-code`
        into a runtime lookup relative to the script location."""
        # the absolute <prefix>/lib/noweb path baked into the scripts
        prefix = os.path.join(self.build_folder, "prefix")
        abs_lib = os.path.join(prefix, "lib", "noweb")

        bin_re = re.compile(r"^(LIB|macrodir)=%s$" % re.escape(abs_lib))
        lib_re = re.compile(r"^(LIB|macrodir)=%s$" % re.escape(abs_lib))

        def _rewrite(path, rel):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                return
            orig = text
            if rel == "bin":
                text = bin_re.sub(
                    r'LIB=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)/../lib/noweb',
                    text,
                )
            else:
                text = lib_re.sub(
                    r'LIB=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd)',
                    text,
                )
            if text != orig:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)

        for rel, sub in (("bin", "bin"), ("lib", os.path.join("lib", "noweb"))):
            d = os.path.join(self.package_folder, sub)
            if not os.path.isdir(d):
                continue
            for name in os.listdir(d):
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    _rewrite(p, rel)

    def package_info(self):
        # Command-line tool: expose bin/ on PATH, no libraries or headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
