#!/usr/bin/env python3
"""Conan recipe — bc-ur 0.3.0 (Blockchain Commons UR Library, C++).

bc-ur 是 "Uniform Resources" (UR, BCR-2020-005) 编码的 C++ 参考实现，用于在
URI / QR Code 中传输结构化二进制数据（区块链钱包互操作场景）。

- 构建系统: autotools（发布 tarball 自带预生成 configure + 手写 Makefile.in）
- 产物: 静态库 libbc-ur.a + include/bc-ur/*.hpp 公开头（无可执行文件 → R38
  不适用，无需 commands.json）
- 依赖: 零第三方依赖，纯 C++17（内部自带 sha2/crc32/memzero 实现）
- 适配: OHOS PC (aarch64, clang 15 / libc++) 零补丁编译通过；上游 tag 0.3.0
  的 configure.ac 仍声明 AC_INIT 0.2.0（上游版本号未同步的文档瑕疵，见 notes.md）

R26: bc-ur 非系统同名库（系统无 libbc-ur），且上游构建系统仅产出静态库
（无 libtool/无 shared 目标），故声明 static-library 类型。

R01 修复（install 裸名头文件）: 手写 Makefile.in 的 install 规则以裸名引用
头文件（无 $(srcdir) 前缀），out-of-source 构建下 install 失败 → layout()
折叠 folders.build="." 强制 in-source。

R03 修复（config.status 临时目录 EACCES）: autoconf 的 config.status 以
`(umask 077 && mktemp -d ./confXXXXXX)` 创建 0700 临时目录并在其中写入
subs1.awk；OHOS HMDFS 不保留 POSIX 权限位（目录被归一化为 2771/760 或直接
拒绝写入），远端 CI 在 Conan 构建工作区（HMDFS 用户存储）上报
`config.status: ./conffHojbF/subs1.awk: Permission denied`。本配方在
build() 前探测构建目录所在文件系统是否保留 0700/exec 语义，不合格时把
autotools 构建复制迁移到保留 POSIX 权限的合格挂载点（tmpfs，如
/data/storage/el2/base，stat 实测 drwx------ 700）执行 configure/make/
install，再打包；无合格挂载点时回退原目录构建（HMDFS 严格设备上会复现
EACCES，属平台约束，恢复条件见 notes.md）。
"""
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 候选"保留 POSIX 权限"挂载点（tmpfs/ext4；HMDFS 不保留，不合格）
_QUALIFIED_MOUNT_BASES = (
    "/data/storage/el2/base",   # OHOS 标准 tmpfs，R02 实测保留 drwx------ 700
    "/data/local/tmp",
    "/storage/External",
    "/storage/userExternal",
)


class BcurConan(ConanFile):
    name = "bc-ur"
    version = "0.3.0"
    description = "Blockchain Commons UR (Uniform Resources) reference implementation in C++"
    license = "BSD-2-Clause-Patent"
    homepage = "https://github.com/BlockchainCommons/bc-ur"
    url = "https://github.com/BlockchainCommons/bc-ur"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # R01: 上游手写 Makefile（tarball 无 Makefile.am）的 install 规则以裸名
        # 引用头文件（无 $(srcdir) 前缀），out-of-source 下 install 在 build
        # 目录找不到头文件 → 强制 in-source 构建
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 无额外 configure 参数（R1 最少化；--prefix 等由 AutotoolsToolchain 注入）
        tc = AutotoolsToolchain(self)
        tc.generate()

    # ── R03: config.status 临时目录 EACCES（HMDFS 权限位）处理 ──

    def _toolchain_configure_args(self):
        """从 AutotoolsToolchain 生成的 conanbuild.conf 读取 configure_args，
        迁移构建时复刻与 Autotools helper 完全一致的 configure 调用。"""
        import configparser
        args = ""
        try:
            cp = configparser.ConfigParser()
            cp.read(os.path.join(self.generators_folder, "conanbuild.conf"))
            args = cp.get("toolchain", "configure_args", fallback="")
        except Exception:
            pass
        return args

    def _build_folder_needs_relocation(self):
        """构建目录所在文件系统是否保留 POSIX 0700/exec 语义。

        HMDFS 上 mkdtemp(0700) 的目录被归一化（本机实测 2771）或写入被拒
        （CI 实测 EACCES），config.status 的 umask-077 临时目录无法工作；
        返回 True 表示需要迁移到合格挂载点。"""
        bf = self.build_folder
        probe = None
        try:
            probe = os.path.join(bf, ".bc-ur-confprobe-{}".format(os.getpid()))
            os.mkdir(probe, 0o700)
            if stat.S_IMODE(os.stat(probe).st_mode) != 0o700:
                return True   # 权限位被归一化（HMDFS 特征）
            s = os.path.join(probe, "x.sh")
            with open(s, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(s, 0o700)
            subprocess.run(["./x.sh"], cwd=probe, check=True)   # exec 探测
            return False
        except Exception:
            return True   # 创建/写入/执行被拒（EACCES 等）→ 需要迁移
        finally:
            if probe and os.path.isdir(probe):
                shutil.rmtree(probe, ignore_errors=True)

    def _relocated_work_dir(self):
        """在保留 POSIX 权限的合格挂载点上建立源码副本构建目录。

        探测候选挂载点：mkdir 0700 + stat 实测 drwx------ 700 + exec 探测；
        合格后建立专用构建根（<base>/.bc-ur-build-<pid>，仅清理该专用根，
        不触碰挂载根本身）并把源码复制到 <根>/src（in-source 构建）。
        返回 src 路径；无合格挂载点返回 None。"""
        for base in _QUALIFIED_MOUNT_BASES:
            if not os.path.isdir(base):
                continue
            probe = None
            try:
                probe = os.path.join(base, ".bc-ur-mntprobe-{}".format(os.getpid()))
                os.mkdir(probe, 0o700)
                if stat.S_IMODE(os.stat(probe).st_mode) != 0o700:
                    continue   # 权限位未保留 → 不合格
                s = os.path.join(probe, "x.sh")
                with open(s, "w") as f:
                    f.write("#!/bin/sh\nexit 0\n")
                os.chmod(s, 0o700)
                subprocess.run(["./x.sh"], cwd=probe, check=True)   # exec 探测
                shutil.rmtree(probe, ignore_errors=True)
                root = os.path.join(base, ".bc-ur-build-{}".format(os.getpid()))
                if os.path.isdir(root):
                    shutil.rmtree(root, ignore_errors=True)
                os.mkdir(root, 0o700)
                work = os.path.join(root, "src")
                shutil.copytree(self.source_folder, work, dirs_exist_ok=True)
                self._relocated_root = root
                return work
            except Exception:
                if probe and os.path.isdir(probe):
                    shutil.rmtree(probe, ignore_errors=True)
                continue
        return None

    def build(self):
        apply_conandata_patches(self)
        self._relocated_work = None
        self._relocated_root = None
        if self._build_folder_needs_relocation():
            work = self._relocated_work_dir()
            if work is not None:
                args = self._toolchain_configure_args()
                self.run('cd "{}" && ./configure {}'.format(work, args), env="conanbuild")
                self.run('cd "{}" && make -j1'.format(work), env="conanbuild")
                self._relocated_work = work
                return
            # 无合格挂载点：回退 in-place（HMDFS 严格设备上 config.status 可能 EACCES）
            self.output.warning("无保留 POSIX 权限的合格挂载点，回退原目录构建"
                                "（HMDFS 严格设备上 config.status 可能 EACCES，见 notes.md）")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        work = getattr(self, "_relocated_work", None)
        if work is not None:
            self.run('cd "{}" && make install DESTDIR="{}"'.format(work, self.package_folder),
                     env="conanbuild")
            # 清理迁移构建目录（tmpfs 临时产物，不入包）：仅删专用构建根
            root = getattr(self, "_relocated_root", os.path.dirname(work))
            if os.path.basename(root).startswith(".bc-ur-build-"):
                shutil.rmtree(root, ignore_errors=True)
            return
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["bc-ur"]