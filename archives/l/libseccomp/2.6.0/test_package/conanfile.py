# test_package/conanfile.py — libseccomp 2.6.0 consumer test (R34)
"""L1 test:
1. 编译并运行 test.c（链接 libseccomp，真实调用
   seccomp_init()/seccomp_release()/seccomp_syscall_resolve_name()
   验证库可用）。
"""
import os

from conan import ConanFile


class LibseccompTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # TMPDIR 注入（鸿蒙安全框架拦 clang 创建临时文件）
        _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = _tmp_dir
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_libseccomp")
        pkg = self.dependencies["libseccomp"].package_folder
        self.run(
            f"{cc} {src} -o {out} -std=c11 "
            f"-I{pkg}/include -L{pkg}/lib -lseccomp")

    def test(self):
        exe = os.path.join(self.build_folder, "test_libseccomp")
        # 静态链接（R26），无运行时依赖，直接执行
        self.run(exe)
