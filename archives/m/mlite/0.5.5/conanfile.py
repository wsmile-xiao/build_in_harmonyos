import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout

# 上游 tests/ 需要 Qt Linguist 的 lrelease（tests/ut_mdesktopentry.pro:7 硬编码
# $$[QT_INSTALL_BINS]/lrelease），而 qt5-qtbase 不含该工具、制品仓亦无 Qt5 qttools。
# 因此打包阶段只构建库与命令行工具（qmake 子目标），上游测试在适配阶段单独实跑，
# 结果见 reports/test-report.md。
BUILD_TARGETS = ("sub-src-all", "sub-tools-all")

# 上游 src/src.pro 的 INSTALL_HEADERS（dconf 关闭构型：不含 MDConf*/MGConfItem 系列）
PUBLIC_HEADERS = (
    "mlite-global.h",
    "mdesktopentry.h",
    "mnotification.h",
    "mnotificationgroup.h",
    "mremoteaction.h",
    "mpermission.h",
    "mfiledatastore.h",
    # 上游同时安装的「便利头」（内容仅 #include 同名真实头，供 #include <MDesktopEntry> 风格）
    "MDesktopEntry",
    "MNotification",
    "MNotificationGroup",
    "MRemoteAction",
    "MPermission",
)


class MliteConan(ConanFile):
    name = "mlite"
    version = "0.5.5"
    description = ("Selected classes pulled from the MeeGo Touch Framework "
                   "(desktop entry / notification / remote action helpers, Sailfish OS)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sailfishos/mlite"
    url = "https://github.com/sailfishos/mlite"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 上游 src/src.pro:17 `QT = core dbus` → Qt5Core + Qt5DBus。
        # 制品仓中只有 qt5-qtbase/5.15.2.2 以 configure -dbus 构建（提供 Qt5DBus
        # 组件与 qmake/qdbusxml2cpp），qt5-qtbase/5.15.2 为 -no-dbus 构型不可用。
        self.requires("qt5-qtbase/5.15.2.2")
        # 上游 src/src.pro:22 无条件 `PKGCONFIG += glib-2.0`（在 dconf 条件块之外），
        # 因此即便 dconf 关闭也必须能解析到 glib-2.0.pc，否则 qmake 直接报
        # "glib-2.0 development package not found"。本构型不编译 mdconf*.cpp，不引用 glib 符号。
        self.requires("glib/2.84.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}")

    def export_sources(self):
        # 本版本无补丁（patches/ 为空）；保留标准补丁通道，后续适配修复可直接新增 conandata patches
        export_conandata_patches(self)

    def source(self):
        # conandata 里保留 tar_format 供人工查阅；conan 2 的 get() 不接受该键
        source_data = dict(self.conan_data["sources"][self.version])
        source_data.pop("tar_format", None)
        urls = source_data.get("url")
        if isinstance(urls, str):
            urls = [urls]
        last_error = None
        for url in urls:
            try:
                get(self, url=url, sha256=source_data.get("sha256"), strip_root=True)
                return
            except ConanException as error:   # 逐个镜像容错（CI 会追加镜像 fallback）
                last_error = error
                self.output.warning(f"源码下载失败 {url}: {error}")
        raise ConanException(f"{self.name}/{self.version} 所有源码地址均下载失败: {last_error}")

    # ── 构建辅助 ────────────────────────────────────────────────────────
    def _qtbase(self):
        return self.dependencies["qt5-qtbase"]

    def _fix_qtbase_relocatability(self, qt_prefix):
        """qtbase 包内 qt.conf 与 mkspecs/**/*.pri 内嵌构建期绝对路径
        (…/.conan2/p/b/qt5-qXXXX/b)，该目录在包上传后已不存在，导致 qmake 报
        "Unknown module(s) in QT: core dbus" 与 "Cannot read …/modules-inst/…pri"。
        这里在构建期把它们改写为包目录（与 archives/l/libngf-qt 的处理一致）。"""
        qt_conf = os.path.join(qt_prefix, "bin", "qt.conf")
        if os.path.isfile(qt_conf):
            with open(qt_conf, "w", encoding="utf-8") as handle:
                handle.write(
                    "[EffectivePaths]\nPrefix=..\n"
                    "[DevicePaths]\n"
                    f"Prefix={qt_prefix}\n"
                    "[Paths]\n"
                    f"Prefix={qt_prefix}\n"
                    f"HostPrefix={qt_prefix}\n"
                    "Sysroot=\nSysrootifyPrefix=false\n"
                    "TargetSpec=linux-clang\nHostSpec=linux-clang\n"
                )
        build_dir_pattern = re.compile(r"/[^\s\"'()]*?/\.conan2/p/b/qt5-q[0-9a-f]+/b")
        legacy_prefix = "/storage/Users/storage/Users/currentUser"
        mkspecs = os.path.join(qt_prefix, "mkspecs")
        fixed = 0
        for root, _dirs, files in os.walk(mkspecs):
            for name in files:
                if not name.endswith(".pri"):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as handle:
                    content = handle.read()
                updated = build_dir_pattern.sub(qt_prefix, content).replace(
                    legacy_prefix, "/storage/Users/currentUser")
                if updated != content:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(updated)
                    fixed += 1
        self.output.info(f"qtbase 可重定位性修复：qt.conf 已改写，mkspecs/*.pri 修改 {fixed} 个")

    def _write_mkspec(self, qt_prefix):
        """自定义 mkspec：继承 qtbase 的 linux-clang，并补回被 pkg-config 过滤掉的 -L/lib。
        glib 的 pkg-config Libs 含 `-l:ld-musl-aarch64.so.1`，其 `-L/lib` 会被 pkg-config
        当系统路径剔除，导致 ld.lld 报 "unable to find library -l:ld-musl-aarch64.so.1"。"""
        mkspec_dir = os.path.join(self.generators_folder, "mlite-ohos")
        os.makedirs(mkspec_dir, exist_ok=True)
        with open(os.path.join(mkspec_dir, "qmake.conf"), "w", encoding="utf-8") as handle:
            handle.write(
                "# generated by mlite conanfile.py\n"
                "# 继承 qtbase 的 linux-clang 规格（制品仓无 ohos mkspec），并补 -L/lib\n"
                f"include({qt_prefix}/mkspecs/linux-clang/qmake.conf)\n"
                "QMAKE_LFLAGS += -L/lib\n"
            )
        return mkspec_dir

    def generate(self):
        # 依赖的 pkg-config 元数据（上游 .pro 使用 `CONFIG += link_pkgconfig`）。
        # 不引入 dconf → 上游 `packagesExist(dconf)` 为假，走 dconf 关闭构型（上游原生支持：
        # src/src.pro:46-48 `warning("dconf not found; MDConfItem will not be built")`）。
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)   # 本版本无补丁 → no-op；保留标准通道
        qt_prefix = self._qtbase().package_folder
        self._fix_qtbase_relocatability(qt_prefix)
        mkspec_dir = self._write_mkspec(qt_prefix)
        qmake = os.path.join(qt_prefix, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException("qt5-qtbase/5.15.2.2 未提供 bin/qmake")
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)

        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        env.define("QTDIR", qt_prefix)
        env.prepend_path("PATH", os.path.join(qt_prefix, "bin"))
        with env.vars(self, scope="build").apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} '
                f"-spec {shlex.quote(mkspec_dir)} VERSION={self.version} mlite.pro",
                cwd=self.source_folder)
            self.run(
                f'cd "{self.source_folder}" && make -j{jobs} {" ".join(BUILD_TARGETS)}',
                cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE.LGPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libmlite5.so*", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        for header in PUBLIC_HEADERS:
            copy(self, header, src=os.path.join(self.source_folder, "src"),
                 dst=os.path.join(self.package_folder, "include", "mlite5"),
                 keep_path=False)
        # 上游 tools/：mlitenotificationtool（上游 /usr/bin）与 mliteremoteaction（上游 /usr/libexec）
        for tool in ("mlitenotificationtool", "mliteremoteaction"):
            copy(self, tool, src=os.path.join(self.source_folder, "tools", tool),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["mlite5"]
        # 本包同时安装两个命令行工具（tools/ 构建产物），故显式声明 bindirs，
        # 与软件级 commands.json 的 CLI 声明一致（R38）
        self.cpp_info.bindirs = ["bin"]
        # 上游把头文件装到 /usr/include/mlite5，其 mlite5.pc 给 `-I${includedir}`
        # （includedir=${prefix}/include/mlite5），因此消费方以 #include <MDesktopEntry> 使用
        self.cpp_info.includedirs = ["include/mlite5"]
        # 上游 src/src.pro:17 `QT = core dbus` 与 src/mlite5.pc.in:11 `Requires: Qt5DBus`
        # glib：上游 src/src.pro:22 无条件 `PKGCONFIG += glib-2.0`（dconf 关闭时仍会链接
        # glib 的 pkg-config 库集），因此与上游链接语义保持一致地声明出来；
        # 本构型不编译 mdconf*.cpp，不引用 glib 符号（静态库不产生 DT_NEEDED）。
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5DBus",
            "glib::glib",
        ]
        self.cpp_info.set_property("cmake_file_name", "MLite")
        self.cpp_info.set_property("cmake_target_name", "MLite::MLite")
        # 与上游安装的 mlite5.pc 同名（上游 src/src.pro:97 PCFILE=mlite5.pc）
        self.cpp_info.set_property("pkg_config_name", "mlite5")
