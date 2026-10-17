#!/usr/bin/env python3
"""Conan test_package for libjwt3 3.3.3 — 消费者视角验证（L1）。

test.c 真实调用 libjwt3 公开 API：JWKS 载入 → 取 JWK → HS256 签发 →
校验通过 → 篡改签名/篡改 payload/换密钥/非法令牌/claim 策略不符 等负样本
必须失败，共 20+ 项检查，不引入 libcheck。

test_ohos.c 覆盖 OHOS 平台特有语义：SONAME 加载、DT_SONAME/DT_NEEDED、
4 个 CLI 工具经 Conan bindirs 通道可达、/bin/sh 驱动前提。

OHOS 注意（与主配方同因）：
  * 本设备加载器对 LD_LIBRARY_PATH 的遵守不可靠（E505），故 generate() 给测试
    二进制嵌入 RUNPATH，并用 CMAKE_INSTALL_RPATH_USE_LINK_PATH 把链接行上的
    全部 libdir（含 jansson 等传递依赖）自动纳入。
  * conan 的 cmake.build() 会注入 -j<cpu_count>，OHOS/musl 下 make jobserver
    并行 spawn clang 会静默失败（E525/E074），故改 subprocess 直接 `make -j1`。
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class Libjwt3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test.c", "test_ohos.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()   # 提供 conanrun 环境（运行时库路径）
        tc = CMakeToolchain(self)
        # 把被测包的 bindirs（bin/）注入测试程序，用于验证 R38 的 4 个 CLI
        # 工具经 Conan 通道真实可达（Conan 2 的 cpp_info 不向消费者导出包内
        # 绝对路径，故由 test_package 自己从 dependencies 取）。
        bindir = self._ohos_bindir()
        if bindir:
            tc.cache_variables["LIBJWT3_BINDIR"] = bindir
            self.output.info("OHOS test bindir: %s" % bindir)
        if str(self.settings.os) == "OHOS":
            libdirs = self._ohos_libdirs()
            if libdirs:
                rpath = ";".join(libdirs)
                tc.cache_variables["CMAKE_INSTALL_RPATH"] = rpath
                tc.cache_variables["CMAKE_BUILD_RPATH"] = rpath
                tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
                # 链接行上的传递依赖 libdir 一并纳入 RPATH（jansson 等）
                tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = True
                self.output.info("OHOS test RUNPATH dirs: %s" % ":".join(libdirs))
        tc.generate()

    def _tested_package_folder(self):
        for dep in self.dependencies.values():
            pkgdir = dep.package_folder
            if pkgdir and os.path.isdir(pkgdir) and \
                    os.path.basename(pkgdir) and dep.ref.name == "libjwt3":
                return pkgdir
        # 兜底：取依赖里含 include/jwt.h 的包
        for dep in self.dependencies.values():
            pkgdir = dep.package_folder
            if pkgdir and os.path.isfile(os.path.join(pkgdir, "include", "jwt.h")):
                return pkgdir
        return ""

    def _ohos_bindir(self):
        pkgdir = self._tested_package_folder()
        if not pkgdir:
            return ""
        d = os.path.join(pkgdir, "bin")
        return d if os.path.isdir(d) else ""

    def _ohos_libdirs(self):
        dirs = []
        for dep in self.dependencies.values():
            pkgdir = dep.package_folder
            if not pkgdir or not os.path.isdir(pkgdir):
                continue
            for sub in ("lib", "lib64"):
                d = os.path.join(pkgdir, sub)
                if os.path.isdir(d) and d not in dirs:
                    dirs.append(d)
        return dirs

    def _find_test_binary(self, name):
        for d in list(self.cpp.build.bindirs or []):
            cand = os.path.join(d, name)
            if os.path.isfile(cand):
                return cand
        hits = glob.glob(os.path.join(str(self.build_folder), "**", name),
                         recursive=True)
        for p in hits:
            if os.path.isfile(p) and not os.path.islink(p):
                return p
        return None

    def _sdk_llvm_libdir(self):
        """OHOS SDK 编译器 llvm/lib（含 lld 的 libxml2.so.16 运行时依赖）。"""
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or compilers.get("cpp") or "clang"
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # OHOS：conan 的 cmake.build() 会注入 -j<cpu_count> 并行，make jobserver
        # 在 musl 进程树下并行 spawn clang 会静默失败（同主包 conanfile 的规避）。
        # 改 subprocess 直接 `make -j1` 串行编译（绝对路径），绕开 jobserver 竞态。
        make = shutil.which("make") or "/data/service/hnp/bin/make"
        env = os.environ.copy()
        sdk_ld = self._sdk_llvm_libdir()
        if sdk_ld:
            old_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(p for p in (sdk_ld, old_ld) if p)
            self.output.info("OHOS build LD_LIBRARY_PATH=%s" % env["LD_LIBRARY_PATH"])
        proc = subprocess.run([make, "-j1"], cwd=str(self.build_folder), env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)
        if proc.stdout:
            for line in proc.stdout.splitlines():
                self.output.info(line)
        if proc.returncode != 0:
            raise Exception("test_package make -j1 build failed rc=%d"
                            % proc.returncode)

    def _run_test(self, name, out_path):
        """执行单个测试二进制（失败 self.run 直接抛错），输出重定向后
        解析 ok:/FAIL: 行动态计数（不硬编码用例数）。"""
        binary = self._find_test_binary(name)
        if binary is None:
            raise Exception("%s binary not found in the build tree" % name)
        self.run('"%s" > "%s" 2>&1' % (binary, out_path), env="conanrun")
        ok = fail = 0
        try:
            with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("ok:"):
                        ok += 1
                    elif line.startswith("FAIL:"):
                        fail += 1
        except OSError:
            pass
        if ok == 0:
            raise Exception("%s produced no checks (empty/无效测试)" % name)
        return {"test": name, "ok": ok, "fail": fail}

    def test(self):
        results = []
        if can_run(self):
            if str(self.settings.os) == "OHOS":
                # RUNPATH 是主解析路径，这里再用 LD_LIBRARY_PATH 兜底
                libdirs = self._ohos_libdirs()
                if libdirs:
                    old = os.environ.get("LD_LIBRARY_PATH", "")
                    os.environ["LD_LIBRARY_PATH"] = ":".join(
                        libdirs + ([old] if old else []))
                    self.output.info("OHOS test LD_LIBRARY_PATH=%s"
                                     % os.environ["LD_LIBRARY_PATH"])

            out_dir = os.path.join(str(self.build_folder), "hmbs-testlog")
            os.makedirs(out_dir, exist_ok=True)
            # 1) 消费者功能测试（JWKS→签发→校验→多种篡改负样本）
            results.append(self._run_test(
                "test_libjwt3", os.path.join(out_dir, "test_libjwt3.log")))
            # 2) 鸿蒙（OHOS）平台特有测试：SONAME 加载语义 /
            #    OpenSSL 静态链入 / 4 个 CLI 工具经 bindirs 可达 / /bin/sh 驱动
            results.append(self._run_test(
                "test_ohos", os.path.join(out_dir, "test_ohos.log")))

        discovered = sum(r["ok"] for r in results)
        failed = sum(r["fail"] for r in results)
        passed = bool(results) and failed == 0 and all(
            r["ok"] > 0 for r in results)
        marker = {
            "executed": bool(results),
            "passed": passed,
            "command": "./test_libjwt3 + ./test_ohos",
            "discovered": discovered,
            "passedCount": discovered if passed else 0,
            "tests": results,
            "ohos_specific_tests": [r for r in results if r["test"] == "test_ohos"],
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if not results:
            raise Exception("libjwt3 test consumer is not runnable on this configuration")
        if not passed:
            raise Exception("libjwt3 test_package had failing checks: %s" % marker)
