#!/usr/bin/env python3
"""Conan consumer test for libaxc 0.3.7."""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv


class LibaxcTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # readonly_tmp: /tmp is read-only on the farm; reuse the HMBS
        # injected writable TMPDIR when usable, else fall back to a
        # build-folder tmp dir. Only the tmp root is redirected.
        for key in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(key)
            if cand and os.path.isdir(cand):
                try:
                    probe = os.path.join(cand, ".hmbs_write_probe")
                    with open(probe, "w") as f:
                        f.write("ok")
                    os.remove(probe)
                    tmp = cand
                    break
                except Exception:
                    continue
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(tmp, exist_ok=True)
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass
        return tmp

    def _probe_compiler(self, cmd):
        # Version probe: existence + X_OK is not enough (a stale conf
        # path can exist yet fail at exec). Run --version instead.
        try:
            proc = subprocess.run(
                [cmd, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _resolve_verified(self, conf_key, default):
        try:
            compiler_exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compiler_exes = {}
        candidate = compiler_exes.get(conf_key, default) or default
        seen = []
        for cand in (
            candidate,
            shutil.which(os.path.basename(candidate))
            if candidate
            else None,
            shutil.which(default),
            "/data/service/hnp/bin/%s" % default,
        ):
            if cand and cand not in seen:
                seen.append(cand)
        for cand in seen:
            if os.path.isfile(cand) or shutil.which(cand):
                if self._probe_compiler(cand):
                    return cand
        # Last resort: basename on PATH even without successful probe,
        # so the error (if any) comes from the real driver, not a stale
        # absolute conf path.
        for cand in seen:
            if cand:
                return cand
        return candidate or default

    def _patch_toolchain_compilers(self, cc, cxx):
        # CMakeToolchain emits SET(CMAKE_C/CXX_COMPILER ... FORCE) from
        # the profile conf. When that conf path is stale, cache_variables
        # alone may not win; rewrite the generated toolchain file lines
        # in place so try_compile uses the version-probed drivers.
        roots = [self.generators_folder]
        try:
            roots.append(os.path.join(self.build_folder, "build"))
        except Exception:
            pass
        targets = []
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _d, files in os.walk(root):
                for fn in files:
                    if fn in ("conan_toolchain.cmake", "toolchain.cmake"):
                        targets.append(os.path.join(dirpath, fn))
        if not targets:
            cand = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(cand):
                targets.append(cand)
        for path in targets:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                orig = text
                text = re.sub(
                    r'set\s*\(\s*CMAKE_C_COMPILER\s+[^)]*\)',
                    'set(CMAKE_C_COMPILER "%s")' % cc,
                    text,
                    flags=re.IGNORECASE,
                )
                text = re.sub(
                    r'set\s*\(\s*CMAKE_CXX_COMPILER\s+[^)]*\)',
                    'set(CMAKE_CXX_COMPILER "%s")' % cxx,
                    text,
                    flags=re.IGNORECASE,
                )
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info("patched toolchain compilers: %s" % path)
            except Exception as exc:
                self.output.warning("toolchain patch skipped for %s: %s" % (path, exc))

    def generate(self):
        buildenv = VirtualBuildEnv(self)
        buildenv.generate()
        tmpdir = self._ensure_writable_tmp()
        cc = self._resolve_verified("c", "clang")
        cxx = self._resolve_verified("cpp", "clang++")
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        self.output.info("test_package compilers: CC=%s CXX=%s" % (cc, cxx))
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        shell = os.environ.get("SHELL", "/bin/sh")
        if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
            env.define("SHELL", shell)
            env.define("CONFIG_SHELL", shell)
        env.vars(self, scope="build").save_script("conanaxctestbuild")
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_C_COMPILER"] = cc
        tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()
        self._patch_toolchain_compilers(cc, cxx)

    def build(self):
        tmpdir = self._ensure_writable_tmp()
        cc = os.environ.get("CC") or self._resolve_verified("c", "clang")
        cxx = os.environ.get("CXX") or self._resolve_verified("cpp", "clang++")
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self._patch_toolchain_compilers(cc, cxx)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross build: consumer execution skipped")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_axc")
        self.run('"%s" context' % test_bin, env="conanrun", cwd=self.build_folder)
        self.run('"%s" buf' % test_bin, env="conanrun", cwd=self.build_folder)
        self.output.info(
            'HMBS_TEST_PACKAGE_RESULT='
            '{"executed":true,"passed":true,"command":"test_axc context buf",'
            '"discovered":2,"passedCount":2}'
        )
        self._reemit_upstream_marker()

    def _reemit_upstream_marker(self):
        # 缓存命中复发：当 Conan 复用主包二进制时 build() 被跳过，
        # 其 HMBS_UPSTREAM_TEST_RESULT 不打印，当轮即判 incomplete。
        # 此处复发 package/res/hmbs_upstream.json（build() 真实执行
        # 的 make test 数字），不重新定义测试口径（librist 0.2.18 /
        # libsieve 先例）。缺失仅告警，不伪造。
        import json as _json
        _cand = None
        try:
            _dep = self.dependencies["libaxc"]
            _pf = getattr(_dep, "package_folder", None)
            if _pf:
                _cand = os.path.join(_pf, "res", "hmbs_upstream.json")
        except Exception:
            _cand = None
        try:
            if _cand and os.path.isfile(_cand):
                with open(_cand, "r", encoding="utf-8") as _fh:
                    _data = _json.load(_fh)
                if isinstance(_data, dict) and _data.get("discovered"):
                    _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                             + _json.dumps(_data, ensure_ascii=False))
                    print(_umsg, flush=True)
                    try:
                        self.output.info(_umsg)
                    except Exception:
                        pass
                    return
            self.output.warning(
                "persisted hmbs_upstream.json missing; "
                "upstream evidence only available on fresh build")
        except Exception as _e:
            self.output.warning("upstream re-emit failed: %r" % (_e,))
