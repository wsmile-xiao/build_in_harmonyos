#!/usr/bin/env python3
"""Conan recipe — buildtorrent 0.9.1 (Autotools).

BitTorrent .torrent file creation command-line tool by Claude Heiland-Allen.
Single C program (buildtorrent.c + bundled md5.c/sha1.c), no external
dependencies. Upstream ships no test suite (no TESTS/check target), so build()
does not invoke `make check`; functional coverage is provided by test_package.
"""
import os
import re
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BuildtorrentConan(ConanFile):
    name = "buildtorrent"
    version = "0.9.1"
    description = "Command-line .torrent file creation program"
    license = "GPL-2.0-or-later"
    homepage = "https://mathr.co.uk/web/buildtorrent.html"
    url = "https://code.mathr.co.uk/buildtorrent.git"
    topics = ("bittorrent", "torrent", "cli")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "buildtorrent 0.9.1 is adapted for Linux/OHOS, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Keep GNU extensions visible where the OHOS SDK provides them
        # (e.g. scandir/alphasort). NOTE: OHOS <dirent.h> lacks
        # versionsort() even under _GNU_SOURCE (proven R3: -D_GNU_SOURCE
        # still yields "use of undeclared identifier 'versionsort'"), so
        # the real portability fix is the versionsort->alphasort fallback
        # in build(), not this flag alone.
        tc.extra_cflags.append("-D_GNU_SOURCE")
        if self.settings.os == "OHOS":
            # The bundled 2022 config scripts predate HarmonyOS. The compiler
            # still targets OHOS; these portable triplets only avoid an OS-name
            # rejection in configure's feature detection.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def _patch_configure_umask(self, configure_path):
        """HMFS workaround (E011/E112/E118 family): strip ``umask 077`` from
        the AS_TMPDIR temp-dir creation in the shipped ``configure``.

        HMFS refuses writes into ``mktemp -d`` dirs created as drwx--S---
        (0700 + setgid), so ``config.status`` aborts with
        ``can't create ./confXXXXXX/subs1.awk: Permission denied``.
        Removing the ``umask 077 &&`` prefix (a52dec/dar proven: umask 022)
        lets mktemp use the default umask so the temp dir stays writable.
        The pattern also matches the ``config.status`` heredoc template
        embedded in ``configure`` (both ``umask`` and autoconf's ``umash``
        misspelling are covered).
        """
        with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        patched, n_mktemp = re.subn(
            r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
        patched, n_mkdir = re.subn(
            r"um(?:ask|ash) 077 && mkdir", "mkdir", patched)
        if n_mktemp == 0 and n_mkdir == 0:
            self.output.warning(
                "configure has no AS_TMPDIR 'umask 077' pattern; "
                "HMFS workaround not applied")
            return
        with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        self.output.info(
            "patched configure AS_TMPDIR: removed 'umask 077 && ' "
            "for HMFS writable tmpdir (mktemp:%d, mkdir:%d)"
            % (n_mktemp, n_mkdir))

    def _patch_versionsort_fallback(self, source_folder):
        """OHOS portability: fall back from ``versionsort()`` to POSIX
        ``alphasort()`` in ``buildtorrent.c``.

        R3 proved ``-D_GNU_SOURCE`` (flag + prepended source define) is NOT
        sufficient: the compiler still reports
        ``buildtorrent.c:1439:18: error: use of undeclared identifier
        'versionsort'`` with a ``#define _GNU_SOURCE 1`` redefinition
        warning, i.e. the OHOS SDK <dirent.h> simply does not provide
        versionsort(). Upstream documents ``-s/--sort`` Version mode as
        "when available", so mapping that single compar assignment to the
        always-available POSIX alphasort() preserves build and keeps
        directory-mode sorting deterministic. No test is skipped.
        """
        main_c = os.path.join(source_folder, "buildtorrent.c")
        if not os.path.isfile(main_c):
            return
        with open(main_c, "r", encoding="utf-8", errors="replace") as handle:
            orig = handle.read()
        text = orig
        # Drop the R2 prepend if it ever persists in a dirty source tree;
        # the -D_GNU_SOURCE toolchain flag already covers that macro and
        # the duplicate define only produced a redefinition warning.
        prefix = "#ifndef _GNU_SOURCE\n#define _GNU_SOURCE 1\n#endif\n"
        if text.startswith(prefix):
            text = text[len(prefix):]
        if "versionsort" not in text:
            if text != orig:
                with open(main_c, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
            return
        n = len(re.findall(r"\bversionsort\b", text))
        patched = re.sub(r"\bversionsort\b", "alphasort", text)
        with open(main_c, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        self.output.info(
            "patched buildtorrent.c: versionsort->alphasort fallback "
            "for OHOS (no versionsort in SDK headers, %d occurrence(s))" % n)

    def build(self):
        apply_conandata_patches(self)
        self._patch_versionsort_fallback(self.source_folder)
        # [readonly_tmp] /tmp is read-only on HMDFS; keep Autoconf and all
        # child processes on the HMBS-provided writable tmpdir. Only the
        # temp-file root is redirected; no test is skipped or removed.
        hmbs_tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not hmbs_tmp or hmbs_tmp == "/tmp":
            hmbs_tmp = self.build_folder
        try:
            os.makedirs(hmbs_tmp, exist_ok=True)
        except OSError:
            hmbs_tmp = self.build_folder
            os.makedirs(hmbs_tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = hmbs_tmp
        # Use HMBS-injected /bin/sh for any re-exec (avoid HNP bash getcwd
        # failure on HMFS); Autotools helper inherits this environment.
        os.environ["SHELL"] = os.environ.get("SHELL") or "/bin/sh"
        os.environ["CONFIG_SHELL"] = os.environ.get("CONFIG_SHELL") or os.environ["SHELL"]
        # HMDFS strips the executable bit on copy; restore it so
        # Autotools.configure() can run ./configure. HMFS may ignore
        # chmod (HMBS_CAP_CHMOD=0), so tolerate failure: configure already
        # executed past this point in the failing log, umask fix below is
        # the real gate.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            try:
                current_mode = os.stat(configure_path).st_mode
                os.chmod(configure_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except OSError:
                self.output.warning("chmod +x configure ignored (HMBS_CAP_CHMOD=0)")
            # [unsafe_local_mktemp] minimal fix: drop 'umask 077' so the
            # mktemp/mkdir tmpdir is writable. Deliberately NOT a mktemp
            # exit-1 shim: with HMBS_CAP_CHMOD=0 the shim is not executable
            # and the mkdir fallback itself carries 'umask 077', so the shim
            # route cannot work (avahi R22->R23 lesson).
            self._patch_configure_umask(configure_path)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # No upstream test suite: Makefile.am defines only bin_PROGRAMS
        # (buildtorrent) and man_MANS, with no TESTS/check_PROGRAMS targets,
        # so there is no `make check` to run here. Functional coverage is
        # provided by test_package/test_buildtorrent.sh.

    def package(self):
        # [readonly_tmp] keep install-sh/mkdir on HMBS writable tmpdir too;
        # only the temp-file root is redirected.
        hmbs_tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not hmbs_tmp or hmbs_tmp == "/tmp":
            hmbs_tmp = self.build_folder
        try:
            os.makedirs(hmbs_tmp, exist_ok=True)
        except OSError:
            hmbs_tmp = self.build_folder
            os.makedirs(hmbs_tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = hmbs_tmp
        os.environ["SHELL"] = os.environ.get("SHELL") or "/bin/sh"
        os.environ["CONFIG_SHELL"] = os.environ.get("CONFIG_SHELL") or os.environ["SHELL"]
        autotools = Autotools(self)
        autotools.install()
        # Fallback: HMFS install-sh/chmod quirks (HMBS_CAP_CHMOD=0) or
        # VPATH layout differences may leave bin/buildtorrent missing even
        # though `make install` exits 0. Guarantee the single bin_PROGRAMS
        # binary is present by copying the built binary manually.
        # Only the install location is repaired; no test is skipped.
        bindir = os.path.join(self.package_folder, "bin")
        target = os.path.join(bindir, "buildtorrent")
        if not os.path.isfile(target):
            self.output.warning(
                "make install did not place bin/buildtorrent; "
                "trying manual fallback copy from build tree")
            candidate = None
            for search_root in (self.build_folder, self.source_folder):
                if not search_root or not os.path.isdir(search_root):
                    continue
                for root, _dirs, files in os.walk(search_root):
                    if "buildtorrent" not in files:
                        continue
                    path = os.path.join(root, "buildtorrent")
                    if not os.path.isfile(path):
                        continue
                    # Skip sources/scripts with the same basename.
                    if path.endswith((".c", ".h", ".1", ".sh")):
                        continue
                    try:
                        if os.path.getsize(path) < 1024:
                            continue
                    except OSError:
                        continue
                    candidate = path
                    if root == self.build_folder or root.endswith(os.sep + "build"):
                        break
                if candidate:
                    break
            if candidate:
                self.output.info(
                    "fallback copy buildtorrent binary: %s -> %s"
                    % (candidate, target))
                copy(self, "buildtorrent",
                     src=os.path.dirname(candidate), dst=bindir)
                try:
                    current_mode = os.stat(target).st_mode
                    os.chmod(target, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                except OSError:
                    self.output.warning("chmod +x fallback binary ignored (HMBS_CAP_CHMOD=0)")
            else:
                try:
                    listing = os.listdir(self.build_folder)
                except OSError:
                    listing = []
                self.output.warning(
                    "fallback found no built buildtorrent binary; "
                    "build_folder listing: %s" % (listing,))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
