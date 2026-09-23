#!/usr/bin/env python3
"""Conan recipe — libbdplus 0.2.0 (Autotools).

VideoLAN research library implementing the BD+ System Specifications
for Blu-ray content protection (BD+ VM, conversion tables).

OHOS adaptations (all in-recipe, no source patches):
  - configure probes libgcrypt/gpg-error exclusively through the
    libgcrypt-config and gpg-error-config helper scripts (AC_PATH_PROG,
    hard error when absent), but libgcrypt >= 1.10 no longer ships
    libgcrypt-config (clamz/0.5 precedent). Build-local wrapper scripts
    generated from the Conan dependency cpp_info are prepended to PATH
    (gpgme/1.24.0 config-overrides precedent); their --libs answers
    point at a build-private la-free lib view (E236), never at the
    Conan cache libdirs whose .la files retain libdir='//lib'.
    AutotoolsDeps is deliberately NOT generated: it would inject the
    same poisoned cache -L dirs into LDFLAGS, which automake places
    ahead of the wrapper LIBS on the libtool link line, so libtool
    would probe the stale .la first (ezstream 5-round diagnosis).
    Dependency headers/libs reach configure exclusively through the
    wrappers (-I<cache>/include, -L<private> -l...).
  - True cross mode (build != host): the shipped config.guess is
    2018 vintage without ohos detection, so both triplets are given
    explicitly. build != host makes autoconf set cross_compiling=yes
    and skip the compile-and-RUN sanity test that fails in the build
    sandbox (`cannot run C compiled programs`). Safe here: audited
    configure.ac/generated configure contain zero AC_RUN_IFELSE/
    AC_TRY_RUN probes (only compile/link checks), and the
    AC_FUNC_STRERROR_R cross-guess macro it defines is never used by
    any source file.
  - --without-libaacs: libaacs is an example-only dependency (the
    noinst bdplus_test helper); no consumable libaacs recipe exists in
    this repo and the examples are never installed.
  - Upstream ships no automated test suite (see
    test_package/MANIFEST.yml audit), so no `make check` wiring;
    HMBS_UPSTREAM_TEST_RESULT status=no_tests is emitted instead.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy
from conan.tools.files import export_conandata_patches, get, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibbdplusConan(ConanFile):
    name = "libbdplus"
    version = "0.2.0"
    description = "VideoLAN research library implementing the BD+ System Specifications for Blu-ray"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.videolan.org/developers/libbdplus.html"
    url = "https://code.videolan.org/videolan/libbdplus"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libbdplus is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def requirements(self):
        self.requires("libgcrypt/1.11.0", transitive_headers=True, transitive_libs=True)
        self.requires("libgpg-error/1.55", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        # Low-memory guard (真机 compile 曾报 `/bin/sh: Out of memory`):
        # -O1/-g0 降低 cc1 常驻内存与目标文件体积，相对默认 -O2/-g
        # 更适合受限真机；仅影响本包编译，不改 API/ABI。
        tc.extra_cflags.append("-O1")
        tc.extra_cflags.append("-g0")
        tc.generate()
        self._create_config_wrappers()

    def build(self):
        apply_conandata_patches(self)
        # E002: 真机 /tmp 只读(erofs)且默认 TMPDIR 落在 HMDFS 上时，
        # conftest 写 dummy.c 报 Permission denied，首项 AC_PROG_CC 即
        # 报 `cannot run C compiled programs`(libgcrypt/1.11.0 同机实证)。
        # 重定向到 build 目录下可写可执行 _tmp，仅替换临时文件根目录。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        for _key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_key] = _tmp
        # E129/E011: autoconf scratch dirs created under `umask 077`
        # become owner-unwritable on HMDFS (drwx--S---); rewrite to
        # umask 022 in the shipped script (ezstream/libgcrypt precedent).
        # Verified: exactly 2 occurrences in this configure.
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "configure not found in source tree: %s" % configure
            )
        replace_in_file(self, configure, "umask 077", "umask 022")
        # Belt and suspenders for the same HMDFS quirk: child processes
        # inherit a permissive umask as well.
        os.umask(0o022)
        # E236 second layer (ezstream probe-race lesson): even with
        # AutotoolsDeps dropped, defensively strip any residual Conan
        # cache -L dirs from the configure environment so libtool can
        # never probe a poisoned .la; the private la-free dir (created
        # in generate()) is the only -L for -lgcrypt/-lgpg-error.
        # Keep toolchain/sysroot -L flags untouched: only drop -L paths
        # that contain a stale dependency .la file.
        _priv = os.path.join(self.build_folder, "bdplus-private-libs")
        self._scrub_cache_libdirs(_priv)
        autotools = Autotools(self)
        autotools.configure()
        # Keep single-job: 受限真机曾报 `/bin/sh: Out of memory`，禁止提速改 -jN。
        autotools.make(args=["-j1"])
        self._emit_upstream_marker()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Never ship libtool archives (generated artefacts, R6).
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # 3rd-round strategy (dev-alias-only repair proved insufficient):
        # reseed the package lib dir directly from the linked build-tree
        # objects instead of trusting `make install` DESTDIR symlinks.
        self._repair_package_libs()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def _repair_package_libs(self):
        import glob as _glob
        import shutil as _shutil
        try:
            _shared = bool(self.options.shared)
        except Exception:
            _shared = True
        # Diagnose: what did `make install` actually leave behind?
        try:
            _pkg_files = []
            for _root, _dirs, _files in os.walk(self.package_folder):
                for _f in _files:
                    _rel = os.path.relpath(os.path.join(_root, _f), self.package_folder)
                    if "bdplus" in _rel or _rel.endswith(".so") or _rel.endswith(".a"):
                        _pkg_files.append(_rel)
            self.output.info("libbdplus package content (filtered): %s" % sorted(_pkg_files)[:20])
        except Exception:
            pass
        _libdir = os.path.join(self.package_folder, "lib")
        try:
            os.makedirs(_libdir, exist_ok=True)
        except Exception:
            pass
        if _shared:
            # Collect every linked candidate from the build tree
            # (.libs holds the real libtool outputs under VPATH builds).
            _patterns = ["**/.libs/libbdplus.*", "**/libbdplus.so*"]
            _built = []
            for _pat in _patterns:
                try:
                    _built.extend(_glob.glob(os.path.join(self.build_folder, _pat),
                                             recursive=True))
                except Exception:
                    pass
            _built = sorted({p for p in _built if os.path.isfile(p)
                             and not p.endswith(".la") and not p.endswith(".o")})
            try:
                self.output.info("libbdplus build-tree candidates: %s" % _built[:10])
            except Exception:
                pass
            # Seed versioned objects first so the dev alias has a source.
            for _src in _built:
                _base = os.path.basename(_src)
                # Only library artefacts, not .c/.h strays.
                if not (_base.endswith(".a") or ".so" in _base):
                    continue
                _dst = os.path.join(_libdir, _base)
                if not os.path.isfile(_dst):
                    try:
                        _shutil.copyfile(_src, _dst)
                    except OSError:
                        pass
            # Ensure the unversioned dev file CMakeDeps searches for.
            _dev = os.path.join(_libdir, "libbdplus.so")
            if not os.path.isfile(_dev):
                _cands = sorted(_glob.glob(os.path.join(_libdir, "libbdplus.so.*")))
                _cands = [p for p in _cands if os.path.isfile(p)]
                if _cands:
                    try:
                        _shutil.copyfile(_cands[-1], _dev)
                    except OSError:
                        pass
                elif _built:
                    try:
                        _shutil.copyfile(_built[-1], _dev)
                    except OSError:
                        pass
            # Headers/pc fallback when DESTDIR install skipped them.
            _inc = os.path.join(self.package_folder, "include", "libbdplus")
            if not os.path.isfile(os.path.join(_inc, "bdplus.h")):
                try:
                    copy(self, "*.h", src=os.path.join(self.source_folder, "src", "libbdplus"),
                         dst=_inc)
                except Exception:
                    pass

    def package_info(self):
        self.cpp_info.libs = ["bdplus"]
        self.cpp_info.requires = ["libgcrypt::libgcrypt", "libgpg-error::libgpg-error"]
        self.cpp_info.set_property("cmake_file_name", "libbdplus")
        self.cpp_info.set_property("cmake_target_name", "libbdplus::libbdplus")
        self.cpp_info.set_property("pkg_config_name", "libbdplus")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    # ------------------------------------------------------------------ #
    # configure arguments                                                  #
    # ------------------------------------------------------------------ #
    def _configure_args(self):
        args = [
            "--prefix=/",
            "--libdir=/lib",
            "--includedir=/include",
            # Cross mode (not the E007 equal-triplet native fallback):
            # equal build/host forces cross_compiling=no, so configure
            # tries to EXECUTE conftest and hard-errors with `cannot run
            # C compiled programs` in the build sandbox (two consecutive
            # preflight failures on the compiler sanity check, while
            # compilation itself produces a.out fine). build != host
            # enters cross_compiling=yes and skips only that run test.
            # --build is informational only (this package compiles no
            # build-time tools); --host keeps SYS on the generic posix
            # path. Audited safe: zero AC_RUN_IFELSE/AC_TRY_RUN probes in
            # configure.ac and generated configure.
            "--build=x86_64-pc-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--disable-dependency-tracking",
            # libaacs is example-only (noinst bdplus_test helper);
            # no consumable libaacs recipe exists in this repo.
            "--without-libaacs",
        ]
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        return args

    # ------------------------------------------------------------------ #
    # *-config wrapper scripts for configure probes                       #
    # ------------------------------------------------------------------ #
    def _abs_dirs(self, dep, dirs):
        package_folder = str(dep.package_folder)
        absolute = []
        for entry in dirs:
            path = entry if os.path.isabs(entry) else os.path.join(package_folder, entry)
            if path not in absolute:
                absolute.append(path)
        return absolute

    def _wrappers_bin_dir(self):
        return os.path.join(self.build_folder, "bdplus-config-wrappers", "bin")

    def _write_script(self, path, content):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        try:
            os.chmod(path, 0o755)
        except OSError:
            # HMBS_CAP_CHMOD may be 0 on the device; the copy2-preserved
            # exec bit is not needed here, shell runs `sh <script>`.
            pass

    def _scrub_cache_libdirs(self, priv):
        """Drop residual Conan-cache -L dirs holding stale .la files.

        Only -L tokens whose directory contains a dependency .la are
        removed; toolchain/sysroot -L flags are preserved. -L<priv> is
        then prepended so libtool probes the la-free view first.
        Operates on LDFLAGS and LIBS (the two link-line carriers).
        """
        import glob as _glob

        os.makedirs(priv, exist_ok=True)
        for _var in ("LDFLAGS", "LIBS"):
            _val = os.environ.get(_var, "")
            if not _val:
                continue
            _kept = []
            for _tok in _val.split():
                if _tok.startswith("-L") and len(_tok) > 2:
                    _dir = _tok[2:].strip("\"'")
                    try:
                        if _glob.glob(os.path.join(_dir, "*.la")):
                            continue
                    except OSError:
                        pass
                _kept.append(_tok)
            _prefix = "-L%s" % priv
            if _prefix not in _kept:
                _kept.insert(0, _prefix)
            os.environ[_var] = " ".join(_kept)

    def _materialize_private_libs(self, *deps):
        """E236: copy dependency archives into a build-private la-free
        directory. The Conan-cached libgcrypt.la/libgpg-error.la retain
        non-relocatable libdir='//lib' metadata; libtool prefers a visible
        .la over the sibling .so and then fails reading //lib/*.la
        (`is not a valid libtool archive`). Plain-file copies (symlinks
        resolved) carry no .la, so -L<private> -lfoo links the real
        objects directly. The Conan cache is left untouched (ezstream
        E236 precedent).
        """
        import glob as _glob
        import shutil as _shutil

        priv = os.path.join(self.build_folder, "bdplus-private-libs")
        os.makedirs(priv, exist_ok=True)
        for dep, base in deps:
            for libdir in self._abs_dirs(dep, dep.cpp_info.libdirs):
                patterns = [
                    os.path.join(libdir, "lib%s.so*" % base),
                    os.path.join(libdir, "lib%s.a" % base),
                ]
                for pattern in patterns:
                    for path in _glob.glob(pattern):
                        if os.path.isdir(path):
                            continue
                        name = os.path.basename(path)
                        if name.endswith(".la"):
                            continue
                        # copyfile follows symlinks: each alias becomes a
                        # plain file (no symlinks needed despite
                        # HMBS_CAP_SYMLINK=1; chmod=0 is fine, linking
                        # only reads the files).
                        _shutil.copyfile(path, os.path.join(priv, name))
            # Guarantee the -l<base> dev alias even if the package ships
            # only versioned .so files without the unversioned symlink.
            dev = os.path.join(priv, "lib%s.so" % base)
            if not os.path.isfile(dev):
                cands = sorted(
                    _glob.glob(os.path.join(priv, "lib%s.so.*" % base)))
                if cands:
                    _shutil.copyfile(cands[-1], dev)
        return priv

    def _create_config_wrappers(self):
        """configure requires libgcrypt-config and gpg-error-config on
        PATH (AC_PATH_PROG, hard error when absent). The Conan
        libgcrypt package ships no such script, so answer the two
        probes configure actually uses (--cflags/--libs) from the
        resolved dependency package paths. --libs points at the E236
        private la-free lib view, never at the Conan cache libdirs. A
        companion PATH script is saved so the wrappers are visible
        inside the conanbuild env.
        """
        gcrypt = self.dependencies["libgcrypt"]
        gpgerr = self.dependencies["libgpg-error"]
        gcrypt_inc = " ".join(
            "-I%s" % d for d in self._abs_dirs(gcrypt, gcrypt.cpp_info.includedirs)
        )
        gpgerr_inc = " ".join(
            "-I%s" % d for d in self._abs_dirs(gpgerr, gpgerr.cpp_info.includedirs)
        )
        privlib = self._materialize_private_libs(
            (gcrypt, "gcrypt"), (gpgerr, "gpg-error"))
        gcrypt_version = str(gcrypt.ref.version)
        gpgerr_version = str(gpgerr.ref.version)

        bindir = self._wrappers_bin_dir()
        os.makedirs(bindir, exist_ok=True)

        self._write_script(
            os.path.join(bindir, "libgcrypt-config"),
            "#!/bin/sh\n"
            "# libbdplus build-local wrapper (libgcrypt ships no such script).\n"
            "# Only the probes used by libbdplus configure are answered.\n"
            'case "$1" in\n'
            '  --cflags) echo "%s %s" ;;\n'
            '  --libs) echo "-L%s -lgcrypt -lgpg-error" ;;\n'
            '  --version) echo "%s" ;;\n'
            '  --api-version) echo "1" ;;\n'
            '  --prefix|--exec-prefix) echo "%s" ;;\n'
            '  *) echo "libgcrypt-config wrapper: unknown option $1" >&2; exit 1 ;;\n'
            "esac\n"
            % (gcrypt_inc, gpgerr_inc, privlib,
               gcrypt_version, str(gcrypt.package_folder)),
        )
        self._write_script(
            os.path.join(bindir, "gpg-error-config"),
            "#!/bin/sh\n"
            "# libbdplus build-local wrapper (answers from the Conan package).\n"
            'case "$1" in\n'
            '  --cflags) echo "%s" ;;\n'
            '  --libs) echo "-L%s -lgpg-error" ;;\n'
            '  --version) echo "%s" ;;\n'
            '  --prefix|--exec-prefix) echo "%s" ;;\n'
            '  *) echo "gpg-error-config wrapper: unknown option $1" >&2; exit 1 ;;\n'
            "esac\n" % (gpgerr_inc, privlib, gpgerr_version,
                        str(gpgerr.package_folder)),
        )

        env = Environment()
        env.prepend_path("PATH", bindir)
        env.vars(self).save_script("bdplus_config_wrappers")

    # ------------------------------------------------------------------ #
    # upstream test evidence                                               #
    # ------------------------------------------------------------------ #
    def _emit_upstream_marker(self):
        # Upstream 0.2.0 ships no automated suite (audit in
        # test_package/MANIFEST.yml): no TESTS/check_PROGRAMS, no tests
        # tree; src/examples/ holds two manual noinst programs.
        marker = {
            "status": "no_tests",
            "framework": "autotools-make-check",
            "command": "make check (upstream provides no automated suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libbdplus 0.2.0 ships no automated test harness: "
                "top Makefile.am defines no TESTS/check_PROGRAMS, no "
                "tests directory exists, and src/examples/ holds only "
                "two manual noinst programs (bdplus_test needs a real "
                "BD disc + keys); see test_package/MANIFEST.yml "
                "upstream_test_audit"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
