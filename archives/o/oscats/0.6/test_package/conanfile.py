import os

from conan import ConanFile
from conan.tools.build import cross_building


class OscatsTestConan(ConanFile):
    """test_package — oscats 0.6 消费者契约（OHOS 适配自研；上游 0 自动化测试）。

    编译 test_oscats.c 并链接静态 liboscats.a，跑一次真实的 1D CAT 闭环
    （20 个 1PL 题项 → 注册模拟/估计/曝光/定长/择近算法 → 3 名考生各作答
    10 题），断言库产物在 OHOS aarch64 上可用。断言清单见 MANIFEST.yml。
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # oscats.h → gsl.h 引入 glib/gobject 与 GSL 类型；静态 liboscats.a 的
        # 未解析符号由 glib-2.0/gobject-2.0/gsl/gslcblas 提供——显式 requires
        # 使这些包的 package_folder 在 build() 期可用
        self.requires("glib/2.84.0.1")
        self.requires("gsl/2.8")

    def build(self):
        # TMPDIR：鸿蒙安全框架拦 clang 在不可写目录建临时文件
        _tmp = os.path.join(self.build_folder, ".conan_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # R33：编译器从 conan conf 取
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"

        oscats_pkg = self.dependencies["oscats"].package_folder
        glib_pkg = self.dependencies["glib"].package_folder
        gsl_pkg = self.dependencies["gsl"].package_folder

        # liboscats.a 在链接期解析 glib/gobject/gsl 符号，运行期还需 glib 的
        # 传递依赖（pcre2/libffi/zlib）可达；conanrun 只保证直依赖，故汇总
        # 全图依赖 libdir 作 rpath 兜底
        rpaths = []
        for _ref, _d in self.dependencies.items():
            pf = getattr(_d, "package_folder", None) or ""
            for p in _d.cpp_info.aggregated_components().libdirs:
                ld = p if os.path.isabs(p) else os.path.join(pf, p)
                if os.path.isdir(ld):
                    rpaths.append(ld)
        rpath_flags = " ".join("-Wl,-rpath," + p
                               for p in dict.fromkeys(rpaths))

        src = os.path.join(self.source_folder, "test_oscats.c")
        out = os.path.join(self.build_folder, "test_oscats")
        self.run(
            f"{cc} {src} -o {out} "
            f"-I{oscats_pkg}/include/liboscats "
            f"-I{glib_pkg}/include/glib-2.0 "
            f"-I{glib_pkg}/lib/glib-2.0/include "
            f"-I{gsl_pkg}/include "
            f"-L{oscats_pkg}/lib -L{glib_pkg}/lib -L{gsl_pkg}/lib "
            f"{rpath_flags} "
            f"-loscats -lgobject-2.0 -lglib-2.0 -lgsl -lgslcblas -lm"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        self.run(os.path.join(self.build_folder, "test_oscats"), env="conanrun")
