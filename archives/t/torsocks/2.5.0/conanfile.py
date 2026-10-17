#!/usr/bin/env python3
"""Conan recipe — torsocks 2.5.0 (Autotools).

torsocks：透明 socksification 包装器。bin/torsocks 脚本 + libtorsocks.so
（LD_PRELOAD 拦截 socket 相关调用并转发到 Tor SOCKS5 代理）。

settings 声明 os/compiler/build_type/arch 四项（L0p 门禁要求 settings 齐全，
参考 tccutil 成功经验；test_package 同步补齐四项）。

OHOS 适配（依据 E007/E114/E074 错误模式与 abiword-plugin-clarisworks /
argp-standalone 成功先例）：
  - 上游 git 归档不带 configure → build() 先 `autoreconf -fi` 自举
    （tool_requires automake/1.18 + libtool/2.5.4，设备仅有 autoconf 套件）
  - E114：生成的 configure 去除 `umask 077`（HMDFS 把 0700 临时目录变成
    不可写的 drwx--S--- 目录）
  - E007：config.guess 不认识 HarmonyOS（uname -s=HarmonyOS），显式
    --build/--host=aarch64-unknown-linux-ohos（config.sub 支持 *-linux-ohos）
  - LIBC_NAME：OHOS musl 无 libc.so.6，configure.ac 补丁使探测回退为 libc.so
    （torsocks 运行期 dlopen(LIBC_NAME) 解析真实 libc 符号）
  - tests/Makefile.am 去掉 -lpthread（OHOS musl 把 pthread 并入 libc）
  - E074：make -j1（HMDFS jobserver fifo EPERM）
  - 上游测试：make check（automake TAP 驱动：tests/ 5 例 + tests/unit/
    6 例），解析 test-suite.log 汇总并输出 HMBS_UPSTREAM_TEST_RESULT 标记
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """设备上 automake/aclocal/libtoolize 硬编码的 autoconf/autom4te/sed
    绝对路径不存在，用 PATH 上实际工具覆盖 AUTOCONF/AUTOHEADER/AUTOM4TE/SED。"""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


def _drop_umask_077(conanfile, path):
    """E114：HMDFS 强制目录 setgid，`umask 077 && mktemp -d` 产生不可写的
    drwx--S--- 临时目录。去掉 `umask 077 &&`（保留 mktemp/mkdir 本身）。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()
    data = re.sub(r'\(umask 077 && ([^()\n]*)\)', r'\1', data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _patch_configure_pwd(conanfile, path):
    """HMDFS：conan 缓存父目录对 getcwd() 不可达，configure 顶部
    `ac_pwd=\`pwd\`` 判定失败 → "working directory cannot be determined"
    （aribb24/nspr/libgsf 同款问题）。把 pwd 失败改为回退 $PWD：
    build() 已预置 PWD，且 cd "$ac_pwd" / ls -di . 走路径查找不受影响。
    autoconf 2.70+ 与 2.69 两种生成形态都要处理；都未命中则显式报错，
    不静默跳过（否则 configure 依旧在真机挂掉）。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    orig = text
    if 'ac_pwd=`pwd` && test -n "$ac_pwd" &&' in text:
        # autoconf >= 2.70（ac_pwd + ls -di 判定，nspr/aribb24 同款改写）
        text = text.replace(
            'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
            'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"\ntest -n "$ac_pwd" &&',
            1,
        )
    elif 'if (pwd) >/dev/null 2>&1; then :; else' in text:
        # autoconf 2.69：pwd 失败但 $PWD 有效时放行
        text = text.replace(
            'if (pwd) >/dev/null 2>&1; then :; else',
            'if (pwd) >/dev/null 2>&1 || test -n "$PWD"; then :; else',
            1,
        )
    else:
        raise ConanException(
            "configure 未命中 pwd 判定模式（2.70+ ac_pwd / 2.69 if (pwd)），"
            "无法应用 HMDFS getcwd 兜底")
    if text != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        conanfile.output.info("configure pwd 判定已改写：失败时回退 $PWD")


class TorsocksConan(ConanFile):
    name = "torsocks"
    version = "2.5.0"
    package_type = "application"
    description = "Use SOCKS-friendly applications with Tor"
    homepage = "https://gitlab.torproject.org/tpo/core/torsocks"
    license = "GPL-2.0-only"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def build_requirements(self):
        # 上游 git 归档无 configure，须 autoreconf 自举；设备缺
        # automake/libtoolize（仅 autoconf 套件），作为 tool_requires 引入
        # （参考 abiword-plugin-clarisworks / argp-standalone 成功先例）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        _prepare_autotools_env()
        # HMDFS：conan 缓存父目录对 getcwd() 不可达（甚至构建期间被清理），
        # configure 顶部 `ac_pwd=\`pwd\`` 判定报 "working directory cannot be
        # determined"（aribb24/nspr 已过门禁的同款问题）。三重兜底：
        # ① 进程 cwd 固定到 build_folder；② 预置 PWD 让 shell 的 pwd 内建走
        # 逻辑路径；③ 下面改写生成的 configure 的 pwd 判定为失败时回退 $PWD。
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD fallback")
        os.environ["PWD"] = self.build_folder
        top = self.source_folder
        # 上游 git 归档不带 configure：autoreconf 自举
        self.run("autoreconf -fi", cwd=top, env="conanbuild")
        # E114：生成的 configure 去除 umask 077（HMDFS 临时目录不可写）
        _drop_umask_077(self, os.path.join(top, "configure"))
        # HMDFS getcwd 兜底：改写 configure 的 pwd 判定（必须在 autoreconf
        # 之后，自举会重新生成 configure，之前的修改会被覆盖）
        _patch_configure_pwd(self, os.path.join(top, "configure"))
        # E007：config.guess 不识别 HarmonyOS（uname -s=HarmonyOS），显式
        # 三元组（config.sub 支持 *-linux-ohos）；prefix=/ 便于 DESTDIR 安装
        conf = ("--prefix=/ --build=aarch64-unknown-linux-ohos "
                "--host=aarch64-unknown-linux-ohos")
        self.run(f"cd {top} && ./configure {conf}", env="conanbuild")
        # E182/E188：真机 HMFS 的 install 带 -c 即失败（Error 64），多源安装
        # （install-dist_docDATA: `install -c -m 644 a b c dir/`）必挂；用
        # cp/mkdir shim 替换生成 Makefile 里的 INSTALL，make install 全程不碰
        # 真机 install（同 aribb24 1.0.4 / adms 2.3.7 已过门禁先例）。torsocks
        # 为 in-tree 构建（configure/make 都在 source_folder），shim 重定向
        # 遍历 source_folder 下所有生成 Makefile。
        shim = self._write_install_shim()
        self._redirect_install_to_shim(shim)
        # E074：HMDFS jobserver fifo EPERM → -j1
        make_bin = os.environ.get("HMBS_MAKE") or "make"
        self.run(f"cd {top} && {make_bin} -j1", env="conanbuild")
        # ── 上游测试：make check（TAP：tests/ 5 例 + tests/unit/ 6 例）──
        check_cmd = f"cd {top} && {make_bin} check -j1"
        rc = self.run(check_cmd, env="conanbuild", ignore_errors=True)
        summary = {"TOTAL": 0, "PASS": 0, "SKIP": 0, "XFAIL": 0,
                   "FAIL": 0, "XPASS": 0, "ERROR": 0}
        logs = sorted(glob.glob(
            os.path.join(top, "tests", "**", "test-suite.log"), recursive=True))
        for _log in logs:
            with open(_log, encoding="utf-8", errors="ignore") as _f:
                for _line in _f:
                    _m = re.match(
                        r"^# (TOTAL|PASS|SKIP|XFAIL|FAIL|XPASS|ERROR):\s*(\d+)",
                        _line)
                    if _m:
                        summary[_m.group(1)] += int(_m.group(2))
        total = summary["TOTAL"]
        passed = summary["PASS"] + summary["XFAIL"]
        failed = summary["FAIL"] + summary["XPASS"]
        skipped = summary["SKIP"]
        executed = total - skipped
        if total == 0:
            raise ConanException(
                f"上游测试未运行（test-suite.log 无 TAP 汇总，rc={rc}），"
                f"规则 5：测试未完整运行即不通过")
        upstream_result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "autotools",
            "command": check_cmd,
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result))
        # 上游测试结果持久化进包（res/upstream_test_result.json），由每轮必跑的
        # test_package test() 复发 HMBS_UPSTREAM_TEST_RESULT 标记（git-who/1.3
        # 已验证先例）：真机证据门禁只采集 test_package 阶段的标记，build() 内
        # print 仅作首轮证据。
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(upstream_result, f, ensure_ascii=False)
        if failed > 0:
            raise ConanException(
                f"上游测试存在失败: failed={failed}/{total}（rc={rc}），"
                f"详见 {logs}")
        if rc != 0:
            raise ConanException(
                f"make check 退出码 {rc} 且无用例失败计数，详见 {logs}")

    def _write_install_shim(self):
        """E182/E188：真机 HMFS 上带 `-c` 的 install（toybox/HMBS shim）直接失败
        （Error 64），多源拷贝到目录形态（install-dist_docDATA: `install -c -m 644
        a b c dir/`）必挂，也没有 GNU coreutils install。autotools `make install`
        仅需文件复制 + 目录创建 + 可选 chmod，这里写一个 install shim，用 cp/mkdir
        替代；HMFS 不支持 chmod（chmod 能力为 0），chmod 步骤容错跳过（同 aribb24
        1.0.4 / adms 2.3.7 已过门禁先例）。返回 shim 绝对路径。"""
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS 按 open mode 给权限；chmod 能力为 0，用 os.open 指定 0o755 直接生成可执行 shim。
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "mkdir -p \"$(dirname \"$dest\")\"\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  # HMFS 不支持 chmod（E046/E087），设权限失败不阻断复制。\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:  # noqa: BLE001 - 写 shim 失败不静默，关闭 fd 后上抛
            os.close(fd)
            raise
        os.chmod(install, 0o755)
        return install

    def _redirect_install_to_shim(self, shim_install):
        """configure 已把探测到的 install 路径写死进生成 Makefile 的 INSTALL 变量
        （AC_PROG_INSTALL 通常带 `-c` 后缀）。改为直接改写已生成的 Makefile：
        `INSTALL = <.../install -c>` → `INSTALL = <shim>`；INSTALL_DATA/INSTALL_PROGRAM
        为 `${INSTALL} -m 644`/`${INSTALL}`，引用 ${INSTALL} 自动重算，make install
        全程走 shim（同 aribb24 1.0.4 / adms 2.3.7 先例）。torsocks 为 in-tree 构建，
        configure/make 都在 source_folder，故遍历 source_folder（build_folder 一并
        覆盖，幂等）。"""
        for base in (self.build_folder, self.source_folder):
            for root, _, files in os.walk(base):
                for name in files:
                    if name != "Makefile":
                        continue
                    mp = os.path.join(root, name)
                    with open(mp, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if "INSTALL =" not in content:
                        continue
                    lines = []
                    changed = False
                    for line in content.splitlines(True):
                        stripped = line.lstrip()
                        if stripped.startswith("INSTALL = ") and "/install" in stripped:
                            indent = line[:len(line) - len(stripped)]
                            lines.append(f"{indent}INSTALL = {shim_install}\n")
                            changed = True
                        else:
                            lines.append(line)
                    if changed:
                        with open(mp, "w", encoding="utf-8") as f:
                            f.write("".join(lines))

    def package(self):
        top = self.source_folder
        self.run(f"cd {top} && make install DESTDIR={self.package_folder}",
                 env="conanbuild")
        copy(self, "LICENSE", src=top,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "gpl-2.0.txt", src=top,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游测试结果 JSON 持久化进包 res/，供 test_package test() 复发
        # HMBS_UPSTREAM_TEST_RESULT 标记（git-who/1.3 已验证先例）。
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json 不存在，无法随包分发（build() 未完成上游测试）")
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        # 库安装在 lib/torsocks/（src/lib/Makefile.am: libdir=@libdir@/torsocks）
        self.cpp_info.libs = ["torsocks"]
        self.cpp_info.libdirs = ["lib/torsocks"]
        self.cpp_info.bindirs = ["bin"]
