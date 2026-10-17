#!/usr/bin/env python3
"""Conan recipe for x86-simd-sort 5.0 — Intel's x86 SIMD sorting library.

Upstream: https://github.com/Intel/x86-simd-sort (BSD-3-Clause).

Builds the x86-simd-sort C++ shared/static library with Meson.  The library is
x86-only (AVX2/AVX-512); on non-x86 targets (OHOS aarch64) a patch compiles
out the x86 __builtin_cpu_init/supports dispatch and every entry point
resolves to the portable scalar (std::sort) implementation.

The upstream gtest suite (3 TYPED_TEST files) is built via -Dbuild_tests=true
and executed inside build(), reported through HMBS_UPSTREAM_TEST_RESULT.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class X86SimdsortConan(ConanFile):
    name = "x86-simd-sort"
    version = "5.0"
    description = "C++ template library for high performance SIMD based sorting routines (Intel x86-simd-sort)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Intel/x86-simd-sort"
    url = "https://github.com/Intel/x86-simd-sort"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # HarmonyOS 专项测试源文件（随配方进入 source 树，build() 中编译运行）
        copy(self, "ohos-test.cpp",
             src=os.path.join(self.recipe_folder, "test_package"),
             dst=self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("x86-simd-sort supports Linux/OHOS only")

    def requirements(self):
        pass

    def build_requirements(self):
        # meson's dependency('gtest_main') resolves via pkg-config
        self.test_requires("gtest/1.17.0#ab1bc3bf51522490eef07a83c2dbd203")

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # build the upstream gtest suite and testexe
        tc.project_options["build_tests"] = "true"
        tc.generate()
        pkgdeps = PkgConfigDeps(self)
        pkgdeps.generate()
        # CI 首错修复（R02）：meson 对 clang 按基名探测 llvm-ar，而 CI worker
        # PATH 不含 llvm/bin → "Unknown linker(s): [['llvm-ar']]"。
        # 把 SDK 绝对路径的 llvm-ar/llvm-ranlib 注入 native 文件 [binaries]。
        self._inject_meson_archiver()
        # The local gtest recipe only exports a root gtest.pc, while the
        # upstream meson.build queries dependency('gtest_main'); emit the
        # gtest_main.pc shim so meson can resolve it.
        gtest = self.dependencies.get("gtest")
        if gtest is not None:
            gtest_main_pc = (
                f"prefix={gtest.package_folder}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: gtest_main\n"
                f"Description: GoogleTest (with main() function)\n"
                f"Version: 1.17.0\n"
                f"Requires: gtest = 1.17.0\n"
                f"Libs: -L${{libdir}} -lgtest_main -lpthread\n"
                f"Cflags: -I${{includedir}} -DGTEST_HAS_PTHREAD=1\n"
            )
            save(self, os.path.join(self.generators_folder, "gtest_main.pc"), gtest_main_pc)

    def _inject_meson_archiver(self):
        """把 llvm-ar/llvm-ranlib 绝对路径写入 conan_meson_native.ini [binaries]。

        meson 探测 clang 工具链时按基名查找 llvm-ar，CI buildbot worker 的 PATH
        不含 /data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin（只有 profile
        的 tools.build:compiler_executables 显式给了 c/cpp），导致
        "Unknown linker(s): [['llvm-ar']]"。此处从 SDK 固定路径注入，等价于
        accountsservice 26.27.3 的 _inject_meson_tools 先例。
        """
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.sep in cc else ""
            ar = compilers.get("ar") or None
            ranlib = compilers.get("ranlib") or None
            sdk_bin = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"
            for directory in (bindir, sdk_bin, "/data/service/hnp/bin"):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            if not ar or not ranlib:
                self.output.warning("llvm-ar/llvm-ranlib 未找到，meson 将按 PATH 探测")
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if insert:
                content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()
        self._run_ohos_test()

    def _run_ohos_test(self):
        """编译并运行 HarmonyOS 专项测试（scalar 分派/NaN/keyvalue/object 等平台点）。"""
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        src = os.path.join(self.source_folder, "ohos-test.cpp")
        libdir = self.build_folder  # meson build dir holds libx86simdsortcpp.so
        out = os.path.join(self.build_folder, "ohos-test")
        includedirs = [
            os.path.join(self.source_folder, "lib"),
            os.path.join(self.source_folder, "utils"),
        ]
        includes = " ".join(f"-I{d}" for d in includedirs)
        compile_cmd = (
            f"clang++ -std=c++17 -O2 {includes} {src} "
            f"-L{libdir} -lx86simdsortcpp -o {out}"
        )
        run_cmd = f"LD_LIBRARY_PATH={libdir} {out}"
        proc = subprocess.run(
            [bash, "-c", compile_cmd + " && " + run_cmd],
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
        )
        output = proc.stdout
        self.output.info(output)
        marker = {
            "status": "passed" if proc.returncode == 0 else "failed",
            "framework": "ohos-special",
            "command": compile_cmd + " && " + run_cmd,
            "exit_code": proc.returncode,
        }
        self.output.info("HMBS_OHOS_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if proc.returncode != 0:
            raise RuntimeError("OHOS special test failed:\n" + output[-3000:])

    def _run_upstream_tests(self):
        """Run the upstream gtest testexe and emit HMBS_UPSTREAM_TEST_RESULT."""
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        testexe = os.path.join(self.build_folder, "testexe")
        cmd = f"{testexe} --gtest_color=no"
        proc = subprocess.run(
            [bash, "-c", cmd],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3600,
        )
        output = proc.stdout
        passed = sum(int(m) for m in re.findall(r"\[  PASSED  \] (\d+) tests", output))
        failed = sum(int(m) for m in re.findall(r"\[  FAILED  \] (\d+) tests", output))
        executed = passed + failed
        discovered = executed
        if executed == 0:
            m = re.search(r"(\d+) tests from .* were not run", output)
            if not m:
                m = re.search(r"\[==========\] (\d+) tests", output)
            if m:
                discovered = int(m.group(1))
            executed = 0
            passed = 0
        status = "passed" if proc.returncode == 0 and failed == 0 and executed > 0 else "failed"
        marker = {
            "status": status,
            "framework": "gtest",
            "command": cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if status != "passed":
            self.output.error("upstream tests failed; tail:\n" + output[-3000:])
            raise RuntimeError("upstream tests failed")
        # keep the raw log for evidence
        log_path = os.path.join(self.build_folder, "upstream-gtest.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(output)
            self.output.info(f"HMBS_UPSTREAM_TEST_LOG={log_path}")
        except Exception:
            pass

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["x86simdsortcpp"]
        self.cpp_info.set_property("pkg_config_name", "x86simdsortcpp")
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))