#!/usr/bin/env python3
"""Conan recipe for cdargs 1.0.0 on HarmonyOS PC.

cdargs is a shell navigation tool: cdargs keeps bookmarks for
frequently used directories and provides an easy-to-use browser to
jump to them. A single C++ translation unit (src/cdargs.cc +
src/cdargs.h) compiled directly with clang++, linked against ncurses
(wide-char). Upstream source: cdargs 1.35 (Debian). Dependency:
ncurses (published on ohpcd).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CdargsConan(ConanFile):
    name = "cdargs"
    version = "1.0.0"
    package_type = "application"
    license = "GPL-2.0-only"
    homepage = "http://www.skamphausen.de/cgi-bin/ska/CDargs"
    url = "http://www.skamphausen.de/cgi-bin/ska/CDargs"
    description = "cdargs - bookmarks and browsing for the cd command"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            strip_root=True)

    def build(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cdargs does not support os={self.settings.os}")
        ncurses = self.dependencies["ncurses"]
        # E011 根治（calcurse 同款实证）：HMDFS 上执行位被剥 → 二进制不可执行。
        # 方案：源码复制到非 HMDFS（/data/storage/el2/base/cache）再编译。
        work = "/data/storage/el2/base/cache/cdargs-src"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # 直接 clang++ 编译单一翻译单元（cdargs 无 config.h / 无 configure
        # 生成宏，ncursesw 头/库已知：OHOS ncurses 只发布宽字符静态库，经
        # -DHAVE_NCURSES_H 走 <ncurses.h> + -lncursesw）。
        #
        # 不用 autotools make 的原因（CI 实证）：cdargs 1.35 的 automake 1.4
        # 递归构建在 OHOS worker 上生成的子 Makefile 中 @top_srcdir@ 被环境
        # 污染成二进制乱码（/data/storage/el2/base/cache/cdargs-src 正常，但
        # config.status 替换出的 top_srcdir = '/\xef\xbf\xbd-v\x11...flag'），
        # make 进入 contrib/ 重建 Makefile.in 时对不存在的
        # '/<乱码>flag/configure.in' 报 "No rule to make target"（contrib 是
        # SUBDIRS 首项，cdargs 二进制在 src/ 根本未构建）。直接编译不依赖
        # configure/config.status 生成的 Makefile，确定性构建。
        cxx = self._compiler_executable("cpp", "clang++")
        # configure 会把 confdefs.h 里的 #define VERSION "1.35" 经 confdef2opt.sed
        # 转成 -DVERSION="1.35" 放进 DEFS，再经 src/Makefile 传给编译器；
        # 直接编译时须手动补上（cdargs.cc:1004 version() 用 VERSION 打印版本）。
        self.run(
            f"{cxx} -DHAVE_NCURSES_H "
            f"-DVERSION=\\\"1.35\\\" "
            f"-I{ncurses.package_folder}/include "
            f"{os.path.join('src', 'cdargs.cc')} "
            f"-o {os.path.join('src', 'cdargs')} "
            f"-L{ncurses.package_folder}/lib -lncursesw",
            cwd=work,
        )

    def package(self):
        work = "/data/storage/el2/base/cache/cdargs-src"
        copy(self, "cdargs", src=os.path.join(work, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cdargs.1", src=os.path.join(work, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # OHOS 仅执行带签名 ELF——consumer 测试要实际运行 cdargs
        # （-f <list> -a <dir> 非交互加书签），必须 self-sign。
        self._sign_ohos_elf(
            os.path.join(self.package_folder, "bin", "cdargs"))

    def package_info(self):
        self.conf_info.define("user.cdargs:exe", os.path.join(
            self.package_folder, "bin", "cdargs"))

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _sign_ohos_elf(self, path):
        if str(self.settings.os) != "OHOS":
            return
        with open(path, "rb") as handle:
            if b".codesign" in handle.read():
                os.chmod(path, 0o755)
                return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to sign OHOS executables")
        tmp_dir = os.path.join(self.build_folder, "sign-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_in = os.path.join(tmp_dir, "cdargs")
        tmp_out = tmp_in + ".signed"
        shutil.copy2(path, tmp_in)
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", tmp_in],
            capture_output=True,
            timeout=10,
        )
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
