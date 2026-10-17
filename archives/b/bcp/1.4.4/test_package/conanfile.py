#!/usr/bin/env python3
"""Conan test_package — bcp 1.4.4（真跑消费者，静态闭包直连 .a）。

为什么不用 pkg-config：本包与全部已发布 COIN-OR 依赖的 .pc 都把 prefix=/ 固化
在构建机上（libdir=/Libs 路径不可用，coinor-cbc 问题表 #7 同族），所以编译标志
从 dependencies cpp_info 遍历（.host 视图带传递依赖），链接串按「依赖方在前」
直连 .a 绝对路径展开——与主配方 build() 的闭包口径完全一致。

测试执行：test() 对消费者 ELF 做 OHOS 自签（否则加载器 EPERM）后直跑，
以退出码 + 输出 `BCP consumer OK: N/10` 双判（断言明细见 main.cpp 注释）。
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class BcpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "main.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _collect_includes(self):
        """遍历传递依赖收集 -I：conan 2 的 .host 视图必带传递依赖（被测包的依赖
        只 require 被测包本身时靠它才能遍历到，coinor-osi 先例同款注释）。"""
        seen, incs = set(), []
        for ref, dep in self.dependencies.host.items():
            key = str(ref.ref) if hasattr(ref, "ref") else str(ref)
            if key in seen:
                continue
            seen.add(key)
            base = getattr(dep, "package_folder", None) or ""
            for p in dep.cpp_info.includedirs:
                if not os.path.isabs(p) and base:
                    p = os.path.join(base, p)
                if os.path.isdir(p):
                    incs.append("-I" + p)
        return " ".join(dict.fromkeys(incs))

    def build(self):
        inc = self._collect_includes()
        pkg = self.dependencies["bcp"].package_folder
        d = {name: self.dependencies[name].package_folder
             for name in ("coinutils", "coin-or", "clp", "cgl", "vol", "zlib")}
        # 闭包串（依赖方在前）：与主配方 build() 完全同序，静态单遍解析方向正确
        link = " ".join([
            os.path.join(pkg, "lib", "libBcp.a"),
            os.path.join(d["clp"], "lib", "libOsiClp.a"),
            os.path.join(d["clp"], "lib", "libClpSolver.a"),
            os.path.join(d["clp"], "lib", "libClp.a"),
            os.path.join(d["vol"], "lib", "libOsiVol.a"),
            os.path.join(d["vol"], "lib", "libVol.a"),
            os.path.join(d["cgl"], "lib", "libCgl.a"),
            os.path.join(d["coin-or"], "lib", "libOsi.a"),
            os.path.join(d["coinutils"], "lib", "libCoinUtils.a"),
            os.path.join(d["zlib"], "lib", "libz.a"),
            "-lm",
        ])
        cc = os.environ.get("CXX", "clang++")
        # 与主构建同源钉 gnu++14：主包 autoconf 构建未传 -std，clang15 默认即
        # gnu++14（旧式动态异常规格 deprecated 仍合法）；profile cppstd=17 会让消
        # 者编译撞上游 BCP_buffer.hpp 的 throw(BCP_fatal_error)——build2 实测 3
        # errors「ISO C++17 does not allow dynamic exception specifications」
        # （C++ 标准代差族；编排方裁决 2026-09-23 A：改 std_flag 最小面，不动上游头）。
        std_flag = "-std=gnu++14"
        # 钉死与主配方同源的基座 flags，不继承 CI 环境泄漏值（R33 同族纪律）
        self.run(f"{cc} {std_flag} -O3 -pipe -DNDEBUG main.cpp -o bcp_consumer "
                 f"{inc} {link}")

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException("required OHOS signing tools are missing")
        output = path + ".signed"
        if os.path.lexists(output):
            os.unlink(output)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True, text=True, timeout=60,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(output).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def test(self):
        if cross_building(self):
            self.output.warning("cross-building: cannot run bcp consumer here")
            return
        exe = os.path.join(self.build_folder, "bcp_consumer")
        if not os.path.isfile(exe):
            raise ConanException(f"consumer binary missing: {exe}")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(exe)
        # 直跑（§二.19：真跑消费者，输出含 10/10 由本命令退出码兜底）
        self.run(f'"{exe}"', env="conanrun")
