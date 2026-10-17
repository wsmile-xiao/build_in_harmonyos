#!/usr/bin/env python3
"""Conan recipe for sdcc 4.6.0 — Small Device C Compiler
(C/C++ compiler toolchain, autotools, SourceForge source).

Adaptation lessons applied:
- E007: config.guess (2018) cannot guess OHOS — pass --build/--host
  explicitly to bypass the guess.
- OHOS musl lacks `pthread_setcancelstate` declaration — patch boost's
  sp_thread_sleep.hpp (copy + declare) + -D_GNU_SOURCE.
- gputils (PIC toolchain) missing on ohpcd — disable PIC ports
  (--disable-pic14-port/--disable-pic16-port).
- E011: config.status temp-dir creation may hit Permission denied on
  hmdfs — set TMPDIR to the build staging dir.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class SdccConan(ConanFile):
    name = "sdcc"
    version = "4.6.0"
    description = "Small Device C Compiler (8051/Z80/STM8 etc.)"
    license = "GPL-2.0"
    homepage = "https://sdcc.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("bison/3.8.2")
        self.requires("flex/2.6.4")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # ============================================================
        # 关键修复（路径 C）：整个构建迁移到非 HMDFS 分区。
        # HMDFS（/storage 挂载）上 make 子进程 getcwd 失败：
        #   "getcwd: cannot access parent directories: Not supported"
        # （support/cpp 的 gcc 嵌套构建 configure-gcc 目标 cd ./gcc 后
        #   ${PWD_COMMAND} 失效 → ./gcc/configure 找不到）。
        # 已实测：源码复制到 /data（非 HMDFS）后 pwd/cd/getcwd 全部正常，
        # chmod 生效。构建在 /data 完成，产物复制回 source_folder 供
        # package() 打包（package() 逻辑不变）。
        # ============================================================
        import glob
        import time
        work_root = None
        for cand in ("/data/storage/el2/base/cache", "/data/cache",
                     self.build_folder):
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".sdcc-w-probe")
                with open(probe, "w") as _f:
                    _f.write("x")
                os.remove(probe)
                work_root = cand
                break
            except OSError:
                continue
        if not work_root:
            raise ConanException("no writable non-hmdfs work dir for sdcc")
        # work 名：不要用 tempfile.mktemp —— 其返回绝对路径（/storage/...），
        # [5:] 截取会把路径污染成深层嵌套；用 pid+time 生成纯文件名。
        work = os.path.join(work_root, f"sdcc-{os.getpid()}-{int(time.time() * 1000)}")
        if os.path.isdir(work):
            shutil.rmtree(work)
        shutil.copytree(self.source_folder, work, symlinks=True)
        # 关键：copytree 保留 HMDFS 源权限（gcc 目录 drwxrws--x 等，other
        # 无读权限）——/data 非 HMDFS 上 chmod 生效，递归 0o777 让 make
        # 子进程（other 用户）能 getcwd/stat 父目录链。
        for root, _dirs, _files in os.walk(work):
            try:
                os.chmod(root, 0o777)
            except OSError:
                pass
        # 复制 boost-patch 进 work（CPPFLAGS 引用 work 内相对路径）
        boost_inc = self.dependencies["boost"].package_folder
        patch_dir = os.path.join(work, "boost-patch")
        src_hpp = os.path.join(boost_inc, "include", "boost", "core",
                               "detail", "sp_thread_sleep.hpp")
        if os.path.isfile(src_hpp):
            dst_hpp = os.path.join(patch_dir, "boost", "core", "detail",
                                   "sp_thread_sleep.hpp")
            os.makedirs(os.path.dirname(dst_hpp), exist_ok=True)
            shutil.copy2(src_hpp, dst_hpp)
            content = open(dst_hpp).read()
            anchor = "#define BOOST_CORE_DETAIL_SP_THREAD_SLEEP_HPP_INCLUDED"
            if anchor in content and "pthread_setcancelstate(int" not in content:
                decl = ("\n// OHOS musl: pthread_setcancelstate not declared in "
                        "<pthread.h> — declare it\n"
                        "#if defined(BOOST_HAS_PTHREADS) && !defined(__ANDROID__)\n"
                        "extern \"C\" int pthread_setcancelstate(int __state, "
                        "int *__oldstate);\n#endif\n")
                open(dst_hpp, "w").write(content.replace(anchor,
                                                         anchor + decl, 1))
        tmpdir = os.path.join(work, "cfg-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        cppflags = f"-I{patch_dir} -I{os.path.join(boost_inc, 'include')} " \
                   f"-D_GNU_SOURCE"
        bld = "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
        install_prefix = os.path.join(work, "install-prefix")
        opts = "--disable-pic14-port --disable-pic16-port --disable-nls " \
               f"--without-ccache --enable-host-shared --prefix={install_prefix}"
        # E011 fix (part 1+2): patch EVERY configure script recursively —
        # sdcc has multiple recursive autotools subprojects (support/cpp,
        # support/packihx, ...) each with its own configure invoked via
        # AC_CONFIG_SUBDIRS. Each config.status must use $TMPDIR + umask 022
        # instead of ./confXXXXXX + umask 077 (CI: ./conf*/subs1.awk
        # Permission denied on each nested configure until patched).
        cfg_scripts = glob.glob(os.path.join(work, "**", "configure"),
                                recursive=True)
        for cfg_script in cfg_scripts:
            if not os.path.isfile(cfg_script):
                continue
            s = open(cfg_script).read()
            s2 = s.replace('mktemp -d "./confXXXXXX"',
                           'mktemp -d "$TMPDIR/confXXXXXX"')
            s2 = s2.replace("tmp=./conf$$-$RANDOM",
                            "tmp=$TMPDIR/conf$$-$RANDOM")
            s2 = s2.replace("(umask 077 && mktemp -d",
                            "(umask 022 && mktemp -d")
            if s2 != s:
                open(cfg_script, "w").write(s2)
        cmd = (f"CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ "
               f"CPPFLAGS='{cppflags}' TMPDIR='{tmpdir}' ./configure {bld} {opts}")
        self.run(cmd, cwd=work)
        # ============================================================
        # 关键修复（路径 C）：make 递归子项目用 $(MAKE) -C $$lib ——
        # make 的 chdir 不更新 PWD 环境变量，子 shell 的 pwd 触发
        # getcwd()；而 /data/storage/el2 等父目录对 other 用户无 r 权限，
        # getcwd 遍历父目录链失败（"cannot access parent directories:
        # Permission denied"）。改成子 shell (cd $$lib && $(MAKE))：
        # bash cd 更新 PWD，子 make 继承正确 PWD，不再 getcwd。
        # （已实测：patch 后 make 正常进入 support/cpp、sim/ucsim 等，
        #   getcwd 错误完全消失。）
        top_makefile = os.path.join(work, "Makefile")
        if os.path.isfile(top_makefile):
            ms = open(top_makefile).read()
            # 关键修复：make 的 $(MAKE) -C X 递归不改 PWD 环境变量 →
            # 子 shell pwd 触发 getcwd() 失败（/data 父目录对 other 无 r
            # 权限）；bash cd 更新 PWD 则正常（实测）。逐条精确替换，
            # 避免全局正则把带目标参数的行（如 sdcc-ld 的 $(SDCC_LD)）
            # 拆坏。for/foreach 循环与单目录 -C 分开处理。
            import re as _re
            fixes = [
                ("for lib in $(SDCC_LIBS); do $(MAKE) -C $$lib; done",
                 "for lib in $(SDCC_LIBS); do (cd $$lib && $(MAKE)); done"),
                ("for misc in $(SDCC_MISC); do $(MAKE) -C $$misc ; done",
                 "for misc in $(SDCC_MISC); do (cd $$misc && $(MAKE)) ; done"),
                ("$(foreach as, $(SDCC_AS), $(MAKE) -C $(as) &&)",
                 "$(foreach as, $(SDCC_AS), (cd $(as) && $(MAKE)) &&)"),
                ("$(MAKE) -C sdas/linksrc $(SDCC_LD)",
                 "(cd sdas/linksrc && $(MAKE) $(SDCC_LD))"),
            ]
            for _old, _new in fixes:
                ms = ms.replace(_old, _new)
            # 其余行尾形式 $(MAKE) -C <dir>（无后续目标参数）：
            # 行尾用 (\s*)$ 锚定，避免误伤 foreach/for 行
            ms = _re.sub(r'\$\(MAKE\) -C (\S+)(\s*)$',
                         r'(cd \1 && $(MAKE))', ms, flags=_re.M)
            open(top_makefile, "w").write(ms)
        # ============================================================
        # sdcpp（support/cpp）是 gcc 12.1.0 裁剪版：config/ 只有
        # dummy/i386/riscv，缺 aarch64 目录——但 host 是 aarch64，
        # cc1 编译必然引用 config/aarch64/*.def（缺失则编译失败）。
        # 创建空 .def 桩文件（sdcpp 是预处理器，aarch64 扩展选项
        # 内容无关紧要，仅需文件存在）——work 树实测 cc1/cpp 均
        # 构建成功（cc1 5MB / cpp 4.2MB）。
        # 另：support/cpp 无 libiberty 目录，gcc Makefile 的
        # LIBIBERTY 默认指向 ../libiberty/（不存在）——改为
        # ../../sdbinutils/libiberty/libiberty.a（sdbinutils 的
        # libiberty 已在顶层 make 中构建）。
        # 注意：gcc/Makefile 由 configure-gcc 目标生成——必须先触发
        # configure-gcc 再 patch LIBIBERTY/建 .def。
        # ============================================================
        cpp_dir = os.path.join(work, "support", "cpp")
        # 先触发 configure-gcc（生成 gcc/Makefile + config.status）
        self.run(
            f"/data/service/hnp/bin/bash -c \"umask 022 && "
            f"cd '{cpp_dir}' && "
            f"make configure-gcc TMPDIR='{tmpdir}'\"",
            cwd=cpp_dir)
        gcc_dir = os.path.join(cpp_dir, "gcc")
        # 空 .def 桩（aarch64 后端描述，SDCC sdist 裁剪缺失）
        aarch64_dir = os.path.join(gcc_dir, "config", "aarch64")
        os.makedirs(aarch64_dir, exist_ok=True)
        for _def in ("aarch64-arches.def", "aarch64-cores.def",
                     "aarch64-option-extensions.def"):
            _p = os.path.join(aarch64_dir, _def)
            if not os.path.isfile(_p):
                open(_p, "w").write(
                    f"/* minimal stub for {_def} — SDCC sdist trims "
                    "aarch64 support */\n")
        # LIBIBERTY 指向 sdbinutils（support/cpp 无 libiberty 目录）
        gcc_mk = os.path.join(gcc_dir, "Makefile")
        if os.path.isfile(gcc_mk):
            s = open(gcc_mk).read()
            s2 = s.replace(
                "LIBIBERTY = ../libiberty/$(LIBIBERTY_PICDIR)/libiberty.a",
                "LIBIBERTY = ../../sdbinutils/libiberty/libiberty.a")
            if s2 != s:
                open(gcc_mk, "w").write(s2)
        # bversion.h：SDCC sdist 裁剪掉了模板，configure 不生成它——
        # gcc.o 编译需要（#if (GCC_VERSION >= 3000) 数字宏），手动写入。
        bversion = os.path.join(gcc_dir, "bversion.h")
        if not os.path.isfile(bversion):
            open(bversion, "w").write(
                "/* bversion.h — normally generated by configure;\n"
                "   SDCC sdist trims the template. */\n"
                "#define GCC_VERSION 120100\n"
                "#define GCC_VERSION_FULL \"12.1.0\"\n")
        # all-tree.def：make 生成目标（gcc.o 编译依赖），先跑一次
        self.run(
            f"/data/service/hnp/bin/bash -c \"umask 022 && "
            f"cd '{gcc_dir}' && "
            f"make all-tree.def -j2 TMPDIR='{tmpdir}'\"",
            cwd=gcc_dir)
        # 非 HMDFS 分区上 getcwd 正常。关键教训：不要 export PWD——
        # 预设 PWD 与 make 实际 cwd 不符时，bash 子进程会重新 getcwd，
        # 反而触发 Permission denied（实测：手动 make configure-gcc 在
        # work 树成功 exit=0，无 export PWD）。仅 umask 022 + cd 即可。
        self.run(
            f"/data/service/hnp/bin/bash -c \"umask 022 && "
            f"cd '{work}' && "
            f"make -j2 TMPDIR='{tmpdir}'\"",
            cwd=work)
        # make install：device 库（device/lib/build/*/*.lib）必须安装到
        # share/sdcc/lib 才能被 sdcc 链接时找到（test_package 8051 编译
        # 链接报 "Couldn't find library 'mcs51'"——不 install 则缺库）。
        # STRIP=/bin/true：SDCC install 默认 strip 二进制，OHOS 上
        # stripped ELF 执行报 "Operation not permitted"（实测：未 strip
        # 的 src/sdcc 可执行，strip 副本不可执行）——禁用 strip。
        self.run(
            f"/data/service/hnp/bin/bash -c \"umask 022 && "
            f"cd '{work}' && "
            f"make install STRIP=/bin/true -j2 TMPDIR='{tmpdir}'\"",
            cwd=work)
        # 产物复制回 source_folder（package() 从 source_folder 打包
        # bin/share/lib/libexec——libexec 含 cc1，sdcpp 运行时调用它，
        # 漏复制则包内无 cc1：test 报 "cannot execute 'cc1'"）
        for entry in ("bin", "share", "lib", "libexec"):
            s = os.path.join(install_prefix, entry)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(self.source_folder, entry),
                                dirs_exist_ok=True)

    def package(self):
        src = self.source_folder
        if not os.path.isdir(os.path.join(src, "bin")):
            raise ConanException(f"sdcc bin dir missing under {src}")
        # bin/share/lib + libexec（cc1 在 libexec/sdcc/<target>/<ver>/cc1，
        # SDCC 驱动运行时需要它——漏打包则 sdcc 找不到 cc1）
        for entry in ("bin", "share", "lib", "libexec"):
            s = os.path.join(src, entry)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(self.package_folder, entry))

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.output.info(f"PATH={bindir}")
