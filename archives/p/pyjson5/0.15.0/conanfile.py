#!/usr/bin/env python3
"""Conan recipe — pyjson5 0.15.0（纯 Python JSON5 解析/序列化库 + pyjson5 CLI）。

pyjson5 官方包名 json5：纯 Python（官方 tag v0.15.0 源码 30 文件、13 个 .py、
0 个 C/C++ 源文件），setuptools 打包（pyproject.toml，packages=["json5"]），
附带 pyjson5 命令行工具（console entry point json5.tool:main）。Python 类
适配（R47 python_class_task，无编译、无补丁）。

适配要点（knowledge/operations/build-systems.md §12 无构建/打包族）：
- 无编译：build() 不定义（不伪造编译日志，R34 由 test_package 实质执行保证）
- 解释器：requires python/3.12.9（ohpcd 制品仓已发布二进制，CI 可复现；
  版本与设备/HMBS python3 对齐）
- 布局：lib/python3.12/site-packages/json5/（runenv PYTHONPATH 直接导入）
  + bin/pyjson5（console script 等价包装，shebang env python3，内部按相对
  路径把 site-packages 前置进 sys.path，不依赖外部 PYTHONPATH 预置）
- R38：产物含可执行 CLI（bin/pyjson5）→ 软件级 commands.json 声明
- R26 不适用（无系统同名库冲突）；R32 不适用（无 C 编译 settings.os 分支）
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class Pyjson5Conan(ConanFile):
    name = "pyjson5"
    version = "0.15.0"
    description = "A Python implementation of the JSON5 data format (pyjson5)"
    license = "Apache-2.0"
    homepage = "https://github.com/dpranke/pyjson5"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python/3.12.9")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译（纯 Python 只装不编，R34 由 test_package 实质执行保证）
        apply_conandata_patches(self)

    def package(self):
        # 纯 Python 包 json5/ → site-packages（PYTHONPATH 导入路径）
        copy(self, "*",
             src=os.path.join(self.source_folder, "json5"),
             dst=os.path.join(self.package_folder, "lib", "python3.12",
                              "site-packages", "json5"))
        # console script 等价：bin/pyjson5（等价 setuptools entry point）
        wrapper = (
            "#!/usr/bin/env python3\n"
            "\"\"\"pyjson5 - JSON5 命令行工具（pyjson5 包 console entry point）。\"\"\"\n"
            "import os\n"
            "import sys\n"
            "\n"
            "_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
            "_site = os.path.join(_pkg_dir, 'lib', 'python3.12', 'site-packages')\n"
            "if _site not in sys.path:\n"
            "    sys.path.insert(0, _site)\n"
            "\n"
            "from json5.tool import main  # noqa: E402\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(main())\n"
        )
        save(self, os.path.join(self.package_folder, "bin", "pyjson5"), wrapper)
        # save() 默认无执行位；CLI 必须可执行（R38/L0k，直接运行）
        os.chmod(os.path.join(self.package_folder, "bin", "pyjson5"), 0o755)
        # LICENSE
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # 无编译产物 → 单一 package_id

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # 运行期环境：PYTHONPATH 指向 site-packages，PATH 含 bin
        site = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        self.runenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
