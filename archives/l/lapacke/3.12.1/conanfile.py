#!/usr/bin/env python3
"""Conan recipe — LAPACKE 3.12.1（netlib reference LAPACK 的标准 C 接口，独立交付）

源码树即 netlib lapack 3.12.1（与依赖包 lapack/3.12.1 同一官方 tarball、同一
版本口径）；本配方只编译其中纯 C 的 LAPACKE 包装层（LAPACKE/src 2522 个 +
LAPACKE/utils 156 个翻译单元，共 2678 个对象），Fortran 本体（liblapack/
libblas）不在此构建，由依赖 lapack/3.12.1 提供（包内含 flang Fortran 运行时
libFortranRuntime/libFortranDecimal，静态链接闭合 _FortranA* 符号）。

为什么不用上游 CMake 开 BUILD_LAPACKE：该入口会触发 FortranCInterface_VERIFY
链接验证，flang-ohos 精简运行集无法完成（lapack/3.12.1 先例因此只交付了
liblapack/libblas，见其 package_info 注释）——绕开 Fortran 构建面、直接以设备
clang 编译 LAPACKE 纯 C 源，是产出独立 liblapacke 的可行路线。

lapacke_mangling.h 由上游 include/lapacke_mangling_with_flags.h.in 复制生成：
3.12.1 tarball 的该模板不含占位符，默认分支即命名修饰 lcname##_（ADD_），与
无后缀 reference LAPACK 的 Fortran 符号（dgesv_ 等）一致。

交付形态：纯静态 liblapacke.a（package_type=static-library），与依赖
lapack/3.12.1 的实际交付（仅 .a）一致。不提供 shared：LAPACKE 包装层引用的
部分 extras 例程（*gbsvxx/*gbrfsx 精化族、*geqpf、*lagge/*latms 等 matgen
辅助族）在 reference liblapack.a 中不存在（上游默认构建面即如此），自包含
.so 会被消费者 lld 的 --no-allow-shlib-undefined 拒绝（本机实测）；消费静态
归档时链接器只拉取被引用对象，不受该缺口影响。

上游测试（R51 清点）：LAPACKE/example 上游 Makefile `all` 目标 = 4 个演示程序
（DGESV/DGELS × colmajor/rowmajor），build() 内编译链接本构建产物并在设备上
真实执行。唯一偏差：上游入口以 $(FC) 链接演示可执行文件，此处用设备 CC——
编译对象/头文件/被链库保持上游语义（同 liblapacke 0.3.30 先例的轻量默认路径）；
*_64 变体属 ILP64 口径（平台 lapacke64 任务域），example_user.c 不在上游 all
目标，均不在本配方执行范围。
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

HNP_BIN = "/data/service/hnp/bin"
# LAPACKE/src 2522 + LAPACKE/utils 156（lapack-3.12.1 官方 tarball 实数）
EXPECTED_OBJECTS = 2678


class LapackeConan(ConanFile):
    name = "lapacke"
    version = "3.12.1"
    description = ("LAPACKE — standard C interface to reference LAPACK (netlib), "
                   "standalone library from the lapack 3.12.1 source tree")
    license = "BSD-3-Clause"
    homepage = "https://github.com/Reference-LAPACK/lapack"
    url = ""
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("lapack/3.12.1")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS（设备原生）")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _cc(self):
        conf_cc = self.conf.get("tools.build:compiler_executables", default={},
                                check_type=dict).get("c")
        return conf_cc if conf_cc else os.path.join(HNP_BIN, "clang")

    def _ar(self):
        ar = os.path.join(HNP_BIN, "llvm-ar")
        return ar if os.path.isfile(ar) else "ar"

    def _jobs(self):
        return int(self.conf.get("tools.build:jobs",
                                 default=min(4, os.cpu_count() or 2)))

    def _lapack_libdir(self):
        return self.dependencies["lapack"].cpp_info.libdirs[0]

    def _lapack_link_flags(self):
        # 以 lapack/3.12.1 包内实际交付的静态库闭合 Fortran 符号面：
        # liblapack.a（LAPACK 本体）→ libblas.a（reference BLAS）→
        # libFortranRuntime.a / libFortranDecimal.a（flang 运行时）→ -lm。
        return '-L"%s" -llapack -lblas -lFortranRuntime -lFortranDecimal -lm' \
            % self._lapack_libdir()

    def _generate_mangling_header(self, lapacke_dir):
        include_dir = os.path.join(lapacke_dir, "include")
        template = os.path.join(include_dir, "lapacke_mangling_with_flags.h.in")
        generated = os.path.join(include_dir, "lapacke_mangling.h")
        with open(template, "r") as f:
            content = f.read()
        # 3.12.1 tarball 的该模板不含占位符，内容原样生效；replace 仅为兼容
        # 其他版本模板的 @LAPACK_SUFFIX@ 占位（置空 = 无后缀 reference LAPACK，
        # 默认分支命名修饰 lcname##_，与依赖包 liblapack.a 的 Fortran 符号一致）。
        with open(generated, "w") as f:
            f.write(content.replace("@LAPACK_SUFFIX@", ""))

    def _compile(self, lapacke_dir):
        cc, jobs = self._cc(), self._jobs()
        for sub in ("src", "utils"):
            # 设备 xargs 为 busybox 形态（无 -I{}）；用批量追加方式一次编译
            # 多个翻译单元（clang 多 -c 输入，对象文件落在各自源码目录）。
            cmd = 'ls *.c | xargs -P %d -n 16 "%s" -O2 -fPIC -I"%s" -c' \
                % (jobs, cc, os.path.join(lapacke_dir, "include"))
            self.run(cmd, cwd=os.path.join(lapacke_dir, sub))

    def _archive(self, lapacke_dir):
        objects = sorted(glob.glob(os.path.join(lapacke_dir, "src", "*.o"))) + \
            sorted(glob.glob(os.path.join(lapacke_dir, "utils", "*.o")))
        if len(objects) != EXPECTED_OBJECTS:
            raise ConanException("LAPACKE 对象文件数 %d != 预期 %d（src+utils 翻译单元）"
                                 % (len(objects), EXPECTED_OBJECTS))
        lib_dir = os.path.join(self.build_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        self.run('%s rcs "%s" "%s"/*.o "%s"/*.o'
                 % (self._ar(), os.path.join(lib_dir, "liblapacke.a"),
                    os.path.join(lapacke_dir, "src"),
                    os.path.join(lapacke_dir, "utils")))
        return lib_dir

    def build(self):
        apply_conandata_patches(self)
        lapacke_dir = os.path.join(self.source_folder, "LAPACKE")
        self._generate_mangling_header(lapacke_dir)
        self._compile(lapacke_dir)
        lib_dir = self._archive(lapacke_dir)
        self._run_upstream_examples(lapacke_dir, lib_dir)

    def _run_upstream_examples(self, lapacke_dir, lib_dir):
        """上游 LAPACKE/example 的 `all` 目标：4 个演示程序编译链接本构建产物
        并在设备上真实执行。上游 Makefile 以 $(FC) 链接（$(LAPACKELIB)
        $(LAPACKLIB) $(BLASLIB)）；此处以设备 CC 链接同一批库——链接器一处
        偏差（同 liblapacke 0.3.30 先例），被测对象与执行语义保持上游。
        """
        cc = self._cc()
        example_dir = os.path.join(lapacke_dir, "example")
        demos = ["example_DGESV_colmajor", "example_DGESV_rowmajor",
                 "example_DGELS_colmajor", "example_DGELS_rowmajor"]
        build_dir = os.path.join(self.build_folder, "lapacke_examples")
        os.makedirs(build_dir, exist_ok=True)
        lapacke_lib = os.path.join(lib_dir, "liblapacke.a")
        for demo in demos:
            exe = os.path.join(build_dir, demo)
            self.run('"%s" "%s" "%s" -I"%s" -I"%s" -o "%s" "%s" %s'
                     % (cc, os.path.join(example_dir, demo + ".c"),
                        os.path.join(example_dir, "lapacke_example_aux.c"),
                        example_dir,
                        os.path.join(lapacke_dir, "include"), exe,
                        lapacke_lib, self._lapack_link_flags()))
            self.run('"%s"' % exe)
        self.output.info(
            "upstream LAPACKE examples executed: %d/%d (upstream links with FC; "
            "CC used for this lightweight default path — deviation documented)"
            % (len(demos), len(demos)))

    def package(self):
        lapacke_dir = os.path.join(self.source_folder, "LAPACKE")
        # lapacke.h #include "lapack.h" 与 "lapacke_64.h"，五个上游头加生成的
        # lapacke_mangling.h 一起交付（上游 make install 同口径）。
        headers = ["lapacke.h", "lapack.h", "lapacke_64.h", "lapacke_config.h",
                   "lapacke_utils.h", "lapacke_mangling.h"]
        for header in headers:
            src = os.path.join(lapacke_dir, "include", header)
            if not os.path.isfile(src):
                raise ConanException("缺少交付头文件: %s" % header)
            copy(self, header, src=os.path.join(lapacke_dir, "include"),
                 dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=os.path.join(self.build_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=lapacke_dir,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["lapacke"]
        self.cpp_info.system_libs = ["m"]
