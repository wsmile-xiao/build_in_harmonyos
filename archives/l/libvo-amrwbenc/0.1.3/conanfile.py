#!/usr/bin/env python3
"""Conan recipe — libvo-amrwbenc 0.1.3 (autotools).

VisualOn AMR-WB（Adaptive Multi-Rate Wideband，G.722.2）**编码器**：一组纯 C++
实现的 AMR-WB 编码核心（`amrwbenc/`）＋一个稳定的 C 适配层
（`enc_if.h`：`E_IF_init` / `E_IF_encode` / `E_IF_exit`）＋一个命令
行编码器 `amrwb-enc`（把 16 kHz 单声道 WAV 编成 `#!AMR-WB` 码流）。
解码侧由同源的 opencore-amr 提供，两者构成完整的 AMR-WB 编解码链路。

OHOS（鸿蒙 PC / aarch64）适配要点（沿用 lame/sqlite3 的 autotools 方案）：

1. **三元组**：`config.sub` 不认识 `aarch64-linux-ohos`，configure 会因为
   “cannot guess build type” 失败。这里按 lame 的做法用**名义 GNU 三元组**
   `--host/--build=aarch64-linux-gnu`，真实目标仍由 profile 的
   `tools.build:compiler_executables`（OHOS clang）决定。
2. **uname shim**：设备上的 `uname -s` 是 `HarmonyOS`，config.guess 会据此
   走到未知分支 —— 在 PATH 最前面放一个 shim（`-s` 报 `Linux`、`-m` 报 `aarch64`）。
3. **E011（umask）**：上游 configure 内有 `umask 077`，在 HMDFS/SELinux 下会让
   临时目录不可写，构建前替换为 `umask 022`。
4. **bin_PROGRAMS 缺失**：本发行包的 `Makefile.in` 里 `bin_PROGRAMS = amrwb-enc`
   没有被 `all` 目标引用（较新 automake/make 下展开成空对象列表，直接 `make amrwb-enc`
   会报 “no input files”），`make install` 也不会装它。这里在库构建完后
   **按 Makefile.am 的声明手工编译同一个目标**（源码、链接库与上游一致），
   让 `bin/amrwb-enc` 真正随包交付。

License: Apache-2.0
"""
import os
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

TRIPLETS = {"armv8": "aarch64-linux-gnu", "x86_64": "x86_64-linux-gnu"}


class LibvoAmrwbencConan(ConanFile):
    name = "libvo-amrwbenc"
    version = "0.1.3"
    description = ("VisualOn AMR-WB (G.722.2) encoder library + amrwb-enc CLI "
                   "(16 kHz wideband speech)")
    license = "Apache-2.0"
    homepage = "https://sourceforge.net/projects/opencore-amr/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "codec", "amr-wb", "speech")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def requirements(self):
        pass

    def _compiler(self):
        """按 R33 从 conf 取编译器，避免在运行命令里使用未定义的 shell 变量。"""
        conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return conf.get("c", "clang")

    def generate(self):
        arch = str(self.settings.arch)
        triplet = TRIPLETS.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                "libvo-amrwbenc 0.1.3 配方目标为鸿蒙 PC，仅支持 armv8/x86_64，"
                "收到 arch='%s'" % arch)
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--host=%s" % triplet)
        toolchain.configure_args.append("--build=%s" % triplet)
        toolchain.generate()

    def _patch_umask(self):
        """E011：上游 configure 里的 umask 077 在 HMDFS/SELinux 下会让临时目录不可写。"""
        path = os.path.join(self.source_folder, "configure")
        with open(path, encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        if "umask 077" in text:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text.replace("umask 077", "umask 022"))

    def _install_uname_shim(self):
        """config.guess 通过 uname 判断系统；设备上 uname -s 为 HarmonyOS。"""
        shim = os.path.join(self.build_folder, "_uname_shim")
        os.makedirs(shim, exist_ok=True)
        path = os.path.join(shim, "uname")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                '#!/bin/sh\n'
                'case "${1:-}" in\n'
                '  -s|"") echo Linux ;;\n'
                '  -r) echo 6.6 ;;\n'
                '  -m) echo aarch64 ;;\n'
                '  *) exec /system/bin/uname "$@" 2>/dev/null || exec /bin/uname "$@" ;;\n'
                'esac\n')
        os.chmod(path, 0o755)
        os.environ["PATH"] = shim + os.pathsep + os.environ.get("PATH", "")

    def _fix_autotools_timestamps(self):
        """HMDFS 时间戳偏移导致 make 误判 Makefile.am/configure.ac 比生成物新，进而调用
        automake 重新生成并报 `newly created file is older than distributed files`。
        解法同仓库 aldo 0.7.8 先例：configure.ac 设成 now-5，生成物（configure/aclocal.m4/
        config.h.in/*Makefile.in）设成 now —— 生成物更新，但没有任何文件处于未来时刻
        （否则 configure 的 'build environment is sane' 检查会失败）。"""
        source = self.source_folder
        configure_ac = os.path.join(source, "configure.ac")
        if not os.path.exists(configure_ac):
            return
        try:
            time.sleep(0.1)
            now = time.time()
            os.utime(configure_ac, (now - 5, now - 5))
            now = time.time()
            for root, _dirs, files in os.walk(source):
                for name in files:
                    if name in ("Makefile.in", "aclocal.m4", "configure", "config.h.in"):
                        try:
                            os.utime(os.path.join(root, name), (now, now))
                        except OSError:
                            pass
        except OSError:
            pass

    def build(self):
        apply_conandata_patches(self)
        self._patch_umask()
        self._fix_autotools_timestamps()
        self._install_uname_shim()
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS 上并行 make 偶发失败，按仓库惯例串行（sqlite3/lame 同法）
        autotools.make(args=["-j1"])

        # 上游 Makefile.in 的 bin_PROGRAMS 没有进入 all/install 目标 —— 按
        # Makefile.am 的声明（amrwb_enc_SOURCES = amrwb-enc.c wavreader.c，
        # amrwb_enc_LDADD = libvo-amrwbenc.la）手工编译同一个目标。
        cc = self._compiler()
        # 注意：self.run() 的默认 cwd 是 **执行 conan 的目录**（CI 里是仓库根），
        # 不是源码目录 —— 因此这里全部用绝对路径 + 显式 cwd（CI #6385x 实测报
        # `clang-15: error: no such file or directory: 'amrwb-enc.c'`）。
        src = self.source_folder
        self.run(
            '%s -O2 -fPIC "%s/amrwb-enc.c" "%s/wavreader.c" -I"%s" '
            '-L"%s/.libs" -L"%s/.libs" -lvo-amrwbenc -lm '
            "-Wl,-rpath,'$ORIGIN/../lib' -o \"%s/amrwb-enc\""
            % (cc, src, src, src, src, self.build_folder, src), cwd=src)

    def package(self):
        autotools = Autotools(self)
        autotools.install()                       # 库 + include/vo-amrwbenc/enc_if.h + vo-amrwbenc.pc
        copy(self, "amrwb-enc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        for name in ("COPYING", "NOTICE"):
            copy(self, name, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["vo-amrwbenc"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "vo-amrwbenc")
