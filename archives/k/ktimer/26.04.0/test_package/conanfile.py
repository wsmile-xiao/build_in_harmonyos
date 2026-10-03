#!/usr/bin/env python3
"""Conan test_package for ktimer 26.04.0.

上游 ktimer 26.04.0 无任何测试用例（无 tests/ 目录、CMakeLists 无 add_test /
enable_testing / ecm_add_tests，MANIFEST 如实申报 0）。本 test_package 为适配后
补全的消费者冒烟测试：真实运行安装后的 ktimer 二进制。

- QT_QPA_PLATFORM=offscreen：Qt6 无显示环境可用（qtbase 自身测试同款）；
- ktimer --version：KAboutData::processCommandLine 在 KDBusService / 托盘 /
  主窗口创建**之前**处理 --version 并退出 0，验证二进制可执行、Qt6/KF6/
  DBus 共享库依赖经 conanrun env 完整解析（不会触达会话总线与托盘）；
- KF6 依赖包烤死的坏 RPATH 由 _reconstruct_kf6_rpaths 重构
  （kcrash/kconfigwidgets 等包构建时 CONAN_HOME 与当前缓存不同，自身 RPATH
  烤成过期绝对路径或 ../../bin 相对路径 —— kteatime 26.04.0 先例）；
- 超时由脚本内 subprocess.run(timeout=60) 兜底（OHOS worker 无 shell timeout）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class KtimerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _reconstruct_kf6_rpaths(self):
        """KF6 依赖包烤死的坏 RPATH 重构（kteatime 26.04.0 先例，
        CI #60939/#60984/#60996 实测）。返回受控 CWD，失败返回 None。"""
        cache_home = None
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf and os.path.isdir(os.path.join(pf, "lib")):
                cache_home = os.path.dirname(
                    os.path.dirname(os.path.dirname(pf)))
                break
        if not cache_home:
            self.output.warning("[recon] 无法定位 conan 缓存 home，跳过重构")
            return None
        conan2_link = os.path.join(
            os.path.dirname(os.path.dirname(cache_home)), ".conan2")
        try:
            if os.path.islink(conan2_link):
                if os.path.realpath(conan2_link) != cache_home:
                    os.unlink(conan2_link)
                    os.symlink(cache_home, conan2_link)
            elif not os.path.exists(conan2_link):
                os.symlink(cache_home, conan2_link)
        except OSError as e:
            self.output.warning(f"[recon] .conan2 软链失败: {e}")
        bin_dir = os.path.join(cache_home, "bin")
        try:
            os.makedirs(bin_dir, exist_ok=True)
        except OSError as e:
            self.output.warning(f"[recon] 创建 {bin_dir} 失败: {e}")
            return None
        for dep in self.dependencies.values():
            lib_dir = (os.path.join(dep.package_folder, "lib")
                       if dep.package_folder else None)
            if not (lib_dir and os.path.isdir(lib_dir)):
                continue
            for name in sorted(os.listdir(lib_dir)):
                if not name.endswith(".so"):
                    continue
                src = os.path.join(lib_dir, name)
                if os.path.islink(src):
                    try:
                        real = os.path.realpath(src)
                        os.unlink(src)
                        shutil.copy2(real, src)
                        os.chmod(src, 0o755)
                    except OSError as e:
                        self.output.warning(
                            f"[recon] 原地真实化 {name} 失败: {e}")
                dst = os.path.join(bin_dir, name)
                if os.path.lexists(dst):
                    continue
                try:
                    shutil.copy2(src, dst)
                    os.chmod(dst, 0o755)
                except OSError as e:
                    self.output.warning(
                        f"[recon] 复制 {name} 到 bin 失败: {e}")
        recon_cwd = os.path.join(cache_home, "recon", "kt")
        try:
            os.makedirs(recon_cwd, exist_ok=True)
        except OSError as e:
            self.output.warning(f"[recon] 创建 {recon_cwd} 失败: {e}")
            return None
        self.output.info(f"[recon] 受控 CWD={recon_cwd}（../../bin -> {bin_dir}）")
        return recon_cwd

    def test(self):
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        # conanrun 的 PATH 在部分 worker 场景不含被测包 bin 目录
        # （CI #60877 实测 [Errno 2]），显式传绝对路径。
        ktimer = self.dependencies["ktimer"]
        if ktimer.package_folder:
            env.define("KTIMER_BIN",
                       os.path.join(ktimer.package_folder, "bin", "ktimer"))
        with env.vars(self).apply():
            recon_cwd = self._reconstruct_kf6_rpaths()
            script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "test_ktimer.py")
            self.run(f"python3 {script}", env="conanrun", cwd=recon_cwd)
