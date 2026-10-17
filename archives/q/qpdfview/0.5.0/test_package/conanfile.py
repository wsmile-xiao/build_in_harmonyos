import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # **VirtualRunEnv / VirtualBuildEnv 必须一并写上**：显式给 generators 会
    # **替换**（而非追加）conan 的默认集，漏了 VirtualRunEnv 就没有 conanrun
    # 环境，test() 里 env="conanrun" 拿不到 LD_LIBRARY_PATH，表现为编译链接
    # 全过、跑起来报 `Error loading shared library ...`（poppler 实撞）。
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── 编译期 ───────────────────────────────────────────────────────────

    def _qt_include_flags(self):
        """Qt5 头文件：<pkg>/include 与 <pkg>/include/<QtModule> 两层都要。"""
        pkg = self.dependencies["qt5-qtbase"].package_folder
        flags = [f"-I{os.path.join(pkg, 'include')}"]
        for module in ("QtCore", "QtGui", "QtWidgets", "QtXml"):
            flags.append(f"-I{os.path.join(pkg, 'include', module)}")
        return " ".join(flags)

    def _qt_link_flags(self):
        pkg = self.dependencies["qt5-qtbase"].package_folder
        libdir = os.path.join(pkg, "lib")
        libs = ["-lQt5Widgets", "-lQt5Gui", "-lQt5Core", "-lQt5Xml"]
        return f"-L{libdir} " + " ".join(libs) + f" -Wl,-rpath,{libdir}"

    def build(self):
        cc = os.environ.get("CXX", "clang++")
        # 库本体按 profile 的 cppstd 编，测试标准必须跟上，否则 Qt5 头里的
        # C++17 设施（std::optional 等）全报找不到。
        _std = self.settings.get_safe("compiler.cppstd")
        std_flag = ("-std=c++%s" % str(_std).replace("gnu", "")) if _std else ""
        self.run(
            f"{cc} {std_flag} -fPIC test.cpp -o test_probe "
            f"{self._qt_include_flags()} {self._qt_link_flags()}"
        )

    # ── 运行期 ───────────────────────────────────────────────────────────

    def _dep_libdirs(self):
        dirs = []
        for _ref, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                if os.path.isdir(libdir) and libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def _run_prefix(self):
        """运行期环境前缀：多前缀 conan 依赖链必须显式给出全部 lib 目录。

        不能只依赖 conanrun：VirtualRunEnv 生成的 conanrunenv 里 libdirs 可能
        是空的（本仓已记录：shared=False 发布的包 conan 视为静态、不写
        libdirs，但包里确实装了 .so），而链接期的 -Wl,-rpath 也不总起作用。
        症状是编译链接全过、一跑就 `Error loading shared library ...`。
        """
        parts = [f'LD_LIBRARY_PATH="{os.pathsep.join(dict.fromkeys(self._dep_libdirs()))}"']
        parts.append("QT_QPA_PLATFORM=offscreen")
        plugins = []
        for require, dep in self.dependencies.items():
            if not require.ref.name.startswith("qt5-"):
                continue
            candidate = os.path.join(dep.package_folder, "plugins")
            if os.path.isdir(candidate):
                plugins.append(candidate)
        if plugins:
            parts.append(f'QT_PLUGIN_PATH="{os.pathsep.join(plugins)}"')
        fonts = os.path.join(
            self.dependencies["fontconfig"].package_folder, "etc", "fonts"
        )
        if os.path.isdir(fonts):
            parts.append(f'FONTCONFIG_PATH="{fonts}"')
        return " ".join(parts)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return

        pkg = self.dependencies["qpdfview"].package_folder
        bindir = os.path.join(pkg, "bin")

        # ── 1) 包内容完整性（L1e 破坏性负测试依赖这些断言）──
        for path in (
            os.path.join(bindir, "qpdfview"),
            os.path.join(bindir, "libqpdfview_pdf.so"),
            os.path.join(bindir, "libqpdfview_image.so"),
            os.path.join(pkg, "share", "applications", "qpdfview.desktop"),
            os.path.join(pkg, "share", "man", "man1", "qpdfview.1"),
            os.path.join(
                pkg, "share", "icons", "hicolor", "scalable", "apps", "qpdfview.svg"
            ),
        ):
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"包内缺少文件: {path}")

        prefix = self._run_prefix()

        # ── 2) 可执行文件冒烟：--help 必须能跑起来（R40：GUI 冒烟）──
        self.run(f'{prefix} "{os.path.join(bindir, "qpdfview")}" --help', env="conanrun")

        # ── 3) 插件端到端：dlopen + 真实加载/渲染 PDF ──
        probe = os.path.join(self.build_folder, "test_probe")
        pdf = os.path.join(self.source_folder, "test.pdf")
        self.run(
            f'{prefix} "{probe}" "{bindir}" libqpdfview_pdf.so "{pdf}"',
            env="conanrun",
        )
