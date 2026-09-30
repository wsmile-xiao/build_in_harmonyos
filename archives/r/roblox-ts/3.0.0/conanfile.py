#!/usr/bin/env python3
"""Conan recipe — roblox-ts 3.0.0（npm / Node.js CLI：TypeScript → Luau 编译器）

roblox-ts 是纯 TypeScript/Node.js 命令行工具（入口 bin/rbxtsc）。上游 npm 官方
发布包已含预编译 out/**/*.js（206 个 .js + 206 个 .d.ts）与 include/*.lua
（2 个 Luau 运行时文件），但不含 node_modules —— 其 9 个运行时 npm 依赖
（typescript@5.5.3、kleur、yargs、chokidar、fs-extra、resolve、
@roblox-ts/{luau-ast,path-translator,rojo-resolver} 及全部传递依赖，共 51 个包）
必须在 build 阶段材质化，否则 rbxtsc 启动即 MODULE_NOT_FOUND。

范式与 archives/a/actions-up（npm CLI + 运行时依赖安装）同款：
  build()    : npm install --omit=dev 材质化运行时依赖闭包 + 真实 CLI 验证
  package()  : out/ + include/ + node_modules/ + package.json → libexec/roblox-ts/
  启动器     : bin/rbxtsc（POSIX sh，显式解析可用 node 后 exec）

OHOS 适配要点（均有 test_package 用例覆盖）：
  1. 上游入口 shebang 为 `#!/usr/bin/env node`。OHOS 上 /usr/bin/env 在部分运行
     uid 下不可执行，故不依赖 shebang，改由 POSIX sh 启动器显式解析解释器。
  2. **Node.js 必须 `--jitless`**：本机 OHOS 镜像上 node v24.13.0 一旦执行 JS
     即崩（`Fatal error in , line 0 / Check failed: 12 == (*__errno_location())`，
     rc=133；知识库 E400）。npm 自身是 node 程序，故构建期 npm 与运行期 rbxtsc
     全部以 `--jitless` 驱动（与 archives/u/uglify 同款做法）。
  3. npm 入口须用**真实 npm-cli.js 路径**而非 PATH 上的 npm 包装脚本：本机 PATH
     首位是另一套 node（v24.19.0）的 shell 包装脚本，直接交给本配方选定的 node
     执行会因符号链接不可 lstat 报 EACCES（本机实测）。
  4. PATH 首位可能是不可用的工具链 node，启动器按候选顺序探测 `node --version`，
     取第一个可用解释器（RBXTSC_NODE > PATH > OHOS 系统 hnp node）。
"""
import glob
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)
from conan.tools.layout import basic_layout


class RobloxTsConan(ConanFile):
    name = "roblox-ts"
    version = "3.0.0"
    description = "A TypeScript-to-Luau Compiler for Roblox"
    license = "MIT"
    homepage = "https://github.com/roblox-ts/roblox-ts"
    url = ""  # CI fills this

    package_type = "application"

    # CI L0p 门禁要求四项齐备（OHOS profile 兼容性）
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS settings.yml 为 OHOS 定义 version 子设置且无默认值，配方未声明
        # os.version 时 conan 计算 package_id 会报
        # "Invalid: 'settings.os.version' value not defined"；有该子设置才 rm_safe。
        if hasattr(self.settings, "os") and hasattr(self.settings.os, "version"):
            self.settings.rm_safe("os.version")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        # 解析 Node.js 运行时与 npm CLI（不可用则直接判不可配置）
        self._node_tools()

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _node_tools(self):
        """解析 (node 可执行文件, npm-cli.js) —— 两者必须成对可用。

        优先 harmonybrew（CI worker 既有布局，见 archives/a/acorn），其次 OHOS 系统
        hnp node（`/data/service/hnp/node.org/<ver>/bin/node` 为真实路径，`bin/node`
        符号链接在部分运行环境下 realpath 不展开，故直接枚举真实路径）。
        npm 入口取所选 node 安装自带的 npm-cli.js——不走 PATH 上的 npm 包装脚本
        （本机 PATH 首位是另一套 node 的 shell 包装脚本，交给本配方选定的 node
        执行会因符号链接不可 lstat 报 EACCES）。
        """
        candidates = [os.path.expanduser("~/.harmonybrew/bin/node")]
        candidates += sorted(glob.glob("/data/service/hnp/node.org/*/bin/node"))
        candidates.append("/data/service/hnp/bin/node")
        which_node = shutil.which("node")
        if which_node:
            candidates.append(which_node)

        for cand in candidates:
            node = os.path.realpath(cand)
            if not (os.path.isfile(node) and os.access(node, os.X_OK)):
                continue
            base = os.path.dirname(node)
            for rel in (os.path.join("..", "lib", "node_modules", "npm", "bin", "npm-cli.js"),
                        os.path.join("lib", "node_modules", "npm", "bin", "npm-cli.js")):
                npm_cli = os.path.normpath(os.path.join(base, rel))
                if os.path.isfile(npm_cli):
                    return node, npm_cli
        raise ConanInvalidConfiguration(
            "Node.js runtime / npm CLI (npm-cli.js) pair not found")

    def build(self):
        apply_conandata_patches(self)
        # 上游发布布局完整性校验：布局变更时立即失败而非静默打包空壳
        for rel in (os.path.join("out", "CLI", "cli.js"),
                    os.path.join("out", "CLI", "index.js"),
                    os.path.join("include", "RuntimeLib.lua"),
                    "package.json",
                    "LICENSE"):
            p = os.path.join(self.source_folder, rel)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise ConanInvalidConfiguration(
                    f"upstream npm artifact incomplete: missing/empty {rel}")

        node, npm_cli = self._node_tools()
        node_dir = os.path.dirname(node)
        # Node.js 是与 C/C++ 无关的自包含运行时，不能继承 OHOS SDK 的 C/C++ 构建环境
        # （conanbuild.sh 注入的 LD_LIBRARY_PATH 指向 SDK llvm/lib，会让 node 异常
        # 终止 Native stack trace / SIGABRT）。故本步骤 env=None（不套 env 文件），
        # 并显式给出干净的 PATH/NODE_OPTIONS。
        # NODE_OPTIONS=--jitless 覆盖 npm 派生出的所有 node 子进程（E400）。
        npm = (f'PATH="{node_dir}:/data/service/hnp/bin:/usr/bin:/bin" NODE_OPTIONS=--jitless '
               f'"{node}" --jitless "{npm_cli}"')

        # 材质化运行时依赖闭包（--omit=dev 只装 9 个运行时依赖及其传递依赖；
        # --ignore-scripts/--no-save/--no-package-lock 保证不改动上游清单）
        npm_log = os.path.join(self.build_folder, "npm-install.log")
        self.run(
            npm + " install --omit=dev --ignore-scripts --no-bin-links "
                  "--no-audit --no-fund --no-save --no-package-lock"
                  f' < /dev/null > "{npm_log}" 2>&1 || {{ rc=$?; cat "{npm_log}"; exit $rc; }}',
            cwd=self.source_folder, env=None,
        )
        if not os.path.isdir(os.path.join(self.source_folder, "node_modules")):
            raise ConanInvalidConfiguration("npm install produced no node_modules")

        # 真实执行编译器 CLI（非空壳：驱动真实 rbxtsc 入口）
        for args, tag in (("--version", "version"), ("--help", "help")):
            log = os.path.join(self.build_folder, f"rbxtsc-{tag}.log")
            self.run(f'"{node}" --jitless out/CLI/cli.js {args}'
                     f' < /dev/null > "{log}" 2>&1 || {{ rc=$?; cat "{log}"; exit $rc; }}',
                     cwd=self.source_folder, env=None)
            with open(log) as fh:
                self.output.info(f"rbxtsc {args} -> {fh.read().strip()}")

    def package(self):
        app_dir = os.path.join(self.package_folder, "libexec", "roblox-ts")

        # 预编译 JS + 类型声明 + Luau 运行时 + 分发元数据
        copy(self, "out/*", src=self.source_folder, dst=app_dir)
        copy(self, "include/*", src=self.source_folder, dst=app_dir)
        copy(self, "package.json", src=self.source_folder, dst=app_dir)
        copy(self, "README.md", src=self.source_folder, dst=app_dir)
        # 运行时依赖闭包（含 .bin 等隐藏项，用 copytree 保证完整）
        shutil.copytree(os.path.join(self.source_folder, "node_modules"),
                        os.path.join(app_dir, "node_modules"), symlinks=True)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        launcher_body = "\n".join((
            "#!/bin/sh",
            "# roblox-ts (rbxtsc) launcher — HarmonyOS PC 适配",
            "set -eu",
            'script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)',
            "# 上游入口 shebang 为 `#!/usr/bin/env node`；OHOS 上 /usr/bin/env 在部分",
            "# 运行 uid 下不可执行，故改由本 POSIX sh 启动器显式解析解释器。",
            "# 候选顺序：RBXTSC_NODE 覆盖 > PATH 中的 node > OHOS 系统 hnp node；",
            "# 逐个探测 `node --version`，取第一个可用者（PATH 首位可能是不可用的",
            "# 工具链 node）。--jitless：OHOS 上 node 执行 JS 即崩（E400），",
            "# 与仓库既有 npm CLI（acorn / uglify）同款约定。",
            "# 注意：本脚本带 `set -u`，RBXTSC_NODE 可能未设置，必须用 ${VAR:-} 展开，",
            "# 否则会在注释行报 `RBXTSC_NODE: parameter not set` 中止（CI 实测）。",
            'node_bin=""',
            'for cand in "${RBXTSC_NODE:-}" "$(command -v node 2>/dev/null)" /data/service/hnp/bin/node; do',
            '    [ -n "$cand" ] || continue',
            '    [ -x "$cand" ] || continue',
            '    if "$cand" --jitless --version >/dev/null 2>&1; then node_bin="$cand"; break; fi',
            'done',
            'if [ -z "$node_bin" ]; then',
            '    echo "rbxtsc: no working Node.js interpreter found (set RBXTSC_NODE)" >&2',
            '    exit 127',
            'fi',
            'exec "$node_bin" --jitless "$script_dir/../libexec/roblox-ts/out/CLI/cli.js" "$@"',
            "",
        ))
        launcher = os.path.join(self.package_folder, "bin", "rbxtsc")
        save(self, launcher, launcher_body)
        os.chmod(launcher,
                 os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
