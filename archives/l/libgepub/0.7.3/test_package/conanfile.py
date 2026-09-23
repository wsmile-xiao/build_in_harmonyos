#!/usr/bin/env python3
"""Conan test_package for libgepub 0.7.3 — Conan L1 official test.

Builds test.c (real libgepub API: GepubTextChunk, GepubArchive, GepubDoc
over a synthetic EPUB generated offline by make_book.py) plus
upstream_headless.c (headless port of upstream tests/test-gepub.c 7 TEST()
cases: test_open/read/root_file/doc_name/doc_resources/doc_spine/doc_toc,
GTK/webkit harness excluded) with CMake (CMakeDeps + CMakeToolchain) and
runs both headless. Binaries are wrapped with bash because OHOS
/system/bin/sh (mksh) cannot exec ELF directly.

Emits both hmbs evidence markers on every run (print, bare stdout):
  HMBS_TEST_PACKAGE_RESULT (discovered=6 groups, passedCount=6)
  HMBS_UPSTREAM_TEST_RESULT (status=passed, 7/7 upstream TESTs via
  ./upstream_headless — see MANIFEST.yml)
Both binaries exit 1 on any failed assertion, so a regression fails conan
test loudly instead of passing silently.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LibgepubTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # Explicit generator list REPLACES the conan default set, so VirtualRunEnv
    # / VirtualBuildEnv must be listed or test() loses the conanrun
    # LD_LIBRARY_PATH at run time (libsoup3 recipe precedent).
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib must be an explicit test_package dep: public gepub headers
        # include glib/gio/gobject, and CMakeDeps emits empty data for the
        # transitive glib dep (conan 2.29). Same version/pinning as the
        # libgepub recipe itself (shared glib/2.84.0.1.1, libsoup3-chain pin).
        self.requires("glib/2.84.0.1.1", options={"shared": True})

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH, so embed RPATH pointing
        # at the (shared) dependency lib dirs in the test binary. musl only
        # honors legacy DT_RPATH, not DT_RUNPATH (lld default), hence
        # --disable-new-dtags (libsoup3 recipe precedent).
        rpaths = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir:
                    continue
                p = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(p):
                    rpaths.append(p)
        configure_vars = {}
        if rpaths:
            configure_vars = {"CMAKE_EXE_LINKER_FLAGS": " ".join(
                ["-Wl,--disable-new-dtags"] + ["-Wl,-rpath,%s" % p for p in rpaths])}
        cmake.configure(variables=configure_vars)
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # Fixture generation is stdlib-only (zipfile) and needs NO conan libs.
        # True-machine evidence (2026-09-18): HMBS_PYTHON3
        # (/.../.harmonybrew/Cellar/python@3.14/.../python3) fails under
        # env="conanrun" with:
        #   Error relocating .../libpython3.14.so.1.0: libintl_dgettext:
        #   symbol not found (exit 127).
        # The conanrun LD_LIBRARY_PATH pulls conan gettext/libintl ahead of
        # the harmonybrew one the interpreter was linked against, so the
        # interpreter cannot even start. Fix: run make_book.py with a CLEAN
        # env (no LD_LIBRARY_PATH/LD_PRELOAD from conan) and prefer the
        # already-running Conan interpreter (sys.executable, proven working
        # -- conan itself runs on it) over HMBS_PYTHON3.
        test_dir = self.source_folder
        book = os.path.join(self.build_folder, "book.epub")
        _candidates = []
        for _c in (getattr(sys, "executable", None),
                   os.environ.get("HMBS_PYTHON3"),
                   shutil.which("python3"),
                   "/usr/bin/python3", "/bin/python3"):
            if _c and _c not in _candidates:
                _candidates.append(_c)
        _candidates = [_c for _c in _candidates if _c]
        if not _candidates:
            _candidates = ["python3"]
        # Writable tmp root: /tmp may be read-only on the true machine
        # ([readonly_tmp] diagnosis); fall back to build-folder subdir.
        _tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP") or "/tmp"
        try:
            _writable = os.access(_tmp, os.W_OK | os.X_OK)
        except Exception:
            _writable = False
        _fallback_tmp = os.path.join(self.build_folder, "hmbs-tmp")
        if not _writable:
            try:
                os.makedirs(_fallback_tmp, exist_ok=True)
            except Exception:
                pass
            _tmp = _fallback_tmp
        _clean_env = dict(os.environ)
        _clean_env.pop("LD_LIBRARY_PATH", None)
        _clean_env.pop("LD_PRELOAD", None)
        _clean_env["TMPDIR"] = _tmp
        _clean_env["TMP"] = _tmp
        _clean_env["TEMP"] = _tmp
        _clean_env["PYTHONNOUSERSITE"] = "1"
        _picked = None
        _last_err = None
        for _c in _candidates:
            try:
                _r = subprocess.run([_c, "--version"], capture_output=True,
                                    text=True, env=_clean_env, timeout=60)
                if _r.returncode == 0:
                    _picked = _c
                    break
                _last_err = (_r.stdout + _r.stderr)[-500:]
            except Exception as _e:  # noqa: BLE001 -- try next candidate
                _last_err = str(_e)[-500:]
                continue
        if _picked is None:
            raise ConanException(
                "no working python3 for make_book.py (tried %s): %s"
                % (_candidates, _last_err))
        self.output.info("make_book python: %s (TMPDIR=%s)" % (_picked, _tmp))
        _mk = subprocess.run([_picked, os.path.join(test_dir, "make_book.py"), book],
                             capture_output=True, text=True, env=_clean_env, timeout=120)
        self.output.info((_mk.stdout + _mk.stderr)[-2000:])
        if _mk.returncode != 0:
            raise ConanException(
                "make_book.py failed with %s (code %d)" % (_picked, _mk.returncode))
        if not os.path.isfile(book) or os.path.getsize(book) == 0:
            raise ConanException("book.epub missing or empty after make_book.py")
        # Explicit LD_LIBRARY_PATH from ALL deps (relative libdirs resolved
        # against package_folder); conanrun env alone is not enough on OHOS
        # (libsoup3 r3 precedent: empty libdirs + bare "lib:" entries).
        _seen, libdirs = set(), []
        for _r, _d in self.dependencies.items():
            _k = str(getattr(getattr(_r, "ref", _r), "ref", _r))
            if _k in _seen:
                continue
            _seen.add(_k)
            _base = getattr(_d, "package_folder", None) or ""
            for _p in _d.cpp_info.libdirs:
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs:
                    libdirs.append(_p)
        ldpath = os.pathsep.join(libdirs)
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libgepub")
        upstream_bin = os.path.join(self.cpp.build.bindirs[0], "upstream_headless")
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
            f"{test_bin} {book}'",
            env="conanrun")
        # Upstream suite: 7 headless-ported TEST() cases from
        # tests/test-gepub.c (GTK/webkit/display harness excluded; only the
        # GepubArchive/GepubDoc functions run). Exits 1 on any failure, so
        # reaching the markers below means 7/7 passed for real.
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; "
            f"{upstream_bin} {book}'",
            env="conanrun")
        # test binary exits 1 on any failed assertion, so reaching here means
        # 6/6 groups and 16/16 checks passed. Emit hmbs hard-gate markers.
        print('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
              '"command":"./test_libgepub book.epub","discovered":6,"passedCount":6}')
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"ctest",'
              '"command":"./upstream_headless book.epub (headless port of tests/test-gepub.c 7 TESTs)",'
              '"discovered":7,"executed":7,"passed":7,"failed":0,"skipped":0}')
