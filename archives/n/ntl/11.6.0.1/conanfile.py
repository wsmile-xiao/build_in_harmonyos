#!/usr/bin/env python3
"""Conan recipe for NTL 11.6.0."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NtlConan(ConanFile):
    name = "ntl"
    version = "11.6.0.1"
    description = "High-performance portable C++ number theory library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libntl.org"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("NTL supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # NTL 的 configure 会**编译并运行** CheckGMP 探测程序；gmp/6.3.0.1 是共享库，
        # 不给运行期库路径就报：
        #   Error loading shared library libgmp.so.10: (needed by ./CheckGMP)
        #   Error: NTL_GMP_LIP set but GMP not available
        # 报错指向「GMP 不可用」，实为加载器找不到 .so。scope="build" 让它并入 conanbuild。
        VirtualRunEnv(self).generate(scope="build")
        AutotoolsToolchain(self).generate()

    def build(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        ar = executables.get("ar", "llvm-ar")
        ranlib = executables.get("ranlib", "llvm-ranlib")
        configure_args = [
            f"PREFIX={shlex.quote(self.package_folder)}",
            "SHARED=off",
            "NATIVE=off",
            "TUNE=generic",
            # GMP 后端：Sage / passagemath 生态的标配。
            # 关掉它（=off）时 NTL/ZZ.h 会额外定义一个向后兼容的遗留函数
            #     #ifndef NTL_GMP_LIP
            #     inline long digit(const ZZ& a, long k)
            #     #endif
            # 它与 CPython 3.12 的 `typedef uint32_t digit`（longintrepr.h:43）撞名，
            # Cython 生成的 `const digit* = __Pyx_PyLong_Digits(x)` 就报
            #     error: reference to 'digit' is ambiguous
            # passagemath-ntl 10.8.7 实撞 380 处。开 GMP 后端即根治，且性能更好。
            "NTL_GMP_LIP=on",
            # 开了 NTL_GMP_LIP 就必须告诉 NTL 的 configure 去哪找 GMP，
            # 否则它直接报：
            #   Error: NTL_GMP_LIP set but GMP not available
            #          -- set DEF_PREFIX or GMP_PREFIX to point to location of GMP
            "GMP_PREFIX=" + self.dependencies["gmp"].package_folder,
            "NTL_GF2X_LIB=off",
            "NTL_THREADS=on",
            "NTL_SAFE_VECTORS=on",
            "NTL_STD_CXX11=on",
            "ENABLE_RPATH=off",
            'CXX="$CXX"',
            'CXXFLAGS="$CXXFLAGS"',
            'CPPFLAGS="$CPPFLAGS"',
            'LDFLAGS="$LDFLAGS"',
            f"AR={shlex.quote(str(ar))}",
            f"RANLIB={shlex.quote(str(ranlib))}",
        ]
        source_dir = os.path.join(self.source_folder, "src")
        cross_prefix = "CONAN_CROSS_BUILDING=1 " if cross_building(self) else ""
        self.run(
            cross_prefix + "./configure " + " ".join(configure_args),
            cwd=source_dir,
            env="conanbuild",
        )
        self.run("make -j1", cwd=source_dir, env="conanbuild")
        if can_run(self):
            self.run(
                "bash -c 'set -o pipefail; "
                "(while sleep 120; do "
                "echo \"[ntl] upstream tests still running\"; done) & heartbeat=$!; "
                "make check 2>&1 | tee ntl-check.log; status=${PIPESTATUS[0]}; "
                "kill $heartbeat 2>/dev/null || true; "
                "wait $heartbeat 2>/dev/null || true; "
                "if grep -q \"^bad \" ntl-check.log; then exit 1; fi; "
                "exit $status'",
                cwd=source_dir,
                env="conanbuild",
            )

    def package(self):
        source_dir = os.path.join(self.source_folder, "src")
        self.run("make install", cwd=source_dir, env="conanbuild")
        copy(
            self,
            "copying.txt",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ntl"]
        self.cpp_info.set_property("cmake_file_name", "ntl")
        self.cpp_info.set_property("cmake_target_name", "ntl::ntl")
        self.cpp_info.set_property("pkg_config_name", "ntl")
        self.cpp_info.system_libs = ["m", "pthread"]
