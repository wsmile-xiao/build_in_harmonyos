#!/usr/bin/env python3
"""Conan recipe — lapacke64 3.12.1 (CMake, HarmonyOS PC / os=OHOS arch=armv8)

Reference-LAPACK 3.12.1 的 LAPACKE C 接口 ILP64（64 位整数）变体。
BUILD_INDEX64=ON 让上游 CMake 把库名置为 blas64/lapack64/lapacke64：
  - C 侧追加 -DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H -DWeirdNEC
    （lapacke_config.h → lapack_int=int64_t）；
  - Fortran 侧 FORTRAN_ILP=TRUE，CMAKE/CheckLAPACKCompilerFlags.cmake 对
    非 Intel/XL/NAG/NVHPC 编译器兜底加 -fdefault-integer-8（flang 20 支持）。
与仓内 lapack/3.12.1（ILP32、无 C 头文件）ABI 不兼容，故自含单配方从同一
官方 tarball 构建 libblas64+liblapack64+liblapacke64，不 requires 现有包。
Fortran 源码用 flang-ohos/20.1.0（tool_requires）编（同 lapack 3.12.1 先例），
无运行期 conan 依赖。BUILD_INDEX64_EXT_API 显式 OFF：_64 后缀双 API 的
编译器支持列表仅 Intel|GNU，flang 不在列，本包只要单 API ILP64 形态。

上游测试（声明见 test_package/MANIFEST.yml）：
  - LAPACKE/example 4 个 C 演示（DGESV/DGELS × col/row-major）折入 build()：
    设备 CC 链接本构建静态产物，就地真实执行（BUILD_TESTING=OFF 使 example/
    子目录不进主构建，此处手动编译同一上游源文件，等价上游入口语义）。
  - test_package C 消费者：sizeof(lapack_int)==8 断言锁 ILP64 +
    dgesv/dpotrf/dgels/dgeev 数值断言（CI L1 门禁）。
  - TESTING/ 全套 Fortran 测试（EIG/LIN/MATGEN + lapack_testing.py）参考
    BLAS 后端在真机需小时级，不入 CI 门禁（取舍见 notes.md）。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Lapacke64Conan(ConanFile):
    name = "lapacke64"
    version = "3.12.1"
    description = ("LAPACKE ILP64 variant of Reference-LAPACK 3.12.1 — standard C "
                   "interface to LAPACK with 64-bit integers "
                   "(liblapacke64 + liblapack64 + libblas64)")
    license = "BSD-3-Clause"
    homepage = "https://www.netlib.org/lapack/"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS（设备原生）")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── 设备工具链辅助（同 lapack/3.12.1 先例：SDK 路径注入 + flang 包定位）──
    def _flang_info(self):
        pkg = self.dependencies.build["flang-ohos"].package_folder
        return pkg, os.path.join(pkg, "bin", "flang")

    def _sdk_info(self):
        roots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm"))
        if not roots:
            raise ConanException("未找到 OHOS SDK（/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm）")
        llvm = roots[-1]
        clang_dirs = sorted(glob.glob(os.path.join(llvm, "lib", "clang", "*")))
        if not clang_dirs:
            raise ConanException("未找到 SDK clang resource dir（llvm/lib/clang/*）")
        return {
            "llvm_lib": os.path.join(llvm, "lib"),
            "resdir": clang_dirs[-1],
            "sysroot": os.path.normpath(os.path.join(llvm, "..", "sysroot")),
            "target_lib": os.path.join(llvm, "lib", "aarch64-linux-ohos"),
        }

    def generate(self):
        flang_pkg, fc = self._flang_info()
        sdk = self._sdk_info()
        tc = CMakeToolchain(self)
        # flang-ohos 是精简运行集（无 libclang_rt.builtins.a/crtbeginS.o），
        # 编译期需显式指向 SDK clang15 sysroot + resource-dir（同 lapack 3.12.1）；
        # 本配方不依赖 flang 链接可执行文件（纯库构建，检测用静态库 try-compile）。
        tc.variables["CMAKE_Fortran_COMPILER"] = fc
        tc.variables["CMAKE_Fortran_FLAGS"] = (
            "-fPIC --target=aarch64-linux-ohos "
            "--sysroot=%s -resource-dir=%s" % (sdk["sysroot"], sdk["resdir"])
        )
        tc.variables["CMAKE_C_FLAGS"] = "-fPIC"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            "-L%s -L%s -lFortranRuntime -lFortranDecimal -lm"
            % (sdk["target_lib"], os.path.join(flang_pkg, "lib"))
        )
        # flang-ohos 精简运行集无法链接可执行文件（缺 crt）：让 CMake 编译器
        # 检测与 LAPACKE/include 的 FortranCInterface_VERIFY try-compile 都用
        # 静态库模式跳过链接（lapack 3.12.1 已验证该模式可过编译器检测）。
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        # ILP64 形态：blas64/lapack64/lapacke64 + lapack_int=int64_t
        tc.variables["BUILD_INDEX64"] = "ON"
        tc.variables["BUILD_INDEX64_EXT_API"] = "OFF"
        tc.variables["LAPACKE"] = "ON"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["LAPACK_INSTALL_PKGCONFIGDIR"] = "lib/pkgconfig"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # flang 运行期需 SDK llvm/lib（lld 的 libxml2.so.16）+ flang 包 lib（libLLVM/libMLIR）
        flang_pkg, _ = self._flang_info()
        sdk = self._sdk_info()
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [sdk["llvm_lib"], os.path.join(flang_pkg, "lib")])
        cmake = CMake(self)
        cmake.configure()
        self._assert_fortran_ilp64_flags()
        cmake.build()
        self._run_upstream_lapacke_examples()

    def _assert_fortran_ilp64_flags(self):
        """配置后自检：BUILD_INDEX64 应使 CMake 兜底分支给 Fortran 加
        -fdefault-integer-8（FORTRAN_ILP=TRUE，flang 不在 Intel/XL/NAG/NVHPC
        特判列表内）。核验对象是 Fortran 主体目标 blas64/lapack64 的 per-target
        flags——Makefile 生成器把它们放在随源码树镜像的 <子目录>/CMakeFiles/
        <tgt>.dir/flags.make（如 BLAS/SRC/CMakeFiles/blas64.dir/），必须递归
        定位。若未命中，Fortran 侧会静默退回 ILP32，与 C 侧 int64 ABI 错位 →
        配置期直接失败好过运行期数据损坏。"""
        blobs = {}
        for tgt in ("blas64", "lapack64"):
            for p in glob.glob(os.path.join(self.build_folder, "**", "CMakeFiles",
                                            tgt + ".dir", "flags.make"),
                               recursive=True):
                with open(p, "r", errors="replace") as f:
                    blobs[p] = f.read()
        if not blobs:
            # Ninja 生成器没有 flags.make，退回 build.ninja 全文
            for p in glob.glob(os.path.join(self.build_folder, "build.ninja")):
                with open(p, "r", errors="replace") as f:
                    blobs[p] = f.read()
        if not blobs:
            raise ConanException(
                "未找到 blas64/lapack64 的构建 flags 文件（flags.make/build.ninja），"
                "无法自检 ILP64 Fortran 标志")
        bad = [p for p, text in blobs.items() if "-fdefault-integer-8" not in text]
        if bad:
            raise ConanException(
                "Fortran 编译标志中未见 -fdefault-integer-8：%s —— BUILD_INDEX64 的 "
                "ILP64 Fortran 分支未生效（flang 应命中 CheckLAPACKCompilerFlags 兜底分支）"
                % ", ".join(bad))
        self.output.info("ILP64 self-check: -fdefault-integer-8 present in Fortran "
                         "flags (%d 个目标 flags 文件)" % len(blobs))

    def _built_lib(self, name):
        top = os.path.join(self.build_folder, name)
        if os.path.isfile(top):
            return top
        found = sorted(glob.glob(os.path.join(self.build_folder, "**", name),
                                 recursive=True))
        if not found:
            raise ConanException("构建产物缺失：%s（BUILD_INDEX64 未生效？）" % name)
        return found[-1]

    def _sign_file(self, path):
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if os.path.isfile(sign):
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, path, path))

    def _run_upstream_lapacke_examples(self):
        """上游 LAPACKE/example 的 4 个 C 演示（DGESV/DGELS × col/row-major）
        真实执行：BUILD_TESTING=OFF 使 example/ 子目录不进主构建，此处用设备
        CC 编译同一上游源文件（含 lapacke_example_aux.c），以 ILP64 宏口径
        （-DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H，与库本身一致）链接本构建
        liblapacke64→liblapack64→libblas64 + flang Fortran 运行时归档，就地
        执行并检查退出码；stdout 进 conan create 日志（CI L1 证据）。
        上游 Makefile 入口以 $(FC)=flang 链接演示；flang 精简运行集缺目标级
        crt 无法链接可执行，故链接器用设备 CC（仅链接器一处偏差，被链对象
        与头文件保持上游语义，已在 test_package/MANIFEST.yml 声明）。"""
        cc = "/data/service/hnp/bin/clang"
        flang_pkg, _ = self._flang_info()
        rt = os.path.join(flang_pkg, "lib", "libFortranRuntime.a")
        dec = os.path.join(flang_pkg, "lib", "libFortranDecimal.a")
        inc = os.path.join(self.build_folder, "include")
        ex_src = os.path.join(self.source_folder, "LAPACKE", "example")
        out_dir = os.path.join(self.build_folder, "lapacke64_demos")
        os.makedirs(out_dir, exist_ok=True)

        if self.options.shared:
            # shared 形态：.so 实体自签副本进运行目录（XPM 要求加载的 .so
            # 自签），链接行以副本绝对路径作显式输入（CI 默认走静态分支）。
            lib_paths = []
            for n in ("liblapacke64.so", "liblapack64.so", "libblas64.so"):
                src = self._built_lib(n)
                dst = os.path.join(out_dir, n)
                copy(self, n, src=os.path.dirname(src), dst=out_dir)
                self._sign_file(dst)
                lib_paths.append(dst)
        else:
            lib_paths = [self._built_lib(n) for n in
                         ("liblapacke64.a", "liblapack64.a", "libblas64.a")]
        libs = " ".join(lib_paths)

        demos = ("example_DGESV_colmajor", "example_DGESV_rowmajor",
                 "example_DGELS_colmajor", "example_DGELS_rowmajor")
        for demo in demos:
            exe = os.path.join(out_dir, demo)
            self.run('%s -DLAPACK_ILP64 -DHAVE_LAPACK_CONFIG_H -I"%s" "%s.c" "%s" '
                     '-o "%s" %s "%s" "%s" -lm'
                     % (cc, inc, os.path.join(ex_src, demo),
                        os.path.join(ex_src, "lapacke_example_aux.c"), exe,
                        libs, rt, dec),
                     cwd=ex_src)
            if self.options.shared:
                self.run('env LD_LIBRARY_PATH="%s" "%s"' % (out_dir, exe), cwd=out_dir)
            else:
                self.run('"%s"' % exe, cwd=out_dir)
        self.output.info("upstream LAPACKE examples executed: %d/%d"
                         % (len(demos), len(demos)))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 复制 flang Fortran 运行时进包内 lib（liblapack64.a 内引用 _FortranA*
        # 符号，消费方链接需带上；同 lapack/3.12.1 先例）
        flang_pkg, _ = self._flang_info()
        for rt in ("libFortranRuntime.a", "libFortranDecimal.a"):
            src = os.path.join(flang_pkg, "lib", rt)
            if os.path.isfile(src):
                copy(self, rt, src=os.path.dirname(src),
                     dst=os.path.join(self.package_folder, "lib"))
        # 核验交付面：ILP64 三库 + LAPACKE 头（lapacke_mangling.h 是 install
        # 期生成的符号修饰头，缺失说明 FortranCInterface 探测异常）
        ext = ".so" if self.options.shared else ".a"
        missing = [n + ext for n in ("liblapacke64", "liblapack64", "libblas64")
                   if not os.path.isfile(os.path.join(self.package_folder, "lib", n + ext))]
        missing += [h for h in ("lapacke.h", "lapacke_mangling.h", "lapack.h",
                                "lapacke_config.h", "lapacke_utils.h")
                    if not os.path.isfile(os.path.join(self.package_folder, "include", h))]
        if missing:
            raise ConanException("安装产物缺失：%s" % ", ".join(missing))
        self._sign_so()

    def _sign_so(self):
        # 设备原生：XPM 要求加载的 .so 自签（binary-sign-tool 在设备 hnp bin）。
        # 符号链接跳过，只签实体；实体被签后链接链整体有效。
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign):
            self.output.warning("binary-sign-tool 不存在，跳过签名（消费端需自签）")
            return
        for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(so):
                continue
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, so, so))

    def package_info(self):
        # 消费方必须以 ILP64 宏口径包含 lapacke.h（lapack_int=int64_t），
        # 否则与库内 ABI 错位；defines 经 CMakeDeps 自动传播给 CMake 消费者。
        self.cpp_info.libs = ["lapacke64", "lapack64", "blas64",
                              "FortranRuntime", "FortranDecimal"]
        self.cpp_info.defines = ["LAPACK_ILP64", "HAVE_LAPACK_CONFIG_H"]
        self.cpp_info.system_libs = ["m"]
