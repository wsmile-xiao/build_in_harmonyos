import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibkysdkApplicationsConan(ConanFile):
    name = "libkysdk-applications"
    version = "3.0.1.2"
    description = ("kylin SDK based on application level: Qt extension controls, "
                   "window management, process control, display control, D-Bus call, "
                   "gsetting acquisition modules")
    license = "LGPL-3.0"
    homepage = "https://gitee.com/openkylin/libkysdk-applications"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Qt5 基础库与 qmake 工具（同 libngf-qt 先例）
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get_kwargs = {"url": url, "strip_root": True}
                if source_data.get("sha256"):
                    get_kwargs["sha256"] = source_data["sha256"]
                get(self, **get_kwargs)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Fix qt5-qtbase package's qt.conf and .pri files to use the package
        directory instead of the original build directory (relocatability)."""
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as f:
                f.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    f"[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"[Paths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    f"HostPrefix={qtbase_pkg}\n"
                    "Sysroot=\n"
                    "SysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\n"
                    "HostSpec=linux-clang\n"
                )
        build_dir_pattern = re.compile(
            r"(/[^\s]*/\.conan2/p/b/qt5-q[0-9a-f]+/b)"
        )
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(qtbase_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed_content = build_dir_pattern.sub(qtbase_pkg, content)
                if fixed_content != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed_content)

    def build(self):
        apply_conandata_patches(self)
        qtbase = self.dependencies["qt5-qtbase"]
        self._fix_qtbase_paths(qtbase.package_folder)
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException(
                "qt5-qtbase/5.15.2.2 does not provide the required bin/qmake tool"
            )
        build_env = Environment()
        build_env.define("QTDIR", qtbase.package_folder)
        build_env.prepend_path("PATH", os.path.join(qtbase.package_folder, "bin"))
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang kysdk-application.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{self.source_folder}" && make -j{jobs}')

    def package(self):
        src = self.source_folder
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include", "kysdk", "applications")
        # 各模块 .so（qmake 在源码树内构建，产物位于模块目录）
        for module in ("kysdk-qtwidgets", "kysdk-alm", "kysdk-ukenv", "kysdk-widgetutils"):
            copy(self, "*.so*", src=os.path.join(src, module),
                 dst=lib_dir, keep_path=False)
        # 头文件（上游 headers.path = /usr/include/kysdk/applications/）
        copy(self, "*.h", src=os.path.join(src, "kysdk-qtwidgets", "src"),
             dst=inc_dir, keep_path=False)
        copy(self, "*.h", src=os.path.join(src, "kysdk-alm", "src"),
             dst=inc_dir, keep_path=False)
        copy(self, "*.h", src=os.path.join(src, "kysdk-ukenv", "src"),
             dst=inc_dir, keep_path=False)
        copy(self, "*.h", src=os.path.join(src, "kysdk-widgetutils", "src"),
             dst=inc_dir, keep_path=False)
        # HMDFS 按目录继承属主且裁剪 other 权限位（755→750）：测试/消费者阶段的
        # app uid（20020101）跨 uid 读取恒 EACCES（CI #49631-#49701 实证），
        # 且非属主 chown/chmod 静默无效；此处以属主（构建上下文）补 chmod 755，
        # 使产物对任意 app uid 可读可加载（dlopen 实测见 test_package build()）。
        # 若文件系统仍裁剪，测试探针会如实 FAIL（不伪造通过）。
        for root, _, files in os.walk(lib_dir):
            for f in files:
                if f.endswith(".so") or f.endswith(".so.5"):
                    p = os.path.join(root, f)
                    try:
                        os.chmod(p, 0o755)
                    except OSError as e:
                        self.output.warning(f"chmod {p}: {e}")

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = [
            "kysdk-qtwidgets", "kysdk-alm", "kysdk-ukenv", "kysdk-widgetutils",
        ]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core", "qt5-qtbase::Qt5Gui", "qt5-qtbase::Qt5Widgets",
            "qt5-qtbase::Qt5DBus", "qt5-qtbase::Qt5Sql", "qt5-qtbase::Qt5Svg",
            "qt5-qtbase::Qt5Network",
        ]
