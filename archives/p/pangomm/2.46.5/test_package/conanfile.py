#!/usr/bin/env python3
"""test_package for pangomm 2.46.5 — consumer (L1) tests + HarmonyOS-specific test.

test() 执行两组测试：

1. test_probe（test.cpp）——消费者视角 L1：编译 + 链接 + 原生运行。
   实质调用 Pango::init / FontDescription / AttrList（change() 插入判据）/版本宏。

2. test_ohos.sh + test_ohos_probe（test_ohos.cpp）——鸿蒙特有测试（14 条断言）：
   平台身份、SONAME 链物化（OHOS 禁 symlink）、ELF64/AArch64/DYN、
   SONAME、.note.ohos.ident、.codesign 签名段、完整 DT_NEEDED 链、
   无 glibc 专有 NEEDED、RUNPATH 不指向系统库目录（R26）、开发头文件、
   pkg-config 元数据、以及运行时 dlopen(RTLD_NOW)+dlsym+Pango::init() 探针
   （验证 OHOS 签名有效、依赖链可解析、符号来自被测包）。

编译命令从 Conan conf 取编译器（R33），不裸用 shell 环境变量。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cxx(self):
        # R33：编译器从 Conan conf 获取，禁止 ${CXX}。
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return ce.get("cpp") or ce.get("c") or "clang++"

    def _inc_flags(self):
        # pangomm 头文件会 include <pango/pango.h>、<glibmm.h>、<cairomm/...>
        # 与 <sigc++/sigc++.h>，必须收集所有依赖的 includedirs（相对路径按
        # package_folder 绝对化，避免出现 -Iinclude 之类的无效相对项）。
        incs = []
        for _ref, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            dirs = list(dep.cpp_info.includedirs)
            for _comp_name, comp in dep.cpp_info.components.items():
                dirs += list(comp.includedirs)
            for p in dirs:
                if not p:
                    continue
                incs.append("-I" + (p if os.path.isabs(p)
                                    else os.path.join(dep.package_folder, p)))
        return " ".join(dict.fromkeys(incs))

    def _lib_flags(self):
        libdirs = set()
        for d in self.dependencies.values():
            if d.package_folder:
                libdirs.add(os.path.join(d.package_folder, "lib"))
        return " ".join("-L" + d for d in sorted(libdirs))

    def build(self):
        cxx = self._cxx()
        inc = self._inc_flags()
        libdir = self._lib_flags()
        # 统一在 test_package 源目录的 build/ 子目录内编译（该目录已被 .gitignore
        # 忽略），build/test 两阶段路径确定。
        workdir = self.source_folder
        bindir = os.path.join(workdir, "build")
        os.makedirs(bindir, exist_ok=True)

        # L1 消费者测试（链接被测包；pangomm 2.46.x 旧 ABI：pangomm-1.4/cairomm-1.0/
        # glibmm-2.4/sigc-2.0，本包无 giomm 依赖）。
        self.run(
            f"{cxx} test.cpp -o build/test_probe {inc} "
            f"{libdir} -lpangomm-1.4 -lcairomm-1.0 -lglibmm-2.4 "
            f"-lsigc-2.0 -std=c++17",
            cwd=workdir,
        )
        # 鸿蒙特有运行时探针：故意**不链接** libpangomm-1.4，改为运行时 dlopen，
        # 以验证 OHOS 签名与加载器行为（只在真实可运行环境下有意义）。
        self.run(f"{cxx} test_ohos.cpp -o build/test_ohos_probe -std=c++17", cwd=workdir)

    def test(self):
        # 交叉 SDK / qemu 常无法运行 OHOS musl 动态链接二进制：只验编译+链接。
        if cross_building(self) or not can_run(self):
            self.output.info("cross-building / cannot run host：只验编译+链接")
            return

        # OHOS: /system/bin/sh (mksh) 不能 exec ELF，用 CONFIG_SHELL bash 包一层。
        # LD_LIBRARY_PATH 显式给出全部依赖 lib 目录；libpangomm-1.4 无 RUNPATH。
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash") or ""
        if not (bash and os.path.isfile(bash)):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError("bash not found (set CONFIG_SHELL or add bash to PATH)")

        libs = []
        for _ref, d in self.dependencies.items():
            if not d.package_folder:
                continue
            dirs = list(d.cpp_info.libdirs)
            for _comp_name, comp in d.cpp_info.components.items():
                dirs += list(comp.libdirs)
            for ld in dirs:
                if not ld:
                    continue
                # cpp_info.libdirs 可能是相对包根的路径（如 "lib"），需绝对化，
                # 否则 LD_LIBRARY_PATH 出现无效的相对项。
                libs.append(ld if os.path.isabs(ld) else os.path.join(d.package_folder, ld))
        # OHOS shared libs 需要 libc++_shared.so（SDK 提供，不是 Conan 包）。
        _sdk_libcxx = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                       "ohos/native/llvm/lib/aarch64-linux-ohos")
        if os.path.isdir(_sdk_libcxx):
            libs.append(_sdk_libcxx)
        ld_path = ":".join(dict.fromkeys(l for l in libs if l))

        workdir = self.source_folder
        probe = os.path.join(workdir, "build", "test_probe")
        ohos_probe = os.path.join(workdir, "build", "test_ohos_probe")
        pkg = self.dependencies["pangomm"].package_folder

        # ── 1) L1 消费者测试（编译 + 链接 + 原生运行）────────────────────
        self.run(f'LD_LIBRARY_PATH={ld_path} "{bash}" -c "{probe}"')

        # ── 2) 鸿蒙特有测试（编译期已就绪；此处真实执行 14 条断言）───────
        self.run(f'LD_LIBRARY_PATH={ld_path} "{bash}" test_ohos.sh "{pkg}" "{ohos_probe}"',
                 cwd=workdir)
