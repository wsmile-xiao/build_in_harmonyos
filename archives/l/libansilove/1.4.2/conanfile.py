#!/usr/bin/env python3
"""Conan recipe — libansilove 1.4.2 (cmake)"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class LibansiloveConan(ConanFile):
    name = "libansilove"
    version = "1.4.2"
    description = "Library for converting ANSI, ASCII, and other format art into PNG images"
    license = "BSD-2-Clause"
    homepage = "https://www.ansilove.org/"
    url = "https://github.com/ansilove/libansilove"
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
        # 上游 find_path(gd.h) + find_library(gd)：PNG 输出走 gdImagePngPtr()。
        # gd/2.3.3 是 ohpcd 上带真 PNG 实现的版本（libpng 1.6.58 + zlib 传递依赖）；
        # gd/2.3.3.2 配方 ENABLE_PNG=OFF 是桩版（gdImagePngPtr 为 8 字节桩返回 NULL），
        # libansilove 的核心功能（PNG 输出）会直接失败，不可用。
        # gd 静态对象完整链入（NEEDED 无 gd），但其共享依赖 libpng16/libz 留在
        # NEEDED 里，经 _dep_link_flags 补齐（见 build() 注释）。
        self.requires("gd/2.3.3")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # 优先 CI/worker：profile [conf] user_toolchain 或 OHOS_NDK_HOME（glfw/libjpeg-turbo 同法）。
        # 找不到时返回 None → 退化用 conan_toolchain（本机 OHOS PC 原生开发机场景）。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        return None

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")

        llvm_ar = shutil.which("llvm-ar")
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        if not llvm_ar or not ranlib:
            raise ConanInvalidConfiguration(
                "OHOS build requires llvm-ar and a usable ranlib; "
                "llvm-ar={!r}, ranlib={!r}".format(
                    llvm_ar, ranlib
                )
            )

        self.output.info(
            "Archive tools: ar={}, ranlib={}".format(llvm_ar, ranlib)
        )

        defs = [
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_AR:FILEPATH={}".format(llvm_ar),
            "-DCMAKE_RANLIB:FILEPATH={}".format(ranlib),
        ]
        if toolchain:
            # OHOS NDK 工具链（CI worker）
            defs += [
                '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
                "-DOHOS_ARCH=arm64-v8a",
                "-DCMAKE_INSTALL_LIBDIR=lib",   # ohos.toolchain 64 位默认 lib64/
            ]
        # else: 本机 OHOS PC 原生 clang，无交叉需求，不传 toolchain file
        defs += [
            # SONAME 注入（libharu-2.3.0 同根因）：HarmonyOS 无 Platform/HarmonyOS.cmake，
            # CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空 → 上游 SOVERSION 1 不生效，
            # 产物无 DT_SONAME。NO_VERSIONED_SONAME 同时避免设备上建 .so.1 软链。
            "-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON",
            "-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,",
        ]
        # OHOS 官方 toolchain 的库搜索根受 CMAKE_SYSROOT 约束，find_library 看不到
        # Conan 缓存里的 gd 包（远端 CI 失败根因，PR #9925）。CMAKE_PREFIX_PATH 与
        # -L 只影响搜索路径，无法保证命中；这里从依赖元数据显式推导 gd 的头文件
        # 目录与库文件绝对路径，作为 cache 变量注入，使上游 CMakeLists.txt:25-26 的
        # find_path/find_library 直接短路（cache 已有值即不再搜索）。
        gd_inc, gd_lib = self._resolve_gd_paths()
        defs += [
            "-DGD_INCLUDE_DIRS:PATH={}".format(gd_inc),
            "-DGD_LIBRARIES:FILEPATH={}".format(gd_lib),
            # gd 静态对象链入 libansilove.so，其 png_*/z_* 符号需在 .so 链接时一并
            # 解析（OHOS lld --no-allow-shlib-undefined）。上游只 find_library(gd)，
            # 补 -lpng16 -lz 让 .so 自身符号闭包完整。
            '-DCMAKE_EXE_LINKER_FLAGS:STRING={}'.format(self._dep_link_flags()),
            '-DCMAKE_SHARED_LINKER_FLAGS:STRING={}'.format(self._dep_link_flags()),
            "-DCMAKE_INSTALL_PREFIX={}".format(self.package_folder),
            "-DCMAKE_INSTALL_INCLUDEDIR=include",
        ]
        # 空格安全：CMAKE_*_LINKER_FLAGS 含带空格的 -L 路径，必须整体单引号包裹，
        # 由 self.run 的 shell 解析为单个 argv；逐项引号拼接会在这里被拆散。
        self.run('cmake -B "{}" -S "{}" {}'
                 .format(bdir, self.source_folder, " ".join(defs)))
        self.run('cmake --build "{}"'.format(bdir))

    def _resolve_gd_paths(self):
        """从 gd 依赖元数据推导 (include 目录, libgd 库文件绝对路径)，fail-closed。

        cpp_info.includedirs/libdirs 是相对 package_folder 的相对路径（Conan 2.x
        消费侧语义），需自行折叠为绝对路径。任何一步不唯一/不存在即抛错，
        防止 OHOS toolchain 下静默退化成 find_library 搜索失败。
        """
        # self.dependencies["gd"] 未命中会抛 KeyError("'gd' not found ...")
        dep = self.dependencies["gd"]
        pkg_folder = dep.package_folder
        if not pkg_folder or not os.path.isdir(pkg_folder):
            raise ConanInvalidConfiguration(
                "gd dependency package_folder missing or not a directory: {!r}".format(pkg_folder))

        # 头文件目录：取声明的 includedirs（相对 package_folder）中第一个含 gd.h 的
        includedirs = list(dep.cpp_info.includedirs)
        if not includedirs:
            raise ConanInvalidConfiguration(
                "gd cpp_info.includedirs is empty; package_folder: {}".format(pkg_folder))
        include_candidates = [d if os.path.isabs(d) else os.path.join(pkg_folder, d)
                              for d in includedirs]
        for inc_dir in include_candidates:
            if os.path.isfile(os.path.join(inc_dir, "gd.h")):
                gd_include = inc_dir
                break
        else:
            raise ConanInvalidConfiguration(
                "gd.h not found under declared include dirs: {}; package_folder: {}"
                .format(include_candidates, pkg_folder))

        # 库文件：cpp_info.libs 声明链接名（gd），在声明的 libdirs 下找
        # libgd.a / libgd.so 等实际文件；多于一个候选且非同一文件时失败
        libdirs = list(dep.cpp_info.libdirs)
        if not libdirs:
            raise ConanInvalidConfiguration(
                "gd cpp_info.libdirs is empty; package_folder: {}".format(pkg_folder))
        lib_dirs_abs = [d if os.path.isabs(d) else os.path.join(pkg_folder, d)
                        for d in libdirs]
        lib_names = list(dep.cpp_info.libs)
        if not lib_names:
            raise ConanInvalidConfiguration(
                "gd cpp_info.libs is empty; libdirs: {}".format(lib_dirs_abs))
        candidates = []
        for lib_dir in lib_dirs_abs:
            for name in lib_names:
                for pattern in ("lib{}.a", "lib{}.so", "lib{}.so.*", "{}.a", "{}.lib"):
                    candidates.extend(glob.glob(os.path.join(lib_dir, pattern.format(name))))
        # 去重（.so.* 通配可能展开多版本）并过滤符号链接指向自身的异常项
        uniq = sorted(set(c for c in candidates if os.path.isfile(c) and not os.path.islink(c)))
        if not uniq:
            raise ConanInvalidConfiguration(
                "no gd library file found in {}; libs declared: {}; package_folder: {}"
                .format(lib_dirs_abs, lib_names, pkg_folder))
        # 候选收敛：优先 .a（gd 默认静态闭包），否则取唯一非静态
        statics = [c for c in uniq if c.endswith(".a")]
        if len(statics) == 1:
            gd_lib = statics[0]
        elif len(uniq) == 1:
            gd_lib = uniq[0]
        else:
            raise ConanInvalidConfiguration(
                "ambiguous gd library candidates, cannot pick one: {}; "
                "package_folder: {}".format(uniq, pkg_folder))
        self.output.info("GD resolution: include={}, lib={}".format(gd_include, gd_lib))
        return gd_include, gd_lib

    def _dep_link_flags(self):
        # -L 指向 conan 依赖包 lib/，让 png/zlib 链接全部命中（gd 本体已由
        # GD_LIBRARIES cache 变量显式注入，不依赖 -L 搜索）
        flags = []
        for _r, d in self.dependencies.items():
            libs = os.path.join(d.package_folder, "lib")
            if os.path.isdir(libs):
                flags.append('-L"{}"'.format(libs))
        flags += ["-lgd", "-lpng16", "-lz"]
        # 整体单引号：flags 内含带空格的 -L 路径与子引号，必须作为单个 argv
        # 传给 cmake -D，否则 shell 会把 -L"..." 拆散（空格安全，PR #9925 #7）
        return "'{}'".format(" ".join(flags))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        # 裁剪：上游 install 同时装 libansilove.so 与 libansilove-static.a（objlib 双
        # target，无 BUILD_SHARED_LIBS 开关），按选项只留其一
        if self.options.shared:
            for f in glob.glob(os.path.join(self.package_folder, "lib", "*-static.a")):
                os.unlink(f)
        else:
            so = os.path.join(self.package_folder, "lib", "libansilove.so")
            if os.path.isfile(so):
                os.unlink(so)
            # 静态消费按 ansilove 名取 libansilove.a
            src_a = os.path.join(bdir, "libansilove-static.a")
            dst_a = os.path.join(self.package_folder, "lib", "libansilove.a")
            if os.path.isfile(src_a):
                shutil.copy2(src_a, dst_a)
            for f in glob.glob(os.path.join(self.package_folder, "lib", "*-static.a")):
                os.unlink(f)
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # cmake 产的 .so 需 .codesign 签名才能在设备加载：剥旧段 + binary-sign-tool 重签
        libdir = os.path.join(self.package_folder, "lib")
        sos = [f for f in glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
               + glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
               if not os.path.islink(f)]
        if not sos:
            return
        objcopy = os.environ.get("LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool 不可用，跳过代码签名（非 CI/设备环境）")
            return
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["ansilove"]
        # gd 静态链入 libansilove.so，但其引用的 png_*/z_* 符号留在 .so 里未解析
        #（Linux 允许运行时解析；OHOS lld 对可执行文件强制 --no-allow-shlib-undefined）。
        # 消费者必须连带链接 gd 的依赖链（libpng16.so + zlib），故声明 requires 传播。
        self.cpp_info.requires = ["gd::gd"]
        self.cpp_info.set_property("cmake_file_name", "ansilove")
        self.cpp_info.set_property("cmake_target_name", "ansilove::ansilove")
        self.cpp_info.set_property("pkg_config_name", "ansilove")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
