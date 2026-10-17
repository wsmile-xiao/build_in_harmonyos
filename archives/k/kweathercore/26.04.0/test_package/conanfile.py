#!/usr/bin/env python3
"""Conan test_package — kweathercore 26.04.0 (Conan L1 官方测试)

消费者视角验证：头文件可包含（locationqueryresult.h / version.h），库可链接
（libKWeatherCore），二进制可运行（原生 OHOS）。
编译命令从 Conan conf 取编译器（R33），不裸用 shell 环境变量。
"""
import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 汇总全部依赖（含被测包 kweathercore）的 include 路径：
        # kweathercore 头文件会 include <QString>（qtbase）、
        # <KHolidays/...>（kholidays）等，必须收集所有依赖的 includedirs。
        incs = []
        for _ref, dep in self.dependencies.items():
            incs += ["-I" + p for p in dep.cpp_info.includedirs]
            # Qt 头布局：裸 include <QMetaType> 依赖 include/QtCore 子目录
            # 本身作为搜索路径（kweathercore 头内用裸 Qt 头名）。
            if _ref.ref.name.startswith("qt"):
                incs += ["-I" + os.path.join(p, "QtCore")
                         for p in dep.cpp_info.includedirs
                         if os.path.isdir(os.path.join(p, "QtCore"))]
            for _comp_name, comp in dep.cpp_info.components.items():
                incs += ["-I" + p for p in comp.includedirs]
        seen = set()
        uniq = []
        for flag in incs:
            if flag not in seen:
                seen.add(flag)
                uniq.append(flag)
        inc = " ".join(uniq)

        # 所有依赖包的 package_folder/lib 并集（含被测包 kweathercore）。
        libdirs = set()
        for d in self.dependencies.values():
            if d.package_folder:
                libdirs.add(os.path.join(d.package_folder, "lib"))
        libdir = " ".join("-L" + d for d in libdirs) if libdirs else ""

        # R33：编译器从 Conan conf 获取，禁止 ${CXX}。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = ce.get("cpp") or ce.get("c") or "clang++"

        # C++20：上游强制 CMAKE_CXX_STANDARD 20（src 用 std::ranges），
        # 公共头签名与 C++20 对齐；kweathercore 头内 <kweathercore/
        # kweathercore_export.h> 小写裸前缀由主包 include/kweathercore
        # 符号链接解析（主包 includedirs 含 include 根目录）。
        self.run(
            f"{cxx} test.cpp -o test_probe {inc} "
            f"{libdir} -lKWeatherCore -lKF6Holidays -lKF6I18n "
            f"-lQt6Core -lQt6Network -lQt6Positioning -lQt6Qml -std=c++20"
        )

    def test(self):
        # 交叉 SDK / qemu 常无法运行 OHOS musl 动态链接二进制：只验编译+链接。
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return
        # OHOS: /system/bin/sh (mksh) 不能 exec ELF，用 CONFIG_SHELL bash 包一层
        # （libsigc/glibmm test_package 同款）。LD_LIBRARY_PATH 显式给出全部依赖 lib 目录。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        libs = []
        for _ref, d in self.dependencies.items():
            libs += list(d.cpp_info.libdirs)
            for _comp_name, comp in d.cpp_info.components.items():
                libs += list(comp.libdirs)
        # OHOS shared libs 需要 libc++_shared.so（SDK 提供，不是 Conan 包）。
        _sdk_libcxx = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(_sdk_libcxx):
            libs.append(_sdk_libcxx)
        libdirs = list(dict.fromkeys(l for l in libs if l and os.path.isabs(l)))

        # ki18n 依赖包的缓存二进制 libKF6I18nLocaleData.so 带相对路径
        # DT_NEEDED ../../bin/libKF6I18n.so（构建期相对链接固化进 ELF）。
        # loader 对含 / 的 NEEDED 按进程 cwd 解析、不走 LD_LIBRARY_PATH
        # 搜索，直接运行必挂。搭 staging 目录：probe 从 <stage>/a/b 下运行，
        # 把被相对引用的真实库符号链接到 <stage>/bin（上溯 2 级）与
        # <stage>/a/bin（上溯 1 级），使 ../../bin/libX.so / ../bin/libX.so
        # 形式的相对引用均可解析。
        # readelf 用主机工具（OHOS SDK 的 llvm/bin 只有交叉编译器，
        # 不含 readelf），按 PATH 探测 llvm-readelf / readelf。
        readelf = None
        for cand in ("llvm-readelf", "readelf"):
            for d in os.environ.get("PATH", "").split(os.pathsep):
                p = os.path.join(d, cand)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    readelf = p
                    break
            if readelf:
                break
        rel_needed = set()
        if readelf:
            for libdir in libdirs:
                if not os.path.isdir(libdir):
                    continue
                for fn in sorted(os.listdir(libdir)):
                    full = os.path.join(libdir, fn)
                    if not fn.endswith(".so") or os.path.isdir(full):
                        continue
                    # 用 subprocess 捕获 stdout：Conan self.run(output=True)
                    # 的返回值形态随版本变化（str / list[str]），直接解析不可靠。
                    try:
                        proc = subprocess.run(
                            [readelf, "-d", full],
                            capture_output=True, text=True)
                    except Exception:
                        continue
                    out = proc.stdout or ""
                    for line in out.splitlines():
                        if "(NEEDED)" in line and "[" in line:
                            name = line.split("[", 1)[1].split("]", 1)[0]
                            if "/" in name:
                                rel_needed.add(os.path.basename(name))
        self.output.info(
            "readelf={} rel_needed={}".format(readelf, sorted(rel_needed)))
        stage = os.path.join(self.build_folder, "runstage")
        dir_a = os.path.join(stage, "a")
        dir_b = os.path.join(dir_a, "b")
        os.makedirs(dir_b, exist_ok=True)
        for bindir in (os.path.join(stage, "bin"), os.path.join(dir_a, "bin")):
            os.makedirs(bindir, exist_ok=True)
            for base in sorted(rel_needed):
                dst = os.path.join(bindir, base)
                if os.path.lexists(dst):
                    continue
                for libdir in libdirs:
                    src = os.path.join(libdir, base)
                    if os.path.lexists(src):
                        os.symlink(src, dst)
                        break
        probe = os.path.join(self.build_folder, "test_probe")
        ld_path = ":".join(libdirs)
        run_cmd = "cd {} && {}".format(shlex.quote(dir_b), shlex.quote(probe))
        self.run("LD_LIBRARY_PATH={} {} -c {}".format(
            shlex.quote(ld_path), shlex.quote(bash), shlex.quote(run_cmd)))
