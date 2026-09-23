#!/usr/bin/env python3
"""Conan recipe — outcome 2.2.9 (header-only error handling library, modular edition).

整改版（#9741 rule4）：打包 include/ 模块版头文件并声明 quickcpplib /
status-code 两个真实依赖（均按 outcome v2.2.9 官方子模块锁定 commit 适配，
见 archives/q/quickcpplib 与 archives/s/status-code），上游 42 个测试文件
（test/tests/*.cpp，quickcpplib 单测 shim 形态）在本配方 build() 中逐个
编译运行；平台受限项按 EXPECTED_PLATFORM_LIMITS 计 test_skipped 并留证。

status-code 的落位说明：outcome 实验层头文件以两种形态引用 status-code——
相对路径 "status-code/include/status-code/..."（相对 include/outcome/
experimental/，即子模块原始仓库布局）与 "-I 路径下的 <status-code/...>"。
build() 时把 status-code 依赖包的 include/status-code 树复制到源码
include/outcome/experimental/status-code/include/status-code 满足前者，
依赖包 include 目录加入 -I 满足后者；package() 同样复制以使交付包
自洽。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get

# 平台预期外条目（真机摸底实测固化，日志见 reports/ 与 notes.md 账本）
EXPECTED_PLATFORM_LIMITS = []


class OutcomeConan(ConanFile):
    name = "outcome"
    version = "2.2.9"
    description = "Outcome — a C++17/20 error handling library with result/outcome types, header-only (modular edition with upstream test suite)"
    license = ("Apache-2.0", "CC-BY-4.0")
    homepage = "https://github.com/ned14/outcome"
    url = "https://github.com/ned14/outcome"
    topics = ("error-handling", "result", "outcome", "header-only", "cpp17")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def requirements(self):
        # outcome v2.2.9 官方依赖（.gitmodules / .quickcpplib 机制）：
        # status-code 锁定官方子模块 commit a35d88d6；
        # quickcpplib 无 tag，锁定自举期 master commit 72277c70f9。
        self.requires("quickcpplib/0.1.0.0-gh0.20231208")
        self.requires("status-code/1.0-gh0.20240312")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.package = "package"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        exes = self.conf.get("tools.build:compiler_executables") or {}
        cxx = (exes.get("cpp") if isinstance(exes, dict) else None) or "clang++"
        qc_inc = self.dependencies["quickcpplib"].cpp_info.includedirs[0]
        sc_inc = self.dependencies["status-code"].cpp_info.includedirs[0]
        # 相对形态落位：status-code/include/status-code ← 依赖包 include/status-code
        sc_target = os.path.join(self.source_folder, "include", "outcome",
                                 "experimental", "status-code", "include")
        copy(self, "status-code/*", src=sc_inc, dst=sc_target, keep_path=True)

        src = os.path.join(self.source_folder, "test", "tests")
        out = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(out, exist_ok=True)
        passed, skipped, failed = [], [], []
        tests = sorted(f for f in os.listdir(src) if f.endswith(".cpp"))
        for t in tests:
            name = t[:-4]
            exe = os.path.join(out, name)
            cmd = (f'{cxx} -std=c++17 -I "{os.path.join(self.source_folder, "include")}"'
                   f' -I "{qc_inc}" -I "{sc_inc}" "{os.path.join(src, t)}" -o "{exe}"')
            if not _try(self, cmd):
                reason = _lookup(name, "compile")
                if reason:
                    skipped.append((name, reason))
                else:
                    failed.append((name, "compile"))
                continue
            # 时序敏感测试在负载下可能偶发失败：失败先重试一次再定性
            ok = _try(self, f'timeout 120 "{exe}"') or _try(self, f'timeout 120 "{exe}"')
            if ok:
                passed.append(name)
            else:
                reason = _lookup(name, "run")
                if reason:
                    skipped.append((name, reason))
                else:
                    failed.append((name, "run"))
        self.output.info(f"上游测试统计: passed={len(passed)} skipped={len(skipped)} failed={len(failed)} / {len(tests)}")
        for name, reason in skipped:
            self.output.info(f"  test_skipped {name}: {reason}")
        if failed:
            for name, stage in failed:
                self.output.error(f"  未预期失败 {name} ({stage})")
            raise ConanException(f"outcome 上游测试未预期失败 {len(failed)} 项，详见日志")

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        # .ipp inline-implementation headers sit beside the .hpp files
        # (outcome/detail/*.ipp); consumers include them via the .hpp layer.
        copy(self, "*.ipp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        # status-code 相对形态随包交付（同 build() 落位）
        sc_inc = self.dependencies["status-code"].cpp_info.includedirs[0]
        sc_target = os.path.join(self.package_folder, "include", "outcome",
                                 "experimental", "status-code", "include")
        copy(self, "status-code/*", src=sc_inc, dst=sc_target, keep_path=True)
        copy(self, "Licence.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "outcome")
        self.cpp_info.set_property("cmake_target_name", "outcome::outcome")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []


def _try(conanfile, cmd):
    """运行命令，返回退出码是否为 0（不中断 conan create）。"""
    try:
        conanfile.run(cmd)
        return True
    except ConanException:
        return False


def _lookup(name, stage):
    for n, s, reason in EXPECTED_PLATFORM_LIMITS:
        if n == name and (s == stage or s == "any"):
            return reason
    return None
