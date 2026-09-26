#!/usr/bin/env python3
"""Conan recipe for libvmdk 20240510 — libyal VMware VMDK 格式访问库（纯 C，Autotools）。

源码：上游 GitHub release 资产 libvmdk-alpha-20240510.tar.gz（channel=alpha，
      HTTP 200 实测），sha256 与 Debian pristine orig tarball 逐字节一致（cmp
      IDENTICAL）且与 PGP 签名的 libvmdk_20240510-2.dsc Checksums-Sha256 逐字一致
      （三方同源；完整溯源见 conandata.yml 头注与 notes.md「源码溯源」）。

平台适配全部内联在 build() 内（不改上游任何 C/H 源文件与测试脚本，无 patches/ 文件）：
1. E011（HMDFS umask）：随包 configure 内 2 处 `umask 077` → `umask 022`，
   并让整个构建过程保持 umask 022（同族 libsmraw/libvsgpt 先例）。
2. 三元组：随包 config.guess/config.sub（2023-06-23 vintage）不识别 linux-ohos，
   OHOS 下显式 --build/--host=aarch64-unknown-linux-gnu（update_configure_args
   是替换语义，避免与 AutotoolsToolchain 自己生成的三元组重复；同族先例
   libsmraw 20240506 / libvsgpt 0-20240504 / libfsapfs 20240429）。
3. HMDFS 上直接执行源码树脚本受限：OHOS 下用 profile [buildenv] 注入的 bash
   （CONFIG_SHELL=/data/service/hnp/bin/bash）显式启动 configure。
4. 上游测试（make check）：automake 的 TESTS 入口都是 bash 脚本，OHOS 下经
   LOG_COMPILER 指定同一 bash 解释器；测试程序要读回构建树内的共享库，故把
   libvmdk/.libs 追加进 LD_LIBRARY_PATH（只作用于本进程子树，退出时还原）。
5. --disable-python：pyvmdk 绑定不入交付面（上游 --enable-python 默认即 no，
   显式声明意图；HAVE_PYTHON_TESTS 条件不成立，test_python_module.sh 不入注册面）。

依赖：外部 Conan 依赖仅 zlib/1.3.2（W0-2 实查：ohpcd 有 ohos-aarch64 二进制，
      `conan install --build=never --profile:host=ohos-aarch64` rc=0，
      证据 $TASK_DIR/w0-deps.txt 与 W0 检查日志）——libvmdk 的 grain 压缩数据
      解压（libvmdk_compression.c / libvmdk_deflate.c）需要 zlib.h/uncompress。
      接线为 **AutotoolsDeps 单通道**（zlib 的 include/lib 经 conanbuild 注入
      CPPFLAGS/LDFLAGS，configure 自动探测路径成功，原生与干净轮均实测
      `checking for zlib.h... yes` / `checking for uncompress in -lz... yes`）。
      **不要**加 `--with-zlib=<DIR>`：本版共享 m4（m4/zlib.m4 Version 20240314）
      的 DIR 分支把成功态置为 `zlib` 而终闸判 `!= yes`（`yes` 全文件从未被赋值）
      ⇒ 显式 DIR 参数**必然** configure 失败（round-1 G2 实测
      "unable to find supported zlib in directory"，DRAFT-E724 登记）。
      13 个 libyal 支持组件（libbfio libcdata libcerror libcfile libclocale
      libcnotify libcpath libcsplit libcthreads libfcache libfdata libfvalue
      libuna，另加顶层 common/ 共享支撑代码）以 standalone 形式内嵌在发布包内，
      非 Conan 依赖。

交付物：libvmdk.so.1.0.0（默认 shared）+ include/libvmdk.h、include/libvmdk/*.h
        + bin/vmdkinfo、bin/vmdkmount + lib/pkgconfig/libvmdk.pc；
        vmdkmount 的 FUSE 挂载路径在无 libfuse 时编译期降级（见 notes.md 已知限制）。
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
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibvmdkConan(ConanFile):
    name = "libvmdk"
    version = "20240510"
    description = (
        "Library to access the VMware Virtual Disk (VMDK) format (libyal)"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libvmdk"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # zlib 的 include/lib 经 conanbuild 聚合环境注入 configure/make
    # （AutotoolsDeps 先例：archives/a/afflib/3.7.22 等 500+ 主线配方）
    generators = "AutotoolsDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libvmdk adaptation supports Linux and OHOS"
            )

    def requirements(self):
        # W0-2：唯一外部硬依赖；ohpcd 有 ohos-aarch64 二进制（--build=never 实证）
        self.requires("zlib/1.3.2")

    def export_sources(self):
        # conandata.yml 当前无 patches 段（平台适配全部内联在 build()），
        # 保留导出/应用调用使配方对后续补丁形态就绪；无 patches 时为 no-op。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml 的 sources 段自带 url/sha256/filename 三键，原样展开即可
        # （filename 的单一事实来源在 conandata，调用点不得再显式传 filename=——
        #  DRAFT-E597 libsmraw 先例）
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_args(self):
        """generate() 与 build() 必须用同一组参数（共享同一份构造逻辑）。"""
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                # pyvmdk 绑定不入交付面（上游默认即 no，显式声明意图）
                "--disable-python",
                # 工具不静态链接（共享库模式下避免再链一份静态副本；同族口径）
                "--enable-static-executables=no",
                # 注意：**不加** --with-zlib=<DIR>——本版共享 m4/zlib.m4
                # （Version 20240314）DIR 分支成功态置 `zlib` 而终闸判 `!= yes`
                # （`yes` 全文件无赋值点），显式 DIR 参数必然 configure 失败
                # （round-1 G2 实测 "unable to find supported zlib in directory"）。
                # zlib 只走 AutotoolsDeps 注入的 CPPFLAGS/LDFLAGS 自动探测。
            ]
        )
        if self.options.shared:
            toolchain.configure_args.append("--enable-shared")
            toolchain.configure_args.append("--disable-static")
        else:
            toolchain.configure_args.append("--disable-shared")
            toolchain.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            # 本版本 config.sub 不识别 linux-ohos（同族 libvsgpt 设备实测
            # Invalid configuration），沿用 GNU 三元组；update_configure_args
            # 是替换语义，避免重复 --build/--host。
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
                    self.source_folder, "libvmdk", ".libs"
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
        # 树内构建：make install 必须在源码目录执行——conanfile.run() 的默认 cwd
        # 是 build 文件夹（basic_layout 下与源码目录不同），那里没有顶层 Makefile。
        # AutotoolsToolchain 的默认 prefix="/"，DESTDIR=package_folder 即落在
        # package_folder/{include,lib,bin}。
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
        self.cpp_info.libs = ["vmdk"]
        # 交付面含 bin/vmdkinfo、bin/vmdkmount（commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libvmdk")
        self.cpp_info.set_property("cmake_target_name", "libvmdk::libvmdk")
        self.cpp_info.set_property("pkg_config_name", "libvmdk")
