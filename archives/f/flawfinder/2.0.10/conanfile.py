#!/usr/bin/env python3
"""Conan recipe — flawfinder 2.0.10（C/C++ 源码安全缺陷静态扫描工具）

flawfinder 是纯 Python 命令行工具（flawfinder 单文件，2.0.10 无 .py
后缀），零第三方依赖（仅标准库），OHOS 系统 python3 可用（R36 满足）。
无编译：直接安装 flawfinder 为 bin/flawfinder。

上游 setup.py 打包 man page 引用 flawfinder.1.gz（源码仅 .1 未压缩），
wheel 构建失败 → 绕开 setuptools，直接复制脚本 + 替换 shebang
（同 rpl/markdown/2.0.19 模式）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches
from conan.tools.layout import basic_layout


class FlawfinderConan(ConanFile):
    name = "flawfinder"
    version = "2.0.10"
    description = "flawfinder — C/C++ source code static security scanner（纯 Python）"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/david-a-wheeler/flawfinder"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile 要求四项 settings（L0p 门禁）；纯 Python 但需与 profile 对齐
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯 Python 脚本，无编译
        pass

    def package(self):
        src = self.source_folder
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        # shebang #!/usr/bin/env python → python3（系统无 python 别名，仅 python3），
        # 写新文件 + chmod（绕开 HMDFS copy 丢执行位）；2.0.10 脚本名为 flawfinder
        with open(os.path.join(src, "flawfinder"), "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("#!/usr/bin/env python", "#!/usr/bin/env python3", 1)
        dst = os.path.join(bin_dst, "flawfinder")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(dst, 0o755)
        # License
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
