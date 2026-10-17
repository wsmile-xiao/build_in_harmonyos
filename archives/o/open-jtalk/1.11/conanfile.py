#!/usr/bin/env python3
"""Conan recipe for open_jtalk 1.11 (autotools).

Open JTalk — HMM-based Japanese text-to-speech synthesis system.
Upstream: https://open-jtalk.sourceforge.net/ (SourceForge project open-jtalk,
HTS Working Group / Nagoya Institute of Technology).

Adaptation notes (HarmonyOS OHOS aarch64, native build):

- hts_engine_API 1.10 is a hard configure-time requirement of open_jtalk
  (``--with-hts-engine-header-path`` / ``--with-hts-engine-library-path``) and
  is not published anywhere we can depend on: the ohpcd Conan registry has no
  hts_engine recipe (``conan list 'hts_engine/*' -r=ohpcd`` -> 0 matches,
  2026-09-13) and the cmd-pkgs prebuilt index (1248 packages) contains no hts
  entry. It is therefore built privately from its official SourceForge release
  and linked statically into the open_jtalk binary — the same "private_sources"
  approach used by archives/a/aws-c-http. Nothing of hts_engine_API is shipped
  as a separate package; only the resulting ``bin/open_jtalk`` is packaged.

- open_jtalk 1.11 only builds **in tree**: ``bin/Makefile.am`` links
  ``@top_srcdir@/text2mecab/libtext2mecab.a`` and friends, i.e. absolute paths
  into the source directory, while automake builds those archives in the build
  directory. A VPATH/out-of-tree build therefore dies with
  ``No rule to make target '<src>/text2mecab/libtext2mecab.a'``. ``layout()``
  below pins build_folder == source_folder (``src_folder="."`` +
  ``folders.build = "."``), so Conan configures in the copied source tree.

- config.guess/config.sub are the old-style 2013 GNU scripts (no ``GUESS=``
  variable), for which E007's ``patch-autotools-ohos.pl`` anchors do not apply.
  Per E564 they get a minimal anchor patch instead (patch 0001): a runtime
  ``aarch64:HarmonyOS:*:*`` branch in config.guess plus the ``linux-ohos*``
  double anchor in config.sub, so ``aarch64-unknown-linux-ohos`` is produced and
  accepted. No ``__OHOS__`` platform macro is involved. ``configure`` itself
  still needs patch 0002, which removes the ``umask 077`` around its
  config.status scratch directory (a 0700 directory is not writable on the
  setgid HMDFS mount, so configure aborts with
  ``can't create ./confXXXXXX/subs1.awk: Permission denied``).

- hts_engine_API 1.10 gets the same config.guess/config.sub anchor patch (those
  two files are byte-identical to open_jtalk's) plus its own configure umask
  patch and one more fix: ``HTS_misc.c`` uses ``fpos_t.__pos``, which does not
  exist in the OHOS (musl) ``fpos_t`` (``union _G_fpos64_t { char
  __opaque[16]; long long __lldata; double __align; }``); the private patch
  switches ``HTS_ftell`` to ``ftell()``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, patch)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Timestamp pinned on every autotools input after patching so that make's
# maintainer rules cannot regenerate configure/Makefile.in and silently drop
# the patches (2020-01-01).
_AUTOTOOLS_STAMP = 1577836800
_AUTOTOOLS_NAMES = ("configure", "config.guess", "config.sub", "aclocal.m4",
                    "ltmain.sh", "compile", "depcomp", "missing", "install-sh")


class OpenJTalkConan(ConanFile):
    name = "open-jtalk"
    version = "1.11"
    description = "HMM-based Japanese text-to-speech synthesis system (Open JTalk)"
    license = "BSD-3-Clause"
    homepage = "https://open-jtalk.sourceforge.net/"
    url = "https://sourceforge.net/projects/open-jtalk/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*.patch",
             os.path.join(self.recipe_folder, "patches", "hts_engine"),
             os.path.join(self.export_sources_folder, "patches", "hts_engine"))

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"open-jtalk supports Linux/OHOS only, got {self.settings.os}")

    def layout(self):
        # open_jtalk 1.11 does not support VPATH builds (see module docstring):
        # build_folder must be the copied source tree itself.
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for name, metadata in self.conan_data["private_sources"].items():
            get(self, **metadata, destination=self._private_source(name),
                strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The bundled MeCab 0.996 sources are C++98-era and use the `register`
        # storage class, removed in C++17 (the profile's compiler.cppstd).
        # clang reports it as an error; the keyword is simply ignored with
        # -Wno-register on OHOS clang 15 (same as archives/a/autodocksuite).
        tc.extra_cxxflags.append("-Wno-register")
        tc.configure_args.append(
            "--with-hts-engine-header-path={}".format(self._private_include_dir))
        tc.configure_args.append(
            "--with-hts-engine-library-path={}".format(self._private_lib_dir))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._apply_private_patches()
        self._restore_autotools_modes(self.source_folder)
        self._restore_autotools_modes(self._private_source("hts_engine_API"))
        self._pin_autotools_timestamps(self.source_folder)
        self._pin_autotools_timestamps(self._private_source("hts_engine_API"))
        self._build_hts_engine()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream defines no check_PROGRAMS/TESTS in any Makefile.am, so
        # `make check` recurses through every SUBDIR and is a no-op (verified
        # rc=0 on device). It is still invoked for the CI "upstream tests ran"
        # trace; the real consumer verification lives in test_package/test.sh.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["dic"]

    # ── private (vendored) hts_engine_API ──────────────────────────────────

    def _private_source(self, name):
        return os.path.join(self.source_folder, "_deps", name)

    @property
    def _private_prefix(self):
        return os.path.join(self.build_folder, "_hts_engine", "prefix")

    @property
    def _private_include_dir(self):
        return os.path.join(self._private_prefix, "include")

    @property
    def _private_lib_dir(self):
        return os.path.join(self._private_prefix, "lib")

    def _apply_private_patches(self):
        base = self._private_source("hts_engine_API")
        for name in self.conan_data.get("private_patches", {}).get("hts_engine_API", []):
            patch(self, base_path=base,
                  patch_file=os.path.join(self.export_sources_folder, name))

    def _build_hts_engine(self):
        src = self._private_source("hts_engine_API")
        build_dir = os.path.join(self.build_folder, "_hts_engine", "build")
        os.makedirs(build_dir, exist_ok=True)
        os.makedirs(self._private_prefix, exist_ok=True)
        configure = os.path.join(src, "configure")
        args = [f'--prefix="{self._private_prefix}"']
        self.run(f'"{configure}" ' + " ".join(args),
                 cwd=build_dir, env="conanbuild")
        self.run("make -j1", cwd=build_dir, env="conanbuild")
        self.run("make install", cwd=build_dir, env="conanbuild")

    @staticmethod
    def _restore_autotools_modes(root):
        """Restore execute bits on the known autotools helper scripts (E490).

        Some OHOS adaptation paths preserve file content without the POSIX
        execute bits; configure then aborts with "Permission denied" before
        compiling anything. Only the well-known helper names are touched.
        """
        names = ("configure", "config.guess", "config.sub", "install-sh",
                 "missing", "compile", "depcomp", "ltmain.sh", "ar-lib",
                 "mkinstalldirs", "ylwrap", "test-driver")
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                if filename in names:
                    path = os.path.join(dirpath, filename)
                    try:
                        os.chmod(path, os.stat(path).st_mode | 0o111)
                    except OSError:
                        pass

    @staticmethod
    def _pin_autotools_timestamps(root):
        """Pin autotools inputs to one old timestamp.

        Patching ``configure`` (or a ``*.in``) otherwise leaves make's
        maintainer rules free to re-run autoconf/automake and revert the
        patches.
        """
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                if filename.endswith((".m4", ".am", ".in", ".ac")) \
                        or filename in _AUTOTOOLS_NAMES:
                    try:
                        os.utime(os.path.join(dirpath, filename),
                                 (_AUTOTOOLS_STAMP, _AUTOTOOLS_STAMP))
                    except OSError:
                        pass
