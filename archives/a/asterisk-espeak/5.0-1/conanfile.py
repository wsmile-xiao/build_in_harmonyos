#!/usr/bin/env python3
"""Conan recipe for asterisk-espeak 5.0-1 — Asterisk eSpeak TTS module (C).

Asterisk-eSpeak 是 Asterisk 的 espeak 语音合成拨号应用模块（app_espeak.so），
Makefile 构建。编译期依赖：
- espeak-ng（制品仓已发布 espeak-ng/1.51）
- libsamplerate（制品仓已发布 libsamplerate/0.2.2）
- Asterisk 框架头文件（asterisk.h 等）——制品仓无 asterisk 包，但
  Asterisk 是 GPL 开源，从 asterisk-22.5.0 源码提取所需 47 个头文件
  作为 compat 提供（替代依赖路径，同 audacious/autodocksuite 先例）

OHOS 适配:
- Makefile 构建 app_espeak.so（模块形态，无链接库 API）；
- compat/asterisk/*.h 提供 Asterisk 框架头；
- 产物 app_espeak.so 为 Asterisk 模块（测试: 存在性 + 版本校验）。
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, load, save


class AsteriskEspeakConan(ConanFile):
    name = "asterisk-espeak"
    version = "5.0-1"
    description = "Asterisk eSpeak text-to-speech dialplan application"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/zaf/Asterisk-eSpeak"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        # espeak TTS 引擎 + 音频重采样（制品仓均发布；
        # libsamplerate 制品仓二进制为静态 shared=False）
        self.requires("espeak-ng/1.51")
        self.requires("libsamplerate/0.2.2", options={"shared": False})

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Asterisk 框架头（48 个上游递归依赖头）从 asterisk-22.5.0 官方
        # 源码提取（compat 大头部不随仓库提交，缩小 PR diff）：
        # asterisk.h → compat/asterisk.h（顶层），其余 → compat/asterisk/。
        # 手写/修改的 autoconfig.h、buildopts.h、localtime.h 保留随仓库
        # （compat/asterisk/ 下已存在则不覆盖）。
        import re as _re
        import shutil as _sh
        _ast_dir = "asterisk-22.5.0"
        get(self, **self.conan_data["headers"], strip_root=True,
            destination=_ast_dir)
        _src_inc = os.path.join(self.source_folder, _ast_dir, "include")
        _dst = os.path.join(self.source_folder, "compat")
        os.makedirs(os.path.join(_dst, "asterisk"), exist_ok=True)
        _keep = {"autoconfig.h", "buildopts.h", "localtime.h"}
        # BFS 收集：种子 = app_espeak.c 直接 include 的 6 个头（asterisk.h、
        # app.h、channel.h、module.h、config.h、utils.h），递归收集依赖
        _needed = {"asterisk.h", "app.h", "channel.h", "module.h",
                   "config.h", "utils.h"}
        _queue = list(_needed)
        while _queue:
            _h = _queue.pop()
            _p = os.path.join(_src_inc, _h)
            if not os.path.exists(_p):
                _p = os.path.join(_src_inc, "asterisk", _h)
            if not os.path.exists(_p):
                continue
            try:
                _content = open(_p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for _m in _re.findall(
                r'#include\s*[<"](asterisk/[a-z_0-9-]+\.h|ast[a-z_0-9-]*\.h)'
                r'[>"]', _content):
                _n = _m.split("/")[-1]
                if _n not in _needed:
                    _needed.add(_n)
                    _queue.append(_n)
        for _h in sorted(_needed):
            # asterisk.h 在源码 include 顶层；其余在 include/asterisk/
            if _h == "asterisk.h":
                _src = os.path.join(_src_inc, "asterisk.h")
            else:
                _src = os.path.join(_src_inc, "asterisk", _h)
            if not os.path.exists(_src):
                continue
            if _h == "asterisk.h":
                _dst_file = os.path.join(_dst, "asterisk.h")
            else:
                if _h in _keep and os.path.exists(
                    os.path.join(_dst, "asterisk", _h)):
                    continue  # 保留手写/修改版本
                _dst_file = os.path.join(_dst, "asterisk", _h)
            if not os.path.exists(_dst_file):
                _sh.copy2(_src, _dst_file)
                self.output.info(f"extracted asterisk {_h}")

    def export_sources(self):
        # compat/asterisk/*.h：Asterisk 框架头（从 asterisk-22.5.0 源码
        # 提取的 47 个递归依赖头，替代制品仓缺失的 asterisk 包）
        copy(self, "compat/*", self.recipe_folder, self.export_sources_folder)

    def build(self):
        # app_espeak.c: strcasecmp 隐式声明（鸿蒙 clang 视为 error）——
        # patch 源码补 <strings.h>
        src_c = os.path.join(self.source_folder, "app_espeak.c")
        content = load(self, src_c)
        fixed = content.replace(
            '#include <sys/stat.h>',
            '#include <sys/stat.h>\n#include <strings.h>',
        )
        if fixed != content:
            save(self, src_c, fixed)
            self.output.info("patched app_espeak.c: include <strings.h>")
        # 将 compat/asterisk 头文件复制到构建目录（模块编译用）：
        # asterisk.h 在 include 顶层（供 #include "asterisk.h"），
        # asterisk/*.h 在 include/asterisk/（供 #include "asterisk/app.h"）
        compat_ast = os.path.join(self.source_folder, "compat", "asterisk")
        inc_dir = os.path.join(self.build_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        copy(self, "asterisk.h", self.source_folder + "/compat", inc_dir)
        copy(self, "*", compat_ast, os.path.join(inc_dir, "asterisk"))
        # espeak-ng / samplerate 头与库路径
        espeak_pkg = self.dependencies["espeak-ng"].package_folder
        sr_pkg = self.dependencies["libsamplerate"].package_folder
        # 注意：不要加 -I include/asterisk——compat.h 的 #include <strings.h>
        # 会被劫持到 compat/asterisk/strings.h（Asterisk 头）而非系统头，
        # 导致 __ast_realloc 隐式声明冲突。asterisk/*.h 经 -I include 解析。
        cflags = (
            f"-I{inc_dir} "
            f"-I{os.path.join(espeak_pkg, 'include')} "
            f"-I{os.path.join(espeak_pkg, 'include', 'espeak-ng')} "
            f"-I{os.path.join(sr_pkg, 'include')} "
            # Asterisk utils.h 用 clang blocks（RAII_VAR 宏）——需要 -fblocks
            "-fblocks"
        )
        ldflags = (
            f"-L{os.path.join(espeak_pkg, 'lib')} "
            f"-L{os.path.join(sr_pkg, 'lib')} "
            "-lespeak-ng -lsamplerate"
        )
        # 用 make 覆盖变量构建（Makefile 链接规则用 $(LIBS) 而非 LDLIBS；
        # CC 默认 gcc，鸿蒙无 gcc——覆盖为 clang）
        self.run(
            f"make SHELL=/bin/sh CC=clang CFLAGS='{cflags}' LIBS='{ldflags}'",
            cwd=self.source_folder,
        )

    def package(self):
        # app_espeak.so 安装到 lib/asterisk/modules/（模块形态）
        so = os.path.join(self.source_folder, "app_espeak.so")
        if os.path.exists(so):
            dest = os.path.join(
                self.package_folder, "lib", "asterisk", "modules")
            os.makedirs(dest, exist_ok=True)
            copy(self, "app_espeak.so", self.source_folder, dest)

    def package_info(self):
        self.cpp_info.libs = []
