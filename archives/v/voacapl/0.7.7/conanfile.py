#!/usr/bin/env python3
"""Conan recipe — voacapl 0.7.7 (autotools, 鸿蒙 PC / os=OHOS arch=armv8)

voacapl 是火腿无线电 HF 传播预测 CLI 工具（VOACAP 的 Linux/Unix 移植），
纯 Fortran 源码（.for/.f/.f95/.f90），autotools 构建，输出多个命令行工具：
voacapl（主程序）+ anttyp90/anttyp99/dst2ascii/dst2csv/coeffbin/coefbinw/
fof2bin/fof2binw（辅助工具）。无第三方库依赖。

Fortran 工具链要点（设备实测，参照 netcdf-fortran/blas 先例）：
  设备/NDK 无 gfortran，用仓库 flang-ohos/20.1.0 作 tool_requires。
  flang 编译时必须给 --target=aarch64-unknown-linux-ohos、--sysroot=<sdk>/sysroot、
  -resource-dir=<sdk>/llvm/lib/clang/<ver>、-L<sdk>/llvm/lib/aarch64-linux-ohos
  （libunwind.a 只在该目录），否则 ld.lld 报 cannot open Scrt1.o / -l:libunwind.a。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VoacaplConan(ConanFile):
    name = "voacapl"
    version = "0.7.7"
    description = "VOACAP HF propagation prediction CLI (Fortran)"
    license = "LicenseRef-voacapl-special"  # 上游为 NTIA/ITS special + CC0-1.0 混合
    homepage = "https://github.com/jawatson/voacapl"
    url = "https://github.com/jawatson/voacapl"

    package_type = "application"  # 输出 CLI 工具（R38：软件级 commands.json）
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8")

    def build_requirements(self):
        # Fortran 编译器（设备/NDK 无 gfortran，flang-ohos 为仓库既有工具包）
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── Fortran 工具链（参照 blas/netcdf-fortran 先例）──────────────────
    def _flang_package(self):
        package = self.dependencies.build.get("flang-ohos")
        if not package:
            raise ConanException("flang-ohos/20.1.0 tool requirement is missing")
        return package.package_folder

    def _sdk_paths(self):
        """定位唯一一个完整的 OHOS SDK native 根。"""
        llvm_roots = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm")
        )
        if not llvm_roots:
            raise ConanException("OHOS SDK LLVM root was not found")
        llvm_root = llvm_roots[-1]
        resource_dirs = sorted(glob.glob(os.path.join(llvm_root, "lib", "clang", "*")))
        if not resource_dirs:
            raise ConanException("OHOS SDK clang resource-dir was not found")
        return {
            "llvm": llvm_root,
            "sysroot": os.path.normpath(os.path.join(llvm_root, "..", "sysroot")),
            "resource": resource_dirs[-1],
            "target_lib": os.path.join(llvm_root, "lib", "aarch64-linux-ohos"),
        }

    def _fortran_env(self):
        """返回 (F77/FC 编译器, 编译 flags, 链接 flags, 运行期库目录列表)。"""
        flang_package = self._flang_package()
        sdk = self._sdk_paths()
        flang = os.path.join(flang_package, "bin", "flang")
        if not os.path.isfile(flang):
            raise ConanException("flang-ohos 工具包不完整: {}".format(flang))
        target = "--target=aarch64-unknown-linux-ohos"
        compile_flags = "{} --sysroot={} -resource-dir={}".format(
            target, sdk["sysroot"], sdk["resource"])
        link_flags = "-L{} -L{} -lm".format(sdk["target_lib"], os.path.join(flang_package, "lib"))
        # flang 本体依赖 libc++_shared.so（在 target_lib = llvm/lib/aarch64-linux-ohos/）
        # 与 libLLVM/libMLIR/libclang-cpp（flang 包 lib/），缺一不可（Error 127 复现）
        runtime_dirs = [sdk["target_lib"], os.path.join(sdk["llvm"], "lib"),
                        os.path.join(flang_package, "lib")]
        return flang, compile_flags, link_flags, runtime_dirs

    def generate(self):
        flang, compile_flags, link_flags, _runtime = self._fortran_env()
        tc = AutotoolsToolchain(self)
        # autotools 无需 --build/--host（R15 禁用参数）；本地原生编译。
        # ⚠️ 不得手动指定 --prefix=package_folder：Autotools.install()
        # 以 DESTDIR=package_folder 安装，再叠加 prefix 会造成
        # p/<prefix>/bin 嵌套路径（实测 p/storage/.../p/bin）。默认即可。
        # flang 编译器注入
        tc.configure_args.append("F77={}".format(flang))
        tc.configure_args.append("FC={}".format(flang))
        tc.configure_args.append("FFLAGS={}".format(compile_flags))
        tc.configure_args.append("FCFLAGS={}".format(compile_flags))
        tc.configure_args.append("LDFLAGS={}".format(link_flags))
        tc.generate()

    def _apply_runtime_env(self):
        """构建/测试期把 flang 运行库目录加入 LD_LIBRARY_PATH，返回原值。"""
        _f, _c, _l, runtime_dirs = self._fortran_env()
        dirs = list(runtime_dirs)
        previous = os.environ.get("LD_LIBRARY_PATH")
        if previous:
            dirs.append(previous)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(dict.fromkeys(dirs))
        return previous

    # ── 源码级适配（build() 内联，参照 4ti2 先例）─────────────────────
    # refresh-patch 只固化 6 个自动补丁（configure/Makefile 系）；以下
    # CRLF 行尾的 Fortran 源文件修改与新增 shim 在 build() 内联执行，
    # 避免 patch 管线对 CRLF 文件 dry-run 失败导致补丁丢失（实测 0007-0014
    # 被 refresh-patch 重建时清走、conan create 找不到补丁文件）。
    def _apply_source_adaptations(self):
        src = self.source_folder

        # (a) Hollerith 编辑描述符替换（flang 不支持 FORMAT(1H / 2h）
        def _fixup(path, replacements):
            with open(path, "rb") as f:
                data = f.read()
            for old, new in replacements:
                data = data.replace(old, new)
            with open(path, "wb") as f:
                f.write(data)

        _fixup(os.path.join(src, "src", "voacapw", "hfmufs.for"),
               [(b"FORMAT(1H ,", b"FORMAT(1X,")])
        _fixup(os.path.join(src, "src", "voacapw", "hfmufs2.for"),
               [(b"FORMAT(1H ,", b"FORMAT(1X,")])
        _fixup(os.path.join(src, "src", "voacapw", "outant.for"),
               [(b"FORMAT(1H\x0c,", b"FORMAT('1',"),
                (b"FORMAT(1H\x0c", b"FORMAT('1'"),
                (b"2h [,a21,2h] ,a70", b"'[ ',a21,'] ',a70")])

        # (b) 新增 unlink shim（flang 无 gfortran 扩展过程 call unlink）
        shim = os.path.join(src, "src", "voacapw", "ohos_unlink_shim.for")
        if not os.path.isfile(shim):
            with open(shim, "w", encoding="utf-8") as f:
                f.write(
                    "C     --- OHOS/flang shim: gfortran extension call unlink() ---\n"
                    "C     flang has no unlink builtin; use OPEN/CLOSE STATUS='DELETE'.\n"
                    "      SUBROUTINE UNLINK(FNAME, ISTAT)\n"
                    "      CHARACTER*(*) FNAME\n"
                    "      INTEGER ISTAT\n"
                    "      LOGICAL EXISTS\n"
                    "      INQUIRE(FILE=FNAME, EXIST=EXISTS)\n"
                    "      IF (.NOT. EXISTS) THEN\n"
                    "        ISTAT = 0\n"
                    "        RETURN\n"
                    "      END IF\n"
                    "      OPEN(UNIT=99, FILE=FNAME, STATUS='OLD', IOSTAT=ISTAT)\n"
                    "      IF (ISTAT .NE. 0) RETURN\n"
                    "      CLOSE(UNIT=99, STATUS='DELETE', IOSTAT=ISTAT)\n"
                    "      RETURN\n"
                    "      END\n")

        # (c) coeffs 工具路径变量 len 128→512（DESTDIR 长路径截断）
        for name in ("coeffbin.f", "coefbinw.f", "fof2bin.f", "fof2binw.f"):
            p = os.path.join(src, "voacapl", "itshfbc", "coeffs", name)
            with open(p, "rb") as f:
                data = f.read()
            data = data.replace(b"character (len=128) :: working_dir",
                                b"character (len=512) :: working_dir")
            data = data.replace(b"character (len=128) :: filein, fileout",
                                b"character (len=512) :: filein, fileout")
            with open(p, "wb") as f:
                f.write(data)

    def build(self):
        apply_conandata_patches(self)
        self._apply_source_adaptations()
        previous = self._apply_runtime_env()
        try:
            autotools = Autotools(self)
            autotools.configure()
            # automake out-of-source 构建：all-am 依赖 dist 数据文件
            # （voacapl/itshfbc/news/*.txt、antennas/*、README 等），它们位于
            # source 目录而 make 在 build 目录执行；复制数据树到 build 目录。
            src_root = self.source_folder
            dst_root = self.build_folder
            for rel in ("README.md", "NEWS", "COPYING", "ChangeLog.md",
                        "AUTHORS", "logo.png", "makeitshfbc"):
                src = os.path.join(src_root, rel)
                if os.path.isfile(src):
                    copy(self, rel, src=src_root, dst=dst_root)
            src_voacapl = os.path.join(src_root, "voacapl")
            if os.path.isdir(src_voacapl):
                copy(self, "**", src=src_voacapl,
                     dst=os.path.join(dst_root, "voacapl"))
            autotools.make(args=["-j1"])
        finally:
            if previous is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous

    def package(self):
        autotools = Autotools(self)
        # install-data-hook 会运行 coeffbin/fof2bin 等生成 coeffs 二进制，
        # 需要 flang 运行库可加载
        previous = self._apply_runtime_env()
        try:
            autotools.install()
        finally:
            if previous is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = previous
        # 许可证文件
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CLI 工具：声明 bindirs，不声明 cpp_info.libs
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # voacapl 二进制由 flang 链接，运行时依赖 flang-ohos 包 lib/
        # （libLLVM/libMLIR/libclang-cpp）与 SDK llvm/lib/aarch64-linux-ohos
        # （libc++_shared.so）。此处不能走 _fortran_env()（test_package 阶段
        # tool_requires 被 Skipped 解析为 None），用静态 glob 注入 runenv。
        runtime_dirs = []
        flang_pkgs = sorted(glob.glob(os.path.expanduser("~/.conan2/p/flang*/p/lib")))
        if flang_pkgs:
            runtime_dirs.append(flang_pkgs[-1])
        sdk_targets = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"))
        if sdk_targets:
            runtime_dirs.append(sdk_targets[-1])
        if runtime_dirs:
            self.runenv_info.append("LD_LIBRARY_PATH", runtime_dirs)
