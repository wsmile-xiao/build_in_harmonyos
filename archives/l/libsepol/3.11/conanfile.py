#!/usr/bin/env python3
"""Conan recipe for libsepol 3.11 on HarmonyOS PC.

libsepol is a plain Makefile project (no autotools/CMake/meson).
The SELinuxProject monorepo archive contains both libselinux and libsepol.
Only libsepol targets are built here; this is a standalone Conan package
consumed by libselinux, secilc and other SELinux-related packages.

Upgrade 3.10 -> 3.11: new symbols required by secilc 3.11
(sepol_kernel_policydb_decls_to_cil, cil_check_neverallows_against_pdb).

R33: Never use ${CC} or ${CFLAGS} in self.run() — they are empty on CI workers.
     Get compiler from Conan: self.conf.get("tools.build:compiler_executables:c", ...)
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibsepolConan(ConanFile):
    name = "libsepol"
    version = "3.11"
    description = "SELinux binary policy manipulation library"
    license = "LGPL-2.1"
    homepage = "https://github.com/SELinuxProject/selinux"
    url = "https://github.com/SELinuxProject/selinux"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # rule4 整改（2026-09-21 CIW）：上游 libsepol/tests 的 test: 目标链接 -lcunit、
        # 并调用同源码树的兄弟二进制 ../../checkpolicy/checkpolicy 生成测试策略，
        # 故 CUnit 是本包“仅构建期测试用”的依赖（不进入 final package）。
        self.test_requires("cunit/2.1.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")

        # libsepol uses -Werror by default; strip it to avoid build failures
        # on OHOS Clang 15 with newer warning flags.
        cflags = "-O2 -fPIC -D_GNU_SOURCE -I. -I../include"

        # Build libsepol (static library only; CIL objects are merged into
        # libsepol.a by the upstream build, see notes.md).
        self.run(
            f"make -C {self.source_folder}/libsepol -j1 CC={cc} "
            f"CFLAGS='{cflags}' "
            f"DISABLE_SHARED=y "
            f"all",
        )

        # ── 上游测试：真实执行（rule4）──────────────────────────────────
        # 上游 libsepol/tests 的 test: 目标有三重前置（见 knowledge/drafts/
        # DRAFT-libsepol-3.11-upstream-cunit-suite-with-sibling-tool）：
        #   ① CUnit（-lcunit）——由 test_requires(cunit) 提供
        #   ② 同源码树兄弟二进制 checkpolicy ——需先构建
        #   ③ m4 预处理 .conf → .conf.std/.conf.mls ——由 m4 工具完成
        # 缺任一项都跑不起来 ⇒ 这就是 rule4 判「N=28 但 0 执行」的根因。
        cpp = self.dependencies.test["cunit"].cpp_info.aggregated_components()
        cunit_incs = " ".join(f'-I"{p}"' for p in cpp.includedirs)
        cunit_libs = " ".join(f'-L"{p}"' for p in cpp.libdirs) + " " + " ".join(f"-l{l}" for l in cpp.libs)
        cunit_syslibs = " ".join(f"-l{l}" for l in cpp.system_libs)

        # ② 兄弟二进制 checkpolicy（同 tarball；测试用它生成 policy）
        self.run(
            f"make -C {self.source_folder}/checkpolicy -j1 CC={cc} "
            f"CFLAGS='-O2 -D_GNU_SOURCE -I{self.source_folder}/libsepol/include' "
            # checkpolicy 的 Makefile 默认用 `-l:libsepol.a` 且不发 -L；显式传 LIBSEPOLA
            # 指向刚构建出的静态库（上游 Makefile:15-19 支持该变量）。
            f"LIBSEPOLA={self.source_folder}/libsepol/src/libsepol.a",
        )

        # ③ 跑上游套件 test: 目标（m4 生成 policy → CUnit 执行 → 退出码即结论）
        self.run(
            f"make -C {self.source_folder}/libsepol/tests -j1 CC={cc} "
            f"CFLAGS='{cflags} {cunit_incs}' "
            # 注意：tests/Makefile:51 的链接行把 -lcunit 写死在规则里（不经 $(LDLIBS)），
            # 只有 $(LDFLAGS) 出现在 -lcunit 之前 ⇒ **必须走 LDFLAGS 注入 -L**，
            # 否则报 `ld.lld: error: unable to find library -lcunit`（实测 2026-09-21）。
            f"LDFLAGS='{cunit_libs}' "
            f"LDLIBS='{cunit_syslibs}' "
            f"test",
        )

    def package(self):
        # Install headers from libsepol/include/ preserving tree structure
        src_include = os.path.join(self.source_folder, "libsepol", "include")
        for root, dirs, files in os.walk(src_include):
            for f in files:
                if f.endswith(".h"):
                    rel_dir = os.path.relpath(root, src_include)
                    dst_dir = os.path.join(self.package_folder, "include", rel_dir)
                    os.makedirs(dst_dir, exist_ok=True)
                    copy(self, f, root, dst_dir)

        # Install the CIL header with the upstream installed layout
        # <prefix>/include/sepol/cil/cil.h (upstream: libsepol/cil/install
        # maps cil/include/cil/* to $INCLUDEDIR/sepol/cil/*). Downstream
        # consumers such as secilc include <sepol/cil/cil.h>.
        copy(
            self,
            "*.h",
            os.path.join(self.source_folder, "libsepol", "cil", "include", "cil"),
            os.path.join(self.package_folder, "include", "sepol", "cil"),
        )

        # Install static library
        src_lib = os.path.join(self.source_folder, "libsepol", "src")
        copy(self, "libsepol.a", src_lib, os.path.join(self.package_folder, "lib"))

        # Install pkg-config file
        copy(self, "libsepol.pc", src_lib, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["sepol"]
        self.cpp_info.set_property("pkg_config_name", "libsepol")
