#!/usr/bin/env python3
"""Conan recipe for libmodi 0-20251121 — libyal Mac OS 磁盘镜像访问库（纯 C，Autotools）。

覆盖格式：sparse bundle disk image、sparse disk image、UDIF（uncompressed/ADC/
bzip2/LZFSE/LZVN/LZMA/DEFLATE 压缩）。源码：上游 GitHub release 官方资产
libmodi-experimental-20251121.tar.gz（tag 20251121），溯源、sha256 与源码闭包
核对见 archives/l/libmodi/0-20251121/notes.md「源码溯源」。

平台适配全部内联在 build() 内（不改上游任何文件，无 patches/ 文件）：
1. E011（HMDFS umask）：随包 configure 内有 2 处 `umask 077`，HMDFS 上建出的
   0700 临时目录连创建者都无法写入；OHOS 构建期只把这两处改为 `umask 022`，
   并让整个构建过程保持 umask 022。
2. 三元组：随包 config.guess/config.sub 原生接受 `linux-ohos`；OHOS 下显式给出
   `--build/--host=aarch64-unknown-linux-ohos`（libtool 走 PIC/共享分支）。用
   update_configure_args() 覆盖而非追加，避免与 AutotoolsToolchain 自己生成的
   三元组重复。
3. HMDFS 上直接执行源码树脚本受限：OHOS 下用 profile [buildenv] 注入的 bash
   （CONFIG_SHELL=/data/service/hnp/bin/bash）显式启动 configure。
4. 上游测试（make check）：automake 的 TESTS 3 个入口都是 bash 脚本，OHOS 下
   经 LOG_COMPILER 指定同一 bash 解释器；测试程序要读回构建树内的共享库，故把
   libmodi/.libs 追加进 LD_LIBRARY_PATH（只作用于本进程子树，退出时还原）。
   tests/input/ 夹具不在发布包内，test_modiinfo.sh 按上游规则 SKIP；
   pymodi 测试随 --disable-python 整体关闭。

交付物：libmodi.so/1.0.0（默认 shared）+ include/libmodi.h + bin/modiinfo、
bin/modimount + pkgconfig/libmodi.pc；python 绑定（pymodi）与 libfuse 挂载依赖
显式关闭（--disable-python --with-libfuse=no），本库无外部 Conan 依赖（19 个
libyal 组件以 standalone 形式内嵌在发布包内，含 libbfio/libcaes）。
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


class LibmodiConan(ConanFile):
    name = "libmodi"
    version = "0-20251121"
    description = (
        "Library to access the Mac OS disk image formats: "
        "sparse bundle, sparse disk image and UDIF (libyal)"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libmodi"
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
                "libmodi adaptation supports Linux and OHOS"
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
            filename="libmodi-experimental-20251121.tar.gz",
            strip_root=True,
        )

    def _configure_args(self):
        """generate() 与 build() 必须用同一组参数（共享同一份构造逻辑）。"""
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                # 不构建 python 绑定（pymodi），交付面只有 C 库与工具
                "--disable-python",
                # 不引入 libfuse（modimount 保留，但走无 fuse 的降级分支）
                "--with-libfuse=no",
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
            # config.guess/config.sub 原生接受 linux-ohos。
            # update_configure_args 是替换语义，避免重复 --build/--host。
            toolchain.update_configure_args(
                {
                    "--build": "aarch64-unknown-linux-ohos",
                    "--host": "aarch64-unknown-linux-ohos",
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

        conan 的 tools.build:jobs 缺省取 os.cpu_count()（本机 20，而容器
        affinity 只有 8），共享设备上会超订；本包统一按 2 并发构建，调用方可
        用 `-c tools.build:jobs=N` 显式覆盖。
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
                    self.source_folder, "libmodi", ".libs"
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
        self.cpp_info.libs = ["modi"]
        # 交付面含 bin/modiinfo 与 bin/modimount（commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libmodi")
        self.cpp_info.set_property("cmake_target_name", "libmodi::libmodi")
        self.cpp_info.set_property("pkg_config_name", "libmodi")
