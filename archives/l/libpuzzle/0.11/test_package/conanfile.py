#!/usr/bin/env python3
"""Conan test_package — libpuzzle 0.11 consumer verification (L1).

Layer 2 checks: the C binary really calls the public API (context,
cvec/dvec fill, distance, compress roundtrip) over GD-generated PNGs,
and the puzzle-diff CLI is smoke-tested through the POSIX driver, which
emits the HMBS_TEST_PACKAGE_RESULT hard-gate marker.
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibpuzzleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # test_libpuzzle.c includes <gd.h> directly to generate PNG
        # fixtures at runtime, so gd must be an explicit test requirement
        # (transitive via libpuzzle alone does not emit gd CMake config
        # for find_package without this).
        self.requires("gd/2.3.3.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # HMBS readonly_tmp: /tmp is read-only on the device. Probe a
        # writable TMPDIR/TMP/TEMP now so the CMake configure step (which
        # runs after this) inherits it. build() re-probes as well.
        self._ensure_writable_tmp()

    def _ensure_writable_tmp(self):
        # cubelib/4.9.1 precedent: prefer HMBS-injected writable dirs,
        # probe with a real mkstemp, never fall back to read-only /tmp.
        cands = []
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            v = os.environ.get(var)
            if v and v != "0" and v != "/tmp" and v not in cands:
                cands.append(v)
        for d in cands:
            try:
                if not os.path.isdir(d):
                    continue
                fd, p = tempfile.mkstemp(dir=d)
                os.close(fd)
                os.unlink(p)
                for key in ("TMPDIR", "TMP", "TEMP"):
                    os.environ[key] = d
                return
            except Exception:
                continue
        try:
            tmpdir = os.path.join(self.build_folder, "_tmp")
            os.makedirs(tmpdir, exist_ok=True)
            for key in ("TMPDIR", "TMP", "TEMP"):
                os.environ[key] = tmpdir
        except OSError:
            return

    def _resolve_compiler(self, conf_key, names):
        # cubelib/4.9.1 precedent: the repo profile pins
        # tools.build:compiler_executables to /data/service/hnp/bin/clang(++),
        # absent on some HMBS hosts (cmake configure dies with
        # "CMAKE_C_COMPILER: /data/service/hnp/bin/clang ... not found").
        # Keep the conf value when the file exists; otherwise fall back to
        # a PATH-resolved compiler. Pure isfile probing, no X_OK per R49.
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        configured = None
        try:
            configured = conf.get(conf_key)
        except Exception:
            configured = None
        if configured:
            first = str(configured).split()[0].strip("\"'")
            try:
                if first and os.path.isfile(first):
                    self.output.info("libpuzzle test_package keeps configured %s=%s"
                                     % (conf_key, configured))
                    return str(configured).strip()
            except OSError:
                pass
            self.output.info("libpuzzle test_package configured %s=%s missing, PATH fallback"
                             % (conf_key, configured))
        for name in names:
            found = shutil.which(name)
            if found:
                self.output.info("libpuzzle test_package %s PATH fallback: %s" % (conf_key, found))
                return found
        self.output.info("libpuzzle test_package %s bare fallback: %s" % (conf_key, names[0]))
        return names[0]

    def _scrub_toolchain_stale_compilers(self, cc, cxx):
        # Rewrite the stale baked-in compiler paths in the generated
        # conan_toolchain.cmake (experience 1 pattern): only when the stale
        # path is actually missing on this host, so CI workers with a good
        # HNP toolchain stay untouched.
        try:
            toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        except Exception:
            return False
        try:
            if not (toolchain and os.path.isfile(toolchain)):
                return False
            with open(toolchain, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return False
        rewrote = False
        for stale, good in (("/data/service/hnp/bin/clang", cc),
                            ("/data/service/hnp/bin/clang++", cxx)):
            if stale in content:
                try:
                    missing = not os.path.isfile(stale)
                except OSError:
                    missing = True
                if missing and good and good != stale:
                    content = content.replace(stale, good)
                    rewrote = True
                    self.output.info("libpuzzle test_package scrubbed stale %s -> %s"
                                     % (stale, good))
        if rewrote:
            try:
                with open(toolchain, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass
        return rewrote

    def _remove_stale_cmake_cache(self):
        # A CMakeCache.txt baked with the stale compiler path keeps failing
        # even after the toolchain is scrubbed; drop caches that reference
        # a compiler file missing on this host (experience 1: clear cache).
        removed = []
        try:
            roots = [self.build_folder]
        except Exception:
            return removed
        for root in roots:
            try:
                for dirpath, _dirnames, filenames in os.walk(root):
                    if "CMakeCache.txt" not in filenames:
                        continue
                    cache = os.path.join(dirpath, "CMakeCache.txt")
                    try:
                        with open(cache, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                    except OSError:
                        continue
                    stale_hit = "/data/service/hnp/bin/clang" in text
                    if not stale_hit:
                        continue
                    try:
                        missing = not os.path.isfile("/data/service/hnp/bin/clang")
                    except OSError:
                        missing = True
                    if not missing:
                        continue
                    try:
                        os.remove(cache)
                        removed.append(cache)
                        self.output.info("libpuzzle test_package removed stale CMakeCache: %s" % cache)
                    except OSError as e:
                        self.output.warning("libpuzzle test_package cannot remove %s: %s" % (cache, e))
            except Exception:
                continue
        return removed

    def build(self):
        self._ensure_writable_tmp()
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        self._scrub_toolchain_stale_compilers(cc, cxx)
        self._remove_stale_cmake_cache()
        self.output.info("libpuzzle test_package CMAKE_C_COMPILER=%s CMAKE_CXX_COMPILER=%s"
                         % (cc, cxx))
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def test(self):
        cmake = CMake(self)
        cmake.test()
        # L0d/R34: run the real consumer test (API calls, not echo).
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libpuzzle")
        pkg = self.dependencies[self.tested_reference_str]
        puzzle_diff = os.path.join(pkg.package_folder, "bin", "puzzle-diff")
        here = os.path.dirname(os.path.abspath(__file__))
        driver = os.path.join(here, "test_driver.sh")
        # `sh` resolves to /system/bin/sh on OHOS and POSIX sh elsewhere.
        self.run(
            'sh "%s" "%s" "%s" "%s"'
            % (driver, test_bin, puzzle_diff, self.build_folder),
            env="conanrun",
        )
