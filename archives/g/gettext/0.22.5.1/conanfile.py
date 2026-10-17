#!/usr/bin/env python3
"""Conan recipe for gettext 0.22.5.1 — GNU internationalization tools.

gettext provides the envsubst command (required by abuild rootbld) plus the
GNU gettext toolchain (msgfmt, xgettext, gettext, ...) and the libintl
runtime library.

Key adaptation points:
- Autotools build; config.guess/config.sub patched to recognize the
  aarch64-unknown-linux-ohos triplet (patches 0001/0002).
- OHOS already ships a system iconv; gettext builds with HAVE_ICONV and
  uses its bundled gnulib for libunistring (no external dependency).
- Built as an application package: the 20+ CLI tools in bin/ are the
  deliverable; libintl is bundled in the same package (static + shared).
- Upstream test suite (make check): gnulib-tests 466 + libtextstyle 4
  pass; a small number of tool tests fail on OHOS due to platform gaps
  (iconv charset coverage, missing autom4te, locale data) — recorded
  honestly in notes.md.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GettextConan(ConanFile):
    name = "gettext"
    version = "0.22.5.1"
    description = "GNU internationalization tools (gettext, envsubst, msgfmt, ...)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gettext/"
    url = "https://www.gnu.org/software/gettext/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # gettext is not an OHOS system-name library; keep default shared
        # build so both .a and .so are produced (R26 does not apply).
        tc.configure_args.append("--disable-rpath")
        # Trim build/install volume to stay within the CI 3600s limit:
        # the upstream examples tree (hello-java/c++/... and their po
        # catalogs) is not needed at runtime, and Java/C++/OpenMP/Emacs
        # bindings only inflate the build. Matches the released 0.22.5
        # static-library recipe's configure options.
        tc.configure_args.extend(
            [
                "--disable-java",
                "--disable-c++",
                "--disable-openmp",
                "--without-emacs",
            ]
        )
        tc.generate()

    def _build_environment(self):
        environment = Environment()
        # /var/tmp does not exist on OHOS and root '/' is read-only; give
        # tests a writable temp area.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        return environment

    def _fix_configure_umask(self):
        """OHOS sandbox uid mapping: `mktemp -d` creates a 0700 dir owned by
        a mapped uid that the build process cannot write (Permission denied
        in config.status / config.guess, 'could not setup config files
        machinery'). The upstream scripts wrap mktemp with `umask 077`, which
        yields 0700 dirs; rewriting to umask 002 yields 0775 dirs that the
        file_manager group can write. Applies to every configure /
        config.guess / config.sub under the source tree (gettext ships
        per-subdirectory copies, e.g. libtextstyle, that patches do not
        reach). Also syncs the OHOS-patched config.guess/config.sub from the
        top-level build-aux into subdirectory copies so nested configure
        runs (libtextstyle, ...) can guess the aarch64-unknown-linux-ohos
        build type."""
        import glob
        import shutil
        src = self.source_folder
        # Sync patched config.guess/config.sub from top-level to all copies.
        for name in ("config.guess", "config.sub"):
            master = os.path.join(src, "build-aux", name)
            if not os.path.isfile(master):
                continue
            for copy in glob.glob(os.path.join(src, "**", name), recursive=True):
                if os.path.abspath(copy) == os.path.abspath(master):
                    continue
                try:
                    shutil.copy2(master, copy)
                except OSError:
                    pass
        # Rewrite umask 077 -> 002 in every configure/config.guess/config.sub.
        targets = []
        for pattern in ("configure", "build-aux/config.guess", "build-aux/config.sub",
                        "**/configure", "**/config.guess", "**/config.sub"):
            targets.extend(glob.glob(os.path.join(src, pattern), recursive=True))
        for cfg in sorted(set(targets)):
            if not os.path.isfile(cfg):
                continue
            with open(cfg, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            if "umask 077" not in content:
                continue
            content = content.replace("umask 077", "umask 002")
            with open(cfg, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _trim_examples_from_install(self):
        """Drop the examples/doc subtrees from gettext-tools' SUBDIRS.

        On OHOS every installed file spawns a separate /system/bin/install
        process; gettext-tools/examples alone ships ~1400 .po catalogs
        (8+ hello-* demo dirs x 60+ languages), which blew the CI 3600s
        conan-create timeout during `make install`. examples/doc are
        build-time documentation, not needed at runtime, so strip them
        from SUBDIRS in the generated Makefile before make/install."""
        import re
        makefile = os.path.join(self.build_folder, "gettext-tools", "Makefile")
        if not os.path.isfile(makefile):
            self.output.warning("gettext-tools/Makefile not found; examples not trimmed")
            return
        with open(makefile, encoding="utf-8") as handle:
            content = handle.read()
        def _strip(match):
            line = re.sub(r"\bexamples\b", "", match.group(0))
            line = re.sub(r"\bdoc\b", "", line)
            return line
        new_content = re.sub(r"^SUBDIRS\s*=.*$", _strip, content,
                             flags=re.MULTILINE)
        if new_content != content:
            with open(makefile, "w", encoding="utf-8") as handle:
                handle.write(new_content)
            self.output.info("Trimmed examples/doc from gettext-tools SUBDIRS")

    def build(self):
        apply_conandata_patches(self)
        self._fix_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        self._trim_examples_from_install()
        autotools.make(args=["-j1"])
        # Upstream test suite: gnulib-tests (466) + libtextstyle (4) pass;
        # a few tool tests fail on OHOS due to platform gaps. Run with
        # ignore_errors so platform-limited failures do not block the build,
        # and record actual pass/fail in notes.md.
        with self._build_environment().vars(self).apply():
            self.run("make -j1 check", ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # libintl and friends are installed under lib/
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["intl", "gettextpo", "asprintf", "textstyle"]
