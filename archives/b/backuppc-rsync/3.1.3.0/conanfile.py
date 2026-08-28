#!/usr/bin/env python3
"""Conan recipe — backuppc-rsync 3.1.3.0 (rsync-bpc, Autotools).

backuppc-rsync 是 BackupPC 的定制版 rsync（上游名 rsync-bpc）：在 rsync 3.1.3
基础上增加 BackupPC 池文件系统 shim 层（backuppc/ 子目录 + bpc_sysCalls.c），
产物为单一命令行工具 bin/rsync_bpc，与原生 rsync 协议线级兼容。

依赖：无外部 Conan 依赖。zlib/popt 使用源码内置版本（--with-included-popt，
OHOS 无 libpopt；rsync 3.1.x 的 zlib 为源码内置实现）。

R26: 终端工具静态链接。
R32: settings.os 判断使用 in ("Linux", "OHOS")。
R33: build() 不裸用 shell 环境变量，编译参数全部来自 AutotoolsToolchain。
R34: test_package 真实执行 bin/rsync_bpc 完成本地同步功能验证。

[shell_getcwd]: HMBS 平台诊断——HMDFS 上 getcwd() 的 ".." 向上遍历失败
（向前路径解析正常），HNP bash/mksh 启动即报 shell-init/job-working-directory
警告，configure.sh（autoconf 2.69）的 AC_INIT 目录检查 `ac_pwd=`pwd``
直接终止："working directory cannot be determined"。修复（nspr/4.37 +
air-quality-sensor/0.1.5 先例）：①OHOS 下导出有效 PWD=build_folder
（bash/mksh 的 pwd 信任有效 $PWD，不再调 getcwd）；②os.chdir 到构建目录；
③程序化改写 configure.sh 的 pwd 探测，失败时回退 $PWD。
E002: OHOS /tmp 为 erofs 只读挂载；TMPDIR/TMP/TEMP 注入工具链环境与
进程环境，configure/make/mktemp/shell 临时文件全部落到可写目录。

[vpath_objdirs]: VPATH 构建目录缺 backuppc/ 对象子目录——上游
AC_CONFIG_FILES 的 dummy 清单（configure.ac:1120：lib/zlib/popt）漏配
BackupPC 新增的 backuppc/ 子目录，config.status 不会在构建目录创建它，
而 .c.o 规则以相对路径 `-o backuppc/xxx.o` 输出，clang 报 unable to
open output file。build() 在 make 前扫描生成的 Makefile，幂等创建
全部含目录前缀的 *.o 目标所需子目录（保底补 backuppc/）。
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BackuppcRsyncConan(ConanFile):
    name = "backuppc-rsync"
    version = "3.1.3.0"
    description = "BackupPC customized rsync (rsync-bpc): incremental backup transfer tool compatible with native rsync protocol"
    license = "GPL-3.0"
    homepage = "https://github.com/backuppc/rsync-bpc"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        """E002: OHOS /tmp 是 erofs 只读挂载。

        优先复用 hmbs 注入的任务级临时目录（HMBS_TMPDIR/TMPDIR/TMP/TEMP），
        缺失时回退 $HOME/tmp 下按包隔离的目录；确保目录存在。
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value:
                tmpdir = value
                break
        else:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp",
                                  "backuppc-rsync-3.1.3.0")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder or os.getcwd()
        return tmpdir

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 终端工具静态链接（与同族 rsync 包一致）
        tc.extra_ldflags.append("-static")
        # E114: --no-create 先生成 config.status 而不立即执行，
        # 以便在执行前程序化修复 HMDFS 上 mktemp 权限问题。
        tc.configure_args.append("--no-create")
        # OHOS 无系统 libpopt，确定性使用源码内置 popt
        tc.configure_args.append("--with-included-popt")
        # E002: /tmp 只读——把可写 TMPDIR 写入 conanbuild 环境，
        # 使 configure/make/mktemp 及其 shell 临时文件避开 /tmp
        env = tc.environment()
        tmpdir = self._writable_tmpdir()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # E165: 修复源码树内脚本 shebang（仅 OHOS 需要）
        self._fix_all_shebangs()

        # E002: 进程级可写 TMPDIR（mktemp/shell 临时文件不再落到只读 /tmp）
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        # [shell_getcwd] HMDFS：getcwd 向上遍历失败，先程序化修复 configure.sh
        # 的 AC_INIT 目录检查（pwd 失败回退 $PWD），再导出有效 PWD 并 chdir 到
        # 构建目录（nspr/4.37 + air-quality-sensor/0.1.5 先例）
        if self.settings.os == "OHOS":
            self._patch_configure_workdir()
            os.environ["PWD"] = self.build_folder
            self.output.info(
                "[shell_getcwd] PWD=%s exported for configure workdir fallback"
                % self.build_folder)
        # 构建进程 cwd 先行落到（向前可解析的）构建目录再启动 configure
        os.chdir(self.build_folder)

        # 源码包同时带有 configure(/bin/sh 包装器) 与 configure.sh，
        # 包装器会 exec configure.sh，Autotools 可直接调用。
        autotools = Autotools(self)
        # E114 步骤 1：configure --no-create 只生成 config.status 不执行
        autotools.configure()

        # E114 步骤 2：在执行前修复生成的 config.status（生成文件，不打源码补丁）
        self._fix_config_status_mktemp()

        # 运行 config.status 生成 Makefile/config.h（显式用解释器执行，
        # 避免 shebang 依赖；env=["conanbuild"] 提供 CC/CFLAGS 等工具链环境）
        self.run("bash config.status", env=["conanbuild"])

        # configure 在 libc 中检测到 getpass 但 OHOS 无头文件声明，
        # 生成 config.h 后 undef HAVE_GETPASS，让 rsync.h 提供本地声明
        self._undef_getpass()

        # [vpath_objdirs] VPATH 构建目录缺 backuppc/（上游 AC_CONFIG_FILES
        # 的 dummy 清单漏配该子目录），make 前确保所有对象输出子目录存在
        self._ensure_object_dirs()

        autotools.make(args=["-j1"])

        # OHOS ELF 自签名：静态链接产物需含 .codesign 段，否则真机 exec 被内核 SIGKILL (signal 9 / exit 137)。
        # 经验 dkjson/2.8-1.1 已验证：llvm-objcopy 清理旧段 + binary-sign-tool selfSign。
        if self.settings.os == "OHOS":
            for candidate in (
                os.path.join(self.build_folder, "rsync_bpc"),
                os.path.join(self.build_folder, "rsync"),
            ):
                if os.path.isfile(candidate):
                    self._sign_ohos_binary(candidate)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        if self.settings.os == "OHOS":
            pkg_bin = os.path.join(self.package_folder, "bin", "rsync_bpc")
            if os.path.isfile(pkg_bin):
                self._sign_ohos_binary(pkg_bin)

    def package_info(self):
        # 命令行工具包（bin/rsync_bpc），非库
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

    # ------------------------------------------------------------------
    # 平台适配辅助（程序化修复，不修改生成文件之外的源码）
    # ------------------------------------------------------------------

    def _sign_ohos_binary(self, bin_path):
        """OHOS ELF 自签名（dkjson/2.8-1.1 经验复用）。

        静态链接的 rsync_bpc 缺少 .codesign 时，HongMeng 内核直接 SIGKILL（signal 9，
        conan create exit 137），并非 Permission denied。本方法幂等：
        llvm-objcopy --remove-section .codesign 清理旧段，再用 binary-sign-tool
        selfSign 1 生成新签名；双路径 fallback（/data/service/hnp/bin 与 PATH），
        chmod 包在 try/except 以兼容 HMBS_CAP_CHMOD=0 的只读文件系统。
        """
        # 清理旧签名段（不存在则忽略）
        for tool in (
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "llvm-objcopy",
        ):
            try:
                subprocess.run(
                    [tool, "--remove-section", ".codesign", bin_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=10,
                )
                break
            except Exception:
                continue
        # 自签名
        signed = False
        for tool in (
            "/data/service/hnp/bin/binary-sign-tool",
            shutil.which("binary-sign-tool") or "binary-sign-tool",
        ):
            try:
                result = subprocess.run(
                    [tool, "sign", "-inFile", bin_path, "-outFile", bin_path, "-selfSign", "1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=15,
                )
                if result.returncode == 0:
                    signed = True
                    self.output.info("OHOS self-signed %s with %s" % (bin_path, tool))
                    break
            except Exception:
                continue
        if not signed:
            self.output.warning("OHOS signing failed for %s (binary-sign-tool not found or error)" % bin_path)
        try:
            os.chmod(bin_path, 0o755)
        except OSError:
            pass

    def _ensure_object_dirs(self):
        """[vpath_objdirs] VPATH 构建下对象输出子目录缺失。

        上游用 AC_CONFIG_FILES 的 dummy 文件顺带创建对象子目录：
        configure.ac:1120 为 `AC_CONFIG_FILES([Makefile lib/dummy zlib/dummy
        popt/dummy shconfig])`——config.status 生成这些文件时自动创建
        lib/、zlib/、popt/。但 BackupPC 新增的 backuppc/ 子目录不在清单里
        （Makefile.in distclean 却引用了 backuppc/dummy），且 .c.o 规则以
        相对路径 `-o backuppc/xxx.o` 直接输出、无任何 mkdir 步骤：源内构建
        时目录天然存在掩盖问题，VPATH 构建（conan build-release）下 clang
        报 "unable to open output file 'backuppc/bpc_attrib.o'"。
        程序化兜底：扫描生成的 Makefile 中全部含目录前缀的 *.o 目标，
        在构建目录逐一幂等创建对应子目录；Makefile 缺失时保底补 backuppc/。
        """
        makefile = None
        for base in (self.build_folder, self.source_folder):
            if not base:
                continue
            path = os.path.join(base, "Makefile")
            if os.path.isfile(path):
                makefile = path
                break
        obj_re = re.compile(r"\b((?:[A-Za-z0-9_.+-]+/)+)[A-Za-z0-9_.+-]+\.o\b")
        dirs = set(["backuppc"])
        if makefile:
            try:
                with open(makefile, "r", encoding="utf-8",
                          errors="replace") as f:
                    content = f.read()
            except OSError:
                content = ""
            for match in obj_re.finditer(content):
                rel_dir = match.group(1)
                if rel_dir.startswith("./"):
                    rel_dir = rel_dir[2:]
                rel_dir = rel_dir.rstrip("/").replace("\\", "/")
                parts = rel_dir.split("/")
                if rel_dir and not rel_dir.startswith("/") \
                        and ".." not in parts:
                    dirs.add(rel_dir)
        target_root = self.build_folder or self.source_folder
        created = []
        for rel_dir in sorted(dirs):
            target = os.path.join(target_root, *rel_dir.split("/"))
            if os.path.isdir(target):
                continue
            try:
                os.makedirs(target, exist_ok=True)
                created.append(rel_dir)
            except OSError as exc:
                self.output.warning(
                    "[vpath_objdirs] cannot create %s: %s" % (target, exc))
        self.output.info(
            "[vpath_objdirs] ensured %d object subdir(s)%s"
            % (len(dirs), ("; created: %s" % ", ".join(created))
               if created else ""))

    def _fix_all_shebangs(self):
        """E165: 将 #!/bin/sh、#!/bin/bash 替换为 OHOS 实际路径。

        R32: 仅在 OHOS 上执行；Linux 保持标准路径。
        """
        if self.settings.os != "OHOS":
            return
        src = self.source_folder
        sh_replacements = {
            "#!/bin/sh": "#!/system/bin/sh",
            "#! /bin/sh": "#! /system/bin/sh",
            "#!/bin/bash": "#!/data/service/hnp/bin/bash",
            "#! /bin/bash": "#! /data/service/hnp/bin/bash",
        }
        for root, dirs, files in os.walk(src):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    if os.path.getsize(fpath) > 4 * 1024 * 1024:
                        continue
                    with open(fpath, "r") as f:
                        first_line = f.readline()
                    if first_line.startswith("#!") and (
                            "/bin/sh" in first_line or "/bin/bash" in first_line):
                        with open(fpath, "r") as f:
                            content = f.read()
                        for old, new in sh_replacements.items():
                            content = content.replace(old, new)
                        with open(fpath, "w") as f:
                            f.write(content)
                except (UnicodeDecodeError, PermissionError,
                        IsADirectoryError, OSError):
                    pass

    def _find_generated_file(self, name):
        """config.status/config.h 由 configure 生成，位置随布局不同而异。"""
        for base in (self.build_folder, self.source_folder):
            path = os.path.join(base, name)
            if path and os.path.exists(path):
                return path
        return None

    def _patch_configure_workdir(self):
        """[shell_getcwd] 修复 configure.sh 的 AC_INIT 工作目录检查。

        HMDFS 上 getcwd() 的 ".." 向上遍历失败，autoconf 2.69 生成的
        `ac_pwd=`pwd`` 检查直接 as_fn_error "working directory cannot be
        determined"。改为 pwd 失败时回退到 $PWD（由 build() 显式导出为
        构建目录绝对路径；bash/mksh 的 pwd 信任有效 $PWD，不再调 getcwd；
        ls -di . 与 cd "$ac_pwd" 均为向前路径解析，HMDFS 支持）。
        configure.sh 是生成文件，程序化改写、不打源码补丁（E114 同范式）。
        """
        old_pattern = 'ac_pwd=`pwd` && test -n "$ac_pwd" &&'
        new_pattern = ('ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\n'
                       'test -n "$ac_pwd" &&')
        patched = False
        for name in ("configure.sh", "configure"):
            path = os.path.join(self.source_folder, name)
            if not path or not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            if old_pattern not in content:
                continue
            content = content.replace(old_pattern, new_pattern, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            patched = True
            self.output.info(
                "[shell_getcwd] patched %s: ac_pwd falls back to $PWD" % name)
        if not patched:
            self.output.warning(
                "[shell_getcwd] working-dir pattern not found in "
                "configure.sh; relying on PWD env var only")

    def _fix_config_status_mktemp(self):
        """E114: config.status 用 mktemp 在当前目录（HMDFS）建临时目录权限不足。

        将临时目录重定向到 $TMPDIR 下固定路径；在 configure --no-create
        之后、config.status 执行之前应用。autoconf 2.69 生成的 config.status
        含三类 tmp 回退模式，逐一替换；均未命中则跳过（交由平台 mktemp
        fallback 能力处理），不视为错误。
        """
        cs_file = self._find_generated_file("config.status")
        if not cs_file:
            return
        with open(cs_file, "r") as f:
            content = f.read()
        # E002: 使用可写临时目录（/tmp 只读），与 generate()/build() 注入一致
        tmpdir = self._writable_tmpdir()
        fixed_dir = os.path.join(tmpdir, "bpc-rsync-config-status-tmp")
        try:
            os.makedirs(fixed_dir, exist_ok=True)
        except OSError:
            return
        replaced = 0
        # Pattern 1: 主路径 mktemp -d "./confXXXXXX"
        content, n = re.subn(
            r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
            'tmp=%s' % fixed_dir,
            content)
        replaced += n
        # Pattern 2: 回退 ./conf$$-$RANDOM
        content, n = re.subn(r'tmp=\./conf\$\$-\$RANDOM',
                             'tmp=%s' % fixed_dir, content)
        replaced += n
        # Pattern 3: mkdir "$tmp" 兜底改为空操作（目录已存在）
        content, n = re.subn(r'\(umask 077 && mkdir "\$tmp"\)', 'true', content)
        replaced += n
        if replaced:
            with open(cs_file, "w") as f:
                f.write(content)
            self.output.info(
                "E114: redirected %d mktemp pattern(s) in config.status to %s"
                % (replaced, fixed_dir))

    def _undef_getpass(self):
        """config.h 中 HAVE_GETPASS 未定义化：OHOS libc 有符号无头文件声明。"""
        ch_file = self._find_generated_file("config.h")
        if not ch_file:
            return
        with open(ch_file, "r") as f:
            lines = f.readlines()
        new_lines = []
        changed = False
        for line in lines:
            if "HAVE_GETPASS" in line and line.strip().startswith("#define"):
                new_lines.append("/* #undef HAVE_GETPASS */\n")
                changed = True
            else:
                new_lines.append(line)
        if changed:
            with open(ch_file, "w") as f:
                f.writelines(new_lines)
