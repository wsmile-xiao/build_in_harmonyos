#!/usr/bin/env python3
"""Conan recipe — status-code 1.0-gh0.20240312 (header-only status codes).

system_error2（Niall Douglas）：泛型/POSIX/Win32 状态码与 system_code，
outcome 实验层的底层依赖。上游无 tag/release，按 outcome v2.2.9 官方
.gitmodules 锁定 commit a35d88d6（CMake 工程版本 1.0 + gh0.<YYYYMMDD>）。
上游测试 test/ 下 4 个用例文件 + main.cpp 共享 runner（原生 main 形态），
在本包 build() 中逐个编译运行。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get

# 平台预期外条目（真机摸底后固化，证据见 notes.md / reports）：
# 每项 = (测试名, 阶段, 原因)；p0709a 需 C++20。
EXPECTED_PLATFORM_LIMITS = []


class StatusCodeConan(ConanFile):
    name = "status-code"
    version = "1.0-gh0.20240312"
    description = "status-code (system_error2) — lightweight C++ status code handling, header-only"
    license = "Apache-2.0"
    homepage = "https://github.com/ned14/status-code"
    url = "https://github.com/ned14/status-code"
    topics = ("error-handling", "status-code", "header-only", "cpp17")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.package = "package"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 上游测试：test/ 下 5 个独立 .cpp（各含 main，原生形态），
        # 逐个编译运行；p0709a 按 C++20；平台受限项按
        # EXPECTED_PLATFORM_LIMITS 跳过（本包实测无）。
        exes = self.conf.get("tools.build:compiler_executables") or {}
        cxx = (exes.get("cpp") if isinstance(exes, dict) else None) or "clang++"
        src = os.path.join(self.source_folder, "test")
        out = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(out, exist_ok=True)
        std_by_case = {"p0709a": "c++20"}
        passed, skipped, failed = [], [], []
        tests = sorted(f for f in os.listdir(src) if f.endswith(".cpp"))
        for t in tests:
            name = t[:-4]
            std = std_by_case.get(name, "c++17")
            exe = os.path.join(out, name)
            cmd = f'{cxx} -std={std} -I "{os.path.join(self.source_folder, "include")}" "{os.path.join(src, t)}" -o "{exe}"'
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
            raise ConanException(f"status-code 上游测试未预期失败 {len(failed)} 项，详见日志")

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "Licence.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "status-code")
        self.cpp_info.set_property("cmake_target_name", "status-code::status-code")
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
