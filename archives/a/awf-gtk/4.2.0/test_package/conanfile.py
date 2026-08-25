#!/usr/bin/env python3
"""Conan test_package for awf-gtk 4.2.0 (application / executable smoke).

awf-gtk4 is a GTK4 GUI application. On a headless CI worker the full GUI
cannot open a display, so the verifiable consumer contract is the CLI query
path: `awf-gtk4 --version` must print the upstream version. The recipe patches
the source so the --version/--list paths flush stdout and `_exit(0)` before
GTK teardown, making them exit 0 (E252 lawful asset boundary: CLI query path
usable headless; interactive GUI rendering needs a display session).

The binary is linked against the installed OpenHarmony GTK4 system prefix, so
the test must add that prefix's lib/external + lib dirs to LD_LIBRARY_PATH
before running it (the conan package only owns bin/awf-gtk4 + share data).
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class AwfgtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _system_prefix(self):
        for env_name in ("GTK_PREFIX", "DEFAULT_PREFIX"):
            value = os.environ.get(env_name)
            if value:
                prefix = os.path.normpath(value)
                if self._gtk_pc_exists(prefix):
                    return prefix
        default = "/storage/Users/currentUser/usr/local"
        if self._gtk_pc_exists(default):
            return default
        for pc in sorted(glob.glob("/data/service/hnp/**/gtk4.pc", recursive=True)):
            prefix = os.path.dirname(os.path.dirname(pc))
            if self._gtk_pc_exists(prefix):
                return prefix
        return default

    def _gtk_pc_exists(self, prefix):
        return (
            os.path.isfile(os.path.join(prefix, "lib", "pkgconfig", "gtk4.pc"))
            or os.path.isfile(os.path.join(prefix, "share", "pkgconfig", "gtk4.pc"))
        )

    def test(self):
        dep = self.dependencies["awf-gtk"]
        bindir = os.path.join(dep.package_folder, "bin")
        binary = os.path.join(bindir, "awf-gtk4")
        if not os.path.isfile(binary):
            raise RuntimeError("awf-gtk4 not found in package bin/: {}".format(binary))
        self.output.info("package bin: {}".format(binary))

        prefix = self._system_prefix()
        env = Environment()
        # prepend 依次前插，最终顺序 external → lib → hnp（external 优先，
        # 含签名的新版 glib/pango/libintl/libnotify；hnp 的旧 libintl 若在前
        # 会遮蔽 external，导致 libgtk-4 重定位缺 libintl_bindtextdomain 等）
        for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*", "libintl.so*"):
            for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                env.prepend_path("LD_LIBRARY_PATH", os.path.dirname(match))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib", "external"))

        # conan 依赖（cairo/graphene/libnotify）的 libdirs 显式注入（兜底）：
        # CI 上 external 目录不含 libnotify.so.4（它是 conan 包而非
        # cmd-pkgs），若 conanrun env 未把其 libdir 放入 LD_LIBRARY_PATH，
        # awf-gtk4 运行时重定位报 notify_* symbol not found（CI #30719/
        # #30745/#30755）。
        # 注意必须用 append_path（追加到末尾）而非 prepend_path：上面的
        # prepend 是前插，若 conan deps 在 external 之后 prepend，反而会把
        # conan 缓存库（未签名/旧版 libglib/libz/libpng）插到 external
        # 前面，遮蔽 external 里的签名库，导致 loader 从 lib 顶层加载残留
        # 坏库（CI #30760：Error loading shared library libglib-2.0.so）。
        # append 使 external → lib → hnp → conan deps，签名库始终优先。
        for dep_name in ("cairo", "graphene", "libnotify"):
            dep = self.dependencies.get(dep_name)
            if not dep or not getattr(dep, "package_folder", None):
                continue
            for libdir in dep.cpp_info.libdirs or ["lib"]:
                full = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
                if os.path.isdir(full):
                    env.append_path("LD_LIBRARY_PATH", full)

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        with env.vars(self).apply():
            self.run("{} {} {}".format(bash, script, binary), env="conanrun")
