#!/usr/bin/env python3
"""Conan recipe — adms 2.3.7 (Autotools).

ADMS (Automatic Device Model Synthesizer) converts Verilog-AMS compact
device models into ready-to-compile C code for SPICE simulators.
Release tarball ships pre-generated parser/lexer sources, so the build
does not need flex/bison/perl (the configure-time checks are neutralized
by patches/0001-configure-skip-build-tools-check.patch).
"""

import json
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AdmsConan(ConanFile):
    name = "adms"
    version = "2.3.7"
    description = "ADMS is a code generator that converts Verilog-AMS compact device models into ready-to-compile C code for SPICE simulators"
    license = "GPL-3.0"
    homepage = "https://github.com/Qucs/ADMS"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 工具默认静态链接，避免 OHOS 上 .so 运行时缺失
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # HarmonyOS: config.guess 不识别该平台，强制 build triplet（同 bash 配方）
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def _write_install_shim(self):
        # E182/E188: 真机 HMFS 上带 `-c` 的 install（toybox/HMBS shim）直接失败 (Error 64)，
        # 多源拷贝到目录形态（install-man1: `install -c a.1 b.1 dir/`）必挂，也没有 GNU coreutils
        # install。autotools `make install` 仅需文件复制 + 目录创建 + 可选 chmod，
        # 这里写一个 install shim，用 cp/mkdir 替代；HMFS 不支持 chmod，chmod 步骤容错跳过
        # （同 libfstconst 已过门禁先例）。返回 shim 绝对路径供 Makefile INSTALL 重定向。
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS 在创建时按 open mode 给权限（libfstconst notes 记载）；chmod 能力为 0，
        # 用 os.open 指定 0o755 直接生成可执行 shim，避免 open()+os.chmod 在真机失效。
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
                    "  # HMFS 不支持 chmod (E046/E087)，设权限失败不阻断复制。\n"
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
        # configure 已把探测到的 install 路径写死进所有子 Makefile 的 INSTALL 变量。
        # 改为 sed 直接改已生成的 Makefile：把 `INSTALL = <.../install ...>` 替换为
        # `INSTALL = <shim>`，INSTALL_DATA/INSTALL_PROGRAM 默认 `${INSTALL} -m 644`/`${INSTALL}`
        # 引用 ${INSTALL} 自动重算，make install 全程走 shim（同 libfstconst 先例）。
        bf = self.build_folder
        for root, _, files in os.walk(bf):
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

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: conan 创建构建树后父目录对 getcwd() 不可达，configure 内 `pwd`
        # 失败报 "working directory cannot be determined"；预置 PWD 让 shell 的
        # pwd 内建走逻辑路径（同 analog/homebrew 配方先例），补丁 0002 兜底回退 $PWD。
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        if str(self.settings.os) == "OHOS":
            # E182/E188: 真机 HMFS 的 install 带 -c 即失败 (Error 64)，man 页多源安装必挂；
            # 用 cp/mkdir shim 替换 Makefile 里的 INSTALL，make install 不再碰真机 install。
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
        autotools.make()
        # L1: 接入上游测试 —— admsCheck 自检 + admsXml 转换 dummy.va（上游 README/代码注释定义的功能测试流程）
        self._run_upstream_tests(autotools)

    def _run_upstream_tests(self, autotools):
        bin_dir = os.path.join(self.build_folder, "admsXml")
        workdir = os.path.join(self.build_folder, "upstream_test")
        os.makedirs(workdir, exist_ok=True)
        # 测试在 build 目录的子目录运行，刷新 PWD 避免 shell 解析到错误目录
        os.environ["PWD"] = workdir
        adms_check = os.path.join(bin_dir, "admsCheck").replace("\\", "/")
        adms_xml = os.path.join(bin_dir, "admsXml").replace("\\", "/")

        # 每个用例：命令退出码为 0 且输出文件非空才算通过（证伪：不轻信 exit 0）
        cases = [
            {
                "name": "admsCheck 自检（生成 dummy.va/dummy.xml）",
                "cmd": f'"{adms_check}" && test -s dummy.va && test -s dummy.xml',
            },
            {
                "name": "admsXml 转换 dummy.va -e dummy.xml → dummy.net",
                "cmd": f'"{adms_xml}" dummy.va -e dummy.xml && test -s dummy.net',
            },
        ]
        discovered = len(cases)
        executed = 0
        passed = 0
        failed = 0
        for case in cases:
            executed += 1
            try:
                self.run(case["cmd"], cwd=workdir, env="conanbuild")
            except Exception as exc:  # noqa: BLE001 - 测试失败计入 failed 而非中断构建
                failed += 1
                self.output.warning(f"upstream test failed: {case['name']}: {exc}")
            else:
                passed += 1
                self.output.info(f"upstream test passed: {case['name']}")

        if failed > 0:
            status = "failed"
        elif passed > 0:
            status = "passed"
        else:
            status = "no_tests"
        marker = {
            "status": status,
            "framework": "adms-upstream",
            "command": "admsCheck && admsXml dummy.va -e dummy.xml",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = [
            "admsElement",
            "admsPreprocessor",
            "admsVeriloga",
            "admsAdmstpath",
        ]
