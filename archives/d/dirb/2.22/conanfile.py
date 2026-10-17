#!/usr/bin/env python3
"""Conan recipe — dirb 2.22 (Autotools, CLI tool)"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 配方内 install(1) shim：automake 1.9 的 INSTALL_DATA 展开为 `${INSTALL} -m 644`，
# man 页/程序安装是否成功依赖平台 install(1) 的模式位语义。本 shim 忽略模式位，
# 文件用 cp(1) 复制、目录用 mkdir -p，支持多文件安装，使安装路径不依赖平台
# install 行为。真机探针（本 run worker）：`/system/bin/install -c -m 644` 返回 0
# （产物权限位受文件系统 umask 影响为 640），shim 保留以保证确定性；CI 实测
# make install（含 man 页）成功。
_INSTALL_SHIM = r"""#!/bin/sh
# install(1) shim for the HarmonyOS PC target filesystem.
# Mode flags are ignored (mode bits not relied upon); files are copied with
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


class DirbConan(ConanFile):
    name = "dirb"
    version = "2.22"
    description = ("DIRB is a web content scanner: dictionary-based brute force "
                   "probe of hidden web resources (directories, files, objects)")
    license = "GPL-2.0"
    homepage = "https://sourceforge.net/projects/dirb/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dirb 唯一外部依赖 libcurl（configure.ac 用 curl-config + AC_CHECK_LIB
        # 探测）。curl/8.15.0 与制品仓已发布的预编译二进制对齐。
        self.requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # AC_CHECK_LIB(curl, curl_easy_init) 与链接需要 -I/-L（经环境变量注入）
        AutotoolsDeps(self).generate()
        # configure.ac 在 PATH 上直接调用 curl-config 探测 libcurl 版本与
        # cflags/libs：把全部 host 依赖包的 bin 目录前置到 conanbuild 环境
        # （即 curl 包的 bin，含 curl-config）。同时把依赖 libdir 前置到
        # LD_LIBRARY_PATH：configure 的 conftest 链接共享 libcurl.so 后需要
        # 立即运行（OHOS 动态加载器找不到 conan 缓存中的 .so → "cannot run
        # C compiled programs"；同问题与修法记载于
        # archives/a/aaphoto/0.45/notes.md 问题表第 3 行）。
        env = Environment()
        for dep in self.dependencies.host.values():
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("curl_config_path")

    def _patch_configure_tmpdir(self):
        """HMDFS/只读 /tmp 平台适配（autoconf 2.69 生成的 configure 内部模板）。

        autoconf 生成的 configure 用 "./confXXXXXX" + umask 077 建临时目录，
        在 HMDFS 与只读 /tmp 上失败（同 E114，记载于
        archives/a/aaphoto/0.45/notes.md 问题表第 1 行）；改为 ${TMPDIR:-/tmp}
        并去掉 umask 077。
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
        as_fn_error "working directory cannot be determined"。dirb 的
        configure 为 autoconf 2.69 生成（ac_pwd 模式实测存在）；改写判定，
        getcwd 失败时回退 $PWD（HMDFS getcwd 问题另见
        knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.md）。
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
        if content != original:
            with open(configure_path, "w") as f:
                f.write(content)
        else:
            self.output.warning(
                "configure pwd-check pattern not found; relying on PWD env")

    def build(self):
        apply_conandata_patches(self)

        # tarball 的 configure 自带 exec bit，但 conan 解包后丢失（run1/run2
        # 日志：can't execute: Permission denied，Error 126）。真机探针：python
        # os.chmod 与 /usr/bin/chmod 均可置位（640→750，X_OK）；同款手法见
        # archives/a/abiword-plugin-pdf/3.0.8/conanfile.py。
        # Autotools.configure() 直接 exec configure，无执行位即失败。
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            os.chmod(configure_path, 0o755)

        # HMDFS 平台诊断 [shell_getcwd]：预置 PWD 让 shell pwd 内建走逻辑路径
        # （bash 在 getcwd 失败时回退 $PWD），配合 _patch_configure_pwd() 兜底。
        os.environ["PWD"] = self.build_folder

        self._patch_configure_tmpdir()
        self._patch_configure_pwd()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # ── 上游测试门禁：NO_UPSTREAM_TESTS 证据 ──
        # dirb 上游无任何自动化测试套件：全部 4 个 Makefile.am（顶层 + src/
        # gendict_src/web2dic）仅 default/install/distclean 目标，无 check/TESTS；
        # docs/ 仅 CHANGES/FAQ/GENDICT/INSTALLATION/TODO 文本；configure.ac 无
        # 测试框架探测；tarball 无 test/ 目录（详见本版本 notes.md）。
        # 输出 no_tests 标记供 CI/Coordinator 固定证据。（command 用 "none"：
        # CI L1c 会 grep 日志中的 make check/ctest 字样，避免对"无上游测试"
        # 的库误报 upstream tests executed。）
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "none (no upstream test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        # automake 1.9 的 Makefile.in 把 INSTALL_DATA 定义为 `${INSTALL} -m 644`，
        # configure 探测到平台 INSTALL=/system/bin/install -c。为不依赖平台
        # install 的模式位与多文件语义，用配方内 shim 覆盖 INSTALL 与
        # INSTALL_DATA：忽略模式位、文件走 cp、目录走 mkdir -p（CI 实测
        # make install 含 man 页成功）。
        # 注意：INSTALL 首词保持 "/bin/sh <脚本>" 形式（与 automake/libtool 对
        # 安装程序的调用约定兼容）。
        shim_path = os.path.join(self.build_folder, "install-shim.sh")
        with open(shim_path, "w", encoding="utf-8") as f:
            f.write(_INSTALL_SHIM)
        cmd = (
            'make install DESTDIR="%s" '
            'INSTALL="/bin/sh %s" '
            "INSTALL_DATA='$(INSTALL)'"
        ) % (self.package_folder, shim_path)
        self.run(cmd, cwd=self.build_folder, env="conanbuild")

        # 上游 make install 不安装 wordlists：装入 <prefix>/share/dirb/wordlists，
        # 与 0002 补丁的运行期默认路径 <exe_dir>/../share/dirb/wordlists 对应。
        shutil.copytree(
            os.path.join(self.source_folder, "wordlists"),
            os.path.join(self.package_folder, "share", "dirb", "wordlists"),
            dirs_exist_ok=True,
        )

    def package_info(self):
        # CLI 工具（dirb/gendict/html2dic），无库产物
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
