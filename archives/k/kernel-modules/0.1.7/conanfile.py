#!/usr/bin/env python3
"""Conan recipe — kernel-modules 0.1.7（Arch Linux 上游软件 kernel-modules-hook）。

kernel-modules-hook 是 Arch Linux 官方仓库软件（pkgver=0.1.7，arch=('any')）：
内核升级时用 libalpm（pacman）hook + rsync 备份/恢复 /usr/lib/modules，并用
systemd-tmpfiles 规则 + systemd oneshot 服务清理旧内核模块。上游为纯
POSIX shell/配置文件类工具，无 C/C++ 编译，无 tests/ 目录。

OHOS 无 libalpm/systemd 运行时，故按「数据/配置资源包」收录：
  - source()：多文件 dict 形式（仿 cute_files/1.0.0），每制品文件独立
    https 官方 raw URL + sha256；
  - build()：无编译；用 sh -n 校验两个 hook 内嵌的 Exec shell 命令可解析
    （参考先例 archives/a/akms/0.3.0 用 sh -n 校验脚本），systemd service 的
    ExecStart 为 bash 语法，用 bash -n 校验；
  - package()：5 个制品文件放入 share/kernel-modules-hook/，UNLICENSE 放入
    licenses/。
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches


def _extract_exec_cmd(text):
    """从 libalpm hook / systemd unit 的 Exec 行提取被引号包裹的 shell 命令体。

    支持两种上游格式：
      Exec = /bin/sh -c 'CMD'
      ExecStart=/bin/bash -exc 'CMD'
    并对 systemd ExecStart 转义做还原（$$ → $、\\' → '），使 CMD 还原为
    systemd 实际传给 shell 的原始命令。返回 None 表示未能提取（build()/test
    会据此报错，避免"假校验"）。
    """
    m = re.search(
        r"^\s*(?:Exec|ExecStart)\s*=\s*/bin/(?:sh|bash)\s+-[a-zA-Z]+\s+'(.+)'\s*$",
        text,
        flags=re.MULTILINE,
    )
    if not m:
        return None
    cmd = m.group(1)
    cmd = cmd.replace("$$", "$").replace("\\'", "'")
    return cmd


def _find_shell():
    """探测可用的 POSIX shell（CI/OHOS 沙箱可能无 /bin/sh，需探测 mksh/ash/dash 等）。"""
    for name in ("sh", "bash", "dash", "ash", "mksh", "ksh"):
        p = shutil.which(name)
        if p:
            return p
    for p in ("/system/bin/sh", "/system/bin/mksh", "/system/bin/bash",
              "/bin/sh", "/usr/bin/sh", "/usr/bin/ash", "/usr/bin/dash",
              "/system/bin/ash"):
        if os.path.exists(p):
            return p
    return None


class KernelModulesConan(ConanFile):
    name = "kernel-modules"
    version = "0.1.7"
    description = ("kernel-modules-hook — keep the system fully functional after a "
                   "kernel upgrade (libalpm hooks + systemd-tmpfiles + systemd service)")
    license = "Unlicense"
    homepage = "https://github.com/saber-nyan/kernel-modules-hook"
    url = "https://github.com/saber-nyan/kernel-modules-hook"
    topics = ("kernel", "kernel-modules", "libalpm", "pacman", "arch", "systemd")

    # 数据/配置资源包（libalpm hook + tmpfiles 规则 + systemd 服务）：无编译产物、
    # 无可执行 bin，本包不可直接运行；package_type=application 与参考先例
    # （akms/ausweisapp-nftrules）保持一致，软件级 commands.json 随之声明。
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kernel-modules supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        # 多文件 dict 形式（仿 archives/c/cute_files/1.0.0）：每制品文件独立 url+sha256
        for filename, data in self.conan_data["sources"].items():
            download(self, data["url"],
                     os.path.join(self.source_folder, filename),
                     sha256=data["sha256"])

    def build(self):
        apply_conandata_patches(self)  # 无补丁时空操作
        # 纯数据/配置包无编译；build() 校验上游配置内嵌 shell 命令语法可解析
        # （参考先例 archives/a/akms/0.3.0 用 sh -n 校验脚本）。
        hooks = {
            "10-linux-modules-pre.hook": "sh",
            "10-linux-modules-post.hook": "sh",
            "linux-modules-cleanup.service": "bash",  # ExecStart 为 bash 语法（[[ ]]）
        }
        # CI/OHOS 沙箱可能无 /bin/sh（PR #11026 曾因 FileNotFoundError: 'sh' 失败），
        # 用探测到的 shell 执行语法校验；完全无可用 shell 时跳过校验并提示
        # （本机 Linux 正常执行 sh -n / bash -n，非空壳）。
        for rel, shell in hooks.items():
            path = os.path.join(self.source_folder, rel)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            cmd = _extract_exec_cmd(text)
            if not cmd:
                raise ConanException(
                    f"{rel}: 未能从 Exec/ExecStart 行提取 shell 命令，校验失败")
            shell_bin = _find_shell() if shell == "sh" else shutil.which("bash")
            if not shell_bin:
                self.output.warning(
                    f"{rel}: 未找到可用 {shell}，跳过 {shell} -n 语法校验")
                continue
            self.run(f"{shell_bin} -n -c {shlex.quote(cmd)}", env="conanbuild")
            self.output.info(f"OK: {rel} 内嵌 shell 命令语法校验通过（{shell} -n）")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        # 5 个制品文件 → share/kernel-modules-hook/（聚合到 OHOS 无 libalpm/systemd
        # 运行时的共享目录，对应上游 PKGBUILD 的 usr/share/libalpm/hooks 等布局语义）；
        # UNLICENSE → licenses/（与 akms/cute_files 先例一致）。
        share_dir = os.path.join(pkg, "share", "kernel-modules-hook")
        os.makedirs(share_dir, exist_ok=True)
        for name in ("10-linux-modules-pre.hook",
                     "10-linux-modules-post.hook",
                     "linux-modules-cleanup.conf",
                     "linux-modules-cleanup.service"):
            shutil.copy2(os.path.join(src, name), os.path.join(share_dir, name))
        os.makedirs(os.path.join(pkg, "licenses"), exist_ok=True)
        shutil.copy2(os.path.join(src, "UNLICENSE"),
                     os.path.join(pkg, "licenses", "UNLICENSE"))

    def package_info(self):
        self.cpp_info.libs = []
