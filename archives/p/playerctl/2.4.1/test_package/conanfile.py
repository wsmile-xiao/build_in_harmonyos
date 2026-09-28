#!/usr/bin/env python3
"""test_package for playerctl 2.4.1 — 消费者视角验证（R34）。

真实依赖被测包的两条消费路径（详见 test_playerctl.c 的 A/B/C/D 四组断言）：
  1) 链接安装后的 libplayerctl.so，实际调用公共 C API
     （PLAYERCTL_VERSION_S 版本契约、playerctl_player_name_get_type /
      playerctl_source_get_type 类型注册、playerctl_player_name_copy+free
      深拷贝语义）；
  2) fork+exec 执行安装后的 bin/playerctl、bin/playerctld。

OHOS 要点（实测，见 notes.md）：
  * 被测 ELF 无 RUNPATH（上游 meson 未设置）→ 运行时靠 VirtualRunEnv 导出的
    LD_LIBRARY_PATH 才能解析 libplayerctl.so.2 / libglib-2.0.so.0。裸跑会
    报 "Error loading shared library"，属 conan 共享依赖 CLI 的预期行为。
  * 测试程序不写临时文件（OHOS /tmp 只读）、不调 system()/popen()
    （OHOS 无 /bin/sh），全部 fork+execv。
  * 编译器优先取 tools.build:compiler_executables（OHOS profile 指向
    /data/service/hnp/bin/clang），避免裸名 clang 探测失败。
  * 头文件路径：<playerctl/playerctl.h> 直接 include <glib-object.h>，消费者
    必须同时具备 glib 的公开头目录。glib 的两个公开头目录不是 <prefix>/include
    的子目录（pkg-config Cflags 正是 -I${includedir}/glib-2.0
    -I${libdir}/glib-2.0/include），而 conan 组件化包在根 cpp_info 上不暴露
    目录，故这里「cpp_info 通用路径 + glib 布局兜底」双取并集：多余的 -I
    对编译无副作用，缺一个则编译失败。
"""

import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

# glib 公开头的非默认安装位置（与 glib 自身 .pc 的 Cflags 一致）
_GLIB_EXTRA_INCLUDE_SUBDIRS = (
    os.path.join("include", "glib-2.0"),
    os.path.join("lib", "glib-2.0", "include"),
)


class PlayerctlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dependency_folder_of(self, name):
        """按名解析（含传递）依赖的 package_folder，找不到返回 None。"""
        try:
            return self.dependencies[name].package_folder
        except Exception:
            pass
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == name:
                return dependency.package_folder
        return None

    def _collect_include_and_lib_dirs(self):
        include_dirs = []
        lib_dirs = []

        def add_includes(folder, dirs):
            for relative in dirs or []:
                candidate = relative if os.path.isabs(relative) \
                    else os.path.join(folder, relative)
                if os.path.isdir(candidate):
                    include_dirs.append(candidate)

        def add_glib_layout(folder):
            for relative in _GLIB_EXTRA_INCLUDE_SUBDIRS:
                candidate = os.path.join(folder, relative)
                if os.path.isdir(candidate):
                    include_dirs.append(candidate)

        for dependency in self.dependencies.host.values():
            folder = dependency.package_folder
            if not folder:
                continue
            standard_include = os.path.join(folder, "include")
            if os.path.isdir(standard_include):
                include_dirs.append(standard_include)
            standard_lib = os.path.join(folder, "lib")
            if os.path.isdir(standard_lib):
                lib_dirs.append(standard_lib)

            info = dependency.cpp_info
            try:
                add_includes(folder, info.includedirs)
            except Exception:
                pass
            # 组件化依赖（如 glib）的目录挂在各组件上
            try:
                for component in info.components.values():
                    add_includes(folder, component.includedirs)
            except Exception:
                pass
            add_glib_layout(folder)

        def dedupe(items):
            seen = set()
            unique = []
            for item in items:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)
            return unique

        return dedupe(include_dirs), dedupe(lib_dirs)

    def build(self):
        import subprocess

        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or shutil.which("cc")
        if not cc:
            raise ConanException("no C compiler available for the test_package")

        playerctl_folder = self.dependencies["playerctl"].package_folder
        include_dirs, lib_dirs = self._collect_include_and_lib_dirs()
        include_dirs.insert(0, os.path.join(playerctl_folder, "include"))

        flags = "".join(' -I"%s"' % d for d in include_dirs)
        flags += "".join(' -L"%s"' % d for d in lib_dirs)
        compile_cmd = ('"%s" -O2 -Wall%s "%s" -lplayerctl -lgobject-2.0 -lglib-2.0'
                       ' -lgio-2.0 -lm -o test_playerctl'
                       % (cc, flags, os.path.join(self.source_folder, "test_playerctl.c")))

        # 本沙箱（HMDFS）上 conan self.run() 的实时管道路径会间歇性地让
        # clang 静默 exit 1（零诊断输出；同命令手工执行必过）——即知识条目
        # DRAFT-zmusic-1.3.0 记录的 self.run 静默失败问题。改用
        # subprocess.run(capture_output=True) 执行（zmusic 已验证解法），
        # 并显式套用 profile [buildenv]（clang 自身依赖其 LD_LIBRARY_PATH），
        # 保留 3 次重试 + stderr 捕获回显。
        log_path = os.path.join(self.build_folder, "compile-debug.log")
        out_bin = os.path.join(self.build_folder, "test_playerctl")
        run_env = dict(os.environ)
        try:
            run_env.update({key: str(value) for key, value
                            in self.buildenv.vars(self).items()})
        except Exception:
            pass
        compiled = False
        for attempt in (1, 2, 3):
            if attempt > 1:
                time.sleep(2)
                self.output.warning("test_package compile retry #%d" % attempt)
            proc = subprocess.run('%s 2>"%s"' % (compile_cmd, log_path),
                                  shell=True, capture_output=True, text=True,
                                  cwd=self.build_folder, env=run_env)
            if proc.returncode == 0 and os.path.isfile(out_bin):
                compiled = True
                break
            self.output.warning("compile attempt %d failed (rc=%d)%s"
                                % (attempt, proc.returncode,
                                   (" stderr: %s" % proc.stderr.strip()[:400]
                                    if proc.stderr.strip() else "")))
            if os.path.isfile(log_path):
                content = open(log_path, encoding="utf-8", errors="replace").read()
                if content:
                    self.output.warning("clang stderr (attempt %d): %s"
                                        % (attempt, content.strip()))
        if not compiled:
            raise ConanException("test_package compile failed after 3 attempts")

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run: cross-compiled package (can_run=False)")
            return
        bindir = os.path.join(self.dependencies["playerctl"].package_folder, "bin")
        # env="conanrun"：显式应用 VirtualRunEnv 生成的环境脚本。
        # 被测 ELF 与测试程序均无 RUNPATH，缺 LD_LIBRARY_PATH 会报
        # "Error loading shared library libplayerctl.so.2" 并以 127 退出。
        self.run(
            '"%s" "%s"' % (os.path.join(self.build_folder, "test_playerctl"), bindir),
            cwd=self.build_folder,
            env="conanrun",
        )
