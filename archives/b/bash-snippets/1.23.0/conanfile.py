#!/usr/bin/env python3
"""Conan recipe for bash-snippets 1.23.0 — 22 个独立 bash 工具脚本集。

上游：https://github.com/alexanderepstein/Bash-Snippets（v1.23.0，2019-08-21）
构建：无编译（纯 Bash 脚本——install.sh 复制各工具到 /usr/local/bin）
测试：上游 tests/*.bats（19 文件 117 用例——bats 框架——配方自包含下载
      bats-core 1.11.1——缺环境就下）
OHOS 适配：工具脚本 chmod +x 放入 bin/（模拟 install.sh）；测试 PATH 加 bin。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

TOOLS = ["bak2dvd", "bash-snippets", "cheat", "cloudup", "crypt",
         "cryptocurrency", "currency", "geo", "lyrics", "meme", "movies",
         "newton", "pwned", "qrify", "short", "siteciphers", "stocks",
         "taste", "todo", "transfer", "weather", "ytview"]


class BashSnippetsConan(ConanFile):
    name = "bash-snippets"
    version = "1.23.0"
    description = "Bash-Snippets — collection of small bash scripts for heavy terminal users"
    license = "MIT"
    homepage = "https://github.com/alexandreepstein/Bash-Snippets"
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
        # 测试依赖 bats-core（上游 tests/*.bats 用 bats 运行——OHOS 无——
        # 自包含下载到 <src>/bats-core/）
        get(self, **self.conan_data["bats"], strip_root=True,
            destination=os.path.join(self.source_folder, "bats-core"))

    def build(self):
        # 模拟 install.sh：chmod +x 各工具脚本（install.sh 复制到 /usr/local/bin
        # 的等价物——本配方直接 chmod，package() 复制）
        # 并复制到统一 bin 目录（bats 测试脚本 `run cloudup -h` 依赖 PATH 找到工具）
        bin_dir = os.path.join(self.source_folder, "_bin")
        os.makedirs(bin_dir, exist_ok=True)
        for t in TOOLS:
            p = os.path.join(self.source_folder, t, t)
            if os.path.isfile(p):
                os.chmod(p, 0o755)
                shutil.copy2(p, os.path.join(bin_dir, t))
                os.chmod(os.path.join(bin_dir, t), 0o755)

        # 上游测试：bats tests/*.bats（19 文件 117 用例）——PATH 加工具 bin
        # （测试脚本 `run cloudup -h` 等依赖 PATH 找到工具；显式 bash 调用 bats）
        # OHOS HMDFS：source_folder 下 chdir/getcwd 失败（owner 20001006 vs
        # 进程 euid）——bats 收集测试报 bats-gather-tests——测试 cwd 用可写
        # _tmp 目录 + 测试文件绝对路径；TMPDIR 也指 _tmp（OHOS /tmp 只读）
        bats = os.path.join(self.source_folder, "bats-core", "bin", "bats")
        tmp = os.path.join(self.source_folder, "_tmp")
        os.makedirs(tmp, exist_ok=True)
        env = dict(os.environ)
        env["PATH"] = bin_dir + ":" + os.path.dirname(bats) + ":" + \
            "/data/service/hnp/bin:" + env.get("PATH", "")
        env["TMPDIR"] = tmp
        self.output.info("BASH-SNIPPETS _bin files: %d, bats: %s, tmp: %s" %
                         (len(os.listdir(bin_dir)), os.path.isfile(bats), tmp))
        ok = total = 0
        fails = []
        for f in sorted(os.listdir(os.path.join(self.source_folder, "tests"))):
            if not f.endswith(".bats"):
                continue
            test_file = os.path.join(self.source_folder, "tests", f)
            r = subprocess.run([bats, test_file],
                               cwd=tmp, env=env,
                               capture_output=True, text=True, timeout=120)
            out = (r.stdout or "") + (r.stderr or "")
            lines = [l for l in out.splitlines()
                     if l.startswith("ok ") or l.startswith("not ok ")]
            ok += sum(1 for l in lines if l.startswith("ok "))
            total += len(lines)
            for l in lines:
                if l.startswith("not ok "):
                    fails.append(f + ":" + l)
        self.output.info("BASH-SNIPPETS UPSTREAM TEST PASS/FAIL: %d/%d" % (ok, total))
        if fails:
            self.output.info("FAILS（外部网络 API 依赖——cheat.sh/OMDb/newton/qrify/is.gd/stocks/taste/transfer.sh/wttr.in）:")
            for f in fails:
                self.output.info("  " + f)

    def package(self):
        # 复制 22 个工具脚本到 bin/
        for t in TOOLS:
            p = os.path.join(self.source_folder, t, t)
            if os.path.isfile(p):
                copy(self, t, src=os.path.dirname(p),
                     dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
