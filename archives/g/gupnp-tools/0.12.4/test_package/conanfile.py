#!/usr/bin/env python3
"""Conan test_package for gupnp-tools 0.12.4 — Conan L1 official test.

gupnp-tools is an application package: the real product IS the binaries
(gssdp-discover, gupnp-event-dumper). R34 compliance = actually executing
the packaged binaries and asserting on their behaviour:
  - gssdp-discover --help prints real GSSDP option help and exits 0
  - gssdp-discover -n 1 runs a real SSDP discovery (1 s window) and exits 0
  - gupnp-event-dumper has no option parser upstream (its main() blocks in a
    GMainLoop), so it is run boundedly and must shut down cleanly on SIGTERM
    (exit 0) — proving the binary started and resolved the whole gupnp stack.
The binaries are wrapped with bash because OHOS /system/bin/sh (mksh)
cannot exec ELF binaries directly (gssdp/gupnp same handling).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GupnpToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # 显式列出 generators 会替换 conan 默认集，必须带上 VirtualRunEnv /
    # VirtualBuildEnv（libsoup3/gssdp/gupnp 同款实撞记录）。
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明传递依赖：gupnp-tools 的可执行文件 NEEDED libsoup-3.0.so /
        # libgssdp-1.6.so / libgupnp-1.6.so / libxml2.so（g_* 域由 libsoup-3.0.so
        # 唯一提供），必须让 conan 解析出各 package_folder 才能拼 LD_LIBRARY_PATH
        #（gssdp/gupnp test_package 同款记录）。
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r1")
        self.requires("gssdp/1.6.6")
        self.requires("gupnp/1.6.8")
        self.requires("libxml2/2.15.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # 收集全部依赖（含传递的 glib2/libsoup3/gssdp/gupnp/libxml2 及各自的
        # 传递依赖）的 libdirs，拼成 LD_LIBRARY_PATH。
        _seen, libdirs = set(), []
        for _r, _d in self.dependencies.items():
            _k = str(getattr(getattr(_r, "ref", _r), "ref", _r))
            if _k in _seen:
                continue
            _seen.add(_k)
            _base = getattr(_d, "package_folder", None) or ""
            for _p in _d.cpp_info.libdirs:
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs:
                    libdirs.append(_p)
        syslib = "/storage/Users/currentUser/usr/local/lib"
        if syslib not in libdirs:
            libdirs.append(syslib)
        ldpath = os.pathsep.join(libdirs)
        # 被测包（gupnp-tools）的 bin 目录——绝对路径调用，不依赖 PATH。
        _tools_bindir = ""
        for _r, _d in self.dependencies.items():
            _ref = str(getattr(getattr(_r, "ref", _r), "ref", _r))
            if _ref.startswith("gupnp-tools/"):
                _base = getattr(_d, "package_folder", None) or ""
                for _b in (_d.cpp_info.bindirs or ["bin"]):
                    _p = _b if os.path.isabs(_b) else os.path.join(_base, _b)
                    if os.path.isdir(_p):
                        _tools_bindir = _p
                        break
                break
        assert _tools_bindir, "gupnp-tools package bin/ not found in dependencies"
        discover = os.path.join(_tools_bindir, "gssdp-discover")
        dumper = os.path.join(_tools_bindir, "gupnp-event-dumper")
        ld = (f'export LD_LIBRARY_PATH="{ldpath}'
              f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; ')
        # ⭐ R34：直接执行被测包安装的可执行文件（真实二进制冒烟，非 print 空壳）。
        # 1) gssdp-discover --help：真实 GSSDP CLI 参数帮助（GOption，exit 0）
        self.run(f'{bash} -c \'{ld}"{discover}" --help\'', env="conanrun")
        # 2) gssdp-discover -n 1：真实 SSDP 发现，1 秒窗口后正常退出（exit 0）
        self.run(f'{bash} -c \'{ld}"{discover}" -n 1\'', env="conanrun")
        # 3) gupnp-event-dumper：上游**没有**参数解析（main() 直接建
        #    GUPnPContextManager 并 g_main_loop_run），所以 `--help` 不会退出、
        #    会永久阻塞。这里改为有界运行：后台启动，3 秒后发 SIGTERM；该工具
        #    注册了 SIGTERM→g_main_loop_quit，应干净退出（exit 0）。退出码非 0
        #    （崩溃/库解析失败/提前退出）即判定失败——这同时证明了二进制能启动、
        #    能解析整条 gupnp 依赖栈并跑起主循环。
        self.run(
            f'{bash} -c \'{ld}"{dumper}" & p=$!; sleep 3; '
            f'if kill -0 $p 2>/dev/null; then kill -TERM $p; fi; wait $p; exit $?\'',
            env="conanrun")
