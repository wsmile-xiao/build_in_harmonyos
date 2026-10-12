#!/usr/bin/env python3
"""test_package for libtk-img (Img / TkImg) 2.1.1 on OHOS.

R34 「消费者可用性」验证 —— 把 libtk-img 当成**外部消费方**看待：

  1. 用 tcl/9.0.3.2 包自带的 tclsh9.0（OHOS aarch64 原生解释器）真实启动；
  2. 仅通过包对外暴露的机制使用它：`auto_path` / `pkgIndex.tcl` → `load`
     → `package require Img`；
  3. 逐个 dlopen 全部 19 个格式处理器（img::bmp / img::png / img::window …）
     与 4 个内置 compat 包装（zlibtcl / pngtcl / tifftcl / jpegtcl）；
  4. 完成一次真实的图像往返（photo 生成 → BMP 写盘 → 读回 → 逐像素比较）。

上游 tcltest 套件（tests/*.test）已由 recipe 的 build() 步真实执行
（`_run_upstream_tests`，等价于上游 `make tcltests`），其统计**不由本
test_package 替代**；本文件只回答「包在 OHOS 上作为消费者依赖是否真的可用」。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

# 消费者测试脚本会真实 dlopen 的格式处理器
HANDLER_PKGS = (
    "img::base", "img::bmp", "img::gif", "img::ico", "img::jpeg",
    "img::pcx", "img::pixmap", "img::png", "img::ppm", "img::ps",
    "img::sgi", "img::sun", "img::tga", "img::tiff", "img::window",
    "img::xbm", "img::xpm", "img::dted", "img::raw", "img::flir",
)


class LibtkImgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # tclsh9.0 解释器（消费者） + Tk 运行期 + window/xpm 处理器链接的 X11
        self.requires("tcl/9.0.3.2")
        self.requires("tk/9.0.3.2")
        self.requires("libx11/1.8.13")

    # ------------------------------------------------------------------
    @staticmethod
    def _find_img_runtime_dir(pkg_folder):
        """TEA 安装把全部处理器 .so + 合并后的 pkgIndex.tcl 放在
        `<prefix>/lib/Img<version>/`。这里按内容查找，避免硬编码版本号。"""
        for root, _dirs, files in os.walk(pkg_folder):
            if "pkgIndex.tcl" not in files:
                continue
            if any(f.startswith("libtcl9tkimg") and f.endswith(".so")
                   for f in files):
                return root
        return None

    def _runtime_lib_dirs(self):
        """消费者运行所需的全部 lib 目录（含 libX11 的传递依赖 libxcb 等）。"""
        dirs = []
        for name in ("tcl", "tk", "libx11", "libxcb", "libxau", "libxdmcp"):
            try:
                folder = self.dependencies[name].package_folder
            except Exception:
                continue
            lib = os.path.join(folder, "lib")
            if os.path.isdir(lib) and lib not in dirs:
                dirs.append(lib)
        return dirs

    def test(self):
        if not can_run(self):
            self.output.warning("can_run=False（交叉构建），跳过消费者运行期测试")
            return

        tcl_pkg = self.dependencies["tcl"].package_folder
        img_pkg = self.dependencies[self.tested_reference_str].package_folder

        tclsh = os.path.join(tcl_pkg, "bin", "tclsh9.0")
        if not os.path.isfile(tclsh):
            raise ConanException(f"tclsh9.0 未在 tcl 包中找到: {tclsh}")

        img_libdir = self._find_img_runtime_dir(img_pkg)
        if not img_libdir:
            raise ConanException(
                f"未在 libtk-img 包中找到 Img 运行时目录（须同时含 pkgIndex.tcl "
                f"与 libtcl9tkimg*.so）: {img_pkg}")
        n_so = len([f for f in os.listdir(img_libdir) if f.endswith(".so")])
        self.output.info(f"Img 运行时目录: {img_libdir}（{n_so} 个 .so）")

        lib_dirs = self._runtime_lib_dirs()
        tcl_path = self.dependencies["tcl"].package_folder
        tk_path = self.dependencies["tk"].package_folder
        tcllib = " ".join([img_libdir, os.path.join(tcl_path, "lib"),
                           os.path.join(tk_path, "lib")])

        script = os.path.join(self.source_folder, "test_consumer.tcl")
        runner = os.path.join(self.source_folder, "run_test.sh")
        if not os.path.isfile(runner):
            raise ConanException(f"test_package 入口脚本缺失: {runner}")
        timeout_bin = "/bin/timeout" if os.path.exists("/bin/timeout") else "timeout"
        # 环境变量直接内联在命令里：ConanFile.run(env=[...]) 的列表语义是
        # “env 脚本文件名”而非 "VAR=VALUE"，这里显式内联更可预期。
        # 入口走 run_test.sh（仓库 test_package 惯例；宿主机无 /bin/bash，故用 /bin/sh）。
        cmd = (f'LD_LIBRARY_PATH="{":".join(lib_dirs)}" '
               f'TCLLIBPATH="{tcllib}" '
               f'{timeout_bin} 600 /bin/sh "{runner}" '
               f'"{tclsh}" "{script}" "{img_libdir}"')
        self.output.info(f"消费者测试命令: {cmd}")
        self.run(cmd)
