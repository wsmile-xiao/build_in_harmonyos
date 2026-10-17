#!/usr/bin/env python3
"""Conan recipe — qlog 0.51.1（业余无线电日志软件，HarmonyOS PC aarch64 适配）。

QLog（https://github.com/foldynl/QLog）是 Qt6 qmake GUI 应用（业余无线电
日志/电台台站管理），上游构建系统为 qmake（QLog.pro 单工程）。

W0 依赖发布检查（制品仓 ohpcd）结论：
  * qtbase/6.11.1 + qtbase-gui/6.11.1 + qtbase-sql-dbus/6.11.1
    （三变体并存先例：lokalize/26.04.0；QLog 需要 core/gui/widgets/sql/
    network/xml/dbus 全集）
  * qtcharts/6.11.1（统计页）、qtserialport/6.11.1（CW 键控）、
    qtwebsockets/6.11.1（TCI 电台驱动）
  * qtkeychain/0.14.2（凭据存储，libqt6keychain）
  * hamlib/4.7.2（电台控制）、sqlite3/3.53.4（日志数据库）、
    openssl/3.5.6.1.2（TLS：DX 集群/websocket 加密连接）、zlib/1.3.2.1

功能裁剪（CONFIG+=qlog_ohos，patch 内以 qmake CONFIG 选项实现，非平台宏）
--------------------------------------------------------------------
  * **QtWebEngine 缺位**：制品仓没有 qtwebengine。QLog 的在线地图
    （Leaflet + WebEngineView + WebChannel）不可用。上游自带离线世界
    地图 ui/MapWidget（QGraphicsView + NASA 蓝色弹珠底图），patch 以
    QLOG_NO_WEBENGINE 宏提供等价 fallback：MapPageController/OnlineMapWidget
    的离线实现（点位/航迹绘制、setTarget/flyToMyQTH 可用），QWebEnginePage
    移出构建，StatisticsWidget.ui / QSODetailDialog.ui 的内嵌 mapView 改为
    MapWidget。在线图层（极光/MUF/网格热力/聊天点击/IBP 信标）在离线
    模式下降级为 no-op + debug 日志。
  * **QtPrintSupport 缺位**：qtbase-sql-dbus 构建 FEATURE_printsupport=OFF。
    QSL 标签打印/PDF 导出（QPrinter/QPrintDialog）以 QLOG_NO_PRINTSERVICE
    宏禁用（运行期弹提示），屏幕预览（renderPage→QImage）与卡片图片导出
    （renderDirectCard→QImage，纯 QtGui）保留。
  * qtquickcontrols/quickwidgets 未被上游实际使用（grep 无 QQuickWidget），
    随 webengine 一起从 QT 变量移除。

其它要点
--------
  * i18n：上游预编译 .qm 已入库（i18n/*.qm + i18n.qrc），无需 lrelease。
  * QLog.pro 的 unix 分支硬编码 /usr/local 路径与 PKGCONFIG openssl，
    patch 在 qlog_ohos 分支改为显式 LIBS + 外部传入 INCLUDEPATH/
    QMAKE_LIBDIR；HAMLIB 版本宏以命令行 HAMLIBVERSION_MAJOR/MINOR/PATCH
    显式传入，绕过 pkg-config 探测。
  * 签章：package() 最后对 bin/qlog 做 OHOS 代码签名（.codesign 段），
    QMAKE_STRIP 置空（OHOS 加载器拒载 stripped ELF）。
"""
import os
import re
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class QlogConan(ConanFile):
    name = "qlog"
    version = "0.51.1"
    description = (
        "QLog — an amateur radio logbook application (Qt6, HarmonyOS PC "
        "aarch64 adaptation)"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/foldynl/QLog"
    url = "https://github.com/foldynl/QLog"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qlog only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"]["qlog"], strip_root=True)

    # ── 工具链 ────────────────────────────────────────────────────────────

    def _toolchain(self):
        execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = execs.get("c") or "/data/service/hnp/bin/clang"
        cxx = execs.get("cpp") or "/data/service/hnp/bin/clang++"
        if not (os.path.isfile(cc) and os.path.isfile(cxx)):
            raise ConanInvalidConfiguration(f"未找到 clang 工具链: cc={cc} cxx={cxx}")
        return cc, cxx

    def _all_lib_dirs(self):
        dirs = []
        for require, dep in sorted(
            self.dependencies.items(), key=lambda kv: kv[0].ref.name
        ):
            if dep.package_folder is None:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir) and libdir not in dirs:
                dirs.append(libdir)
        return dirs

    # ── Qt6 多前缀模块 .pri（QMAKEMODULES，qpdfview/5 先例）──────────────

    def _setup_qmake_modules(self, build_env):
        """Qt 模块包的 mkspecs/modules/*.pri 记录构建期绝对路径
        （.../.conan2/p/b/<pkg>/b，随 conan 清理消失），qmake 直接引用报
        `Unknown module(s) in QT: charts/serialport/websockets`。复制到
        build 目录、把路径改写为依赖包 package 目录后经 QMAKEMODULES 暴露。
        """
        modules_root = os.path.join(self.build_folder, "qmake-modules")
        modules_dir = os.path.join(modules_root, "modules")
        modules_inst_dir = os.path.join(modules_root, "modules-inst")
        for directory in (modules_dir, modules_inst_dir):
            os.makedirs(directory, exist_ok=True)
        pattern = re.compile(r"/[^\s]*?conan2/p/b/[^/\s]+/b")
        for dep_name in ("qtbase", "qtbase-gui", "qtbase-sql-dbus", "qtcharts",
                         "qtserialport", "qtwebsockets"):
            dep = self.dependencies.get(dep_name)
            if not dep or not dep.package_folder:
                continue
            pkg_root = dep.package_folder
            for sub, target in (
                ("mkspecs/modules", modules_dir),
                ("mkspecs/modules-inst", modules_inst_dir),
            ):
                src = os.path.join(pkg_root, sub)
                if not os.path.isdir(src):
                    continue
                for pri in os.listdir(src):
                    if pri.endswith(".pri"):
                        shutil.copy2(os.path.join(src, pri), os.path.join(target, pri))
            for directory in (modules_dir, modules_inst_dir):
                for pri in os.listdir(directory):
                    if not pri.endswith(".pri"):
                        continue
                    path = os.path.join(directory, pri)
                    with open(path, "r", encoding="utf-8") as handle:
                        content = handle.read()
                    fixed = pattern.sub(lambda _m: pkg_root, content)
                    if fixed != content:
                        with open(path, "w", encoding="utf-8") as handle:
                            handle.write(fixed)
        build_env.define("QMAKEMODULES", modules_dir)

    # ── 构建 ─────────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._toolchain()
        qtbase = self.dependencies["qtbase"]
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake6")
        if not os.path.isfile(qmake):
            qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration(f"qtbase 包内未找到 qmake: {qmake}")

        build_env = Environment()
        # qmake 探测目标编译器用裸名字 clang++ 走 PATH（知识图谱 E540）
        for exe in (cc, cxx):
            tool_dir = os.path.dirname(exe)
            if tool_dir:
                build_env.prepend_path("PATH", tool_dir)
        # qmake/moc/uic/rcc 是 Qt 可执行文件，需要构建期库路径
        for libdir in self._all_lib_dirs():
            build_env.prepend_path("LD_LIBRARY_PATH", libdir)

        # Qt 多前缀模块 .pri → QMAKEMODULES
        self._setup_qmake_modules(build_env)

        # 链接期库路径（clang 识别 LIBRARY_PATH）
        build_env.define("LIBRARY_PATH", os.pathsep.join(self._all_lib_dirs()))

        src = self.source_folder
        package_folder = self.package_folder

        # Qt 扩展模块（qtcharts/qtserialport/qtwebsockets）的 .pri 把
        # QT_MODULE_INCLUDE_BASE 解析到第一个 QMAKEPATH 前缀（qtbase），
        # 导致 -I <qtbase>/include/QtCharts 不存在。显式补模块头目录；
        # 库路径已由 QMAKE_LIBDIR 覆盖。
        module_incs = []
        for dep_name, mod in (("qtcharts", "QtCharts"),
                              ("qtserialport", "QtSerialPort"),
                              ("qtwebsockets", "QtWebSockets")):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                module_incs.append(os.path.join(
                    dep.package_folder, "include", mod))

        # 依赖的 include/lib 目录（hamlib/sqlite3/openssl/zlib/qtkeychain 及
        # Qt 多前缀），显式传给 qmake
        include_dirs, lib_dirs = [], []
        for require, dep in sorted(
            self.dependencies.items(), key=lambda kv: kv[0].ref.name
        ):
            if dep.package_folder is None:
                continue
            incdir = os.path.join(dep.package_folder, "include")
            if os.path.isdir(incdir) and incdir not in include_dirs:
                include_dirs.append(incdir)
        lib_dirs = self._all_lib_dirs()

        qmake_args = [
            os.path.join(src, "QLog.pro"),
            # 功能裁剪（见模块 docstring）：离线地图 fallback + 无打印服务
            "CONFIG+=qlog_ohos",
            "QMAKE_STRIP=",
            f"QMAKE_CC={cc}",
            f"QMAKE_CXX={cxx}",
            f"QMAKE_LINK={cxx}",
            f"QMAKE_LINK_SHLIB={cxx}",
            # hamlib 4.7.2：显式版本宏，绕过 pkg-config 探测
            "HAMLIBVERSION_MAJOR=4",
            "HAMLIBVERSION_MINOR=7",
            "HAMLIBVERSION_PATCH=2",
            "PREFIX=/usr",
        ]
        for inc in include_dirs:
            qmake_args.append(f'INCLUDEPATH+="{inc}"')
        for inc in module_incs:
            qmake_args.append(f'INCLUDEPATH+="{inc}"')
        for lib in lib_dirs:
            qmake_args.append(f'QMAKE_LIBDIR+="{lib}"')
            # 运行期：多前缀 conan 安装，全部依赖 lib 目录补进 RUNPATH
            qmake_args.append(f'QMAKE_RPATHDIR+="{lib}"')
        # INSTALLS 目标安装进 package（make install 直接用）
        qmake_args.append(f"INSTALL_ROOT={package_folder}")

        with build_env.vars(self).apply():
            self.run(
                f'"{qmake}" ' + " ".join(qmake_args),
                cwd=src,
            )
            # 模块库的绝对路径同样解析到了第一个前缀（qtbase），按
            # chinese/1.0.3.r58 先例对生成的 Makefile* 改写为真实包路径
            # （链接行在 Makefile.Release 中）。
            import glob
            import re
            for makefile in glob.glob(os.path.join(src, "Makefile")) + glob.glob(
                os.path.join(src, "Makefile.*")
            ):
                with open(makefile, "r", encoding="utf-8") as handle:
                    content = handle.read()
                for dep_name, libname in (("qtcharts", "libQt6Charts.so"),
                                          ("qtserialport", "libQt6SerialPort.so"),
                                          ("qtwebsockets", "libQt6WebSockets.so")):
                    dep = self.dependencies.get(dep_name)
                    if not dep or not dep.package_folder:
                        continue
                    right = os.path.join(dep.package_folder, "lib", libname)
                    if not os.path.isfile(right):
                        continue
                    # 链接行里的该库可能指向任意其它前缀（第一个解析到
                    # 的 qtbase 包），统一改写为真实包路径
                    content = re.sub(
                        r"/[^\s\"=]+/" + re.escape(libname),
                        right,
                        content,
                    )
                with open(makefile, "w", encoding="utf-8") as handle:
                    handle.write(content)
            # R9: make -j1
            self.run('make -j1 QMAKE_STRIP=""', cwd=src)

    # ── 打包 ─────────────────────────────────────────────────────────────

    _SIGN_SECTION = ".codesign"

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as handle:
                header = handle.read(18)
        except OSError:
            return None
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            return None
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(env_var, executable):
        """定位签章工具：环境变量 > PATH > OHOS 工具链默认位置。"""
        configured = os.environ.get(env_var)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved and not configured:
            fallback = os.path.join("/data/service/hnp/bin", executable)
            if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
                resolved = fallback
        if not resolved:
            raise ConanInvalidConfiguration(
                f"未找到 {executable}（需要 OHOS 工具链来完成 ELF 签章）"
            )
        return resolved

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    def _has_codesign_section(self, objdump, path):
        sections = self._run_tool([objdump, "-h", path], f"inspect ELF sections in {path}")
        return any(self._SIGN_SECTION in line.split() for line in sections.splitlines())

    def _sign_elfs(self, bindir):
        """对 bin/ 下的可执行文件做 HarmonyOS 代码签名（不签名无法 exec）。

        签章是对 ELF 内容的哈希，必须在所有后续处理之后执行，故放在
        package() 最后一步；临时目录 unsigned → signed 再 os.replace 回写，
        并强校验 .codesign 段存在（qpdfview/0.5.0 同法）。
        """
        if str(self.settings.os) != "OHOS":
            return
        targets = []
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            if self._elf_type(path) in (2, 3):
                targets.append(path)
        if not targets:
            return

        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")

        for binary in targets:
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", self._SIGN_SECTION, unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    # package() 安装清单：与上游 QLog.pro 的 INSTALLS 及生成的 Makefile 一致
    # （qlog 二进制 + res/ 下的 desktop/icon/metainfo/manpage）。
    # 不再执行 make install：qmake qinstall（QFile::copy）在部分 CI worker
    # 的 hmdfs 上对任意文件拷贝都报 `Value too large for data type`
    # （EOVERFLOW，见 MR #14448 CI #79959/#81268——连几十字节的
    # qlog.desktop 也失败，与文件大小无关），改用 python 读/写循环拷贝。
    _INSTALL_FILES = (
        ("qlog", "usr/bin/qlog", 0o755),
        ("res/qlog.desktop", "usr/share/applications/qlog.desktop", None),
        ("res/qlog.png", "usr/share/icons/hicolor/256x256/apps/qlog.png", None),
        ("res/io.github.foldynl.QLog.metainfo.xml",
         "usr/share/metainfo/io.github.foldynl.QLog.metainfo.xml", None),
        ("res/qlog.1", "usr/share/man/man1/qlog.1", None),
    )

    def package(self):
        srcdir = self.source_folder
        for rel_src, rel_dst, mode in self._INSTALL_FILES:
            src_path = os.path.join(srcdir, rel_src)
            if not os.path.isfile(src_path):
                raise ConanInvalidConfiguration(f"待安装文件缺失: {src_path}")
            dest_path = os.path.join(self.package_folder, rel_dst)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)
            if os.path.getsize(dest_path) != os.path.getsize(src_path):
                raise ConanInvalidConfiguration(
                    f"文件拷贝不完整: {dest_path}"
                )
            if mode is not None:
                os.chmod(dest_path, mode)
        # PREFIX=/usr → 上游安装进 <pkg>/usr/*，归位到标准 hnp 布局
        srcbindir = os.path.join(self.package_folder, "usr", "bin")
        if os.path.isdir(srcbindir):
            shutil.move(srcbindir, os.path.join(self.package_folder, "bin"))
        shutil.rmtree(os.path.join(self.package_folder, "usr"),
                      ignore_errors=True)
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            raise ConanInvalidConfiguration(f"未生成 bin 目录: {bindir}")
        if not os.path.isfile(os.path.join(bindir, "qlog")):
            raise ConanInvalidConfiguration(f"未生成可执行文件: {bindir}/qlog")
        # 签章必须放最后：任何后置改动都会让 .codesign 哈希失效
        self._sign_elfs(bindir)

    def requirements(self):
        # Qt6 三变体并存（lokalize/26.04.0 先例，SONAME 相同）
        self.requires("qtbase/6.11.1")
        self.requires("qtbase-gui/6.11.1")
        self.requires("qtbase-sql-dbus/6.11.1")
        # Qt 扩展模块
        self.requires("qtcharts/6.11.1")
        self.requires("qtserialport/6.11.1")
        self.requires("qtwebsockets/6.11.1")
        # 凭据存储（libqt6keychain）
        self.requires("qtkeychain/0.14.2")
        # 电台控制 / 日志数据库 / TLS / 压缩
        self.requires("hamlib/4.7.2")
        self.requires("sqlite3/3.53.4")
        self.requires("openssl/3.5.6.1.2")
        self.requires("zlib/1.3.2.1")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 运行期环境：依赖链横跨多个 conan package 前缀
        for require, dep in sorted(
            self.dependencies.items(), key=lambda kv: kv[0].ref.name
        ):
            dep_name = require.ref.name
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir) and dep_name.startswith("qt"):
                self.runenv_info.prepend_path("PATH", bindir)
        # Qt 插件目录（platforms/sqldrivers/imageformats/iconengines…）
        for require, dep in sorted(
            self.dependencies.items(), key=lambda kv: kv[0].ref.name
        ):
            if not dep.package_folder or not require.ref.name.startswith("qt"):
                continue
            plugins = os.path.join(dep.package_folder, "plugins")
            if os.path.isdir(plugins):
                self.runenv_info.prepend_path("QT_PLUGIN_PATH", plugins)
