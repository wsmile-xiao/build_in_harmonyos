#!/usr/bin/env python3
"""Conan test_package for soplex 7.1.6 — Conan L1 consumer test.

Builds a small LP through the public SoPlex C++ API, solves it, and verifies
the objective value. This proves headers, static lib linking and the solver
runtime work for a downstream consumer (R34: must call the library API).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import can_run


class SoplexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # soplex 公开头透传 gmp/zlib 头（soplex.h -> rational.h -> gmp.h，
        # io 类经 gzread -> zlib.h）：test_package 须显式 requires，CMakeDeps
        # 才会生成对应 cmake 配置并传递 include 路径（libqalculate 先例注释
        # 同款，否则 gmp.h not found）。版本与主包 requirements 对齐。
        self.requires("gmp/6.3.0.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 与主包同款编译器路径回退：test_package 的 toolchain 同样会嵌入
        # profile 钉死的 /data/service/hnp/bin/clang(++) 死路径（lz4 实证故障点
        # 就在 test_package 的 cmake.configure）。conf 路径存在则沿用，仅缺失
        # 时回退 PATH 发现的 clang/clang++。
        tc = CMakeToolchain(self)
        try:
            _exes = self.conf.get("tools.build:compiler_executables") or {}
        except Exception:
            _exes = {}
        _cc_conf = _exes.get("c", "") if isinstance(_exes, dict) else ""
        _cxx_conf = _exes.get("cpp", "") if isinstance(_exes, dict) else ""
        if _cc_conf and not os.path.isfile(_cc_conf):
            _cc = shutil.which("clang") or shutil.which("cc") or ""
            if _cc:
                tc.variables["CMAKE_C_COMPILER"] = _cc
        if _cxx_conf and not os.path.isfile(_cxx_conf):
            _cxx = shutil.which("clang++") or shutil.which("c++") or ""
            if _cxx:
                tc.variables["CMAKE_CXX_COMPILER"] = _cxx
        tc.generate()

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _ensure_writable_tmp(self):
        # 真机 /tmp 只读：按 TMPDIR/TMP/TEMP -> $HOME/tmp -> build_folder/hmbs-tmp
        # 顺序建目录加写探针，命中后导出（libsedml 先例改编）。
        candidates = [os.environ.get("TMPDIR"), os.environ.get("TMP"),
                      os.environ.get("TEMP")]
        home = os.environ.get("HOME")
        if home:
            candidates.append(os.path.join(home, "tmp"))
        candidates.append(os.path.join(self.build_folder, "hmbs-tmp"))
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
            except OSError:
                continue
            for key in ("TMPDIR", "TMP", "TEMP", "GOTMPDIR"):
                os.environ[key] = cand
            return cand
        return self.build_folder

    def test(self):
        if can_run(self):
            self._ensure_writable_tmp()
            # 真机 shell：HMBS 注入 SHELL=/bin/sh，真机 capability shell 亦为 /bin/sh；
            # 预检曾出现 /data/service/hnp/bin/bash 不可访问，故按
            # CONFIG_SHELL -> SHELL -> /bin/sh 回退，不再硬编码单一 bash 路径。
            shell = (os.environ.get("CONFIG_SHELL")
                     or os.environ.get("SHELL")
                     or "/bin/sh")
            # 真机 /tmp 只读：测试工作区与临时根目录一律用 HMBS 注入的可写
            # TMPDIR/TMP/TEMP（回退 build_folder/.tmp），仅替换根目录。
            tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                      or os.environ.get("TEMP")
                      or os.path.join(self.build_folder, ".tmp"))
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                tmpdir = self.build_folder
            log = os.path.join(self.build_folder, "hmbs_test_package.log")
            # 消费者用例：公开 API 构建并求解 LP，校验最优目标值
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_soplex")
            # 鸿蒙专项测试：aarch64-ohos 平台属性（ELF e_machine）+ 公开 API 求解
            ohos_path = os.path.join(self.cpp.build.bindirs[0], "test_ohos_soplex")
            cmd = ("TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" \"%s\" -c '\"%s\"; echo \"EXIT1=$?\"; "
                   "\"%s\"; echo \"EXIT2=$?\"' > \"%s\" 2>&1"
                   % (tmpdir, tmpdir, tmpdir, shell, bin_path, ohos_path, log))
            self.run(cmd, env="conanrun", ignore_errors=True)
            out = ""
            try:
                with open(log, "r", encoding="utf-8", errors="replace") as f:
                    out = f.read()
            except OSError:
                out = ""
            tail = "\n".join(out.splitlines()[-12:]) if out else "(empty test log)"
            self.output.info("soplex test_package tail:\n" + tail)
            ok1 = ("test_soplex: PASS" in out) and ("EXIT1=0" in out)
            ok2 = ("test_ohos_soplex: ALL PASS" in out) and ("EXIT2=0" in out)
            passed_count = (1 if ok1 else 0) + (1 if ok2 else 0)
            ok = (passed_count == 2)
            marker = {
                "executed": True,
                "passed": ok,
                "command": "test_soplex + test_ohos_soplex via %s" % shell,
                "discovered": 2,
                "passedCount": passed_count,
            }
            line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            self.output.info(line)
            print(line, flush=True)
            # 缓存命中轮复发上游证据：build() 已把 marker 持久化到包内 res/。
            try:
                res = os.path.join(
                    self.dependencies["soplex"].package_folder, "res", "hmbs_upstream.json")
                if os.path.isfile(res):
                    with open(res, "r", encoding="utf-8") as f:
                        up = json.load(f)
                    self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        up, ensure_ascii=False))
            except Exception as exc:
                self.output.warning("re-emit upstream marker skipped: %s" % exc)
            if not ok:
                raise RuntimeError(
                    "soplex test_package failed (ok1=%s ok2=%s); see hmbs_test_package.log"
                    % (ok1, ok2))
