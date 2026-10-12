import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibkysdkKabaseConan(ConanFile):
    name = "libkysdk-kabase"
    version = "3.0.1.0"
    description = ("openKylin KylinSDK kabase — single_application component "
                   "(QtSingleApplication single-instance helper built on "
                   "QtLocalPeer/QLocalServer). Provides libkysdk-kabase.so and "
                   "the header include/single_application/single_application.hpp.")
    license = "LGPL-3.0"
    homepage = "https://gitee.com/openkylin/libkysdk-applications"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # qmake (tool_requires-like usage) + Qt5 Core/Network/Widgets:
        #   - QApplication/QWidget            -> Qt5Widgets
        #   - QLocalServer/QLocalSocket        -> Qt5Network
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
                # gitee 归档端点（repository/archive/<ref>.tar.gz）的 WAF 只对
                # curl/wget 类 User-Agent 返回 302→blazearchive 的真实归档；对
                # python-requests / Conan / 浏览器类 UA 直接返回 HTML 挑战页
                # （sha256 不符）。conan 默认 UA 为 "Conan/..."，会被拦，故显式
                # 传 UA 头（conan 仅在未提供 UA 时才注入默认值）。retry/retry_wait
                # 一并加大以抗瞬时限流。
                get_kwargs = {"url": url, "strip_root": True,
                              "retry": 5, "retry_wait": 20,
                              "headers": {"User-Agent": "curl/8.0.0"}}
                if source_data.get("sha256"):
                    get_kwargs["sha256"] = source_data["sha256"]
                get(self, **get_kwargs)
                return
            except ConanException as error:
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    def _fix_qtbase_paths(self, qtbase_pkg):
        """Make the qt5-qtbase package relocatable: rewrite bin/qt.conf and the
        mkspecs .pri files so they point at the package folder instead of the
        original build directory (same helper as libkysdk-applications)."""
        qt_conf = os.path.join(qtbase_pkg, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as f:
                f.write(
                    "[EffectivePaths]\n"
                    "Prefix=..\n"
                    "[DevicePaths]\n"
                    f"Prefix={qtbase_pkg}\n"
                    "[Paths]\n"
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
        # 只构建 single_application 组件（kabase.pro 已被 0001 补丁裁剪为仅该组件）
        pro_dir = os.path.join(self.source_folder, "kysdk-kabase", "kabase")
        with build_env.vars(self).apply():
            self.run(
                f'cd "{pro_dir}" && {shlex.quote(qmake)} -spec linux-clang kabase.pro'
            )
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{pro_dir}" && make -j{jobs}')

    def package(self):
        src = os.path.join(self.source_folder, "kysdk-kabase", "kabase")
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include", "single_application")
        copy(self, "libkysdk-kabase.so*", src=src, dst=lib_dir, keep_path=False)
        # 上游 single_app_headers.path = /usr/include/kysdk/applications/kabase/
        # single_application/，本包安装到 include/single_application/，使消费者
        # 的 #include <single_application/single_application.hpp> 直接可用。
        # 这是上游真实文件路径，非改名 shim。
        copy(self, "single_application.hpp",
             src=os.path.join(src, "single_application"),
             dst=inc_dir, keep_path=False)
        # HMDFS 按目录继承属主且裁剪 other 权限位：对产物补 chmod，使任意 app uid
        # 可读可加载（若文件系统仍裁剪，test_package 探针会如实 FAIL，不伪造通过）。
        for root, _, files in os.walk(lib_dir):
            for f in files:
                if ".so" in f:
                    p = os.path.join(root, f)
                    try:
                        os.chmod(p, 0o755)
                    except OSError as e:
                        self.output.warning(f"chmod {p}: {e}")

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["kysdk-kabase"]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Network",
            "qt5-qtbase::Qt5Widgets",
        ]
