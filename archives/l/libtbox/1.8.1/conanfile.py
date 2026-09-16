#!/usr/bin/env python3
"""Conan recipe for libtbox 1.8.1 — xmake.sh (script-only) build system.

tbox is a glib-like cross-platform C library (containers, algorithm,
stream, charset, hash, xml, regex, coroutine, …). Upstream builds with
xmake, but ships a script-only `configure` (xmake.sh engine) that generates
a plain Makefile, so no xmake binary is required on OHOS CI workers.

Build: sh ./configure --plat=linux --arch=arm64 … && make -j1
Install: make install DESTDIR=<package_folder> PREFIX=/
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibtboxConan(ConanFile):
    name = "libtbox"
    version = "1.8.1"
    description = "A glib-like cross-platform C library (stream, coroutine, container, hash, xml, charset)."
    license = "Apache-2.0"
    homepage = "https://github.com/tboox/tbox"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        basic_layout(self)
        # xmake.sh generates the Makefile in the source directory (in-source build)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, candidate, fallbacks):
        """ladspa-sdk pattern: profile absolute paths can be dead symlinks
        in the build env; prefer the absolute path only when it is a real
        executable file, otherwise fall back to bare names resolved via
        PATH (augmented by conanbuild.sh / HMBS buildenv). Never raises."""
        import shutil
        if candidate and os.path.isabs(candidate):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        elif candidate and shutil.which(candidate):
            return shutil.which(candidate)
        for _fb in fallbacks:
            if os.path.isabs(_fb):
                if os.path.isfile(_fb) and os.access(_fb, os.X_OK):
                    return _fb
            elif shutil.which(_fb):
                return shutil.which(_fb)
        # Last resort: bare first fallback; let the real tool invocation
        # surface the error instead of a Python os.access false negative.
        return fallbacks[0]

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler paths come from Conan conf, never from bare shell env vars.
        # ladspa-sdk precedent: the ohos profile absolute path
        # (/data/service/hnp/bin/clang) can be a dead symlink inside the
        # build env, so only honor it when it is a real executable file;
        # otherwise fall back to bare names via PATH. The previous round's
        # pre-configure gate did the opposite (raised ConanException when
        # os.access failed), which hard-blocked configure with
        # "CC not executable" even though PATH resolution would succeed.
        # This round removes that gate entirely.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _cc_raw = compilers.get("c")
        _cxx_raw = compilers.get("cpp")
        _ar_raw = compilers.get("ar")
        _cc_dir = os.path.dirname(_cc_raw) if (_cc_raw and os.path.isabs(_cc_raw)) else ""
        _cxx_dir_try = os.path.join(_cc_dir, "clang++") if _cc_dir else ""
        cc = self._resolve_tool(_cc_raw, ["clang"])
        cxx = self._resolve_tool(_cxx_raw, [_cxx_dir_try, "clang++"] if _cxx_dir_try else ["clang++"])
        _ar_dir_tries = []
        if _cc_dir:
            _ar_dir_tries = [os.path.join(_cc_dir, "llvm-ar"), os.path.join(_cc_dir, "ar")]
        ar = self._resolve_tool(_ar_raw, _ar_dir_tries + ["llvm-ar", "ar"])
        # R5: OHOS has no /bin/sh; CONFIG_SHELL is set by the ohos-aarch64
        # profile [buildenv], default to the OHOS bash path for safety.
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        kind = "shared" if self.options.shared else "static"
        # HMBS readonly_tmp: xmake.sh engine mktemps via ${TMPDIR-/tmp}
        # (_os_tmpfile/_os_iorunv) and OHOS /tmp is read-only. The toolchain
        # probe itself runs through that tmpfile, so a read-only /tmp shows
        # up as "checking for toolchain ... no / toolchain not found!" even
        # when CC is correct. Prefer the HMBS-injected writable TMPDIR/TMP/
        # TEMP, fallback to a build-folder private tmp (never /tmp).
        _hmbs_tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                     or os.environ.get("TEMP") or "")
        if not _hmbs_tmp or _hmbs_tmp == "/tmp" or not os.path.isdir(_hmbs_tmp):
            _hmbs_tmp = os.path.join(self.build_folder, "_hmbs_tmp")
        os.makedirs(_hmbs_tmp, exist_ok=True)
        # Persist for package(): make install also runs shell recipes that
        # may mktemp; OHOS /tmp is read-only (readonly_tmp gate).
        self._hmbs_tmp = _hmbs_tmp
        env = Environment()
        env.define_path("TMPDIR", _hmbs_tmp)
        env.define_path("TMP", _hmbs_tmp)
        env.define_path("TEMP", _hmbs_tmp)
        with env.vars(self).apply():
            self.output.info(f"[libtbox] CC={cc} CXX={cxx} AR={ar} TMPDIR={_hmbs_tmp} SHELL={config_shell}")
            # No pre-configure gate: os.access/isfile checks produced false
            # negatives on dead-symlink absolute paths and hard-blocked
            # configure. Let xmake.sh probe the resolved tools directly so
            # the real toolchain error (if any) surfaces in its own log.
            # --toolchain=envs makes xmake.sh take CC/CXX/AR from the environment
            # (values above, formatted in Python — not bare ${CC} references).
            # --plat=linux: OHOS userspace is Linux-ABI compatible for this pure-C
            # library (posix + epoll poller path); xmake.sh knows no "ohos" plat.
            # --demo=n: examples are not tests and must not become install artifacts.
            # --small=n: build the full module set (hash/charset/xml/regex/…).
            # Optional third-party packages are disabled to keep the build hermetic
            # (regex falls back to posix, zip keeps its builtin codecs).
            # Explicit module enables: --small=n alone SHOULD re-enable the
            # module set (after_check disables modules only when small/micro
            # is enabled), but the preflight link failed with undefined
            # tb_crc32_make/tb_crc32_make_from_cstr (hash module) — so pass
            # every module explicitly to guarantee the full archive even if
            # xmake.sh option defaults shift between releases.
            # umask 022: HMDFS default 077 makes script-created tmp dirs group-
            # unwritable (same class as zzuf/abiword E011/E114 workarounds).
            self.run(
                f"umask 022 && CONFIG_SHELL={config_shell} CC={cc} CXX={cxx} AR={ar} "
                f"TMPDIR={_hmbs_tmp} TMP={_hmbs_tmp} TEMP={_hmbs_tmp} "
                f"{config_shell} ./configure --plat=linux --arch=arm64 "
                f"--mode=release --kind={kind} --toolchain=envs --verbose "
                "--demo=n --small=n --micro=n "
                "--float=y --info=y --exception=n --deprecated=n "
                "--xml=y --zip=y --hash=y --regex=y --object=y "
                "--charset=y --database=y --coroutine=y "
                "--zlib=n --sqlite3=n --mysql=n --openssl=n --polarssl=n "
                "--pcre2=n --pcre=n --prefix=/"
            )
            # R9: keep parallelism at 1 on the OHOS workers.
            self.run(f"umask 022 && TMPDIR={_hmbs_tmp} TMP={_hmbs_tmp} TEMP={_hmbs_tmp} make -j1")
            # Fail fast if the archive is incomplete: the preflight symptom
            # was `-ltbox` found but tb_crc32/tb_vector symbols missing
            # (empty or module-stripped archive links as "undefined symbol",
            # not "library not found"). Surface the real cause here with
            # config + archive evidence instead of a cryptic test_package ld error.
            # NOTE: pure-sh probe (no `nm` dependency); the strict symbol
            # check happens in package() where the final archive path is known.
            self.run(
                "echo '[libtbox] config modules:'; "
                "find . -maxdepth 3 -name 'tbox.config.h' | head -5; "
                "for f in $(find . -maxdepth 3 -name 'tbox.config.h' | head -5); do "
                "echo \"--- $f\"; "
                "grep -E 'TB_CONFIG_MODULE_HAVE_(HASH|CHARSET|XML|REGEX|OBJECT|COROUTINE|DATABASE|ZIP)' \"$f\" || true; "
                "done; "
                "echo '[libtbox] archives:'; "
                "find . -maxdepth 5 \\( -name 'libtbox.*' -o -name '*.a' \\) | head -20; "
                "ls -l ./build/libtbox.a 2>/dev/null || true"
            )
        # L1: upstream ships NO test suite (audited in test_package/MANIFEST.yml
        # and notes.md: no tests/ dir, no gtest/pytest/ctest registration, the
        # generated Makefile has no check/test target, src/demo/* are examples
        # and src/demo/other/test.c is an empty stub returning 0). There is
        # therefore no `make check` to run here by design.

    def package(self):
        # The generated Makefile honors DESTDIR + PREFIX (see _gmake_add_switches
        # in upstream configure): with PREFIX=/ files land directly under the
        # package folder (lib/, include/, lib/pkgconfig/).
        # Recompute writable tmp (do NOT reuse self._hmbs_tmp: Conan may
        # re-instantiate the recipe between build() and package()).
        _ptmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                 or os.environ.get("TEMP") or "")
        if not _ptmp or _ptmp == "/tmp" or not os.path.isdir(_ptmp):
            _ptmp = os.path.join(self.build_folder, "_hmbs_tmp")
        os.makedirs(_ptmp, exist_ok=True)
        self.run(
            "umask 022 && TMPDIR={t} TMP={t} TEMP={t} "
            "make install DESTDIR={pfx} PREFIX=/".format(
                t=_ptmp, pfx=self.package_folder)
        )
        # Strict gate: the installed static archive MUST export the symbols
        # the consumer test links (tb_init, tb_crc32_make, tb_vector_init).
        # Uses llvm-nm/nm when available; falls back to size check so a
        # missing nm binary never green-lights an empty archive silently.
        import shutil as _shutil
        _nm = _shutil.which("llvm-nm") or _shutil.which("nm")
        _lib = os.path.join(self.package_folder, "lib", "libtbox.a")
        if not os.path.isfile(_lib):
            raise Exception(
                "[libtbox] package gate: {} missing; "
                "install did not produce the static archive".format(_lib))
        if _nm:
            self.run(
                "{nm} -g {lib} > ./_hmbs_symbols.txt 2>&1 || true; "
                "echo '[libtbox] symbols:'; "
                "grep -E 'tb_crc32_make|tb_vector_init|tb_init' ./_hmbs_symbols.txt || true; "
                "for s in tb_init tb_crc32_make tb_crc32_make_from_cstr tb_vector_init; do "
                "grep -q \"$s\" ./_hmbs_symbols.txt || "
                "(echo \"[libtbox] package gate: symbol $s missing from libtbox.a\"; exit 1); "
                "done".format(nm=_nm, lib=_lib)
            )
        elif os.path.getsize(_lib) < 50000:
            raise Exception(
                "[libtbox] package gate: libtbox.a suspiciously small "
                "(%d bytes), likely module-stripped" % os.path.getsize(_lib))

    def package_info(self):
        # The library target is "tbox" → libtbox.a / libtbox.so.
        self.cpp_info.libs = ["tbox"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m", "c"]
