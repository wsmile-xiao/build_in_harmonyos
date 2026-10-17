#!/usr/bin/env python3
"""Conan test_package for kteatime 26.04.0.

上游 kteatime 26.04.0 无任何测试用例（无 tests/ 目录、CMakeLists 无 test
目标，MANIFEST 如实申报 0）。本 test_package 为适配后补全的 smoke test：
真实运行安装后的 kteatime 二进制。

- QT_QPA_PLATFORM=offscreen：Qt6 在无显示环境下可用（qtbase 配方自身测试
  同款设置，offscreen 平台插件随 qtbase 安装）；
- kteatime --version：经 KAboutData 打印版本并退出 0，验证二进制可执行、
  Qt6/KF6 共享库依赖经 conanrun env（LD_LIBRARY_PATH）完整解析；
- timeout 30 兜底防挂起（异常则退出码非 0 → FAIL，如实报告）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment


class KteatimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _reconstruct_kf6_rpaths(self):
        """KF6 依赖包烤死的坏 RPATH 重构（CI #60939/#60984 实测）。

        根因：kcrash/ksonnet/kconfigwidgets/kiconthemes 等 KF6 包构建时
        CONAN_HOME 与当前 CI 缓存不同，自身 RPATH 烤死为：
        1) ~/.conan2/p/<hash>/p/lib/... 过期绝对路径（当前缓存
           ~/.cache/conan2/p/<同 hash>/p/lib/ 有真实文件）；
        2) ../../bin/... 相对路径（加载器按进程 CWD 解析）。
        主二进制 RPATH 注入（CMAKE_BUILD_RPATH/INSTALL_RPATH）对传递依赖
        无效（#60984 实测仍 127）。重构：
        - ~/.conan2 -> 缓存 home 软链（哈希一致，绝对路径条目命中真实文件）；
        - 依赖 lib 目录内未版本化 .so 软链原地替换为真实文件
          （HMDFS 软链跟随不可靠，真实复制才稳）；
        - <cache>/bin 装入全部依赖未版本化 .so 真实文件，并从受控 CWD
          （<cache>/recon/kk）运行 → ../../bin 解析到 <cache>/bin。
        返回受控 CWD（失败时 None，退回原 CWD 运行）。
        """
        cache_home = None
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf and os.path.isdir(os.path.join(pf, "lib")):
                # <cache>/p/<hash>/p -> <cache>
                cache_home = os.path.dirname(
                    os.path.dirname(os.path.dirname(pf)))
                break
        if not cache_home:
            self.output.warning("[recon] 无法定位 conan 缓存 home，跳过重构")
            return None
        # 1) ~/.conan2 -> 缓存 home（KF6 烤死的 .conan2 绝对路径在
        #    <HOME>/.conan2，不是 .cache 下；#60996 实测曾误建到 .cache/.conan2）
        conan2_link = os.path.join(
            os.path.dirname(os.path.dirname(cache_home)), ".conan2")
        try:
            if os.path.islink(conan2_link):
                if os.path.realpath(conan2_link) != cache_home:
                    os.unlink(conan2_link)
                    os.symlink(cache_home, conan2_link)
            elif not os.path.exists(conan2_link):
                os.symlink(cache_home, conan2_link)
            self.output.info(f"[recon] {conan2_link} -> {cache_home}")
        except OSError as e:
            self.output.warning(f"[recon] .conan2 软链失败: {e}")
        # 2)+3) 依赖 lib 目录原地真实化 + <cache>/bin 补齐
        bin_dir = os.path.join(cache_home, "bin")
        try:
            os.makedirs(bin_dir, exist_ok=True)
        except OSError as e:
            self.output.warning(f"[recon] 创建 {bin_dir} 失败: {e}")
            return None
        for dep in self.dependencies.values():
            lib_dir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
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
                        os.chown(src, os.getuid(), os.getgid())
                        os.chmod(src, 0o755)
                    except OSError as e:
                        self.output.warning(f"[recon] 原地真实化 {name} 失败: {e}")
                for dst_dir in (bin_dir,):
                    dst = os.path.join(dst_dir, name)
                    if os.path.lexists(dst):
                        continue
                    try:
                        shutil.copy2(os.path.join(lib_dir, name), dst)
                        os.chmod(dst, 0o755)
                    except OSError as e:
                        self.output.warning(f"[recon] 复制 {name} 到 bin 失败: {e}")
        recon_cwd = os.path.join(cache_home, "recon", "kk")
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
        # conanrun 的 PATH 在部分 worker 场景未包含被测试包 bin 目录
        # （CI #60877 实测 subprocess 报 [Errno 2] 'kteatime'），显式把安装后
        # 的二进制绝对路径经 KTEATIME_BIN 传给冒烟脚本，不依赖 PATH 查找。
        kteatime = self.dependencies["kteatime"]
        if kteatime.package_folder:
            env.define("KTEATIME_BIN",
                       os.path.join(kteatime.package_folder, "bin", "kteatime"))
        with env.vars(self).apply():
            recon_cwd = self._reconstruct_kf6_rpaths()
            # 真实执行消费者冒烟测试脚本 test_kteatime.py（L0c 测试源文件）：
            # 运行安装后的 kteatime --version，验证二进制可执行、Qt6/KF6
            # 共享库依赖完整解析；非 0 退出码或超时 → FAIL（如实报告，不隐藏；
            # 超时由脚本内 subprocess.run(timeout=60) 兜底，OHOS worker 无
            # shell timeout 命令）。
            # 受控 CWD 下脚本需绝对路径（#60996 实测 cwd 变更后相对路径
            # test_kteatime.py 找不到 [Errno 2]）
            script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "test_kteatime.py")
            self.run(f"python3 {script}", env="conanrun", cwd=recon_cwd)
