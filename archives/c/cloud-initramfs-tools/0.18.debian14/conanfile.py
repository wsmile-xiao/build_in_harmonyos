#!/usr/bin/env python3
"""cloud-initramfs-tools 0.18.debian14 —— Debian 原生 initramfs-tools 云镜像扩展包（纯 POSIX shell，无编译）。

上游交付物（Debian 原生包，一个源包产出 4 个二进制包，全部 Architecture: all）：
  overlayroot                    : 在只读根之上叠加 overlayfs（tmpfs / blockdev / dmcrypt 三种后端）
  cloud-initramfs-growroot       : 首次启动把根分区扩展到磁盘末尾
  cloud-initramfs-rescuevol      : 存在 LABEL=RESCUE_VOL 的分区时优先从该卷启动
  cloud-initramfs-dyn-netconf    : 把 initramfs 期间配置过的网卡写成 /run/network/interfaces
安装内容（上游 Makefile 的 install 目标，实测 14 个文件）：
  /usr/share/initramfs-tools/hooks/{overlayroot,growroot,rescuevol,cloud-initramfs-dyn-netconf}
  /usr/share/initramfs-tools/scripts/{init-top,init-bottom,local-bottom,local-premount}/...
  /usr/share/initramfs-tools/conf-hooks.d/overlayroot
  /etc/overlayroot.conf、/etc/update-motd.d/97-overlayroot
  /usr/sbin/overlayroot-chroot、/usr/share/man/man8/overlayroot-chroot.8

OHOS 适配（2 处，见 patches/ 与 notes.md）：
  构建期（无源码改动）：OHOS 用户态由 Toybox 提供，不暴露独立 install(1) 命令
  （`command -v install` 无输出；busybox 内含 install applet 但无同名入口），
  上游 `make install` 直接 `/bin/sh: install: inaccessible or not found` → Error 127。
  build() 生成一个指向平台 busybox 的 install shim 并前置 PATH，使上游 Makefile 原样可用。

  运行期（补丁 1 处）：打包的可执行件 overlayroot-chroot 依赖 umount(1)/chroot(1)，
  同属「applet 存在但无同名入口」缺失集。补丁加入 xcmd()：优先按原名调用
  （在完整系统上与上游行为逐字一致），原名缺失时回退 `busybox <applet>`。
  无平台宏、无条件编译，未改变任何调用语义。

R38：本包安装可执行文件（bin/overlayroot-chroot）→ 软件级 commands.json。
R26/R33：不适用（无原生库、无编译命令）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 上游 Makefile `install:` 目标实测落地的文件（相对 DESTDIR），用于构建后完整性校验
EXPECTED_INSTALL = (
    "usr/share/initramfs-tools/hooks/overlayroot",
    "usr/share/initramfs-tools/hooks/growroot",
    "usr/share/initramfs-tools/hooks/rescuevol",
    "usr/share/initramfs-tools/hooks/cloud-initramfs-dyn-netconf",
    "usr/share/initramfs-tools/scripts/init-bottom/overlayroot",
    "usr/share/initramfs-tools/scripts/init-bottom/cloud-initramfs-dyn-netconf",
    "usr/share/initramfs-tools/scripts/init-top/cloud-initramfs-dyn-netconf",
    "usr/share/initramfs-tools/scripts/local-bottom/growroot",
    "usr/share/initramfs-tools/scripts/local-premount/rescuevol",
    "usr/share/initramfs-tools/conf-hooks.d/overlayroot",
    "etc/overlayroot.conf",
    "etc/update-motd.d/97-overlayroot",
    "usr/sbin/overlayroot-chroot",
    "usr/share/man/man8/overlayroot-chroot.8",
)


class CloudInitramfsToolsConan(ConanFile):
    name = "cloud-initramfs-tools"
    version = "0.18.debian14"
    description = ("initramfs-tools modules for cloud images (overlayroot, growroot, "
                   "rescuevol, dyn-netconf)")
    license = "GPL-3.0-or-later"
    homepage = "https://launchpad.net/cloud-initramfs-tools"
    url = "https://salsa.debian.org/cloud-team/cloud-initramfs-tools"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS 与 Linux 同为 ELF/POSIX shell 用户态，二者都受支持
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cloud-initramfs-tools requires Linux or OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _install_shim_dir(self):
        """OHOS 没有独立的 install(1) 命令：用平台 busybox 的 install applet 建同名入口。

        返回 shim 目录；平台自带 install(1)（如常规 Linux coreutils）时返回 None。
        """
        if shutil.which("install"):
            return None
        busybox = shutil.which("busybox")
        if busybox is None:
            for candidate in ("/usr/bin/busybox",
                              "/bin/busybox",
                              "/data/service/hnp/bin/busybox"):
                if os.path.isfile(candidate):
                    busybox = candidate
                    break
        if busybox is None:
            raise ConanException(
                "cloud-initramfs-tools: 平台既无 install(1) 也无 busybox —— "
                "上游 Makefile 的 install: 目标无法执行"
            )
        shim_dir = os.path.join(self.build_folder, "install-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "install")
        # HMDFS 上软链接不可覆盖（ln -sf 失效），只在缺失时创建
        if not os.path.lexists(shim):
            os.symlink(busybox, shim)
        return shim_dir

    def build(self):
        apply_conandata_patches(self)

        staging = os.path.join(self.build_folder, "staging")
        shim_dir = self._install_shim_dir()
        # R33: 只前置 PATH，不改写编译器/标志（本包无编译步骤）
        prefix = f'export PATH="{shim_dir}:$PATH"; ' if shim_dir else ""
        self.run(f"{prefix}make install DESTDIR={staging}", cwd=self.source_folder)

        missing = [rel for rel in EXPECTED_INSTALL
                   if not os.path.exists(os.path.join(staging, rel))]
        if missing:
            raise ConanException(
                "cloud-initramfs-tools: `make install` 未产出预期文件: "
                + ", ".join(missing)
            )

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        hooks = os.path.join("share", "initramfs-tools")
        # initramfs 钩子与阶段脚本（保持上游 usr/share/initramfs-tools 布局）
        copy(self, "hooks/*", src=os.path.join(staging, "usr", "share", "initramfs-tools"),
             dst=os.path.join(self.package_folder, hooks))
        copy(self, "scripts/*", src=os.path.join(staging, "usr", "share", "initramfs-tools"),
             dst=os.path.join(self.package_folder, hooks))
        copy(self, "conf-hooks.d/*", src=os.path.join(staging, "usr", "share", "initramfs-tools"),
             dst=os.path.join(self.package_folder, hooks))
        # 唯一可执行件 → bin/（conanrun 注入 PATH）
        copy(self, "overlayroot-chroot", src=os.path.join(staging, "usr", "sbin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "overlayroot-chroot.8", src=os.path.join(staging, "usr", "share", "man", "man8"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))
        # OHOS 的 /etc 是只读文件系统：配置与 motd 片段放包内 res/，由 runenv 变量指向
        copy(self, "overlayroot.conf", src=os.path.join(staging, "etc"),
             dst=os.path.join(self.package_folder, "res", "etc"))
        copy(self, "97-overlayroot", src=os.path.join(staging, "etc", "update-motd.d"),
             dst=os.path.join(self.package_folder, "res", "etc", "update-motd.d"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        hooks_dir = os.path.join(self.package_folder, "share", "initramfs-tools", "hooks")
        self.buildenv_info.define_path("CLOUD_INITRAMFS_TOOLS_HOOKS", hooks_dir)
        self.runenv_info.define_path("CLOUD_INITRAMFS_TOOLS_HOOKS", hooks_dir)
        # OHOS /etc 只读：包内提供 overlayroot.conf，用户可自行复制到可写位置
        self.runenv_info.define(
            "OVERLAYROOT_CONF",
            os.path.join(self.package_folder, "res", "etc", "overlayroot.conf"),
        )
