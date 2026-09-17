#!/usr/bin/env python3
"""Conan recipe — debugedit 5.3 (autotools, C).

ELF/DWARF debug-info editor (sourceware.org, derived from rpm project).
Produces CLI tools: debugedit, debugedit-classify-ar, find-debuginfo,
sepdebugcrcfix.

OHOS adaptation notes:
- Dep: elfutils/0.195 (libelf + libdw, ohpcd) + libxxhash/0.8.3 (ohpcd).
  configure uses PKG_CHECK_MODULES(LIBELF libelf / LIBDW libdw /
  XXHASH libxxhash>=0.8.0).
- autotools OHOS platform: config.guess/config.sub inline patch + explicit
  --host=aarch64-unknown-linux-ohos.
- OHOS umask 077 (E011): configure/config.status tmp dir 700 perms on hmdfs
  -> patch umask + mkdir -p -m 755 (cloog/dfu/dhcpcd pattern).
- ELF/DWARF read/write: OHOS binaries are ELF, tool should work; runtime
  debuginfo scenarios declared per rule 1.2.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class DebugeditConan(ConanFile):
    name = "debugedit"
    version = "5.3"
    description = "Tool to edit/rewrite debug info (DWARF) in ELF binaries"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceware.org/debugedit/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # elfutils（libelf+libdw）+ libxxhash（debugedit 依赖链）
        self.requires("elfutils/0.195", transitive_headers=True, transitive_libs=True)
        self.requires("libxxhash/0.8.3", transitive_headers=True, transitive_libs=True)
        # file（GNU file，带 `-N`）—— find-debuginfo 用它分类 ELF 与 .a 归档：
        #   find ... -print | file -N -f - | sed -n 's/.*current ar archive.*//p'
        # OHOS 系统 /usr/bin/file 是 toybox 0.8.12，**不支持 -N**（报
        # "file: Unknown option 'N'"）→ 枚举到 0 个文件 → 9 个上游测试连锁失败。
        # 上游 find-debuginfo 运行期真实依赖 `file`（file -bi），故按 requires 声明，
        # 使 runenv 也暴露该工具（与 rizin 等包 require file 的先例一致）。
        self.requires("file/5.48.1")
        # dwz（DWARF 压缩）—— 上游 configure 用 AC_CHECK_PROG([DWZ],[dwz],[dwz]) 硬检查；
        # 且 GDB_ADD_INDEX_CHECKS_OK 的判据为「gdb<15 或 dwz 主版本>0 或 dwz 次版本>=16」，
        # OHOS 侧 gdb 为 16.3（>=15），故必须有 dwz/0.16（DWZ_MINOR=16）才能启用
        # .gdb_index 相关测试，否则 configure 关闭该组检查、测试被跳过。
        self.requires("dwz/0.16")
        # cpio（GNU cpio）—— find-debuginfo 末尾把 .debug 文件搬进 debug 目录时用：
        #   (cd "${debug_base_name}"; cpio -pd0mL --quiet "${RPM_BUILD_ROOT}${debug_dest_name}")
        # OHOS 系统 /bin/cpio 是 toybox 0.8.12，**不支持 --quiet**（报
        # "cpio: Unknown option 'quiet'"）→ 该步骤失败 → find-debuginfo 返回非 0
        # → 相关测试失败（实测影响 6 项）。
        self.requires("cpio/2.15")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_compat_error_h()

    def _patch_compat_error_h(self):
        """OHOS musl 无 glibc 的 <error.h>（error()/error_at_line() 族）——
        写一个 compat error.h 到 include/，patch 三个源文件的 #include <error.h>
        为本地相对 include，提供 stderr 打印 + exit 的等价实现。"""
        hdr_dir = os.path.join(self.source_folder, "include")
        os.makedirs(hdr_dir, exist_ok=True)
        compat = """/* OHOS musl compat: glibc <error.h> absent — minimal stand-in. */
#ifndef _OHOS_COMPAT_ERROR_H
#define _OHOS_COMPAT_ERROR_H
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
/* OHOS musl 无 glibc 的 program_invocation_short_name，但导出 __progname
   （argv[0] 的 basename）。glibc 的 error() 前缀用 program_invocation_*，
   故此处也必须动态取程序名——否则 debugedit-classify-ar / sepdebugcrcfix
   会一律自称 "debugedit"，导致上游 debugedit-classify-ar 组 6 个测试
   因 stderr 前缀不匹配而失败（实测：39/40/41/42/43/44）。*/
extern char *__progname;
#define OHOS_PROGNAME (__progname ? __progname : "debugedit")
static inline void error(int status, int errnum, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fflush(stdout);
    fprintf(stderr, "%s: ", OHOS_PROGNAME);
    vfprintf(stderr, fmt, ap);
    if (errnum != 0) fprintf(stderr, ": %s", strerror(errnum));
    fputc('\\n', stderr);
    va_end(ap);
    if (status != 0) exit(status);
}
static inline void error_at_line(int status, int errnum, const char *fname,
                                 unsigned int lineno, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fflush(stdout);
    fprintf(stderr, "%s:%s:%u: ", OHOS_PROGNAME, fname, lineno);
    vfprintf(stderr, fmt, ap);
    if (errnum != 0) fprintf(stderr, ": %s", strerror(errnum));
    fputc('\\n', stderr);
    va_end(ap);
    if (status != 0) exit(status);
}
#endif
"""
        with open(os.path.join(hdr_dir, "error.h"), "w") as f:
            f.write(compat)
        # patch 三个源文件的 include
        inc = '#include "error.h"'
        for src in ("tools/debugedit.c", "tools/debugedit-classify-ar.c", "tools/sepdebugcrcfix.c"):
            path = os.path.join(self.source_folder, src)
            if not os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            if "#include <error.h>" in text:
                text = text.replace("#include <error.h>", inc, 1)
                open(path, "w", encoding="utf-8").write(text)
                self.output.info(f"patched {src}: <error.h> -> local compat")
        # 编译需 -Iinclude（compat error.h 在源码树 include/ 下）
        self.cpp_info.includedirs = ["include"]

    def generate(self):
        # libelf/libdw/libxxhash 的 .pc（PKG_CHECK_MODULES 命中）
        PkgConfigDeps(self).generate()
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)
        self._write_elfutils_pc()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # compat error.h（source() 生成的 include/error.h，OHOS musl 无 glibc error.h）
        # + 依赖 include/lib 兜底——必须在 tc.generate() 之前设置 extra_cflags
        tc.extra_cflags.append("-I" + os.path.join(self.source_folder, "include"))
        for _n, dep in self.dependencies.items():
            for p in dep.cpp_info.includedirs:
                tc.extra_cflags.append("-I" + p)
            for p in dep.cpp_info.libdirs:
                tc.extra_ldflags.append("-L" + p)
        tc.generate()
        # autoconf $ac_tmp 落 /tmp（OHOS 只读）→ build_folder（cloog/dfu 同款）
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        # help2man 用于生成 man page（构建二进制不需要）——OHOS 无 help2man，
        # Fedora cross 编译同款做法 HELP2MAN=true 绕过（否则 debugedit.1 失败）
        env.define("HELP2MAN", "true")
        # eu-strip/eu-readelf 等 elfutils 工具在 conan 包 bin/ 里，configure
        # AC_CHECK_PROG(eu-strip) 需 PATH 可达（否则报 "eu-strip needed by
        # find-debuginfo"）。
        # **必须 prepend 而非 append**：OHOS 的 /bin/file 是 toybox 0.8.12
        # （不支持 `-N`），若把 conan 包 bin 追加到 PATH 末尾，`file` 会被
        # toybox 版遮蔽 → find-debuginfo 枚举 0 个文件（实测 PATH 解析到
        # /bin/file）。这些包 bin/ 只含各自工具（file / dwz / eu-*），
        # 前置不会遮蔽系统工具。
        # 注意：必须跳过尚未解析出二进制的依赖——它们的 package_folder 为 None，
        # 此时 cpp_info.bindirs/libdirs 返回**相对默认值** ['bin'] / ['lib']，
        # 注入后会生成 "bin"/"lib" 这类相对条目（实测环境文件里出现
        #   PATH=...:bin:bin:bin:...   LD_LIBRARY_PATH=...:lib:lib:lib:lib:...
        # ），既无意义又会被 CWD 下的同名目录意外命中。
        for _n, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for p in dep.cpp_info.bindirs:
                env.prepend_path("PATH", p)
        # 依赖库的**运行期**搜索路径：elfutils 的 libelf/libdw 及其传递依赖
        # （libzstd/libfts/libobstack）都不在系统路径里。不注入 LD_LIBRARY_PATH 时：
        #   ① testsuite 编译出的测试二进制报 "Error loading shared library libdw.so.1"；
        #   ② 更关键——configure 执行 `dwz --version` 直接加载失败（dwz 依赖 libelf→libzstd），
        #      DWZ_MAJOR/DWZ_MINOR 被解析成错误文本，GDB_ADD_INDEX_CHECKS_OK 判为 "no"，
        #      于是**所有 .gdb_index 组测试被跳过**（实测 config.log：
        #      ac_cv_gdb_dwz_ver='16-vs-Error loading shared library libzstd.so.1...'）。
        for _n, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for p in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", p)
        # 上游测试 gdb-index 检查需 gdb（OHOS SDK 自带 /data/service/hnp/bin/gdb，
        # atlocal GDB_ADD_INDEX_CHECKS_OK 依赖 PATH 中 gdb 可达）→ 注入 gdb 所在目录
        if os.path.isdir("/data/service/hnp/bin") and os.path.isfile("/data/service/hnp/bin/gdb"):
            env.append_path("PATH", "/data/service/hnp/bin")
        # `file` 需要 magic 数据库才能分类文件。GNU file 默认按「自身路径/../share/misc/
        # magic.mgc」等位置查找，但在 testsuite 的子 shell 中实测报
        #   file: could not find any valid magic files! (No such file or directory)
        # → 枚举 0 个文件 → find-debuginfo 组测试失败。故显式指向 file 包的 magic.mgc。
        if "file" in self.dependencies:
            magic = os.path.join(self.dependencies["file"].package_folder,
                                 "share", "misc", "magic.mgc")
            if os.path.isfile(magic):
                env.define("MAGIC", magic)
            else:
                self.output.warning(f"file: magic.mgc not found at {magic}")
        envvars = env.vars(self)
        envvars.save_script("conantmpdir")
        # 注入依赖 include/lib（PKG_CHECK_MODULES 用 pkg-config 即可，此处兜底）
        # + compat error.h（source() 生成的 include/error.h，OHOS musl 无 glibc error.h）
        tc.extra_cflags.append("-I" + os.path.join(self.source_folder, "include"))
        for _n, dep in self.dependencies.items():
            for p in dep.cpp_info.includedirs:
                tc.extra_cflags.append("-I" + p)
            for p in dep.cpp_info.libdirs:
                tc.extra_ldflags.append("-L" + p)

    def _write_elfutils_pc(self):
        """elfutils 配方未细分 libelf/libdw 组件，PkgConfigDeps 未生成这两个 .pc
        （只有 libdebuginfod.pc/libxxhash.pc 等）；包内原始 .pc 的 prefix=/ 不可用。
        → 用 elfutils 包实际 lib/include 路径重写 libelf.pc/libdw.pc 到生成器目录，
        使 configure 的 PKG_CHECK_MODULES([LIBELF], [libelf]) 命中。"""
        elf = None
        for _n, dep in self.dependencies.items():
            if str(dep.ref.name) == "elfutils":
                elf = dep
                break
        if elf is None:
            self.output.warning("elfutils dep not found; skip libelf.pc/libdw.pc rewrite")
            return
        libdir = elf.cpp_info.libdirs[0] if elf.cpp_info.libdirs else ""
        incdir = elf.cpp_info.includedirs[0] if elf.cpp_info.includedirs else ""
        for name, lib in (("libelf", "elf"), ("libdw", "dw")):
            pc = os.path.join(self.generators_folder, f"{name}.pc")
            content = (
                f"prefix={os.path.dirname(libdir)}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir={libdir}\n"
                f"includedir={incdir}\n"
                f"\n"
                f"Name: {name}\n"
                f"Description: elfutils {name} library (OHOS rewrite)\n"
                f"Version: 0.195\n"
                f"Libs: -L${{libdir}} -l{lib}\n"
                f"Cflags: -I${{includedir}}\n"
            )
            with open(pc, "w") as f:
                f.write(content)
            self.output.info(f"wrote {name}.pc -> {pc}")

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_platform()
        # 清理前次失败残留的 conf* 临时目录（umask 077 建 700 权限写不进）
        for stale in glob.glob(os.path.join(self.build_folder, "conf*")):
            if os.path.isdir(stale):
                shutil.rmtree(stale, ignore_errors=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # find-debuginfo 是 configure 生成的脚本（scripts/find-debuginfo.in），
        # hmdfs 上权限 770（other 无读执行）→ testsuite 进程（CI USER=100）报
        # No such file（无权限访问）——E488 copy-rewrite chmod 777（debugedit 上游
        # 测试 40 个失败根因①）
        self._fix_script_permissions()

    def _fix_script_permissions(self):
        """find-debuginfo 真根因修复（E488 copy-rewrite 是 _gi.so 的，非本处）：
        OHOS 无 /bin/bash（bash 在 /data/service/hnp/bin/bash）→ shebang
        `#!/bin/bash` 的脚本 exec 报 No such file。把 find-debuginfo 的 shebang
        patch 到实际 bash 路径 + chmod 777（testsuite 进程可执行）。"""
        p = os.path.join(self.build_folder, "find-debuginfo")
        if not os.path.isfile(p):
            self.output.info("find-debuginfo not found under build; skip shebang fix")
            return
        text = open(p, encoding="utf-8", errors="ignore").read()
        if text.startswith("#!/bin/bash"):
            text = "#!/data/service/hnp/bin/bash" + text[len("#!/bin/bash"):]
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            self.output.info("fixed find-debuginfo shebang -> /data/service/hnp/bin/bash (OHOS has no /bin/bash)")
        # chmod 777（其他可读执行）
        tmp = p + ".tmp"
        with open(p, "rb") as r, open(tmp, "wb") as w:
            w.write(r.read())
        os.chmod(tmp, 0o777)
        os.remove(p)
        os.rename(tmp, p)
        self.output.info("find-debuginfo chmod 0777")

    def _patch_ohos_platform(self):
        """config.guess/config.sub OHOS 识别 + configure umask 077 修复（E011）。"""
        import os as _os
        cfg = _os.path.join(self.source_folder, "configure")
        if _os.path.isfile(cfg):
            ctext = open(cfg, encoding="utf-8", errors="ignore").read()
            if "umask 000" not in ctext:
                nl = ctext.find("\n")
                ctext = ctext[:nl+1] + "umask 000\n" + ctext[nl+1:]
                changed = True
            else:
                changed = False
            old_mkt = '(umask 077 && mktemp -d "./confXXXXXX")'
            if old_mkt in ctext:
                ctext = ctext.replace(old_mkt, '(umask 000 && mktemp -d "./confXXXXXX")')
                changed = True
            # dwz 兜底：上游 configure 对 dwz 做硬检查（AC_MSG_ERROR）。
            # 本配方已 require dwz/0.16（其 bin 经上面的 bindirs 循环进入 PATH），
            # 故 configure 正常走「找到 dwz」分支、DWZ 被设为 "dwz"，此处的替换
            # **不会生效**。保留它仅作为「环境异常导致 dwz 不在 PATH」时的兜底，
            # 避免整个构建硬失败（此时该分支被替换为 DWZ=""，find-debuginfo 的
            # --run-dwz 路径不可用，属受限场景，需在 notes 声明）。
            # 历史背景：写下这段时的注释为「ohpcd 无 dwz 包」——该前提已被
            # dwz/0.16 合入（PR #9459）推翻，故本配方改为直接依赖 dwz。
            old_dwz = '  as_fn_error $? "dwz needed by find-debuginfo" "$LINENO" 5'
            if old_dwz in ctext:
                ctext = ctext.replace(old_dwz, '  DWZ=""  # OHOS: dwz optional (find-debuginfo runtime scenario, rule 1.2)')
                changed = True
            if changed:
                with open(cfg, "w") as f:
                    f.write(ctext)
                self.output.info("patched configure: umask 077->000 + dwz optional (E011/runtime tool)")
        for name in ("config.guess", "config.sub"):
            path = _os.path.join(self.source_folder, name)
            if not _os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            changed = False
            if name == "config.sub":
                old1 = "| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr*)"
                if old1 in text and "ohos*)" not in text:
                    text = text.replace(old1, old1.replace("zephyr*)", "zephyr* \\\n\t     | ohos*)"), 1)
                    changed = True
                old2 = "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\\n\t\t   | linux-musl* | linux-relibc* | linux-uclibc* )"
                if old2 in text and "linux-ohos*" not in text:
                    text = text.replace(old2, old2.replace("linux-uclibc* )", "linux-uclibc* | linux-ohos* )"), 1)
                    changed = True
            else:  # config.guess
                old3 = "    aarch64:Linux:*:*)\n\tGUESS=$UNAME_MACHINE-unknown-linux-$LIBC\n\t;;"
                new3 = "    aarch64:Linux:*:*)\n\tcase `uname` in\n\t  *OHOS*) GUESS=$UNAME_MACHINE-unknown-linux-ohos ;;\n\t  *) GUESS=$UNAME_MACHINE-unknown-linux-$LIBC ;;\n\tesac\n\t;;"
                if old3 in text and "OHOS" not in text:
                    text = text.replace(old3, new3, 1)
                    changed = True
            if changed:
                with open(path, "w") as f:
                    f.write(text)
                self.output.info(f"patched {name}: OHOS platform recognition")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
