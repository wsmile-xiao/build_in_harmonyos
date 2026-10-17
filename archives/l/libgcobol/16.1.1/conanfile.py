#!/usr/bin/env python3
"""Conan recipe — libgcobol 16.1.1（GCC 16 COBOL 运行时库，autotools target library）

libgcobol 是 GCC 16 的 target library，无独立 release tarball，源码从
gcc-16.1.0.tar.xz 的 libgcobol/ 子目录获取。release 16.1.0 的主库为纯 C++
（libgcobol.la，SOURCES 全部是 .cc，仅 -lxml2 依赖），不含需要 GCOBOL 前端
编译的 posix/compat COBOL 子库。

关键适配点：
  - 只选择性解压 libgcobol/ 与 gcc/BASE-VER（configure/Makefile 的
    ../gcc/BASE-VER 依赖），避免解压整个 2 GB GCC 树 → HMDFS 磁盘耗尽（Errno 28）。
  - HMDFS 解压后 configure 丢失可执行位且 chmod 不生效（E046/E087）→ 用 /bin/sh 执行。
  - 交叉编译用 --build/--host=aarch64-unknown-linux-musl（仓库惯例，见 gmp/ecl），
    configure.tgt 对 aarch64-*-linux* 判定 LIBGCOBOL_SUPPORTED=yes。
"""
import os
import glob
import tarfile

from conan import ConanFile
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgcobolConan(ConanFile):
    name = "libgcobol"
    version = "16.1.1"
    description = "GCC COBOL runtime library (libgcobol)"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libxml2/2.15.3")

    def layout(self):
        # source_folder 作为 GCC 树根：解压后含 libgcobol/ 与 gcc/BASE-VER。
        basic_layout(self, src_folder=".")

    def source(self):
        src = self.conan_data["sources"]
        archive = os.path.join(self.source_folder, "gcc-src.tar.xz")
        download(self, src["url"], archive, sha256=src["sha256"])
        prefix = "gcc-16.1.0/"
        with tarfile.open(archive, "r:xz") as tar:
            members = []
            for m in tar.getmembers():
                name = m.name
                if name.startswith(prefix + "libgcobol/"):
                    m.name = name[len(prefix):]   # libgcobol/...
                    members.append(m)
                elif name == prefix + "gcc/BASE-VER":
                    m.name = "gcc/BASE-VER"
                    members.append(m)
                elif name.startswith(prefix) and m.isfile() and "/" not in name[len(prefix):]:
                    # GCC 树根直接文件：install-sh/config.guess/config.sub 等
                    # autotools 辅助脚本（configure 从 srcdir/.. 查找）。
                    m.name = name[len(prefix):]
                    members.append(m)
            tar.extractall(self.source_folder, members=members)
        os.remove(archive)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _libxml2_dirs(self):
        """libxml2 头按 <libxml2/libxml/*.h> 组织，取 include/libxml2 供 <libxml/...> 检索。"""
        dep = self.dependencies["libxml2"]
        pkg = dep.package_folder
        inc = os.path.join(pkg, "include", "libxml2")
        lib = os.path.join(pkg, "lib")
        return inc, lib

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "libgcobol", "configure")

        # E011/E052/E060: config.status 在 HMDFS 上 `mktemp -d "./confXXXXXX"`
        # 会因权限失败（subs1.awk Permission denied）。patch configure 把临时
        # 目录改到 $TMPDIR（tmpfs，CI 可写），并在运行时把 TMPDIR 指到
        # /data/storage/el2/base/cache（见 gputils 1.5.2 的同一问题）。
        tmpdir = "/data/storage/el2/base/cache"
        with open(configure, "r") as f:
            cfg_text = f.read()
        cfg_fixed = cfg_text.replace(
            'mktemp -d "./confXXXXXX"', 'mktemp -d "$TMPDIR/confXXXXXX"')
        cfg_fixed = cfg_fixed.replace(
            "tmp=./conf$$-$RANDOM", "tmp=$TMPDIR/conf$$-$RANDOM")
        if cfg_fixed != cfg_text:
            with open(configure, "w") as f:
                f.write(cfg_fixed)

        # C23 的 _Float32/_Float64 是 C 语言类型，clang++（C++ 模式）不认识，
        # 报 "unknown type name '_Float32'"。语义等价替换为 float/double。
        src_cc = os.path.join(self.source_folder, "libgcobol", "libgcobol.cc")
        if os.path.isfile(src_cc):
            with open(src_cc, "r") as f:
                cc_text = f.read()
            cc_fixed = cc_text.replace("_Float32", "float").replace("_Float64", "double")
            if cc_fixed != cc_text:
                with open(src_cc, "w") as f:
                    f.write(cc_fixed)

        build_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(build_dir, exist_ok=True)

        inc, lib = self._libxml2_dirs()
        args = [
            "--prefix=/",
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-musl",
            "--disable-multilib",
            "--disable-libquadmath",
            "--with-target-libxml2-include={}".format(inc),
            "--with-target-libxml2-lib={}".format(lib),
        ]
        # E012: OHOS 只有 LLVM 工具链，显式指定 ar/nm/ranlib/ld/objcopy 等
        # （绝对路径，避免 make 阶段 libtool 依赖 PATH 找不到 llvm-ar）。
        toolchain_env = (
            "AR=/data/service/hnp/bin/llvm-ar NM=/data/service/hnp/bin/llvm-nm "
            "RANLIB=/data/service/hnp/bin/llvm-ranlib STRIP=/data/service/hnp/bin/llvm-strip "
            "OBJCOPY=/data/service/hnp/bin/llvm-objcopy "
            "READELF=/data/service/hnp/bin/llvm-readelf LD=/data/service/hnp/bin/ld.lld "
            "PATH=/data/service/hnp/bin:$PATH"
        )
        # HMDFS 上 configure 无执行位且 chmod 不生效（E046/E087）→ /bin/sh 执行。
        self.run(
            "cd {0} && export {1} && mkdir -p {2} && "
            "TMPDIR={2} /bin/sh {3} {4}".format(
                build_dir, toolchain_env, tmpdir, configure, " ".join(args)),
            env="conanbuild",
        )
        # libgcobol 用 __int128/long double(128b)，clang 生成的 __divti3/__gttf2
        # 等辅助符号在 compiler-rt builtins（libclang_rt.builtins.a，位于 clang
        # 资源目录，OHOS 无 libgcc.a）。只在链接阶段加（configure 阶段加会破坏
        # conftest 链接检测，触发 GCC_NO_EXECUTABLES）。
        self.run(
            "export {0} && make -C {1} -j1 LIBS='-lclang_rt.builtins'".format(
                toolchain_env, build_dir),
            env="conanbuild",
        )

    def package(self):
        build_dir = os.path.join(self.build_folder, "obj")
        self.run(
            "make -C {0} install DESTDIR={1}".format(build_dir, self.package_folder),
            env="conanbuild",
        )
        # libtool install 已把 libgcobol.so*/.a 装到 <pkg>/lib/，无需归位。
        # 删除 libtool .la（烤死 libdir 绝对路径，见 gmp 6.3.0.1 经验）。
        for la in glob.glob(os.path.join(self.package_folder, "**", "*.la"), recursive=True):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["gcobol"]
        self.cpp_info.set_property("pkg_config_name", "libgcobol")
