#!/usr/bin/env python3
"""Conan test_package — unittest 0.50-62 消费者验证（L1）。

消费者视角验证（真实链接打包产物 libunittest.a + 公共头文件）：test_unittest
注册 8 个用例（断言宏/字符串相等/异常断言/生命周期/嵌套套件聚合/TestPtr
引用语义/radix 开关/ExistingBase 包装），经 UnitTest::Registry 运行。
test() 解析框架确定性汇总行 "Tests finished with N passes and M failures."，
与源码注册数 8 交叉核对后输出 HMBS_TEST_PACKAGE_RESULT；任一失败即抛错。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import load


class UnittestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain 在 generate() 内手动实例化（含编译器回退逻辑），
    # 故不在 generators 属性中重复声明（conan 2.x 双重声明即报错）。
    generators = "CMakeDeps"

    # test_unittest.cpp main() 注册的叶子用例数（源码静态可数）
    CONSUMER_TEST_CASES = 8

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 聚合经验 #1 双通道：消费者工具链同步替换不存在的编译器路径。
        # 存在即用，缺失时经 PATH 回退；健康机零改动。
        tc = CMakeToolchain(self)
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        conf_c = conf.get("c")
        conf_cxx = conf.get("cpp")

        def _usable(p):
            return bool(p) and os.path.isfile(p) and os.access(p, os.X_OK)

        cc = conf_c if _usable(conf_c) else shutil.which("clang") or conf_c
        cxx = conf_cxx if _usable(conf_cxx) else shutil.which("clang++") or conf_cxx
        if cc and not _usable(cc):
            cc = None
        if cxx and not _usable(cxx):
            cxx = None
        # 仅当 conf 路径缺失时覆盖工具链变量，不碰其他标志。
        if conf_c and not _usable(conf_c) and cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if conf_cxx and not _usable(conf_cxx) and cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _binary(self, name):
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        raise ConanException("测试可执行文件未找到: %s" % name)

    def _emit_test_package(self, payload):
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(payload)
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        return line

    def _hmbs_sign_one_elf(self, path):
        import shutil as _shutil
        import subprocess as _subp
        try:
            is_ohos = str(self.settings.os) == "OHOS"
        except Exception:
            is_ohos = False
        if not is_ohos:
            return False
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "rb") as _h:
                if _h.read(4) != b"\x7fELF":
                    return False
        except OSError:
            return False
        for _tool in ("/data/service/hnp/bin/llvm-objcopy", _shutil.which("llvm-objcopy") or "llvm-objcopy"):
            try:
                _subp.run([_tool, "--remove-section", ".codesign", path], stdout=_subp.DEVNULL, stderr=_subp.DEVNULL, check=False, timeout=10)
                break
            except Exception:
                continue
        signed = False
        for _tool in ("/data/service/hnp/bin/binary-sign-tool", _shutil.which("binary-sign-tool") or "binary-sign-tool"):
            try:
                _r = _subp.run([_tool, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"], stdout=_subp.PIPE, stderr=_subp.PIPE, check=False, timeout=15)
                if _r.returncode == 0:
                    signed = True
                    break
            except Exception:
                continue
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass
        return signed

    def test(self):
        binary = self._binary("test_unittest")
        try:
            self._hmbs_sign_one_elf(binary)
        except Exception:
            pass
        log = os.path.join(self.build_folder, "consumer-run.log")
        rc = self.run('"%s" > "%s" 2>&1' % (binary, log), ignore_errors=True)
        output = load(self, log)

        # 唯一计数来源：框架确定性汇总行（逐行匹配，禁止字符串数数/算术修补）
        passed = failed = None
        for line in output.splitlines():
            m = re.match(
                r"^Tests finished with (\d+) passes and (\d+) failures\.$",
                line.strip())
            if m:
                passed, failed = int(m.group(1)), int(m.group(2))

        ok = (rc == 0 and passed == self.CONSUMER_TEST_CASES and failed == 0)
        marker = {
            "executed": True,
            "passed": bool(ok),
            "command": "./test_unittest",
            "discovered": self.CONSUMER_TEST_CASES,
            "passedCount": passed if passed is not None else 0,
        }
        self._emit_test_package(marker)
        if not ok:
            raise ConanException(
                "消费者用例未按预期全过（exit code %s, passes=%s, "
                "failures=%s，期望 8/0）：\n%s"
                % (rc, passed, failed, output[-2000:]))
