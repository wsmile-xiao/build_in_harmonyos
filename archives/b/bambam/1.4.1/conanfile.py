#!/usr/bin/env python3
"""Conan recipe — bambam 1.4.1（纯 Python pygame 幼儿键盘敲击/涂鸦游戏）。

bambam（porridge/bambam）是纯 Python pygame 幼儿键盘游戏：单文件模块
bambam.py（804 行，无任何 C/C++ 源）+ data/ 图片声音 + extensions/（yaml
声明式扩展）+ 上游 unittest（test_e2e_test.py 4 用例，不依赖 pygame）。
Python 类适配（R47 用户决策覆盖：lang-preflight 判 python/env_unsupported，
按 pyjson5/alot/blendsel 纯脚本包先例，以 python/pygame 解释器与图形栈为
运行时依赖交付可安装可验证的 Conan 包；决策与依据见 notes.md）。

适配要点（参考 archives/p/pyjson5/0.15.0 纯 Python 无编译打包范式）：
- 无编译：build() 仅 apply_conandata_patches（预期无补丁，R34 由
  test_package 实质执行保证）
- 解释器/图形栈：requires python/3.12.9 + pygame/2.6.1（ohpcd 制品仓已发布）
- 布局：lib/python3.12/site-packages/bambam.py（单文件模块，import bambam
  可用）+ share/bambam/{data,extensions}（run() 自动发现
  <prefix>/share/bambam/data）+ bin/bambam 包装器（shebang env python3，
  相对路径把 site-packages 前置进 sys.path）
- R38：产物含可执行 CLI（bin/bambam）→ 软件级 commands.json 声明
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


class BambamConan(ConanFile):
    name = "bambam"
    version = "1.4.1"
    description = "A keyboard mashing and doodling game for babies and toddlers (pure Python, pygame)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/porridge/bambam"
    url = "https://github.com/porridge/bambam"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python/3.12.9")
        self.requires("pygame/2.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无编译（纯 Python 只装不编，R34 由 test_package 实质执行保证）
        apply_conandata_patches(self)

    def package(self):
        # 单文件模块 bambam.py → site-packages（PYTHONPATH 导入路径）
        copy(self, "bambam.py",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "python3.12",
                              "site-packages"),
             keep_path=False)
        # 资源：data/ 与 extensions/ → share/bambam（run() 自动发现）
        copy(self, "*",
             src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(self.package_folder, "share", "bambam", "data"))
        copy(self, "*",
             src=os.path.join(self.source_folder, "extensions"),
             dst=os.path.join(self.package_folder, "share", "bambam", "extensions"))
        # CLI 包装器：bin/bambam（等价上游 bin 入口，shebang env python3）
        wrapper = (
            "#!/usr/bin/env python3\n"
            "\"\"\"bambam - 幼儿键盘敲击与涂鸦游戏（pygame 纯 Python CLI）。\"\"\"\n"
            "import os\n"
            "import sys\n"
            "\n"
            "_pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
            "_site = os.path.join(_pkg_dir, 'lib', 'python3.12', 'site-packages')\n"
            "if _site not in sys.path:\n"
            "    sys.path.insert(0, _site)\n"
            "\n"
            "from bambam import main  # noqa: E402\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(main())\n"
        )
        save(self, os.path.join(self.package_folder, "bin", "bambam"), wrapper)
        # save() 默认无执行位；CLI 必须可执行（R38/L0k，直接运行）
        os.chmod(os.path.join(self.package_folder, "bin", "bambam"), 0o755)
        # 许可证（上游为 COPYING 文件，GPL-3.0）
        copy(self, "COPYING", src=self.source_folder,
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
