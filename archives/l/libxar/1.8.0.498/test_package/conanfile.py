#!/usr/bin/env python3
"""Conan test_package for libxar 1.8.0.498 — consumer check.

编译并运行 test_xar.c（真实 API 消费者测试，L0c/R34）：libxar 建档/读回/
校验 round-trip（none/gzip/bzip2 × sha1/sha256/sha512）。另对包内
xar CLI 做建档/列档冒烟。
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class LibxarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 探针编译/运行产物全部进临时目录：避免在源树 test_package/ 里留下
        # test_xar_probe 与 probe.* 残留（会污染 worktree 的干净状态）
        self._probe_dir = tempfile.mkdtemp(prefix="libxar-probe-")
        dep = self.dependencies["libxar"]
        cpp = dep.cpp_info
        inc = " ".join("-I" + p for p in cpp.includedirs)
        if not cpp.libdirs:
            raise ConanException("libxar package does not provide a library directory")
        # 静态 libxar.a 的未定义符号分布在各传递依赖（openssl/bzip2 静态库），
        # 聚合全部依赖的 libdir（libxml2 教训：只带本包 libdir 找不到 -lbz2）；
        # 同时对动态依赖（libxml2.so）加 RUNPATH——OHOS 运行时 LD_LIBRARY_PATH
        # 不可靠，RUNPATH 是可靠解析途径（juise/xz 教训）
        lib_flags = " ".join(
            "-L" + d + " -Wl,-rpath," + d
            for _ref, dep in self.dependencies.items() for d in dep.cpp_info.libdirs
        )
        cc = os.environ.get("CC") or "clang"
        # 显式以静态档案 libxar.a 链接（-lxar 会优先命中 .so，运行期还需加载它）；
        # xz 教训：静态链接的消费者探针不依赖运行期库搜索
        self.run(
            "{cc} {src} -o '{out}' {inc} {libs} '{archive}' "
            "-lcrypto -lxml2 -lz -lbz2".format(
                cc=cc,
                src=os.path.join(os.path.dirname(__file__), "test_xar.c"),
                out=os.path.join(self._probe_dir, "test_xar_probe"),
                inc=inc,
                libs=lib_flags,
                archive=os.path.join(cpp.libdirs[0], "libxar.a"),
            )
        )

    def test(self):
        self.run("./test_xar_probe", cwd=self._probe_dir, env="conanrun")
        # xar CLI 冒烟：真实建档 + 列档
        bindir = os.path.join(self.dependencies["libxar"].package_folder, "bin")
        if not os.path.isdir(bindir):
            raise ConanException("libxar package does not provide bin directory")
        xar_bin = os.path.join(bindir, "xar")
        if not os.path.isfile(xar_bin):
            raise ConanException("xar binary missing: {}".format(xar_bin))
        with tempfile.TemporaryDirectory() as tmp:
            sample = os.path.join(tmp, "cli-sample.txt")
            archive = os.path.join(tmp, "cli-sample.xar")
            with open(sample, "w") as f:
                f.write("libxar cli smoke test\n")
            # 在临时目录内用相对路径建档/列档，避免把绝对路径树收进档案
            self.run(
                "cd '{d}' && '{x}' -c -f cli-sample.xar cli-sample.txt "
                "&& '{x}' -t -f cli-sample.xar".format(d=tmp, x=xar_bin),
                cwd=tmp,
                env="conanrun",
            )
        shutil.rmtree(self._probe_dir, ignore_errors=True)
