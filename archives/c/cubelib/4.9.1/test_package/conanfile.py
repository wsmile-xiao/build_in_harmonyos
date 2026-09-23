#!/usr/bin/env python3
"""Installed-package API tests for cubelib 4.9.1."""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CubelibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_cube_api.cpp", "test_cube_write.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        from conan.tools.cmake import CMakeDeps, CMakeToolchain
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()
        self._ensure_writable_tmp()

    def _ensure_writable_tmp(self):
        import tempfile
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
                    self.output.info("cubelib test_package keeps configured %s=%s"
                                     % (conf_key, configured))
                    return str(configured).strip()
            except OSError:
                pass
            self.output.info("cubelib test_package configured %s=%s missing, PATH fallback"
                             % (conf_key, configured))
        for name in names:
            found = shutil.which(name)
            if found:
                self.output.info("cubelib test_package %s PATH fallback: %s" % (conf_key, found))
                return found
        self.output.info("cubelib test_package %s bare fallback: %s" % (conf_key, names[0]))
        return names[0]

    def _scrub_toolchain_stale_compilers(self, cc, cxx):
        try:
            toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        except Exception:
            return
        try:
            if not (toolchain and os.path.isfile(toolchain)):
                return
            with open(toolchain, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return
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
                    self.output.info("cubelib test_package scrubbed stale %s -> %s"
                                     % (stale, good))
        if rewrote:
            try:
                with open(toolchain, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError:
                pass

    def build(self):
        self._ensure_writable_tmp()
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        self._scrub_toolchain_stale_compilers(cc, cxx)
        self.output.info("cubelib test_package CMAKE_C_COMPILER=%s CMAKE_CXX_COMPILER=%s"
                         % (cc, cxx))
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def _abs_test_binary(self, name):
        # self.cpp.build.bindir(s) are build-folder-relative (often "."),
        # so joining them naively yields "./<bin>". Combined with
        # cwd=TMPDIR (writable dir for the write-contract outputs) the
        # relative lookup resolves inside TMPDIR and dies with
        # "/bin/sh: ./cubelib_api_contract: inaccessible or not found"
        # (Error 127). Resolve to an absolute path under build_folder;
        # glob as a last resort for multi-config subdirs. No test skip.
        import glob
        candidates = []
        try:
            bindirs = list(getattr(self.cpp.build, "bindirs", []) or [])
        except Exception:
            bindirs = []
        try:
            _b = getattr(self.cpp.build, "bindir", None)
            if _b and _b not in bindirs:
                bindirs.append(_b)
        except Exception:
            pass
        for _d in bindirs:
            if not _d:
                continue
            _base = _d if os.path.isabs(_d) else os.path.join(self.build_folder, _d)
            candidates.append(os.path.normpath(os.path.join(_base, name)))
        try:
            candidates.append(os.path.normpath(os.path.join(self.build_folder, name)))
        except Exception:
            pass
        for _c in candidates:
            try:
                if _c and os.path.isfile(_c):
                    return _c
            except OSError:
                continue
        try:
            hits = glob.glob(os.path.join(self.build_folder, "**", name), recursive=True)
            for _h in hits:
                try:
                    if os.path.isfile(_h):
                        return os.path.normpath(_h)
                except OSError:
                    continue
        except Exception:
            pass
        self.output.warning("cubelib test_package binary %s not found, tried: %s"
                            % (name, candidates[:4]))
        return candidates[0] if candidates else name

    def test(self):
        if not can_run(self):
            return
        api_bin = self._abs_test_binary("cubelib_api_contract")
        write_bin = self._abs_test_binary("cubelib_write_contract")
        self.output.info("cubelib test_package binaries: %s ; %s" % (api_bin, write_bin))
        run_cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or None
        if run_cwd and not os.path.isdir(run_cwd):
            run_cwd = None
        if run_cwd is None:
            try:
                run_cwd = os.path.join(self.build_folder, "_tmp_run")
                os.makedirs(run_cwd, exist_ok=True)
            except OSError:
                run_cwd = None
        self.run(api_bin, env="conanrun", cwd=run_cwd)
        self.run(write_bin, env="conanrun", cwd=run_cwd)
        marker = {
            "executed": True,
            "passed": True,
            "command": "%s && %s" % (api_bin, write_bin),
            "discovered": 2,
            "passedCount": 2,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
