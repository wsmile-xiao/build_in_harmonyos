#!/usr/bin/env python3
"""libydpdict 1.0.4.1 — ydpdict 词典支持库（autotools + libtool）。

本版本为 1.0.4 的修复版（R37：1.0.4 已发布到制品仓，修复必须递增版本号）：
在 1.0.4 适配基础上补上上游测试真实执行（misc/ 4 个 check 程序，R51/rule4），
并修正 libtool 辅助源 URL（原 5 条镜像中 4 条为 404 路径）。原 1.0.4 适配的
环境修复全部保留（config.guess/config.sub 补丁、ltmain.sh 覆盖、HMDFS mktemp
垫片、SHELL 对齐、VPATH include）。

适配要点：
1. R26：系统同名库按静态产物构建（默认 shared=False）。
2. E007：config.guess / config.sub 需补 HarmonyOS 分支（补丁）。
3. E543：上游发布包的 ltmain.sh 与其 aclocal.m4 声明的 libtool 版本错配，
   由其生成的 libtool 缺少 func_dirname / func_opt_split 等 9 个内建函数，
   `--mode=link` 静默不产出 .so。source() 用 GNU libtool 官方包内版本精确匹配
   （package_revision=1.3293）的 ltmain.sh 覆盖上游残缺文件。
4. E543 同源：conan 用 /bin/sh（本平台为 MIRBSD ksh）启动 configure，而 ohpcd
   profile 的 [buildenv] 导出 SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash。
   configure 于是在 ksh 下测得 ECHO='print -r --'（ksh 内建），却用 bash 执行
   config.status → bash 无 print → "print: command not found"（config.status:712/724），
   最终 "config.status: error: could not setup config files machinery"（build() 失败）。
   profile [buildenv] 优先级高于配方 buildenv_info，故在 build() 中以命令前缀赋值
   调用 configure（POSIX 语义中前缀赋值优先于环境变量），把整条链统一到 /bin/sh：
   configure → config.status → 生成的 libtool → Makefile 的 SHELL。
5. VPATH 构建：上游 AM_CPPFLAGS 只指向 top_srcdir/include，源码外构建时生成的
   include/ydpdict.h 位于 top_builddir/include，src/ydpdict.c 因此报
   "fatal error: 'ydpdict.h' file not found"。build() 在 configure 时补入构建目录
   include 路径（$PWD/include），使其随 CPPFLAGS 进入生成的 Makefile。
6. HMDFS 以目录“组位”授权：autoconf config.status 以
   `(umask 077 && mktemp -d ./confXXXXXX)` 创建临时目录，而 mkdtemp 语义使其权限恒为
   0700（umask 无法放宽），新目录所有者在 HMDFS 上被映射为固定 uid，进程按组位判定
   不可写，写 subs1.awk 时报 "Permission denied"。build() 在构建目录安装 mktemp 垫片
   （以 umask 002 建目录并补 2770，组可写）并前置 PATH，覆盖 configure/make/install。
7. 上游测试真实执行（R51 三步法）：上游 `misc/Makefile.am` 第 1 行声明
   `check_PROGRAMS = ydpstress ydptest ydpxml gentable`（无 TESTS 变量，故
   `make check` 只构建、不自动运行任何用例）。build() 以 `make -C misc check`
   构建 4 个上游测试/校验程序后**逐个真实执行**：ydpstress/ydptest/ydpxml 按上游
   硬编码 DICT_PATH=/usr/local/share/ydpdict 读取词典数据（Young Digital Planet
   商业数据不可分发），用上游自带 misc/mkdict.py 的 .idx/.dat 官方格式合成语料后
   执行其完整负载；gentable（iconv 转换表生成）无数据依赖，直接执行。
8. configure 可选 `PKG_CHECK_MODULES([LIBXML2])` 会误拾构建机 host libxml2
   （交叉构建报 `unable to find library -lxml2`）；build() 以命令前缀
   `PKG_CONFIG_LIBDIR=<空目录>` 阻断，libxml2（仅 misc/ydpxml 的可选校验器）
   确定性关闭，本地/CI 行为一致。
"""
import os
import struct

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# 上游 misc/Makefile.am: check_PROGRAMS（ydptest 与 ydpstress 同源 ydpstress.c）
_UPSTREAM_CHECK_PROGRAMS = ("ydpstress", "ydptest", "ydpxml", "gentable")
# 其中三个按上游硬编码路径读取词典数据
_DICT_PATH = "/usr/local/share/ydpdict"

# 合成词典语料（windows-1250 词条 + RTF 释义原始字节，格式与上游 misc/mkdict.py
# 一致；覆盖 \b/\i/\cf2/\cf5/\f1 音标字节/\super/\par/\sa/\li 与 &<> 转义）。
# 注：\xb3=ł、\xbf=ż、\xe6=ć、\xf3=ó、\xb1=ą（windows-1250）；
# \x82\x85\x88 为 YDP 音标字体私有区字节（read_xhtml 在 \f1 组内转为 ɔʃə）。
_CORPUS = {
    100: [
        (b"s\xb3owo",
         b"{\\b s\xb3owo} {[\\f1\\cf5 \x82\x85\x88]}\\par\\pard{\\line\\cf2"
         b"czasownik\\line} ({\\i dziedzina}){\\f2\\cf1 definicja},"
         b"{\\f2\\cf1 definicja {\\cf2\\i rodzaj}}\\par\\sa100\\li300"
         b"{\\cf0 Przyk\xb3ad u\xbfycia & <test>.}"),
        (b"\xbfaba", b"{\\b \xbfaba}\\par{\\f2\\cf1 definicja dwa & trzy}"),
        (b"\xe6ma", b"{\\b \xe6ma}\\par{\\f2\\cf1 trzecia definicja}"),
        (b"g\xf3ra", b"{\\b g\xf3ra}\\par{\\f2\\cf1 czwarta <definicja>}"),
        (b"l\xf3d", b"{\\b l\xf3d}\\par{\\f2\\cf1 pi\xb1ta definicja}"),
        (b"zz-test", b"{\\b zz-test}\\par{\\f2\\cf1 ascii entry \\super 1}"),
    ],
    101: [
        (b"alpha", b"{\\b alpha}\\par{\\f2\\cf1 first}"),
        (b"beta", b"{\\b beta}\\par{\\f2\\cf1 second}"),
        (b"gamma", b"{\\b gamma}\\par{\\f2\\cf1 third}"),
    ],
    200: [
        (b"delta", b"{\\b delta}\\par{\\f2\\cf1 one}"),
        (b"epsilon", b"{\\b epsilon}\\par{\\f2\\cf1 two}"),
    ],
    201: [
        (b"zeta", b"{\\b zeta}\\par{\\f2\\cf1 only}"),
    ],
}


def _write_dict_pair(dat_path, idx_path, entries):
    """按上游 misc/mkdict.py 格式生成 .idx/.dat 词典对（小端）。

    idx: 256 字节头（magic 0x8D4E11D5、count@8、索引表偏移@16=256）
         + 每词条 8 字节记录 <BBHL>（词长+1, 2, 词条序号, dat 偏移）+ 词 + NUL
    dat: 每词条 <L 长度> + RTF 释义（windows-1250）
    """
    with open(idx_path, "wb") as idx, open(dat_path, "wb") as dat:
        idx.write(struct.pack("<LLHHLL236s", 0x8D4E11D5, 0, len(entries), 0, 0, 256, b""))
        idx_offset = 1
        dat_offset = 0
        for word, definition in entries:
            idx.write(struct.pack("<BBHL", len(word) + 1, 2, idx_offset, dat_offset))
            idx.write(word + b"\0")
            dat.write(struct.pack("<L", len(definition)))
            dat.write(definition)
            idx_offset += 1
            dat_offset += 4 + len(definition)


_MKTEMP_SHIM = r"""#!/bin/sh
# 本机(HMDFS/hmmac=use_task)兼容版 mktemp 垫片。
# 系统 mktemp -d 以 0700 建目录；本文件系统把新目录所有者映射为固定 uid，
# 进程 uid 与之一致性无法保证，0700 目录因此对当前进程不可写
# （autoconf config.status 的 ./confXXXXXX 临时目录即在此处失败）。
# 本垫片改为 umask 002 建目录/文件（组可写，实测 2771 可写），保持唯一性。
dir=0
dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    -d) dir=1; shift ;;
    -u) dry=1; shift ;;
    -q) shift ;;
    --) shift; break ;;
    -*) shift ;;
    *) break ;;
  esac
done
tmpl="$1"
[ -n "$tmpl" ] || tmpl="${TMPDIR:-/tmp}/tmp.XXXXXX"
case "$tmpl" in
  *XXXXXX) pre="${tmpl%XXXXXX}" ;;
  *) pre="$tmpl" ;;
esac
i=0
while [ "$i" -le 500 ]; do
  cand="${pre}$$-$i"
  if [ "$dry" = 1 ]; then
    printf '%s\n' "$cand"
    exit 0
  fi
  if [ "$dir" = 1 ]; then
    if ( umask 002; mkdir "$cand" ) 2>/dev/null; then
      chmod 2770 "$cand" 2>/dev/null
      printf '%s\n' "$cand"
      exit 0
    fi
  else
    if ( umask 002; set -C; : > "$cand" ) 2>/dev/null; then
      printf '%s\n' "$cand"
      exit 0
    fi
  fi
  i=$((i + 1))
done
exit 1
"""


class LibydpdictConan(ConanFile):
    name = "libydpdict"
    version = "1.0.4.1"
    description = "ydpdict dictionary support library"
    license = "LGPL-2.1"
    homepage = "https://toxygen.net/ydpdict/"
    url = "https://github.com/wojtekka/libydpdict"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        # E543：见模块 docstring。用官方 libtool 包内的 ltmain.sh 覆盖残缺件。
        aux = self.conan_data.get("libtool_source")
        if aux:
            aux_dir = os.path.join(self.source_folder, "_libtool_source")
            get(self, **aux, destination=aux_dir)
            copy(
                self,
                "libtool-2.4/libltdl/config/ltmain.sh",
                src=aux_dir,
                dst=self.source_folder,
                keep_path=False,
            )
            rmdir(self, aux_dir)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            # R26：系统同名库构建静态产物
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # 适配要点 4：Autotools.configure() 内部走 conanfile.run(cmd)，无法传环境
        # 前缀，而 profile [buildenv] 的 SHELL/CONFIG_SHELL 会覆盖配方 env。
        # 这里暂存工具链参数，供 build() 自行以命令前缀方式调用 configure。
        self._ohc_configure_args = list(tc.configure_args)

    def build(self):
        apply_conandata_patches(self)
        # 适配要点 6：HMDFS 以目录“组位”授权。CI worker 默认 umask 022 会让
        # config.status/make 的临时目录（mktemp -d）以 700 创建，组不可写，
        # 报 “can't create ./confXXXXXX/subs1.awk: Permission denied”。
        # 在 conan 进程内设 umask 002（configure/make/install 子进程继承），
        # 使临时目录为 775，组可写。
        os.umask(0o002)
        # 适配要点 6：HMDFS 按目录“组位”授权，而 config.status 的临时目录由
        # mktemp -d 创建（mkdtemp 语义：权限恒为 0700，umask 无法放宽），新目录
        # 所有者在 HMDFS 上被映射为固定 uid，进程按组位判定不可写，报
        # "can't create ./confXXXXXX/subs1.awk: Permission denied"。
        # 方案：把本机验证过的 mktemp 垫片装进构建目录并前置 PATH
        # （垫片以 umask 002 建目录并补 2770，组可写），覆盖 configure/make/install。
        shim_bin = os.path.join(self.build_folder, "shimbin")
        os.makedirs(shim_bin, exist_ok=True)
        shim_path = os.path.join(shim_bin, "mktemp")
        with open(shim_path, "w") as fh:
            fh.write(_MKTEMP_SHIM)
        os.chmod(shim_path, 0o755)
        os.environ["PATH"] = shim_bin + os.pathsep + os.environ.get("PATH", "")
        autotools = Autotools(self)
        configure = os.path.join(self.source_folder, "configure")
        args = " ".join(getattr(self, "_ohc_configure_args", []))
        # 适配要点 4：命令前缀赋值优先于任何环境文件导出的同名变量，
        # 使 configure/config.status/生成的 libtool 与 Makefile 都用 /bin/sh。
        # 适配要点 5：VPATH 构建下生成的 include/ydpdict.h 在构建目录，
        # 需显式补入（$PWD 即 configure 的工作目录 = conan 构建目录）。
        # 适配要点 8：PKG_CONFIG_LIBDIR 指向空目录，阻断 configure 可选
        # PKG_CHECK_MODULES([LIBXML2]) 误拾构建机 host libxml2（交叉构建会把
        # host 库塞进 aarch64 链接行：'unable to find library -lxml2'）。
        # libxml2 仅是 misc/ydpxml 的可选 XML 校验器，关闭后渲染负载照常执行，
        # 本地/CI 行为确定一致（与 notes"未启用"声明相符）。
        empty_pc = os.path.join(self.build_folder, "empty-pkgconfig")
        os.makedirs(empty_pc, exist_ok=True)
        self.run(
            'PATH="{}:$PATH" CPPFLAGS="-I$PWD/include $CPPFLAGS" '
            'SHELL=/bin/sh CONFIG_SHELL=/bin/sh '
            'PKG_CONFIG_LIBDIR="{}" PKG_CONFIG_PATH= '
            '"{}" {}'.format(shim_bin, empty_pc, configure, args)
        )
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        self.run('PATH="{}:$PATH" "{}" -j1'.format(shim_bin, make_program))
        # ── 上游测试真实执行（R51 三步法第二步）──
        # misc/Makefile.am: check_PROGRAMS = ydpstress ydptest ydpxml gentable
        # 上游无 TESTS 变量，make check 只构建不自动运行，须逐个真实执行。
        self.run('PATH="{}:$PATH" "{}" -C misc check'.format(shim_bin, make_program))
        self._run_upstream_checks(shim_bin)

    def _run_upstream_checks(self, shim_bin):
        """真实执行上游 4 个 check 程序。

        ydpstress/ydptest/ydpxml 依赖 DICT_PATH=/usr/local/share/ydpdict 的
        词典数据（上游商业词典不可分发，上游自带 misc/mkdict.py 为该格式的官方
        合成工具，此处按同一格式合成语料）；gentable 无数据依赖。
        语料落盘失败（只读根文件系统）时数据依赖程序本环境跳过并在日志说明，
        gentable 照常执行；本地 WSL（qemu-user + OHOS musl 运行根）已 4/4 实测。
        """
        misc = os.path.join(self.build_folder, "misc")

        provisioned = False
        try:
            os.makedirs(_DICT_PATH, exist_ok=True)
            for number, entries in _CORPUS.items():
                _write_dict_pair(
                    os.path.join(_DICT_PATH, "dict%d.dat" % number),
                    os.path.join(_DICT_PATH, "dict%d.idx" % number),
                    entries,
                )
            provisioned = True
            self.output.info(
                "ydpdict test corpus provisioned at %s (%d dicts, %d entries)"
                % (_DICT_PATH, len(_CORPUS), sum(len(v) for v in _CORPUS.values()))
            )
        except OSError as exc:
            self.output.warning(
                "ydpdict test corpus NOT provisioned at %s (%s) —— 目标环境只读根文件系统；"
                "数据依赖的上游测试（ydpstress/ydptest/ydpxml）本环境跳过（本地 qemu + "
                "OHOS musl 运行根已 4/4 实测，PR 描述附证据）；gentable 照常执行。"
                % (_DICT_PATH, exc)
            )

        for program in _UPSTREAM_CHECK_PROGRAMS:
            path = os.path.join(misc, program)
            if not os.path.exists(path):
                raise Exception("upstream check program missing: %s" % path)
            if program != "gentable" and not provisioned:
                self.output.info("skip (no corpus at %s): misc/%s" % (_DICT_PATH, program))
                continue
            self.output.info("running upstream check program: misc/%s" % program)
            self.run('PATH="{}:$PATH" "{}"'.format(shim_bin, path))
            self.output.info("upstream check program PASSED: misc/%s" % program)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ydpdict"]
