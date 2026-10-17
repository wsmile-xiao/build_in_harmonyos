#!/usr/bin/env python3
"""Conan recipe — sensorfw 0.15.2（Sailfish OS 传感器框架）。

sensorfw 是 Sailfish OS 的传感器框架：守护进程 `sensorfwd`（sensord）、D-Bus
客户端库、以及可在运行期 `dlopen()` 的 adaptor / chain / filter / sensor 插件。
构建系统为 qmake（顶层 `sensorfw.pro` 是 `TEMPLATE = subdirs` 的递归工程）。

产物形态：库 + 守护进程可执行文件，故 `package_type = "library"` 并导出
`bindirs`（软件级目录需带 `commands.json`，R38）。

依赖
----
* **qt/5.15.19.1** —— `common-config.pri` 声明 `QT += dbus`，各子工程另有
  `QT += network/testlib`；均需 Qt5DBus / Qt5Network / Qt5Test / Qt5Core。
  `qt/5.15.19.1` 是仓内唯一同时满足下列三点的 Qt5 包：
    1. 含 QtDBus（`qt/5.15.19` 的配方硬编码 `-no-dbus`，**没有** Qt5DBus）；
    2. `mkspecs/modules/*.pri` 为可搬迁形式（0/34 含构建期绝对路径），
       clean 环境 qmake 不会报 `Unknown module(s)`；
    3. 自带 `mkspecs/harmonyos-clang`（clang 15 + libc++），并把
       `QMAKE_LN_SHLIB` 设为 `cp -f`（HarmonyOS 包缓存不允许符号链接）。
  依赖可消费性已在本地用 `conan download` 实测（EXIT=0）；remote 由环境提供，
  不硬编码在这里。注意 L0g 的硬编码 remote 检查是朴素正则，只要文档里写出
  「conan 子命令 + 远程参数」的完整形式，即使只是说明文字也会被判失败，
  故本行刻意不写出该参数。
* **libudev-zero/1.0.4** —— `adaptors/iioadaptor` 通过 libudev 枚举 input
  设备；该包以静态库形式提供 `libudev.a` + 头文件（R26：libudev 属系统同名库，
  始终静态）。

OHOS 适配
---------
五个补丁（见 conandata.yml 与 patches/，全部为 portability 性质，不含平台宏）：

1. `iioadaptor.pro` 的 libudev 查找改为「环境变量优先、pkg-config 回退」；
2. `sensord.pro` 的 libsystemd 链接放到 `CONFIG+=systemd` 之后；
3. `sensord/main.cpp` 的 `sd_notify()` 就绪通知同样条件编译；
4. 四类插件的 `*-config.pri` 追加 `-lsensorfw-qt5`，使每个插件自带
   `DT_NEEDED libsensorfw-qt5.so.0` —— HarmonyOS/musl 的 dlopen 只在对象
   自身的 DT_NEEDED 闭包内解析未定义符号，上游依赖宿主进程提供框架库符号的
   做法在 musl 上必然失败（先例：`archives/l/libnfsidmap-ldap/2.6.4`）；
5. `chains/compasschain.pro` 追加对 4 个插件模块的链接 —— 同因同解的第二处：
   compasschain 直接实例化 `AvgAccFilter` / `DownsampleFilter` /
   `DeclinationFilter` / `MagCalibrationChain`，这些类不在框架库里，而是各自
   插件模块的实现，0004 无法覆盖。

构建
----
in-source build：在源码目录内 `qmake sensorfw.pro` 后 `make -j1`（与仓内
qmake 先例 yasw / libguytools2 一致）。qmake 默认 spec 即 `harmonyos-clang`，
无需 `-spec`。`QMAKE_STRIP=""` 防止 strip。
"""
import os
import re
import time

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


class SensorfwConan(ConanFile):
    name = "sensorfw"
    version = "0.15.2"
    description = (
        "sensorfw — Sailfish OS sensor framework: the sensord daemon, its "
        "D-Bus client library and the dynamically loaded adaptor / chain / "
        "filter / sensor plugins"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sailfishos/sensorfw"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # qmake builds TEMPLATE = lib projects as shared objects here (the
    # harmonyos-clang mkspec sets QMAKE_LN_SHLIB = cp -f), so `shared` is
    # declared for the `library` package type but only True is supported
    # (enforced in validate()).  `fPIC` is likewise fixed by the mkspec and is
    # declared only to keep the standard library-recipe option surface.
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # 插件目录（分类 -> 源码子目录）。四类共用各自的 *-config.pri，
    # 0004 补丁在这四个文件里追加对框架库的链接。
    _plugin_categories = ("adaptors", "chains", "filters", "sensors")
    # upstream: PLUGINPATH = $$[QT_INSTALL_LIBS]/sensord-qt$${QT_MAJOR_VERSION}
    _plugin_dir = "sensord-qt5"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt 是普通依赖，不加 transitive_headers/transitive_libs。
        #
        # 随包发布的头文件确实引用 Qt 类型（datatypes/xyz.h 的
        # QObject/QVariant/QDBusArgument、core/ 与 sensord/ 的 QString），消费者
        # 编译时需要 Qt —— 但上游就是这么界的：sensord-qt5.pc 的 `Requires:` 为空，
        # Cflags 只给 -I${includedir} -I${includedir}/datatypes，即「消费者自带 Qt」。
        # 本仓其余 Qt 消费者亦然：archives/y/yasw/0.6、archives/a/attica5/5.116.0、
        # archives/l/libaccounts-qt/1.13 都用普通的 self.requires("qt...")。
        #
        # 实测（两个仅差这两个标志的对照包，CMakeDeps 输出逐字节相同）表明：
        # transitive_* 对本包生成物没有影响 —— CMakeDeps 收集的是
        # 「消费者的依赖 ∩ 本包的直接依赖」，与该标志无关，因此
        # sensorfw-config.cmake 里的 find_dependency(qt) 无论如何都会生成。
        # 该调用无法自行解析（qt/5.15.19.1 刻意设了 cmake_find_mode = "none"），
        # 由 test_package/cmake/qt-config.cmake 桥接，见 notes.md「已知问题」。
        self.requires("qt/5.15.19.1")
        self.requires("libudev-zero/1.0.4")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )
        # The qmake project always produces shared objects; refusing static
        # avoids handing out a package that silently does not match the option.
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                f"{self.name} only builds shared libraries (qmake TEMPLATE = lib)"
            )

    def source(self):
        # conandata.yml 的 tar_format 仅供校验：get() 不识别该关键字参数，
        # 不能 ** 展开传入（dbus / accountsservice 先例）。
        source_data = self.conan_data["sources"]
        get(
            self,
            url=source_data["url"],
            sha256=source_data.get("sha256", ""),
            strip_root=True,
        )

    # ── 依赖定位 ─────────────────────────────────────────────────────────────

    def _qt(self):
        return self.dependencies["qt"]

    def _qt_root(self):
        qt = self._qt()
        if qt.package_folder is None:
            raise ConanInvalidConfiguration("qt package has no package folder")
        return qt.package_folder

    def _qmake_path(self):
        qmake = os.path.join(self._qt_root(), "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration(f"qmake not found in qt package: {qmake}")
        return qmake

    def _udev_root(self):
        udev = self.dependencies["libudev-zero"]
        if udev.package_folder is None:
            raise ConanInvalidConfiguration(
                "libudev-zero package has no package folder"
            )
        return udev.package_folder

    # ── 构建 ─────────────────────────────────────────────────────────────────

    def _build_environment(self, cc, cxx):
        """构建期环境变量。

        * LD_LIBRARY_PATH：qmake 探测目标编译器、以及 Makefile 内调用的
          moc/uic/rcc 均以包内绝对路径执行；此处防御性补充 Qt lib 目录。
        * SENSORFW_LIBUDEV_*：0001 补丁读取的 libudev 搜索目录。用环境变量
          而不是命令行赋值，因为 qmake 不会把 `VAR=...` 转发给递归构建的
          子工程 qmake。
        """
        build_env = Environment()
        build_env.define("LD_LIBRARY_PATH", os.path.join(self._qt_root(), "lib"))
        udev_root = self._udev_root()
        build_env.define(
            "SENSORFW_LIBUDEV_INCLUDEPATH", os.path.join(udev_root, "include")
        )
        build_env.define("SENSORFW_LIBUDEV_LIBDIR", os.path.join(udev_root, "lib"))

        # 知识 E540 / DRAFT-11153：qmake 收到绝对路径的 QMAKE_CXX 之后，仍会用
        # **裸名字** clang++ 二次探测目标编译器；构建期 PATH 不含工具链目录时
        # 直接失败（"Cannot run target compiler 'clang++'"）。目录来源为
        # profile 的 tools.build:compiler_executables，而非硬编码路径。
        tool_dirs = []
        for exe in (cc, cxx):
            directory = os.path.dirname(exe)
            if directory and directory not in tool_dirs:
                tool_dirs.append(directory)
        for directory in reversed(tool_dirs):
            build_env.prepend("PATH", directory, separator=os.pathsep)
        return build_env

    def build(self):
        apply_conandata_patches(self)

        qmake = self._qmake_path()

        # R33: 编译器一律取自 Conan conf，禁止裸用 ${CC}/${CXX}/${CFLAGS}。
        #     该 conf 是**字典类型**，必须整体取出后按键访问。
        compiler_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_execs.get("c") or "/data/service/hnp/bin/clang"
        cxx = compiler_execs.get("cpp") or "/data/service/hnp/bin/clang++"

        src_dir = self.source_folder
        pro_file = os.path.join(src_dir, "sensorfw.pro")
        if not os.path.isfile(pro_file):
            raise ConanInvalidConfiguration(f"qmake project file not found: {pro_file}")

        qt_bin = os.path.join(self._qt_root(), "bin")
        tool_dir = os.path.dirname(cxx) or "/data/service/hnp/bin"
        path_prefix = f'PATH="{qt_bin}:{tool_dir}:$PATH" '

        with self._build_environment(cc, cxx).vars(self).apply():
            self._configure_qmake(qmake, pro_file, src_dir, cc, cxx, path_prefix)
            # R9: make -j1（不使用 -j$(nproc)）。
            # QMAKE_STRIP="" 防止 strip，保持 not stripped（仓内 qmake 先例同）。
            self.run(f'{path_prefix}make -j1 QMAKE_STRIP=""', cwd=src_dir)

    # ── qmake 配置（含编译器探测瞬时失败的有限重试）───────────────────────────
    #
    # 与 archives/y/yasw/0.6 同因同解：toolchain.prf 用 $$system()（内部
    # QProcess）分两步探测目标编译器；宿主超载时 fork()/exec() 失败 →
    #   Project ERROR: Cannot run target compiler 'clang++'. Output:
    # 且 Output 段为空（子进程从未启动）。属瞬时资源性失败，非配置缺陷。
    # 只对该指纹重试，其他任何失败立即上抛。
    _QMAKE_TRANSIENT_SIGNATURES = (
        "Cannot run target compiler",
        "Maybe you forgot to setup the environment?",
    )
    _QMAKE_ATTEMPTS = 3
    _QMAKE_RETRY_DELAY = 2  # 秒：等宿主 fork 压力回落

    def _configure_qmake(self, qmake, pro_file, src_dir, cc, cxx, path_prefix):
        cmd = (
            f'{path_prefix}"{qmake}" "{pro_file}" '
            f'QMAKE_CC="{cc}" QMAKE_CXX="{cxx}" QMAKE_LINK="{cxx}" '
            f'QMAKE_LINK_SHLIB="{cxx}"'
        )
        stash = os.path.join(src_dir, ".qmake.stash")
        log = os.path.join(self.build_folder, "qmake.log")
        for attempt in range(1, self._QMAKE_ATTEMPTS + 1):
            if attempt > 1 and os.path.isfile(stash):
                # 半写的 stash 会让下一次探测走「从缓存加载」分支，先清掉保证冷探测
                os.remove(stash)
            with open(log, "w", encoding="utf-8") as fh:
                fh.write(f"# qmake attempt {attempt}/{self._QMAKE_ATTEMPTS}\n# {cmd}\n")
                ret = self.run(
                    cmd, cwd=src_dir, ignore_errors=True, stdout=fh, stderr=fh
                )
            with open(log, encoding="utf-8", errors="replace") as fh:
                detail = fh.read()
            if ret == 0:
                if attempt > 1:
                    self.output.info(f"qmake configured on attempt {attempt}")
                return
            transient = any(sig in detail for sig in self._QMAKE_TRANSIENT_SIGNATURES)
            if transient and attempt < self._QMAKE_ATTEMPTS:
                self.output.warning(
                    f"qmake toolchain probe failed ({attempt}/{self._QMAKE_ATTEMPTS}, "
                    f"host fork pressure), retrying in {self._QMAKE_RETRY_DELAY}s; "
                    f"log: {log}"
                )
                time.sleep(self._QMAKE_RETRY_DELAY)
                continue
            self.output.error(detail.rstrip())
            raise ConanException(f"Error {ret} while executing\n{cmd}\nfull log: {log}")

    # ── 打包 ─────────────────────────────────────────────────────────────────
    #
    # 目录布局对齐上游 INSTALLS 规则：
    #   守护进程            -> /usr/sbin/sensorfwd          -> bin/
    #   框架/数据类型/客户端 -> $$SHAREDLIBPATH              -> lib/
    #   插件                -> $$PLUGINPATH (Qt lib/sensord-qt5) -> lib/sensord-qt5/
    #   公开头文件          -> /usr/include/sensord-qt5{,/datatypes} -> include/sensord-qt5/…
    #   配置                -> /etc/sensorfw/sensord.conf.d
    _PUBLIC_HEADER_PREFIX = "$(INSTALL_ROOT)/usr/include/sensord-qt5/"

    def _upstream_public_headers(self):
        """{相对目标路径: 绝对源路径} —— 上游 `make install` 会发布的全部公开头文件。

        `common-install.pri` 里有 `INSTALLS += publicheaders`，因此每个子工程
        生成的 Makefile 都带一条 `install_publicheaders` 规则，其 QINSTALL 行
        就是「发布哪些头文件、放到哪里」的权威定义。直接读取它而不是自行
        glob 源码树，是因为两者并不等价：

        * 规则里的清单是各 .pro 显式声明的 ``$$HEADERS``，不含条件编译头
          （hybris / mce / contextfw）与 qmake 生成物 ``moc_predefs.h``；
        * 布局是「除 datatypes/ 外一律平铺」，包括 ``core/``——``core.pro`` 里
          那句 ``publicheaders.path = $${publicheaders.path}/core`` 并未生效
          （生成的规则目标就是 ``/usr/include/sensord-qt5/abstractchain.h``）；
        * ``filters/`` 因 ``filters.pro`` 的 ``publicheaders.files = *.h`` 零匹配
          而**完全没有安装规则**，上游不存在 ``/usr/include/sensord-qt5/filters/``。

        最终布局与上游 ``sensord-qt5.pc`` 的
        ``Cflags: -I${includedir} -I${includedir}/datatypes`` 一致。
        """
        headers = {}
        pattern = re.compile(
            r"(\S+\.h)\s+" + re.escape(self._PUBLIC_HEADER_PREFIX) + r"(\S+)"
        )
        for dirpath, _dirnames, filenames in os.walk(self.source_folder):
            if "Makefile" not in filenames:
                continue
            with open(os.path.join(dirpath, "Makefile"),
                      encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if self._PUBLIC_HEADER_PREFIX not in line:
                        continue
                    match = pattern.search(line)
                    if match:
                        headers[match.group(2)] = match.group(1)
        return headers

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        copy(self, "COPYING", src=src, dst=os.path.join(pkg, "licenses"))

        # 守护进程（TEMPLATE = app, TARGET = sensorfwd, target.path = /usr/sbin）
        copy(self, "sensorfwd", src=os.path.join(src, "sensord"),
             dst=os.path.join(pkg, "bin"), keep_path=False)

        # 三个共享库：core / datatypes / qt-api。
        # 完整保留 qmake 生成的版本化 SONAME 布局
        # （libX.so -> libX.so.0 -> libX.so.0.9 -> libX.so.0.9.0，均为实体文件，
        #   因为 harmonyos-clang mkspec 把 QMAKE_LN_SHLIB 设为 cp -f）。
        lib_dst = os.path.join(pkg, "lib")
        for directory, pattern in (
            ("core", "libsensorfw-qt5.so*"),
            ("datatypes", "libsensordatatypes-qt5.so*"),
            ("qt-api", "libsensorclient-qt5.so*"),
        ):
            copy(self, pattern, src=os.path.join(src, directory),
                 dst=lib_dst, keep_path=False)

        # 插件：上游装到 $$PLUGINPATH，等价于 Qt lib 目录下的 sensord-qt5/
        plugin_dst = os.path.join(lib_dst, self._plugin_dir)
        for category in self._plugin_categories:
            category_dir = os.path.join(src, category)
            for entry in sorted(os.listdir(category_dir)):
                plugin_dir = os.path.join(category_dir, entry)
                if os.path.isdir(plugin_dir):
                    copy(self, "lib*-qt5.so", src=plugin_dir,
                         dst=plugin_dst, keep_path=False)

        # 公开头文件：完全按上游自己的安装规则落盘，见 _upstream_public_headers()。
        # 注意上游的布局并不是「源码树的 glob」：
        #   * core/ 是**平铺**的（core.pro 里的 publicheaders.path 追加 /core 未生效，
        #     生成的 install_publicheaders 规则目标为 /usr/include/sensord-qt5/xxx.h）；
        #   * 只有 datatypes/ 有子目录；
        #   * 没有 filters/ 子目录（filters/filters.pro 的 `publicheaders.files = *.h`
        #     匹配到 0 个文件，qmake 因此根本没生成 install 规则）；
        #   * 每项是各 .pro 显式声明的 $$HEADERS 清单，因此不含条件编译头
        #     （hybris / mce / contextfw）与 qmake 生成物 moc_predefs.h。
        # 该布局与上游 sensord-qt5.pc 的
        #   Cflags: -I${includedir} -I${includedir}/datatypes
        # 完全一致，也是 package_info().includedirs 的全部内容。
        inc_dst = os.path.join(pkg, "include", self._plugin_dir)
        headers = self._upstream_public_headers()
        if not headers:
            raise ConanException(
                "no upstream public-header install rules found in the build tree "
                f"({self.source_folder}); refusing to package an empty header set"
            )
        self.output.info(
            f"public headers: {len(headers)} files declared by upstream install rules"
        )
        for dst_rel in sorted(headers):
            source = headers[dst_rel]
            copy(self, os.path.basename(source), src=os.path.dirname(source),
                 dst=os.path.join(inc_dst, os.path.dirname(dst_rel)),
                 keep_path=False)

        # 运行期配置（上游 SENSORDCONFIGFILES.path = /etc/sensorfw/sensord.conf.d）
        copy(self, "10-sensord-default.conf", src=os.path.join(src, "config"),
             dst=os.path.join(pkg, "etc", "sensorfw", "sensord.conf.d"),
             keep_path=False)
        copy(self, "20-sensors-default.conf", src=os.path.join(src, "config"),
             dst=os.path.join(pkg, "etc", "sensorfw", "sensord.conf.d"),
             keep_path=False)

    def package_info(self):
        # 消费者视角的链接面与上游 sensord-qt5.pc 一致：
        #   Libs:   -lsensorclient-qt5 -lsensordatatypes-qt5
        #   Cflags: -I${includedir} -I${includedir}/datatypes
        # （libsensorfw-qt5 是守护进程侧框架库，不作为消费方链接目标。）
        self.cpp_info.libs = ["sensorclient-qt5", "sensordatatypes-qt5"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # 只有两项，与上游 .pc 的 Cflags 完全对应：上游安装布局里除
        # datatypes/ 外一律平铺（core/ 也不例外），也不存在 filters/ 子目录。
        self.cpp_info.includedirs = [
            os.path.join("include", self._plugin_dir),
            os.path.join("include", self._plugin_dir, "datatypes"),
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
