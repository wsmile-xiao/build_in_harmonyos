#!/usr/bin/env python3
"""Conan recipe for rl-accel 0.9.1 — ReportLab 加速扩展（CPython C 扩展模块）。

上游交付物只有**一个** C 扩展模块：``src/_rl_accel.c``（1342 行 C，setup.py:
``Extension("_rl_accel", sources=["src/_rl_accel.c"])``、``packages=[]``），
发布到 PyPI 的 wheel 内也只有一个 ``_rl_accel.abi3.so``（cp37-abi3，按 Python 3.7
有限 API 编译）。本配方按同一宏（``Py_LIMITED_API=0x03070000``）与同一产物名
复现该扩展。

【语言判定说明 (R47)】
  lang-preflight 依据 ``pyproject.toml/setup.py`` 与文件名计数（python:3、c:1）
  把本包判为 python。但按 R47 附录 D.4 边界规则「辅助脚本（构建脚本是 python
  等）不算主体语言」，本包主体是唯一编译产物 ``src/_rl_accel.c``，setup.py 属
  构建脚本、tests/*.py 属上游测试脚本，均为辅助脚本。故按主库主体判为 c/cpp
  （c↔cpp 兼容族）继续 conan 适配主流程，依据见 knowledge 中
  ``DRAFT-cmsis-dsp-*-lang-preflight-pyproject-python-misdetect`` 与
  ``DRAFT-exr_image-*-lang-preflight-aux-manifest`` 的
  ``main-body-first-then-compat-family`` 结论。

【依赖】
  · python/3.12.9 —— 提供 Python.h 与 libpython3.12.so。musl 不把 Python 符号
    导出到全局符号表，扩展必须显式 ``-lpython3.12``（NEEDED 里没有 libpython
    时 import 会因符号解析失败而失败）。

【构建】
  直接调 clang 编 ``src/_rl_accel.c``（等价上游 ``setup.py build_ext``），
  不依赖 setuptools（ohpcd 无 setuptools 制品，按 PF4 不写成 tool_requires）。

【测试】
  上游 tests/ 下 2 个可执行测试入口（testcs.py / testrc.py）在 build() 内用
  python 依赖的解释器**真实执行**并校验其输出（R51）；test_package 另做消费者
  视角的真实 API 校验（R34）与一项鸿蒙专项测试。
"""
import os
import shlex
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# OHOS 代码签名工具（HNP 自带；clang 产出的 ELF 通常已自带 .codesign，
# 仅在缺失时兜底补签）
SIGNER = "/data/service/hnp/bin/binary-sign-tool"
OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"

# 上游 tests/ 下的 2 个测试入口及其必须出现的输出标记（R51 真实执行 + 校验）
UPSTREAM_TESTS = (
    ("testcs.py", "calcChecksum(b\"Hello cruel world!\")=142323306"),
    ("testrc.py", None),  # 输出无固定标记；以「无 !!!!! 且两行引用计数一致」校验
)


class RlAccelConan(ConanFile):
    name = "rl-accel"
    version = "0.9.1"
    description = ("Accelerator extension module for the ReportLab Toolkit "
                   "(CPython C extension, Python 3.7 limited API)")
    license = "BSD-3-Clause"
    homepage = "http://www.reportlab.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 产物是 CPython 扩展模块（.so）；conan 2 的 library 类型要求声明 shared。
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    _python_version = "3.12"
    # 上游 setup.py 的 py_limited_kwds：CPython 3.7 有限 API（wheel 标签 cp37-abi3）
    _py_limited_api = "0x03070000"
    # 上游 wheel 内扩展文件名即 _rl_accel.abi3.so（有限 API 产物名）
    _module_file = "_rl_accel.abi3.so"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("python/3.12.9")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # conandata.yml 的 patches 为空（未改动上游源码）；保留调用以维持
        # 配方结构与补丁管线一致。
        apply_conandata_patches(self)

    # ---------------------------------------------------------------- helpers
    def _site_dir(self):
        return os.path.join(self.package_folder, "lib",
                            "python" + self._python_version, "site-packages")

    def _compilers(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return (compilers.get("c") or "clang",
                compilers.get("cpp") or "clang++")

    @staticmethod
    def _has_codesign_section(path):
        """ELF 里是否真有 ``.codesign`` 段（纯 Python 解析段名表）。

        OHOS 沙箱 dlopen 强校验该段；缺失时报的是极易误导的
        ``Permission denied``（看起来像权限问题）。故打包后**实测**该段，
        不依赖签名工具的输出（binary-sign-tool 可能打印 success 而未落地）。
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return False  # 非 64 位小端 ELF
        try:
            e_shoff, = struct.unpack_from("<Q", data, 0x28)
            e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3a)
            if not e_shoff or not e_shnum:
                return False
            strtab_off, = struct.unpack_from(
                "<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18)
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                name_off, = struct.unpack_from("<I", data, off)
                end = data.index(b"\0", strtab_off + name_off)
                if data[strtab_off + name_off:end] == b".codesign":
                    return True
        except (struct.error, ValueError, IndexError):
            return False
        return False

    def _ensure_codesign(self, so_path):
        """确保扩展带 .codesign 段（缺失才兜底签名）。"""
        if self._has_codesign_section(so_path):
            self.output.info(f"{os.path.basename(so_path)} carries .codesign")
            return
        if not os.path.isfile(SIGNER):
            self.output.warning(
                f"{so_path} has no .codesign section and {SIGNER} is absent; "
                "the extension may fail to dlopen in the OHOS sandbox (E212)")
            return
        if os.path.isfile(OBJCOPY):
            subprocess.run([OBJCOPY, "--remove-section", ".codesign", so_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        res = subprocess.run(
            [SIGNER, "sign", "-inFile", so_path, "-outFile", so_path,
             "-selfSign", "1"], capture_output=True, text=True)
        if res.returncode == 0:
            os.chmod(so_path, 0o755)  # 签名后权限归零
        if not self._has_codesign_section(so_path):
            raise ConanException(
                "binary-sign-tool ran but the extension still has no .codesign "
                f"section, so it cannot be dlopened on OHOS: {so_path} "
                f"(signer rc={res.returncode}, {(res.stderr or '')[-200:]})")

    # ------------------------------------------------------------------ build
    def _run_upstream_tests(self, py_exe, py_lib):
        """在 build() 内真实执行上游 tests/ 的两个测试入口并校验输出（R51）。

        两个脚本本身只 print 不 assert，故这里按「退出码 + 关键输出标记」校验，
        避免把"没跑"或"跑了但结果错"记为通过。
        """
        tests_dir = os.path.join(self.source_folder, "tests")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [self.build_folder] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [py_lib] + [p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p])
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        report = os.path.join(self.build_folder, "upstream-tests.log")
        lines = []
        for fname, marker in UPSTREAM_TESTS:
            script = os.path.join(tests_dir, fname)
            if not os.path.isfile(script):
                raise ConanException(
                    f"upstream test entry missing: {script} (R51: refusing to "
                    "report a pass without running the upstream tests)")
            res = subprocess.run([py_exe, script], cwd=self.source_folder,
                                 env=env, capture_output=True, text=True,
                                 timeout=600)
            out = (res.stdout or "") + (res.stderr or "")
            lines.append(f"===== {fname} (exit={res.returncode}) =====\n{out.strip()}")
            if res.returncode != 0:
                raise ConanException(
                    f"upstream test {fname} failed (exit {res.returncode}):\n"
                    + out.strip()[-800:])
            if marker and marker not in out:
                raise ConanException(
                    f"upstream test {fname} ran but its expected output "
                    f"({marker!r}) is missing:\n" + out.strip()[-800:])
            if fname == "testrc.py":
                # 引用计数一致性：两行行首数字序列必须完全相同，且无变更告警
                nums = [ln for ln in out.splitlines() if ln.strip().startswith("[")]
                if "!!!!! reference counts changed !!!!!" in out or len(nums) != 2 \
                        or nums[0] != nums[1]:
                    raise ConanException(
                        "upstream test testrc.py reported a reference-count "
                        "mismatch:\n" + out.strip()[-800:])
            self.output.info(f"upstream test {fname}: PASS (exit 0)")

        with open(report, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        self.output.info(f"upstream tests report: {report}")

    def build(self):
        csrc = os.path.join(self.source_folder, "src", "_rl_accel.c")
        if not os.path.isfile(csrc):
            raise ConanException(f"upstream C source missing: {csrc}")

        py_root = self.dependencies["python"].package_folder
        py_inc = os.path.join(py_root, "include",
                              "python" + self._python_version)
        py_lib = os.path.join(py_root, "lib")
        py_exe = os.path.join(py_root, "bin", "python3.12")
        if not os.path.isfile(os.path.join(py_inc, "Python.h")):
            raise ConanException(f"Python.h missing under {py_inc}")
        if not os.path.isfile(py_exe):
            raise ConanException(f"python interpreter missing: {py_exe}")

        cc, _ = self._compilers()
        out = os.path.join(self.build_folder, self._module_file)
        # 等价上游 setup.py build_ext：同一 C 源、-shared -fPIC、
        # Py_LIMITED_API 与 abi3 产物名；musl 下必须显式 -lpython3.12。
        argv = [cc, "-shared", "-fPIC", "-O2",
                "-DPy_LIMITED_API=" + self._py_limited_api,
                "-I" + py_inc, csrc, "-o", out,
                "-L" + py_lib, "-lpython3.12"]
        self.output.info("build: " + " ".join(shlex.quote(a) for a in argv))
        self.run(" ".join(shlex.quote(a) for a in argv), cwd=self.build_folder)
        if not os.path.isfile(out):
            raise ConanException("build produced no _rl_accel extension module")

        self._run_upstream_tests(py_exe, py_lib)

    # ---------------------------------------------------------------- package
    def package(self):
        site = self._site_dir()
        os.makedirs(site, exist_ok=True)
        copy(self, self._module_file, src=self.build_folder, dst=site)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        installed = os.path.join(site, self._module_file)
        if not os.path.isfile(installed):
            raise ConanException(f"extension missing from package: {installed}")
        self._ensure_codesign(installed)

    def package_info(self):
        self.cpp_info.libs = []
        site = self._site_dir()
        # 消费方与 test_package 自动获得导入路径（只 print 不声明会让消费方报
        # No module named '_rl_accel'）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
