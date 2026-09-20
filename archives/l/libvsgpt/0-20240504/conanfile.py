#!/usr/bin/env python3
"""Conan recipe for libvsgpt 0-20240504 — libyal GPT/MBR 卷系统访问库（纯 C，Autotools）。

源码：Debian pristine orig tarball（上游 GitHub 当前仅剩 20260731/20260911 两个
      tag，20240504 的 tag 与 release 资产均不存在），溯源、sha256 与源码闭包
      核对见 archives/l/libvsgpt/0-20240504/notes.md。

平台适配全部内联在 build() 内（不改上游任何 C/H 源文件与测试脚本，无 patches/ 文件）：
1. E011（HMDFS umask）：随包 configure 内有 2 处 `umask 077`；HMDFS 上按 077 建出的
   0700 临时目录连创建者都无法写入（`can't create .../dummy.c: Permission denied`，
   设备实测 config.guess 即因此失败）；OHOS 构建期只把这两处改为 `umask 022`，
   并让整个构建过程保持 umask 022。
2. 三元组：随包 config.guess/config.sub（timestamp 2023-06-23）不识别 HarmonyOS，且**本版本 config.sub
   也不接受** `linux-ohos`（设备实测：`Invalid configuration 'aarch64-unknown-linux-ohos':
   OS 'ohos' not recognized`），故 OHOS 下显式给出
   `--build/--host=aarch64-unknown-linux-gnu`（同族先例 libfsntfs 20251028 口径），
   用 update_configure_args() 覆盖而非追加，避免与 AutotoolsToolchain 自己生成的
   三元组重复。
3. HMDFS 上直接执行源码树脚本受限：OHOS 下用 profile [buildenv] 注入的 bash
   （CONFIG_SHELL=/data/service/hnp/bin/bash）显式启动 configure。
4. 上游测试（make check）：automake 的 TESTS 3 个入口都是 bash 脚本，OHOS 下经
   LOG_COMPILER 指定同一 bash 解释器；测试程序要读回构建树内的共享库，故把
   libvsgpt/.libs 追加进 LD_LIBRARY_PATH（只作用于本进程子树，退出时还原）。

交付物：libvsgpt.so/1.0.0（默认 shared）+ include/libvsgpt.h、include/libvsgpt/*.h
+ bin/vsgptinfo + lib/pkgconfig/libvsgpt.pc；python 绑定（pyvsgpt）显式关闭
（--disable-python），本库无外部 Conan 依赖（13 个 libyal 组件以 standalone
形式内嵌在发布包内）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cmd_args_to_string
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibvsgptConan(ConanFile):
    name = "libvsgpt"
    version = "0-20240504"
    description = (
        "Library to access the GUID Partition Table (GPT) volume system (libyal)"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libvsgpt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libvsgpt adaptation supports Linux and OHOS"
            )

    def export_sources(self):
        # conandata.yml 当前无 patches 段（平台适配全部内联在 build()），
        # 保留导出/应用调用使配方对后续补丁形态就绪；无 patches 时为 no-op。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libvsgpt_0~20240504.orig.tar.gz",
            strip_root=True,
        )

    def _configure_args(self):
        """generate() 与 build() 必须用同一组参数（共享同一份构造逻辑）。"""
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                # 不构建 python 绑定（pyvsgpt），交付面只有 C 库与工具
                "--disable-python",
                # 工具不静态链接（共享库模式下避免再链一份静态副本）
                "--enable-static-executables=no",
            ]
        )
        if self.options.shared:
            toolchain.configure_args.append("--enable-shared")
            toolchain.configure_args.append("--disable-static")
        else:
            toolchain.configure_args.append("--disable-shared")
            toolchain.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            # 本版本 config.sub 不识别 linux-ohos（设备实测 Invalid configuration），
            # 沿用 GNU 三元组；update_configure_args 是替换语义，避免重复 --build/--host。
            toolchain.update_configure_args(
                {
                    "--build": "aarch64-unknown-linux-gnu",
                    "--host": "aarch64-unknown-linux-gnu",
                }
            )
        return toolchain

    def generate(self):
        self._configure_args().generate()

    def _patch_hmdfs_umask(self):
        """E011：configure 的 umask 077 在 HMDFS 上生成不可写临时目录。"""
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, encoding="utf-8") as configure_file:
            configure_text = configure_file.read()
        if "umask 077" in configure_text:
            with open(configure_path, "w", encoding="utf-8") as configure_file:
                configure_file.write(
                    configure_text.replace("umask 077", "umask 022")
                )
            self.output.info(
                "configure: umask 077 -> 022 (HMDFS writable tempdir, E011)"
            )
        os.chmod(configure_path, 0o755)

    def _jobs(self):
        """显式限制 make 并发。

        conan 的 tools.build:jobs 缺省取 os.cpu_count()（本机 20，而容器 affinity
        只有 8），共享设备上会超订；本包统一按 2 并发构建，调用方可用
        `-c tools.build:jobs=N` 显式覆盖。
        """
        conf_jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        return conf_jobs if conf_jobs else 2

    def build(self):
        apply_conandata_patches(self)
        jobs = self._jobs()
        old_umask = os.umask(0o022)
        old_ld_library_path = os.environ.get("LD_LIBRARY_PATH")
        try:
            if str(self.settings.os) == "OHOS":
                config_shell = os.environ.get(
                    "CONFIG_SHELL", "/data/service/hnp/bin/bash"
                )
                self._patch_hmdfs_umask()
                configure_path = os.path.join(self.source_folder, "configure")
                configure_args = cmd_args_to_string(
                    self._configure_args().configure_args
                )
                self.run(
                    f'"{config_shell}" "{configure_path}" {configure_args}',
                    cwd=self.source_folder,
                )
            else:
                Autotools(self).configure()
            self.run(f"make -j{jobs}", cwd=self.source_folder)

            # ── 上游官方测试（make check）──
            if str(self.settings.os) == "OHOS":
                library_path = os.path.join(
                    self.source_folder, "libvsgpt", ".libs"
                )
                if old_ld_library_path:
                    os.environ["LD_LIBRARY_PATH"] = (
                        library_path + os.pathsep + old_ld_library_path
                    )
                else:
                    os.environ["LD_LIBRARY_PATH"] = library_path
                self.run(
                    f'make -j{jobs} check LOG_COMPILER="{config_shell}"',
                    cwd=self.source_folder,
                )
            else:
                self.run(f"make -j{jobs} check", cwd=self.source_folder)
        finally:
            if old_ld_library_path is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld_library_path
            os.umask(old_umask)

    def package(self):
        # 树内构建：make install 必须在源码目录执行——conanfile.run() 的默认 cwd 是
        # build 文件夹（basic_layout 下与源码目录不同），那里没有顶层 Makefile。
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
        )
        # libtool 的 .la 描述文件对消费者无用，且内嵌构建机绝对路径
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        for license_file in ("COPYING", "COPYING.LESSER"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
            )

    def package_info(self):
        self.cpp_info.libs = ["vsgpt"]
        # 交付面含 bin/vsgptinfo（commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libvsgpt")
        self.cpp_info.set_property("cmake_target_name", "libvsgpt::libvsgpt")
        self.cpp_info.set_property("pkg_config_name", "libvsgpt")
