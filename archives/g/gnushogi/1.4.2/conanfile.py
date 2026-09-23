#!/usr/bin/env python3
"""Conan recipe for GNU Shogi 1.4.2 — Japanese chess engine for HarmonyOS PC.

gnushogi is an Autotools project (hand-written Makefiles) producing the
`gnushogi` engine binary; packaged as an application.

Upstream/platform quirks handled here:
- E386 (HMDFS getcwd): conan-spawned shells can start with an unwalkable
  HMDFS cwd; the first getcwd() fails and old autoconf's `ac_pwd` inode
  check then aborts ("working directory cannot be determined"). Every
  build command first `cd /` (recovers the shell) then walks into the
  build dir. Sources are copied in for an in-source build (the
  hand-written Makefile has no VPATH).
- configure's `umask 077` temp-dir wrapper is unwritable on HMDFS
  (knowledge E011) — patched to umask 022.
- The `all:` target in gnushogi/Makefile is a deliberate no-op
  ("No target specified."); build the real `gnushogi` target instead.
- clang >= 11 defaults to -fno-common, but the 2014 code base relies on
  multiple tentative definitions (e.g. DRAW in globals.c/rawdsp.c):
  build with -fcommon.
- The curses UI is optional upstream and probed via -lcurses/-ltermcap;
  the packaged ncurses only ships wide-char libs (ncursesw), so the probe
  cannot hit. Build --without-curses: the text UI is fully functional.
- Upstream only parses single-char options and its 'v' case exits 1;
  a patch adds GNU standard --version/--help exiting 0 (required by the
  OHOS packaging smoke gate, mirrors the 'v' output).
- The packaged ELF must be self-signed to run on OHOS (knowledge E077).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

# E386：conan spawn 的 shell 若继承到 HMDFS 冷节点 cwd，首次 getcwd 即败
# 且状态残留；先 `cd /` 退出坏目录即可恢复，随后再走进工作目录。
CD_WORK = 'cd / && cd "{work}"'


class GnushogiConan(ConanFile):
    name = "gnushogi"
    version = "1.4.2"
    description = "GNU Shogi — Japanese chess (shogi) engine with text interface"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnushogi/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # 源码目录与构建目录分离，便于把源码拷入 build 目录做 in-source
        # 构建（手写 Makefile 无 VPATH）
        self.folders.source = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # clang >= 11 默认 -fno-common：上游代码大量使用暂定定义（如
        # globals.c 与 rawdsp.c 对 DRAW 的重复定义），链接期符号冲突
        tc.extra_cflags.append("-fcommon")
        # curses UI 为上游可选项，经 -lcurses/-ltermcap 探测；制品仓
        # ncurses 6.5 仅提供宽字符库（ncursesw），探测无法命中。文本
        # UI 不依赖 curses，禁用后引擎功能完整且无第三方依赖
        tc.configure_args.append("--without-curses")
        # E386：environment() 在 toolchain 改动完成后取值，再补 shell
        # 钉死——阻止 autoconf 挑选 hnp bash 重新执行 configure
        env = tc.environment()
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        # 在 build_folder 下用独立子目录做 in-source 构建：不能清空
        # build_folder 本身——conan 的 generators（conanbuild.sh）就在
        # 其 conan/ 子目录里，删掉会导致工具链环境（CC 等）全部丢失
        work = os.path.join(self.build_folder, "build")
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        # 源码拷入做 in-source 构建（手写 Makefile 无 VPATH）
        self.run(f'cp -a "{self.source_folder}/." "{work}/"')
        c = CD_WORK.format(work=work)
        # E386：profile [buildenv] 会把 SHELL/CONFIG_SHELL 强制成 hnp
        # bash 且 source 顺序晚于工具链脚本，须在命令内再覆盖一次，
        # 否则 configure 以 bash 重执行后在 HMDFS 上 getcwd 必败
        self.run(f'{c} && export CONFIG_SHELL=/bin/sh SHELL=/bin/sh'
                 ' && ./configure --prefix=/ --without-curses',
                 env="conanbuild")
        # 上游 gnushogi/Makefile 的 all: 是防呆占位（打印
        # "No target specified."），顶层同名 gnushogi 目标亦为空壳；
        # 真实构建入口是子目录 gnushogi/Makefile 的 gnushogi 目标
        self.run(f'{c} && make -C gnushogi -j1 gnushogi', env="conanbuild")
        self._work = work

    def _sign_ohos_elf(self, path):
        """E077：OHOS 上 ELF 需自签名后才可执行。

        binary-sign-tool 不存在时（CI 签名由流水线 sign.sh 处理）静默
        跳过；设备本机构建则就地自签。
        """
        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            return
        output = path + ".signed"
        # E540：conan 构建环境的 LD_LIBRARY_PATH 指向 SDK llvm/lib，
        # 会劫持 binary-sign-tool 的 libc++.so 加载；剥掉后按工具自身
        # 的 rpath 解析
        sign_env = dict(os.environ)
        sign_env.pop("LD_LIBRARY_PATH", None)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
            env=sign_env,
        )
        os.replace(output, path)

    def package(self):
        work = getattr(self, "_work", os.path.join(self.build_folder, "build"))
        engine_dir = os.path.join(work, "gnushogi")
        copy(self, "gnushogi", src=engine_dir,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=work,
             dst=os.path.join(self.package_folder, "licenses"))
        bin_path = os.path.join(self.package_folder, "bin", "gnushogi")
        if not os.path.isfile(bin_path):
            raise ConanException("gnushogi engine binary missing after build")
        os.chmod(bin_path, 0o755)
        self._sign_ohos_elf(bin_path)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # package_type = "application"：消费者通过 PATH 使用引擎二进制
        self.cpp_info.bindirs = ["bin"]
