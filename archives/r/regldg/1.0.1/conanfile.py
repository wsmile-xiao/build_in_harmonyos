#!/usr/bin/env python3
"""Conan 2 recipe — regldg 1.0.1（Patrick Cronin，正则表达式字典生成器，零依赖）.

regldg 是单文件 C 命令行工具：读取正则表达式，输出所有匹配的文本字符串
（word list / dictionary 生成）。上游构建形态为纯 Makefile（无 configure、
无 install、无 check/test 目标）：`make` 直出单二进制 `regldg`，`bin.install`
即完成安装（Homebrew 同型处理）。

OHOS 适配要点：
- 编译器从 `tools.build:compiler_executables` 取（R33：CI 上 $CC 为空），
  以 make 命令行变量覆盖上游写死的 `COMPILE=cc ...` / `LINK=gcc ...`。
- patches/0001 复用 Homebrew homebrew-core 的 Clang 修复
 （COMPILE 加 `-Wno-int-conversion`，新版 Clang 对上游旧式 int 转换告警），
  非自研补丁。
- 上游无任何自动化测试（Makefile 仅 all/clean 目标，见
  test_package/MANIFEST.yml 审计），build() 内仅做 Homebrew 等价 smoke
  （`./regldg test`）自证二进制可运行；功能断言由 test_package 承载。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get


class RegldgConan(ConanFile):
    name = "regldg"
    version = "1.0.1"
    description = "Regular expression grammar language dictionary generator"
    license = "MIT"
    homepage = "https://regldg.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("regex", "cli", "dictionary-generator", "text-processing")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # regldg 是单文件 CLI 工具（无库产物），无 shared/static 选项（R26 不适用：
    # 非系统同名库，无 .so 污染风险）。

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _resolve_cc(self):
        # 真机 clang 已从 /data/service/hnp/bin 迁移到 ~/usr/local/bin，
        # 而共享 profile 仍指向旧绝对路径。配置路径存在才用，否则按
        # PATH 与用户目录回退（zydis/4.1.1 已验证模式），避免 make 报
        # "No such file or directory"。
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables",
                default={}, check_type=dict) or {}
        except Exception:
            executables = {}
        configured = executables.get("c")
        if configured and os.path.isfile(configured):
            return configured
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in ("clang", "cc", "gcc"):
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or "clang"

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器从 conan conf 取（CI 上 $CC 为空），配置路径失效时
        # 回退到 PATH/~/usr/local/bin 的真实编译器并打印诊断。
        cc = self._resolve_cc()
        self.output.info("HMBS diag resolved cc=%s" % cc)

        src = str(self.source_folder)
        # R9: -j1。上游 Makefile 写死 COMPILE=cc / LINK=gcc，以命令行变量覆盖
        # 为 OHOS 工具链（make 命令行变量优先级高于 Makefile 内定义）。
        self.run(f'make COMPILE="{cc} -O2 -Wall -Wno-int-conversion -g -c"'
                 f' LINK="{cc} -O2 -Wall -g -lm" -j1',
                 cwd=src, env="conanbuild")

        # 层1 smoke（Homebrew `test do system bin/"regldg", "test"` 等价）：
        # 正则 "test" 为有限语言，输出单个词 "test"，自证二进制可运行。
        self.run("./regldg test", cwd=src, env="conanbuild")

    def package(self):
        src = str(self.source_folder)
        pkg = str(self.package_folder)
        copy(self, "regldg", src=src, dst=os.path.join(pkg, "bin"))
        copy(self, "LICENSE", src=src, dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        # 命令行工具：为下游 VirtualRunEnv 暴露 bin/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
