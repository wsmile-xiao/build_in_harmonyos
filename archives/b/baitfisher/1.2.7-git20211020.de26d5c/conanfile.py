#!/usr/bin/env python3
"""Conan recipe for baitfisher 1.2.7 — DNA hybrid enrichment bait design (C++).

BaitFisher/BaitFilter（GPL-3.0，cmayer/BaitFisher-package）设计 DNA
杂交富集探针。纯 C++ 程序：仅需标准 POSIX 头（unistd.h/sys/stat.h/
sys/types.h/dirent.h），Makefile 构建（g++），**无任何外部库依赖**
——鸿蒙适配最简单的一类。

OHOS 适配:
- Makefile 硬编码 CXX=g++ → 配方覆盖 CXX=clang++（Environment 注入）；
- 编译 flags 注入 -Wno-register 等（老 C++ 代码兼容）；
- 测试: test_package 运行 BaitFisher 版本输出验证可执行。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get


class BaitfisherConan(ConanFile):
    name = "baitfisher"
    version = "1.2.7-git20211020.de26d5c"
    description = "BaitFisher/BaitFilter - DNA hybrid enrichment bait design"
    license = "GPL-3.0"
    homepage = "https://github.com/cmayer/BaitFisher-package"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()
        cxx = self.conf.get("tools.build:compiler_executables", default={}).get(
            "cpp") or "clang++"
        env.define("CXX", cxx)
        env.define("CXXFLAGS", "-O3 -Wno-register")
        env.vars(self).save_script("conanbuild_baitfisher_env")

    def build(self):
        # makefile 硬编码 CXX=g++（makefile 内赋值优先于环境）——
        # 用命令行变量覆盖（优先级最高）：CXX=clang++ 等
        cxx = self.conf.get("tools.build:compiler_executables", default={}).get(
            "cpp") or "clang++"
        cc = self.conf.get("tools.build:compiler_executables", default={}).get(
            "c") or "clang"
        self.run(
            f"make -j4 CXX={cxx} CC={cc} CXXFLAGS='-O3 -Wno-register' "
            f"CPPFLAGS='-I .'",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # makefile 实际产物：BaitFisher-v1.2.8 / BaitFilter-v1.0.6
        for exe in ("BaitFisher-v1.2.8", "BaitFilter-v1.0.6"):
            src = os.path.join(self.source_folder, exe)
            if os.path.exists(src):
                self.run(f"install -m 755 {src} {bindir}/")
        # 鸿蒙可执行需 ELF 签名才能运行
        self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        import shutil
        import stat
        import subprocess
        import tempfile
        from conan.errors import ConanInvalidConfiguration
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}")
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}")
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}")
        return any(".codesign" in line.split() for line in section_table.splitlines())

    @staticmethod
    def _run_tool(command, action):
        import subprocess
        from conan.errors import ConanInvalidConfiguration
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}")
        return result.stdout

    @staticmethod
    def _elf_type(path):
        from conan.errors import ConanInvalidConfiguration
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}") from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}")
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        import shutil
        from conan.errors import ConanInvalidConfiguration
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate):
            resolved = candidate
        if not resolved:
            raise ConanInvalidConfiguration(
                f"Required tool '{executable}' not found in PATH")
        return resolved

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
