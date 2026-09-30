#!/usr/bin/env python3
"""Conan recipe — wmname 0.1 (X11 WM name 读写命令行工具, suckless)。

构建系统: raw Makefile + config.mk（无 configure / 无 CMake）
License: MIT
Homepage: https://tools.suckless.org/wmname/
上游源码: https://dl.suckless.org/tools/wmname-0.1.tar.gz

适配要点（证据见 notes.md）:
1. 上游 config.mk 把 X11 头/库路径写死为 /usr/X11R6/include、/usr/X11R6/lib
   （1990 年代路径；设备、CI worker、主机都不存在）⇒ 配方沿用上游 Makefile，
   把 X11INC/X11LIB（以及 INCS/LIBS）覆盖为制品仓依赖包 libx11/6.4.0 +
   xorgproto/2025.1 的真实路径（R36：依赖必须能从制品仓拉取），
   不写死任何设备路径、不使用主机 /usr/include 或 /usr/lib。
2. 上游 Makefile 链接行含 `-s` 且链接后显式 `strip`：OHOS SDK clang 在链接期
   自动生成的 .codesign 被 strip 破坏，产物在 HarmonyOS 上加载即被拒
   （`Operation not permitted` / rc=126，E318/E077B 家族）。
   ⇒ package() 在**最终包内 ELF** 上先移除失效段、再 binary-sign-tool 自签名。
   实测：未重签 rc=126；重签后同一 ELF 正常进入程序逻辑（rc=1 + 上游错误路径）。
3. 设备与 CI worker 都没有 X server ⇒ test_package 执行打包产物，断言上游
   wmname.c 的三条确定性分支（usage / -v / cannot open display），并核对链接后
   ELF 内 property 名字面量（_NET_WM_NAME / _NET_SUPPORTING_WM_CHECK / UTF8_STRING）。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class WmnameConan(ConanFile):
    name = "wmname"
    version = "0.1"
    description = "prints/sets the WM name (_NET_WM_NAME) on the X11 root window"
    license = "MIT"
    homepage = "https://tools.suckless.org/wmname/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # X11 头文件/库全部来自制品仓 conan 包（主机与 CI worker 均无系统 X11）
        self.requires("libx11/6.4.0")
        self.requires("xorgproto/2025.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: 编译器与标志来自 Conan Toolchain 生成的 conanbuild 环境脚本，
        # build() 的 $CC 由该脚本提供，不依赖调用方 shell 里预置的变量
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)

        dep_incs = " ".join(
            f"-I{os.path.join(dep.package_folder, inc)}"
            for dep in self.dependencies.host.values()
            for inc in dep.cpp_info.includedirs
        )
        dep_libs = " ".join(
            f"-L{os.path.join(dep.package_folder, libdir)}"
            for dep in self.dependencies.host.values()
            for libdir in dep.cpp_info.libdirs
        )
        x11 = self.dependencies["libx11"]
        x11_inc = os.path.join(x11.package_folder, x11.cpp_info.includedirs[0])
        x11_lib = os.path.join(x11.package_folder, x11.cpp_info.libdirs[0])

        # 沿用上游 Makefile 的编译式（CFLAGS/LDFLAGS 结构、版本宏、strip 步骤都不改），
        # 只把 X11 路径与 include/lib 搜索路径换成本包 conan 依赖的真实路径。
        # R9: 单文件直编，显式 -j1，不占用设备并发额度。
        self.run(
            f'cd "{self.source_folder}" && make -j1 '
            f'CC="$CC" LD="$CC" '
            f'X11INC="{x11_inc}" X11LIB="{x11_lib}" '
            f'INCS="{dep_incs}" LIBS="{dep_libs} -lX11"',
            env="conanbuild",
        )

    # ── OHOS ELF 签名（E318/E077B：未（有效）签名的 ELF 在 HarmonyOS 上被拒载） ──

    def _find_tool(self, name):
        found = shutil.which(name)
        if found:
            return found
        for d in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        p = os.path.join("/data/service/hnp/bin", name)
        return p if os.path.isfile(p) else None

    def _sign_elf(self, binary):
        objcopy = self._find_tool("llvm-objcopy")
        sign_tool = self._find_tool("binary-sign-tool")
        if not objcopy or not sign_tool:
            raise ConanException(
                "OHOS ELF signing tools not found (llvm-objcopy / binary-sign-tool); "
                "an unsigned ELF is refused by HarmonyOS (E318/E077B)"
            )
        # E077（经验库 §12.13 实测）：调用签名器时必须剔除 LD_LIBRARY_PATH ——
        # conan 构建环境里它指向工具链运行时，binary-sign-tool 会重定位失败
        # （报 std::__h 系列符号全缺）。同时「先移除旧段再签」是 E077 四步顺序，
        # 直接对已签产物重复签会以 127 退出。
        sign_env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
        subprocess.run([objcopy, "--remove-section", ".codesign", binary],
                       capture_output=True, timeout=30, env=sign_env)
        tmp = binary + ".signed.tmp"
        for _ in range(3):
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", binary,
                 "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=60, env=sign_env,
            )
            if r.returncode == 0 and os.path.isfile(tmp):
                shutil.move(tmp, binary)
                os.chmod(binary, 0o755)
                return
        if os.path.exists(tmp):
            os.remove(tmp)
        raise ConanException(f"binary-sign-tool failed for {binary}")

    def package(self):
        binpath = os.path.join(self.package_folder, "bin", "wmname")
        copy(self, "wmname", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 签名对象必须是最终包内文件（strip 已使链接期自动签名失效）
        if str(self.settings.os) == "OHOS":
            self._sign_elf(binpath)
        os.chmod(binpath, 0o755)

    def package_info(self):
        # 命令行工具：只提供 bin/，无可链接库（R38 → 软件级 commands.json）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
