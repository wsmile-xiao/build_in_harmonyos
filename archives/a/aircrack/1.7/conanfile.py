#!/usr/bin/env python3
"""Conan recipe — aircrack 1.7 (Autotools)"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# 配方内 install(1) shim：目标文件系统无 chmod（hmbs 平台能力 chmod=0、
# hardlink=0、install_shim=true），configure 探测到的 install shim 不接受
# `-m <mode>`（EX_USAGE 64），`install -c -m 644` 安装 man 页直接失败。
# 此 shim 忽略模式位，文件用 cp(1) 复制、目录用 mkdir -p，支持多文件安装。
_INSTALL_SHIM = r"""#!/bin/sh
# install(1) shim for the HarmonyOS PC target filesystem
# (hmbs capabilities: install_shim=true, chmod=0, hardlink=0).
# Mode flags are ignored (chmod unsupported); files are copied with
# cp(1), directories are created with mkdir -p.
is_dir=0
mk_leading=0
files=
while [ "$#" -gt 0 ]; do
  case "$1" in
    -d) is_dir=1 ;;
    -D) mk_leading=1 ;;
    -m) shift ;;
    -m?*|--mode=*) ;;
    -c|-p|-v|-s) ;;
    -g|-o|-t) shift ;;
    --) shift
        while [ "$#" -gt 0 ]; do files="$files $1"; shift; done
        break ;;
    -*) ;;
    *) files="$files $1" ;;
  esac
  shift
done

[ -z "$files" ] && exit 0

if [ "$is_dir" = 1 ]; then
  for d in $files; do mkdir -p "$d" || exit 1; done
  exit 0
fi

set -- $files
count=$#
[ "$count" -lt 2 ] && exit 0
if [ "$count" -ge 3 ]; then
  # multi-source install: last argument is the destination directory;
  # ensure it exists (rules usually mkdir it first, be defensive)
  eval "dest=\${$count}"
  mkdir -p "$dest" || exit 1
elif [ "$mk_leading" = 1 ]; then
  # -D with a single source: create the destination's parent directory
  eval "dest=\${$count}"
  mkdir -p "$(dirname "$dest")" || exit 1
fi
cp -f "$@" || exit 1
exit 0
"""


class AircrackConan(ConanFile):
    name = "aircrack"
    version = "1.7"
    description = "Suite of tools for assessing WiFi network security"
    license = "GPL-2.0"
    homepage = "https://www.aircrack-ng.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # openssl 必须用 ohpcd 制品仓实际发布的 3.5.6.1（curl/8.15.0、cpr、
        # ice/3.8.2、icecast 等已入库配方均用此版本；curl notes 实证从 ohpcd
        # 下载 openssl/3.5.6.1#d871951ad035e2c4eecb6112af441801）。3.5.6 在
        # 制品仓无 OHOS armv8 预编译二进制 → conan 从源码构建 → CCI openssl
        # 配方 _ancestor_target 拒绝 OHOS/armv8/clang（真机连续两轮实测报错）。
        self.requires("openssl/3.5.6.1")
        # zlib/1.3.1.1 与制品仓预编译二进制对齐（同 curl/cpr/abuild 先例）
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # 官方 release tarball 是 git 快照，不含预生成 configure；
        # 真机缺 libtoolize/aclocal/autoconf/autoheader/automake（autogen.sh
        # 报 "Could not auto-detect 'libtoolize'"），经 tool_requires 补齐。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS 无 libnl（Linux netlink 库），禁用避免依赖缺失
        tc.configure_args.append("--disable-libnl")
        tc.extra_cflags.append("-Wno-deprecated-declarations")
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def _patch_config_for_ohos(self):
        """Patch config.guess and config.sub to recognize HarmonyOS."""
        src = self.source_folder
        candidates = [src, os.path.join(src, "build-aux")]
        cg_path = cs_path = None
        for d in candidates:
            cg = os.path.join(d, "config.guess")
            cs = os.path.join(d, "config.sub")
            if os.path.exists(cg) and os.path.exists(cs):
                cg_path, cs_path = cg, cs
                break
        if not cg_path:
            return
        self._patch_config_guess(cg_path)
        self._patch_config_sub(cs_path)

    def _patch_config_guess(self, cg_path):
        with open(cg_path, "r") as f:
            content = f.read()
        changed = False

        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = ("#if defined(__ANDROID__)\n    LIBC=android"
                   "\n#elif defined(__OHOS__)\n    LIBC=ohos")
            if old in content:
                content = content.replace(old, new, 1)
                changed = True

        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True

        if changed:
            with open(cg_path, "w") as f:
                f.write(content)

    def _patch_config_sub(self, cs_path):
        with open(cs_path, "r") as f:
            content = f.read()
        changed = False

        if "ohos-linux" not in content:
            pattern = (r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown'
                       r'\s*\n\s*basic_os=linux-android\s*\n\s*;;\s*\n)')
            replacement = (r'\1\tohos-linux)\n'
                           r'\tbasic_machine=$field1-unknown\n'
                           r'\tbasic_os=linux-ohos\n\t;;\n')
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changed = True

        if "ohos*" not in content:
            content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            changed = True

        if "linux-ohos" not in content:
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))',
                                     r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True

        if changed:
            with open(cs_path, "w") as f:
                f.write(content)

    def _patch_configure_tmpdir(self):
        """HMDFS/只读 /tmp 平台适配（autoconf 内部模板，configure.ac 无法修改）。

        autoconf 生成的 configure/config.status 用 "./confXXXXXX" + umask 077
        建临时目录，在 HMDFS 与只读 /tmp 上失败；改为 ${TMPDIR:-/tmp}
        （hmbs 注入可写 TMPDIR）并去掉 umask 077。
        """
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, "r") as f:
            content = f.read()
        original = content
        content = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(mktemp -d "${TMPDIR:-/tmp}/confXXXXXX") 2>/dev/null`'
        )
        content = content.replace(
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            'tmp="${TMPDIR:-/tmp}/conf$$-$RANDOM"\n  mkdir "$tmp"'
        )
        if content != original:
            with open(configure_path, "w") as f:
                f.write(content)

    def _patch_configure_pwd(self):
        """HMDFS getcwd 不可达适配：configure 的 pwd 判定回退 $PWD。

        HMDFS 对构建树父目录不提供 getcwd()，configure 内 `pwd` 失败直接
        as_fn_error "working directory cannot be determined"。改写判定：
        2.71+ 生成的 `ac_pwd=\`pwd\` && test -n "$ac_pwd" &&` 与 2.69 生成的
        `if (pwd) >/dev/null 2>&1 && test -n "\`pwd\`"` 均回退 $PWD
        （libgsf/aribb24/adms 同款做法，真机已验证）。模式缺失时仅告警，
        依赖 build() 预置的 PWD 环境变量兜底（adcli 单靠 PWD 即通过）。
        """
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, "r") as f:
            content = f.read()
        original = content
        content = content.replace(
            'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
            'ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\n'
            'test -n "$ac_pwd" &&')
        content = content.replace(
            'if (pwd) >/dev/null 2>&1 && test -n "`pwd`"',
            'if (pwd) >/dev/null 2>&1 || test -n "$PWD"')
        if content != original:
            with open(configure_path, "w") as f:
                f.write(content)
        else:
            self.output.warning(
                "configure pwd-check pattern not found; relying on PWD env")

    def build(self):
        apply_conandata_patches(self)

        # HMDFS 平台诊断 [shell_getcwd]（adcli/adms/libgsf/aribb24 同款）：
        # HMDFS 对 conan 构建树父目录不提供 getcwd()，bash/autoconf `pwd`
        # 失败报 "configure: error: working directory cannot be determined"。
        # 预置 PWD 让 shell pwd 内建走逻辑路径（bash 在 getcwd 失败时回退 $PWD），
        # 并配合 _patch_configure_pwd() 的 configure 判定改写兜底。
        os.environ["PWD"] = self.build_folder

        # 动态定位 pkg.m4 供 aclocal 使用（不硬编码路径）
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            real_path = os.path.realpath(pkg_config)
            prefix = os.path.dirname(os.path.dirname(real_path))
            aclocal_dir = os.path.join(prefix, "share", "aclocal")
            if os.path.isfile(os.path.join(aclocal_dir, "pkg.m4")):
                existing = os.environ.get("ACLOCAL_PATH", "")
                os.environ["ACLOCAL_PATH"] = (
                    f"{aclocal_dir}:{existing}" if existing else aclocal_dir
                )

        # tarball 仅含 configure.ac：用 autoreconf 生成 configure。
        # 不能用 autogen.sh——它逐个探测 libtoolize/aclocal/autoconf/
        # autoheader/automake，真机全部缺失，直接 exit 1。
        self.run("autoreconf -fiv", cwd=self.source_folder)

        # config.guess/config.sub 识别 HarmonyOS
        self._patch_config_for_ohos()

        # configure 临时目录适配（见 _patch_configure_tmpdir）
        self._patch_configure_tmpdir()

        # configure pwd 判定回退 $PWD（HMDFS getcwd 不可达，见 _patch_configure_pwd）
        self._patch_configure_pwd()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # ── 上游官方测试 (make check) ──
        self._run_upstream_checks()

    def _run_upstream_checks(self):
        """运行上游 make check 并输出 HMBS_UPSTREAM_TEST_RESULT 标记。

        上游 test/Makefile.inc 把 30 个测试脚本（test-aircrack-ng-000x、
        test-airdecap-ng-000x、test-wpaclean-000x、test-alltools、
        test-hex_string_to_array）注册为 automake TESTS，make check 逐个
        输出 "PASS:/FAIL:/SKIP:" 行；数字以真机实际输出为准。
        """
        log = os.path.join(self.build_folder, "make-check.log")
        cmd = 'set -o pipefail; make check -j1 2>&1 | tee "%s"' % log
        try:
            self.run(cmd, cwd=self.build_folder, env="conanbuild")
        except Exception:
            # make check 存在失败用例（退出码非 0）：先解析计数再如实上报
            pass

        discovered = executed = passed = failed = skipped = 0
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.match(r"^(PASS|FAIL|SKIP|XFAIL|XPASS|ERROR):\s+(\S+)",
                                 line.strip())
                    if not m:
                        continue
                    kind = m.group(1)
                    discovered += 1
                    executed += 1
                    if kind == "PASS":
                        passed += 1
                    elif kind in ("FAIL", "ERROR"):
                        failed += 1
                    elif kind == "XPASS":
                        failed += 1
                    else:  # SKIP / XFAIL
                        skipped += 1

        if failed == 0 and discovered > 0:
            status = "passed"
        elif failed > 0:
            status = "failed"
        else:
            status = "no_tests"
        marker = {
            "status": status,
            "framework": "automake",
            "command": "make check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if failed > 0 or skipped > 0:
            # 失败时把 automake test-suite.log 的失败详情段输出到构建日志，
            # 便于 CI/真机日志直接定位（日志仅在失败时存在且体积可控）
            suite_log = os.path.join(self.build_folder, "test-suite.log")
            if os.path.isfile(suite_log):
                with open(suite_log, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        self.output.info("TSLOG: " + line.rstrip("\n"))
            raise ConanException(
                "upstream make check failures/skips: " + json.dumps(marker))

    def package(self):
        # HMFS 平台适配（hmbs 能力：install_shim=true、chmod=0、hardlink=0）：
        # configure 已把 install shim 绝对路径写死进 Makefile 的 INSTALL，
        # man 页安装 `install -c -m 644 ...`（设置模式需 chmod）报 exit 64
        # (EX_USAGE)，install-man1 失败。用配方内 shim 覆盖 INSTALL 与
        # INSTALL_DATA（去掉 `-m 644`），忽略模式位、文件走 cp、目录走 mkdir。
        #
        # 注意：INSTALL 首词必须是 $SHELL 或字面 /bin/sh（libtool 2.5.4
        # ltmain.sh func_mode_install 特判：`sh <脚本> <参数...>` 形式的安装
        # 程序只有首词为 $SHELL//bin/sh 时才被识别，否则把 shim 路径与后续
        # 参数全部当作待安装文件列表，导致 `sh -c <dest>/lib/-c` 报 127）。
        shim_path = os.path.join(self.build_folder, "install-shim.sh")
        with open(shim_path, "w", encoding="utf-8") as f:
            f.write(_INSTALL_SHIM)
        cmd = (
            'make install DESTDIR="%s" '
            'INSTALL="/bin/sh %s" '
            "INSTALL_DATA='$(INSTALL)'"
        ) % (self.package_folder, shim_path)
        self.run(cmd, cwd=self.build_folder, env="conanbuild")

    def package_info(self):
        # aircrack is a CLI tool suite; bindirs carry the executables
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libs = ["aircrack", "aircrack-ce-wpa", "aircrack-ce-wep",
                              "aircrack-osdep", "accrypto", "cowpatty",
                              "ptw", "radiotap"]
