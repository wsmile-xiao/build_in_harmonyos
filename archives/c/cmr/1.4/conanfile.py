#!/usr/bin/env python3
"""Conan recipe — cmr 1.4 (cmake)"""
from conan import ConanFile
from conan.tools.files import get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches



class CmrConan(ConanFile):
    name = "cmr"
    version = "1.4"
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
        self.requires("gmp/6.3.0.1")

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
        # header-only 包没有 shared 这个 option，直接取会在配方运行期 AttributeError。
        # （本行在 cmake.py.snippet 里有**另一种写法的同一条规则** —— 改一处漏一处
        #  是本仓反复栽的同型回归，两份必须一起改。）
        if self.options.get_safe("shared") is not None:
            tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["TESTS"] = "OFF"
        tc.variables["GENERATORS"] = "OFF"
        tc.variables["SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["GMP_INCLUDE_DIR"] = "{}".format(self.dependencies["gmp"].cpp_info.includedirs[0])
        tc.variables["GMP_LIBRARY_RELEASE"] = "{}/libgmp.so".format(self.dependencies["gmp"].cpp_info.libdirs[0])
        tc.variables["GMP_LIBRARIES"] = "{}/libgmp.so".format(self.dependencies["gmp"].cpp_info.libdirs[0])
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
        tc.generate()

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
        for _pkg in ('GMP'):
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
        import glob as _glob, os as _os
        targets = _glob.glob(_os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += _glob.glob(_os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = _os.path.join(self.package_folder, "bin")
        if _os.path.isdir(bindir):
            for name in _os.listdir(bindir):
                p = _os.path.join(bindir, name)
                if _os.path.isfile(p) and not _os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if _os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.includedirs = self._detect_include_dirs()
        self.cpp_info.libs = ['cmr']
        self.cpp_info.set_property("cmake_file_name", "cmr")
        self.cpp_info.set_property("cmake_target_name", "cmr::cmr")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)



    # 与标准 C/C++ 头同名的文件名。含这类文件的子目录**不能**进 includedirs，
    # 否则它会被 -isystem 加进搜索路径、抢在真正的系统头前面被找到。
    _STD_HEADER_NAMES = {
        "time.h", "math.h", "string.h", "stdio.h", "stdlib.h", "assert.h",
        "errno.h", "signal.h", "limits.h", "float.h", "locale.h", "setjmp.h",
        "ctype.h", "wchar.h", "wctype.h", "complex.h", "fenv.h", "inttypes.h",
        "stdint.h", "stddef.h", "stdarg.h", "stdbool.h", "iso646.h", "uchar.h",
        "memory", "list", "array", "vector", "string", "map", "set", "queue",
        "stack", "algorithm", "functional", "utility", "thread", "mutex",
        "atomic", "chrono", "ranges", "format", "locale",
    }

    def _detect_include_dirs(self):
        """扫 include/ 下含头文件的一层子目录，连同 include 本身一起返回。

        很多库把公开头装在版本化子目录（pango-1.0 / glib-2.0 / freetype2 / cspice…），
        只声明 include 的话，消费方按上游惯用法 #include <pango/pango.h> 就找不到 ——
        而这个缺陷在**本包构建装包时完全不暴露**，要到下游编译才炸。

        ⚠️ 但展开必须避开**与标准头同名**的子目录，否则修一个缺陷造一个更坏的：
        fmt 的 include/fmt/ 里有 locale.h，一旦把该目录 -isystem 进去，
        libc++ 的 <__locale> 执行 #include <locale.h> 时会命中 fmt/locale.h，
        musl 真正的 locale.h 永远进不来 —— 下游任何 include <sstream> 的
        翻译单元都报 `use of undeclared identifier 'uselocale'`（spdlog 实撞）。
        消费方本来就写 #include <fmt/format.h>，只需要 include/ 这一层。
        """
        import os as _os
        base = _os.path.join(self.package_folder, "include")
        dirs = ["include"]
        if not _os.path.isdir(base):
            return dirs
        for name in sorted(_os.listdir(base)):
            sub = _os.path.join(base, name)
            if not _os.path.isdir(sub):
                continue
            # 只看子目录**直接**装的头：同名遮蔽只发生在直接被搜索的那一层。
            try:
                direct = _os.listdir(sub)
            except OSError:
                continue
            # **大小写不敏感比对**：鸿蒙设备的文件系统不区分大小写，
            # `#include <string.h>` 会命中 `Poco/String.h`。守卫原先是精确匹配，
            # POCO 的 CamelCase 头一个都没被认出来，include/Poco 照样进了搜索路径 ——
            # 于是 libc++ 的 cstring 包含到 Poco/String.h，编译当场崩（poco 1.15.3 实撞）。
            if any(f.lower() in self._STD_HEADER_NAMES for f in direct):
                continue
            for _root, _d, files in _os.walk(sub):
                if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in files):
                    dirs.append("include/" + name)
                    break
        return dirs

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob as _glob
        import os as _os
        pcs = sorted(_glob.glob(_os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return _os.path.splitext(_os.path.basename(pcs[0]))[0]
