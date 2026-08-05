#!/usr/bin/env python3
"""Conan recipe — opencascade 7.9.3 (cmake)"""
from conan import ConanFile
from conan.tools.files import get
import os
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches



class OpencascadeConan(ConanFile):
    name = "opencascade"
    version = "7.9.3"
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
        pass

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
        tc.variables["BUILD_MODULE_FoundationClasses"] = "ON"
        tc.variables["BUILD_MODULE_ModelingData"] = "ON"
        tc.variables["BUILD_MODULE_ModelingAlgorithms"] = "ON"
        tc.variables["BUILD_MODULE_ApplicationFramework"] = "ON"
        tc.variables["BUILD_MODULE_DataExchange"] = "ON"
        tc.variables["BUILD_MODULE_Visualization"] = "OFF"
        tc.variables["BUILD_MODULE_Draw"] = "OFF"
        tc.variables["BUILD_MODULE_DETools"] = "OFF"
        tc.variables["USE_OPENGL"] = "OFF"
        tc.variables["USE_GLES2"] = "OFF"
        tc.variables["USE_XLIB"] = "OFF"
        tc.variables["USE_VTK"] = "OFF"
        tc.variables["USE_TK"] = "OFF"
        tc.variables["USE_TCL"] = "OFF"
        tc.variables["USE_D3D"] = "OFF"
        tc.variables["USE_OPENVR"] = "OFF"
        tc.variables["USE_FREEIMAGE"] = "OFF"
        tc.variables["USE_FFMPEG"] = "OFF"
        tc.variables["USE_FREETYPE"] = "OFF"
        tc.variables["USE_DRACO"] = "OFF"
        tc.variables["USE_TBB"] = "OFF"
        tc.variables["USE_RAPIDJSON"] = "OFF"
        tc.variables["USE_EIGEN"] = "OFF"
        tc.variables["BUILD_LIBRARY_TYPE"] = "Shared" if self.options.shared else "Static"
        tc.variables["BUILD_DOC_Overview"] = "OFF"
        tc.variables["INSTALL_TEST_CASES"] = "OFF"
        tc.variables["INSTALL_DIR_INCLUDE"] = "include/opencascade"
        tc.variables["INSTALL_SAMPLES"] = "OFF"
        tc.generate()

        # 走这条路线的**理由**：依赖由 CMakeDeps 自动接线，不必像裸 cmake 路那样
        # 逐个手工补 -DX_DIR=... / 预设 find 缓存变量。
        CMakeDeps(self).generate()

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
        self.cpp_info.includedirs = ['include', 'include/opencascade']
        self.cpp_info.libs = ['TKernel', 'TKMath', 'TKG2d', 'TKG3d', 'TKGeomBase', 'TKBRep', 'TKGeomAlgo', 'TKTopAlgo', 'TKPrim', 'TKBO', 'TKBool', 'TKHLR', 'TKFillet', 'TKOffset', 'TKFeat', 'TKMesh', 'TKXMesh', 'TKShHealing', 'TKCDF', 'TKLCAF', 'TKCAF', 'TKBinL', 'TKXmlL', 'TKBin', 'TKXml', 'TKStdL', 'TKStd', 'TKTObj', 'TKBinTObj', 'TKXmlTObj', 'TKVCAF', 'TKDE', 'TKXSBase', 'TKDESTEP', 'TKDEIGES', 'TKDESTL', 'TKDEVRML', 'TKDECascade', 'TKDEOBJ', 'TKDEGLTF', 'TKDEPLY', 'TKXCAF', 'TKXmlXCAF', 'TKBinXCAF', 'TKRWMesh']
        self.cpp_info.set_property("cmake_file_name", "opencascade")
        self.cpp_info.set_property("cmake_target_name", "opencascade::opencascade")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)



    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
