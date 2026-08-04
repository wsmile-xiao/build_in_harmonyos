#!/usr/bin/env python3
"""Conan recipe — poppler 25.12.0.2 (cmake)"""
from conan import ConanFile
from conan.tools.files import get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment



class PopplerConan(ConanFile):
    name = "poppler"
    version = "25.12.0.2"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1")
        self.requires("cairo/1.18.4")
        self.requires("glib/2.84.0.1")
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("libpng/1.6.58")
        self.requires("libtiff/4.7.2")
        self.requires("lcms2/2.19")
        self.requires("openjpeg/2.5.4")
        self.requires("boost/1.90.0.3")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ 这个 if 块是本路线的全部意义所在。
        # os=OHOS 时 conan 默认把 CMAKE_SYSTEM_NAME 设成 "HarmonyOS"，而 cmake 装的平台文件叫
        # Modules/Platform/OHOS.cmake（内容就一行 include(Platform/Linux)），**没有 HarmonyOS.cmake**。
        # 名字对不上时 cmake 不会报错退出，只打一句 "System is unknown to cmake" 就继续，
        # 把一批平台变量留空——其中 CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空，
        # 于是链接命令里没有 -Wl,-soname, → 产物没有 DT_SONAME、也不生成版本软链。
        #
        # 无 SONAME 会**传染给下游**：链接器会把本库的绝对路径原样写进消费方的 DT_NEEDED，
        # 烤死包目录哈希，换机器/清 cache 后消费方在加载期炸（expat → fontconfig 实证）。
        #
        # 必须**带 os 守卫**：这两行是为 os=OHOS 的错名打的补丁，无条件设会在别的
        # profile（如 os=Linux/arch=x86_64）上把 cmake 正确的平台识别顶掉——
        # 那时 cmake 会去找 Platform/OHOS.cmake 而不是 Linux.cmake，平台变量集体走错分支，
        # 且 CMAKE_SYSTEM_PROCESSOR 被写死 aarch64 会让上游的 SIMD/汇编选择也选错。
        # opencascade 7.9.3 MR 评审实撞。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            # 不设则 CMAKE_SYSTEM_PROCESSOR 为 "unknown"，上游按它分支的判断（SIMD/汇编选择等）会走错支。
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        # 64 位默认可能装到 lib64/，而 conan cpp_info.libdirs 与 test_package 找 lib/。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # 必须跟随 options.shared，不能写死 True：写死会让消费方的 `-o shared=False`
        # **静默失效** —— conan 算出不同的 package_id，内容却仍是动态库，
        # 且 cpp_info.libs 列的名字与实际产物对不上，下游链接才炸。
        # opencascade 7.9.3 的 MR 评审实撞；autotools 侧是同一类问题（见 recipe_model
        # 里 configure_extra 拒绝 --enable-shared 那段）。
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["CMAKE_CXX_FLAGS"] = "-fexperimental-library"
        tc.variables["ENABLE_GLIB"] = "ON"
        tc.variables["ENABLE_CPP"] = "ON"
        tc.variables["ENABLE_UTILS"] = "ON"
        tc.variables["ENABLE_LIBTIFF"] = "ON"
        tc.variables["ENABLE_LCMS"] = "ON"
        tc.variables["ENABLE_BOOST"] = "ON"
        tc.variables["ENABLE_LIBOPENJPEG"] = "openjpeg2"
        tc.variables["OPENJPEG_MAJOR_VERSION"] = "2"
        tc.variables["CAIRO_INCLUDE_DIRS"] = "{}/cairo".format(self.dependencies["cairo"].cpp_info.includedirs[0])
        tc.variables["CAIRO_LIBRARIES"] = "{}/libcairo.so".format(self.dependencies["cairo"].cpp_info.libdirs[0])
        tc.variables["GLIB2_MKENUMS"] = "{}/bin/glib-mkenums".format(self.dependencies["glib"].package_folder)
        tc.variables["LCMS2_INCLUDE_DIR"] = "{}".format(self.dependencies["lcms2"].cpp_info.includedirs[0])
        tc.variables["LCMS2_LIBRARIES"] = "{}/liblcms2.so".format(self.dependencies["lcms2"].cpp_info.libdirs[0])
        tc.variables["ENABLE_UNSTABLE_API_ABI_HEADERS"] = "ON"
        tc.variables["ENABLE_QT5"] = "OFF"
        tc.variables["ENABLE_QT6"] = "OFF"
        tc.variables["ENABLE_NSS3"] = "OFF"
        tc.variables["ENABLE_LIBCURL"] = "OFF"
        tc.variables["ENABLE_GPGME"] = "OFF"
        tc.variables["ENABLE_PGP_SIGNATURES"] = "OFF"
        tc.variables["ENABLE_GOBJECT_INTROSPECTION"] = "OFF"
        tc.variables["ENABLE_GTK_DOC"] = "OFF"
        tc.variables["BUILD_GTK_TESTS"] = "OFF"
        tc.variables["BUILD_QT5_TESTS"] = "OFF"
        tc.variables["BUILD_QT6_TESTS"] = "OFF"
        tc.variables["BUILD_CPP_TESTS"] = "OFF"
        tc.variables["BUILD_MANUAL_TESTS"] = "OFF"
        # 【skill: --inject-dep-includes 生成】上游 Find*.cmake 的查找方式五花八门，
        # 逐个喂变量追不完；像 AutotoolsDeps 那样把依赖的 include 目录全给上。
        # 只灌 -I 不灌 -l：后者会破坏上游的链接分离（hwloc 实证）。
        _incs = []
        for _ref, _d in self.dependencies.items():
            for _p in _d.cpp_info.includedirs:
                _incs.append("-I" + _p)
        _incflags = " ".join(dict.fromkeys(_incs))
        for _k in ("CMAKE_C_FLAGS", "CMAKE_CXX_FLAGS"):
            _old = tc.variables.get(_k, "")
            tc.variables[_k] = (str(_old) + " " + _incflags).strip()
        # 【skill: --inject-dep-libdirs 生成】上游若用裸库名链接（而非导入目标），
        # cmake 原样传 -lxxx，没有 -L 就 `unable to find library`。
        # poppler 实撞：CMakeLists.txt:568 `set(poppler_LIBS ${poppler_LIBS} openjp2)`。
        # 只加**搜索路径**，不追加任何 -l —— 追加 -l 才会破坏上游的链接分离（hwloc 实证）。
        _ldirs = []
        for _ref, _d in self.dependencies.items():
            for _p in _d.cpp_info.libdirs:
                _ldirs.append("-L" + _p)
        _ldflags = " ".join(dict.fromkeys(_ldirs))
        for _k in ("CMAKE_EXE_LINKER_FLAGS", "CMAKE_SHARED_LINKER_FLAGS",
                   "CMAKE_MODULE_LINKER_FLAGS"):
            _old = tc.variables.get(_k, "")
            tc.variables[_k] = (str(_old) + " " + _ldflags).strip()
        tc.generate()
        PkgConfigDeps(self).generate()
        # CMakeToolchain **不像 AutotoolsToolchain 那样自动设 PKG_CONFIG_PATH**，
        # 而很多上游的 Find*.cmake 内部走 pkg_check_modules（poppler 的
        # FindCairo/FindGLIB 就是）。不设的话 .pc 生成了也没人找得到。
        _pcenv = Environment()
        _pcenv.define_path("PKG_CONFIG_PATH", self.generators_folder)
        _pcenv.vars(self, scope="build").save_script("conanpkgconf")

        # 走这条路线的**理由**：依赖由 CMakeDeps 自动接线，不必像裸 cmake 路那样
        # 逐个手工补 -DX_DIR=... / 预设 find 缓存变量。
        CMakeDeps(self).generate()
        # 【skill: --prefer-upstream-find 生成】让上游自带的 Find<Pkg>.cmake 压过
        # CMakeDeps 的 config。CMakeToolchain 默认 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON，
        # find_package(Cairo) 会先吃到 cairo-config.cmake（CONFIG 搜索会匹配小写形态），
        # 上游模块一次都不跑；而两者导出的变量名不同（conan 设 Cairo_FOUND，
        # 上游判 CAIRO_FOUND）→ 探测永远为假。poppler 25.12 实撞：cairo/glib/lcms2 全灭。
        # 删掉 config 文件后 find_package 回落 MODULE 模式，上游模块经 pkg_check_modules
        # 正常工作（PKG_CONFIG_PATH 由上面的 --pkgconfig-deps 负责）。
        import os as _os
        for _pkg in ('Cairo', 'GLIB', 'LCMS2'):
            for _f in (_pkg + "Config.cmake", _pkg + "ConfigVersion.cmake",
                       _pkg.lower() + "-config.cmake",
                       _pkg.lower() + "-config-version.cmake"):
                _p = _os.path.join(self.generators_folder, _f)
                if _os.path.isfile(_p):
                    _os.remove(_p)
                    self.output.info("让位给上游 Find%s.cmake：删 %s" % (_pkg, _f))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        CMake(self).install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 代码签名是**鸿蒙专有**动作，用的两个工具都在 OHOS 设备的 /data/service/hnp/bin 下。
        # 在别的 profile（如 os=Linux）上它们根本不存在：
        # objcopy 那步有 `|| true` 兜底，但 binary-sign-tool 那步没有——
        # self.run() 会失败，整个 conan create 在 package 阶段崩掉。
        # 守卫写在方法内而不是各调用点：4 个构建系统模板都会调它，
        # 写在这里只有一处、且以后新增调用点自动覆盖。
        # opencascade 7.9.3 MR 评审实撞。
        if self.settings.os != "OHOS":
            return
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted。签名是内容哈希（存 .codesign 节），**链接之后再改字节就失效**：
        # meson install 抹 RUNPATH（原地涂 X）、libtool relink、strip/objcopy/patchelf 都属此列。
        # 注意**复制不会破坏签名**（哈希随内容一起复制走，2026-08-04 真机对照实验实测）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.includedirs = ['include', 'include/poppler', 'include/poppler/glib', 'include/poppler/cpp']
        self.cpp_info.libs = ['poppler', 'poppler-glib', 'poppler-cpp']
        self.cpp_info.set_property("cmake_file_name", "poppler")
        self.cpp_info.set_property("cmake_target_name", "poppler::poppler")
        self.cpp_info.set_property("pkg_config_name", "poppler-glib")



