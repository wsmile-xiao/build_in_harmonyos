#!/usr/bin/env python3
"""Conan recipe for blesh 0.4.0-git20250806.8060b7a — ble.sh Bash Line Editor。

上游：https://github.com/akinomyoga/ble.sh（commit 8060b7a，2025-08-06）
构建：make（GNUmakefile——ble.pp 用 gawk 预编译生成 out/ble.sh + lib/*.sh）
测试：make check = bash out/ble.sh --test（上游内置测试框架 ble/test）
依赖：bash 3.0+ + POSIX 工具（gawk/sed/grep 等——OHOS 已具备）
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BleshConan(ConanFile):
    name = "blesh"
    version = "0.4.0-git20250806.8060b7a"
    description = "ble.sh — Bash Line Editor (command line editor written in pure Bash)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/akinomyoga/ble.sh"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # contrib submodule（blesh-contrib——make 的 include contrib/contrib.mk
        # 需要；源码 tarball 不含 submodule 内容——自包含下载解压）
        contrib_dir = os.path.join(self.source_folder, "contrib")
        os.makedirs(contrib_dir, exist_ok=True)
        get(self, **self.conan_data["contrib"], strip_root=True,
            destination=contrib_dir)

    def build(self):
        # conan run() 的 env 参数是 list（非 dict）——PATH 加 /system/bin（mkfifo）
        env = [
            "PATH=/system/bin:/data/service/hnp/bin:" + os.environ.get("PATH", ""),
        ]
        # make 生成 out/ble.sh（ble.pp 预处理——gawk）——源码在 source_folder
        # （basic_layout 的 build_folder 无 Makefile——cwd 指到 source_folder）
        self.run("make", cwd=self.source_folder, env=env)
        # OHOS HMDFS 权限模型环境适配：ble.sh 初始化用 [[ -O dir ]] 检查
        # 目录 owner 是否为当前用户——HMDFS 强制 owner 20001006:file_manager
        # （与进程 euid 不同）——改为可写检查 [[ -w dir ]]（不改测试用例）
        out_ble = os.path.join(self.source_folder, "out", "ble.sh")
        if os.path.isfile(out_ble):
            with open(out_ble) as f:
                s = f.read()
            s = s.replace('if ! (umask 077; ble/bin/mkdir -p "$dir" && [[ -O $dir ]]); then',
                          'if ! (umask 077; ble/bin/mkdir -p "$dir" && [[ -w $dir ]]); then')
            s = s.replace('elif [[ ! -O $dir ]]; then',
                          'elif [[ ! -w $dir ]]; then')
            s = s.replace('elif [[ -O $XDG_RUNTIME_DIR ]]; then',
                          'elif [[ -w $XDG_RUNTIME_DIR ]]; then')
            s = s.replace('[[ -d $runtime_dir && -O $runtime_dir ]] || return 1',
                          '[[ -d $runtime_dir && -w $runtime_dir ]] || return 1')
            s = s.replace('if [[ ! -O $_ble_base ]]; then',
                          'if [[ ! -w $_ble_base ]]; then')
            s = s.replace('elif [[ ! -O $_ble_base_repository ]]; then',
                          'elif [[ ! -w $_ble_base_repository ]]; then')
            s = s.replace('{ [[ $USER && -d /home/$USER && -O /home/$USER ]] && home=/home/$USER; } ||',
                          '{ [[ $USER && -d /home/$USER && -w /home/$USER ]] && home=/home/$USER; } ||')
            s = s.replace('{ [[ $USER && -d /Users/$USER && -O /Users/$USER ]] && home=/Users/$USER; } ||',
                          '{ [[ $USER && -d /Users/$USER && -w /Users/$USER ]] && home=/Users/$USER; } ||')
            # OHOS gawk 5.4.0 gensub bug：全局替换（"g"）带捕获组时从第二个
            # 匹配起捕获组为空（a1b2c3 → aX1bXcX）——ble/util/writearray --nlfix
            # 只输出首元素（aireview 后实测 7821/7824 的 1 个 fail）——
            # 强制 IS_GAWK=0 走 gsub 兼容路径（输出正确——已验证）
            s = s.replace('      IS_GAWK = AWKTYPE == "gawk";',
                          '      IS_GAWK = 0;')
            # OHOS HMDFS/沙箱下 /proc/$BASHPID/fd/2 等符号链接不可见（fd 实际
            # 打开但 -e 检查失败）——ble/fd#is-open 1/2 返回 1（2 个 fail）——
            # 改用 fd dup 测试（{ : 10>&$1; }——上游 fallback 兼容实现——
            # 10 避开测试自身使用的 fd 9——已本地实测全绿）——不改测试用例
            s = s.replace('''  function ble/fd#is-open { [[ $1 && -e /proc/$BASHPID/fd/$1 ]]; }
  function ble/fd#is-open/.upgrade { builtin unset -f "$FUNCNAME"; }''',
                          '''  function ble/fd#is-open { { builtin : 10>&"$1"; } 2>/dev/null; }
  function ble/fd#is-open/.upgrade { builtin unset -f "$FUNCNAME"; }''')
            with open(out_ble, "w") as f:
                f.write(s)
        # 上游测试：make check（bash out/ble.sh --test）——跑全部 section
        # 统计真实通过率（OHOS 无 mkfifo 权限——测试框架自带 mock 不阻塞）
        # 非系统性阻塞跑起来：ble.sh 的 ble/util 测试循环遍历 awk/nawk/mawk/
        # gawk 变体（6 控制字符 × 4 变体）——OHOS 缺 nawk/mawk 会导致 12 项
        # skip——下载编译 The One True AWK（onetrueawk/awk）放 PATH 补齐
        # nawk 变体（6 项跑起来）；mawk 编译受阻（configure 临时目录权限——
        # OHOS 沙箱限制——如实记录 6 项仍 skip）
        nawk_bin = os.path.join(self.build_folder, "nawk_bin", "nawk")
        if not os.path.isfile(nawk_bin):
            try:
                nawk_src = os.path.join(self.build_folder, "nawk_src")
                # codeload URL 无 .tar.gz 扩展名——conan get() 会误判 zip
                # （BadZipFile）——显式 filename= 指定（bash-git-prompt 同款教训）
                get(self, **self.conan_data.get("nawk_source", {}),
                    strip_root=True, destination=nawk_src,
                    filename="nawk.tar.gz")
                nawk_dir = nawk_src
                env_nawk = dict(os.environ)
                env_nawk["PATH"] = "/data/service/hnp/bin:/system/bin:" + \
                    env_nawk.get("PATH", "")
                # tarball 不含 awkgram.tab.c/h（bison 生成物）——先用 bison
                # 生成（OHOS 有 bison）再 maketab + 编译
                bison_gen = subprocess.run(
                    ["/data/service/hnp/bin/bison", "-d", "awkgram.y"],
                    cwd=nawk_dir, env=env_nawk, capture_output=True, text=True)
                if bison_gen.returncode != 0:
                    self.output.info("NAWK bison failed: %s" %
                                     (bison_gen.stderr or "")[:200])
                # maketab（HOSTCC）+ 各 .c → .o + 链接（绕 configure——OHOS
                # 沙箱 configure 临时目录权限受限）
                mk = subprocess.run(
                    ["/data/service/hnp/bin/clang", "-g", "-Wall", "-pedantic",
                     "-Wcast-qual", "-O2", "-o", "maketab", "maketab.c"],
                    cwd=nawk_dir, env=env_nawk, capture_output=True, text=True)
                if mk.returncode == 0:
                    with open(os.path.join(nawk_dir, "proctab.c"), "w") as pf:
                        subprocess.run([os.path.join(nawk_dir, "maketab"),
                                        os.path.join(nawk_dir, "awkgram.tab.h")],
                                       cwd=nawk_dir, env=env_nawk,
                                       stdout=pf, stderr=subprocess.DEVNULL,
                                       text=True)
                    objs = []
                    for c in ["b.c", "main.c", "parse.c", "proctab.c", "tran.c",
                              "lib.c", "run.c", "lex.c", "awkgram.tab.c"]:
                        o = c.replace(".c", ".o")
                        rc = subprocess.run(
                            ["/data/service/hnp/bin/clang", "-O2", "-c",
                             "-o", o, c], cwd=nawk_dir, env=env_nawk,
                            capture_output=True, text=True)
                        if rc.returncode == 0:
                            objs.append(o)
                    if len(objs) >= 8:
                        os.makedirs(os.path.dirname(nawk_bin), exist_ok=True)
                        link = subprocess.run(
                            ["/data/service/hnp/bin/clang", "-O2", "-o",
                             nawk_bin] + objs, cwd=nawk_dir, env=env_nawk,
                            capture_output=True, text=True)
                        if link.returncode == 0:
                            self.output.info("NAWK built: %s" % nawk_bin)
            except Exception as e:
                self.output.info("NAWK build skipped: %s" % e)
        sub_env = dict(os.environ)
        sub_env["PATH"] = "/system/bin:/data/service/hnp/bin:" + sub_env.get("PATH", "")
        if os.path.isfile(nawk_bin):
            sub_env["PATH"] = os.path.dirname(nawk_bin) + ":" + sub_env["PATH"]
        sub_env.setdefault("TERM", "xterm")
        sub_env.setdefault("HOME", os.environ.get("HOME", "/storage/Users/currentUser"))
        # HMDFS 下 source_folder getcwd 失败（bash 报 shell-init getcwd 错误）——
        # bash 回退用 PWD 环境变量定位 ble.sh 的 base（否则指向 conan create 的
        # cwd bih_blesh 工作区、测试框架库 lib/core-test 等加载失败）——
        # 显式把 PWD 指到 source_folder（getcwd 的等价替代）
        sub_env["PWD"] = self.source_folder
        r = subprocess.run(["bash", "out/ble.sh", "--test"],
                           cwd=self.source_folder, env=sub_env,
                           capture_output=True, text=True, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        # 剥离 ANSI 颜色码（ble.sh 测试输出带 \x1b[32m...\x1b[m——统计正则
        # 会被颜色码打断匹配不到数字）
        import re
        out_clean = re.sub(r"\x1b\[[0-9;]*m", "", out)
        total_p = total_t = 0
        for line in out_clean.splitlines():
            m = re.search(r"\[section\].*?: (\d+)/(\d+) \(", line)
            if m:
                total_p += int(m.group(1))
                total_t += int(m.group(2))
        self.output.info("BLESH UPSTREAM TEST PASS/FAIL: %d/%d (%.2f%%)" %
                         (total_p, total_t, 100.0 * total_p / total_t if total_t else 0))

    def package(self):
        # make install INSDIR=package_folder（把 out/ 生成的 ble.sh + lib/
        # 复制到 INSDIR——ble.sh 运行时 source 这些文件；cwd 指 source_folder）
        env = [
            "PATH=/system/bin:/data/service/hnp/bin:" + os.environ.get("PATH", ""),
        ]
        self.run(f"make install INSDIR={self.package_folder}",
                 cwd=self.source_folder, env=env)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(self.package_folder)
