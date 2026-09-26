#!/usr/bin/env python3
"""Conan recipe — yasw 0.6（Yet Another Scan Wizard，Qt5 + qmake 图形应用）。

YASW 用于校正用相机翻拍书籍/文档所得图像：去梯形畸变、旋转、裁切、
色彩校正，并导出 PDF。构建系统为 qmake（`src/yasw.pro`），产物为可执行
文件 `yasw`（`TEMPLATE = app`）→ package_type = "application"（R38：
软件级别目录需带 commands.json）。

依赖
----
`src/yasw.pro` 声明 `QT += xml widgets printsupport`（+ 隐式 core/gui）。
全部由 **qt/5.15.19.1** 提供 —— 该配方是深度适配 OHOS PC 的 Qt5：
  * 自建 mkspecs/harmonyos-clang（clang 15 + libc++）
  * 其 `mkspecs/modules/*.pri` 为可搬迁形式（0/34 含构建期绝对路径，
    全部经 `$$QT_MODULE_*_BASE` 间接引用 `$$[QT_INSTALL_LIBS]`），
    因此可被 qmake 在 clean 环境直接消费
  * 含 libQt5PrintSupport（yasw 的 PDF 导出必需）

对照：`qt5-qtbase/5.15.2.2` 与 `qt5/5.15.19` 均不可用 —— 其 package()
原样拷贝 mkspecs，未重写 modules/*.pri 中硬编码的构建期绝对路径
（分别 50/50、46/46 悬空），clean 环境 qmake 报
`Project ERROR: Unknown module(s) in QT: core gui xml widgets printsupport`。
详见 archives/y/yasw/0.6/notes.md 与 reports/。

构建
----
in-source build：qmake 在 `src/` 内运行并生成 Makefile，产物为 `src/yasw`。
qmake 默认 spec 即 harmonyos-clang，无需 `-spec`。
`QMAKE_STRIP=""` 防止 strip（保持 not stripped，与仓内 Qt 应用先例一致）。
"""
import os
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


class YaswConan(ConanFile):
    name = "yasw"
    version = "0.6"
    description = (
        "YASW (Yet Another Scan Wizard) — Qt5 GUI tool that corrects scans of "
        "books and documents: keystone (trapezoid) correction, rotation, "
        "cropping, color correction and PDF export"
    )
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/yascanw/"
    url = "https://sourceforge.net/projects/yascanw/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # QT += xml widgets printsupport —— 全部由 qt/5.15.19.1 提供。
        # 依赖可消费性已实测（conan download 配方 + OHOS/armv8 二进制，EXIT=0）。
        self.requires("qt/5.15.19.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yasw only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        qt = self.dependencies["qt"]
        qt_root = qt.package_folder
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanInvalidConfiguration(
                f"qt 包内未找到 qmake: {qmake}"
            )

        # R33: 编译器一律取自 Conan conf，禁止裸用 ${CC}/${CXX}/${CFLAGS}。
        #      profile ci/conan/profiles/ohos-aarch64 已定义
        #      tools.build:compiler_executables = {c, cpp}。
        #      注意：该 conf 是**字典类型**，必须整体取出后按键访问
        #      （`conf.get("tools.build:compiler_executables:c")` 会抛
        #      ConanException: does not exist in configuration list）。
        compiler_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_execs.get("c") or "/data/service/hnp/bin/clang"
        cxx = compiler_execs.get("cpp") or "/data/service/hnp/bin/clang++"

        build_env = Environment()
        # qmake 探测目标编译器、以及 Makefile 中 Qt 工具（moc/uic/rcc）
        # 均以包内绝对路径调用；qmake/moc/uic/rcc 本身静态链接 Qt
        # （NEEDED 仅 libc++_shared/libc），故无需为构建期注入 LD_LIBRARY_PATH。
        # 此处仅防御性补充 Qt lib 目录，避免宿主环境不一致导致的加载告警。
        build_env.define("LD_LIBRARY_PATH", os.path.join(qt_root, "lib"))

        # 知识图谱 E540（shadow-ci / runner-path-prepend）：qmake 虽然以**绝对
        # 路径**收到 QMAKE_CXX，之后仍会用**裸名字** `clang++` 二次探测目标编译器；
        # 若构建期 PATH 中不含编译器所在目录，则直接失败：
        #   Project ERROR: Cannot run target compiler 'clang++'. Output:
        #   ===================
        #   Maybe you forgot to setup the environment?
        # conan-verify / CI 会以收敛后的环境调用 conan，宿主 PATH 不可假定存在
        # /data/service/hnp/bin（本地交互 shell 有、收敛环境没有 → 只在 CI 复现）。
        # 目录来源为 profile 的 tools.build:compiler_executables，非硬编码路径。
        tool_dirs = []
        for exe in (cc, cxx):
            d = os.path.dirname(exe)
            if d and d not in tool_dirs:
                tool_dirs.append(d)
        for d in reversed(tool_dirs):
            build_env.prepend("PATH", d, separator=os.pathsep)

        # 同时准备「内联 PATH 前缀」用的目录（见下方 self.run 处说明）。
        qt_bin = os.path.join(qt_root, "bin")
        tool_dir = os.path.dirname(cxx) or "/data/service/hnp/bin"

        # in-source build（与仓内 Qt 应用先例一致）
        src_dir = os.path.join(self.source_folder, "src")
        pro_file = os.path.join(src_dir, "yasw.pro")
        if not os.path.isfile(pro_file):
            raise ConanInvalidConfiguration(f"未找到 qmake 工程文件: {pro_file}")

        with build_env.vars(self).apply():
            # qmake 默认 spec = harmonyos-clang（qt/5.15.19.1 为 OHOS 配置），
            # 无需显式 -spec。
            #
            # 知识图谱 E540 + DRAFT-11153（knowthelist 2.3.1 / PR #11153 同因同解）：
            # qmake 探测目标编译器时以**裸名字** `clang++` 走 PATH 查找 —— 它既不读
            # CC/CXX 环境变量，也**不接受命令行 QMAKE_CXX= 赋值**（探测发生在赋值解析
            # 之前），故上面传的绝对路径只能用于 Makefile 生成，探测仍依赖 PATH。
            # 构建期 PATH 不含 /data/service/hnp/bin 时直接失败：
            #   Project ERROR: Cannot run target compiler 'clang++'. Output:
            # → 把工具链目录**内联**进命令（与 build_env 双保险）。
            #
            # 命令形式对齐仓内同因同解先例 archives/k/knowthelist/2.3.1/conanfile.py：
            # 用 self.run(..., cwd=src_dir) 而不是 `cd "..." && ...`。
            path_prefix = f'PATH="{qt_bin}:{tool_dir}:$PATH" '
            self._configure_qmake(qmake, pro_file, src_dir, cc, cxx, path_prefix)
            # R9: make -j1（不使用 -j$(nproc)）。
            # QMAKE_STRIP="" 防止 strip，保持 not stripped。
            # 同样内联 PATH：Makefile 中 Qt 工具与编译器的调用同样经 PATH 兜底。
            self.run(f'{path_prefix}make -j1 QMAKE_STRIP=""', cwd=src_dir)

    # ── qmake 配置（含编译器探测瞬时失败的有限重试）───────────────────────────
    #
    # 已实测定位（完整证据见 reports/yasw-0.6-g2-qmake-probe-finding.md）：
    # toolchain.prf 用 $$system()（内部 QProcess）分两步探测目标编译器：
    #   ① line  38  <cxx> -E <macros.cpp>              → QMAKE_CXX.COMPILER_MACROS
    #   ② line 210  LC_ALL=C <cxx> … -E -v -xc++ -     → QMAKE_CXX.INCDIRS/LIBDIRS
    # 宿主超载时（实测 load average 38 / 20 CPU，Committed_AS 129 GiB vs 物理 31 GiB），
    # QProcess::waitForStarted() 因 fork()/exec() 失败返回 false → qmake 报
    #   Project ERROR: Cannot run target compiler 'clang++'. Output:
    #   ===================
    #   ===================
    # 且 **Output 段为空**（子进程从未启动 → 无 stderr 可捕获）；失败现场留下半写的
    # .qmake.stash（仅 COMPILER_MACROS，513 B；完整为 1440 B，含 INCDIRS/LIBDIRS）。
    # 同命令/同环境/同目录重复执行时而通过时而失败（冷启动 20/20 通过 vs conan
    # 上下文内 2/6 失败）→ **瞬时资源性**失败，非配置缺陷；PATH、LD_LIBRARY_PATH、
    # TMPDIR、cwd 形式、QMAKE_* 命令行赋值、safe-delete 沙箱均已逐一排除。
    #
    # 处置：只对该指纹重试，且不掩盖真实错误 —— 其他任何失败立即上抛。
    _QMAKE_TRANSIENT_SIGNATURES = (
        "Cannot run target compiler",
        "Maybe you forgot to setup the environment?",
    )
    _QMAKE_ATTEMPTS = 3
    _QMAKE_RETRY_DELAY = 2  # 秒：等宿主 fork 压力回落

    def _configure_qmake(self, qmake, pro_file, src_dir, cc, cxx, path_prefix):
        """运行 qmake 生成 Makefile，对编译器探测的瞬时失败做有限重试。"""
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
                ret = self.run(cmd, cwd=src_dir, ignore_errors=True,
                               stdout=fh, stderr=fh)
            with open(log, encoding="utf-8", errors="replace") as fh:
                detail = fh.read()
            if ret == 0:
                if attempt > 1:
                    self.output.info(f"qmake 配置成功（第 {attempt} 次尝试）")
                return
            transient = any(sig in detail for sig in self._QMAKE_TRANSIENT_SIGNATURES)
            if transient and attempt < self._QMAKE_ATTEMPTS:
                self.output.warning(
                    f"qmake 编译器探测瞬时失败（{attempt}/{self._QMAKE_ATTEMPTS}，"
                    f"宿主 fork 压力），{self._QMAKE_RETRY_DELAY}s 后重试；日志: {log}"
                )
                time.sleep(self._QMAKE_RETRY_DELAY)
                continue
            # 非瞬时失败，或重试额度用尽 → 原样上抛，不做掩盖
            self.output.error(detail.rstrip())
            raise ConanException(f"Error {ret} while executing\n{cmd}\n完整日志: {log}")

    def package(self):
        # in-source build → 可执行文件位于 <source>/src/yasw
        copy(
            self,
            "yasw",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

    def package_info(self):
        # 图形应用（TEMPLATE = app），无消费方库目标
        self.cpp_info.bindirs = ["bin"]
