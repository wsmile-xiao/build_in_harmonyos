from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.scm import Version
import os


class OpenexrConan(ConanFile):
    name = "openexr"
    version = "3.3.4"
    description = "OpenEXR is a high dynamic-range (HDR) image file format developed by Industrial Light & Magic"
    license = "BSD-3-Clause"
    homepage = "https://github.com/AcademySoftwareFoundation/openexr"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # imath 包名小写（本仓库名为 imath/3.2.2，非 Imath）
        self.requires("imath/3.2.2", transitive_headers=True)
        self.requires("libdeflate/1.22")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # 上游 OpenEXRCore/CMakeLists.txt 依赖 Imath::Imath（PUBLIC 传递），
        # 其 openexr_config.h 以 "#include <ImathConfig.h>" 方式引用 Imath
        # 配置头。上游 ImathConfig 组件的安装接口同时暴露 include/ 与
        # include/Imath 两个目录（见 ImathTargets.cmake 的
        # Imath::ImathConfig INTERFACE_INCLUDE_DIRECTORIES）。本仓库
        # imath/3.2.2 配方 cpp_info 默认只声明 include/，CMakeDeps 生成的
        # ImathConfig.cmake 缺少 include/Imath 目录，导致 OpenEXRCore
        # 编译报 'ImathConfig.h' file not found。这里在依赖侧把 imath 组件
        # 的 includedirs 补齐为 [include, include/Imath]（绝对路径，与上游
        # 安装口径一致；必须在 CMakeDeps 构造前完成，组件级直接生效）。
        imath_info = self.dependencies["imath"].cpp_info
        for info in [imath_info] + list(imath_info.components.values()):
            dirs = list(info.includedirs)
            if not any(d.endswith("include/Imath") or d.endswith("include\\Imath")
                       for d in dirs):
                for d in dirs:
                    if d.endswith("include"):
                        dirs.append(os.path.join(d, "Imath"))
                        break
                info.includedirs = dirs

        # 上游 OpenEXRSetup.cmake 的 find_package(libdeflate CONFIG) 分支
        # 只认 libdeflate::libdeflate_shared / _static 目标名；Conan 的
        # libdeflate/1.22 包自带上游 cmake config（libdeflate-config.cmake
        # 导出 libdeflate::libdeflate_shared）。这里用 CMakeDeps 属性改写把
        # 组件目标名对齐为 _shared（实际库为 .so，语义一致），使上游逻辑
        # 走外部 libdeflate 而非 FetchContent 内嵌源码（CI 无网络下载）。
        # 注意：必须在 imath includedirs 补齐之后构造 CMakeDeps。
        deps = CMakeDeps(self)
        deps.set_property("libdeflate", "cmake_target_name",
                          "libdeflate::libdeflate_shared")

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_WEBSITE"] = False
        tc.variables["OPENEXR_INSTALL_EXAMPLES"] = False
        tc.variables["OPENEXR_BUILD_TOOLS"] = True
        tc.variables["OPENEXR_BUILD_LIBS"] = True
        tc.variables["OPENEXR_FORCE_INTERNAL_DEFLATE"] = False
        if self.options.shared:
            # CMake 对 HarmonyOS 平台（无专属 platform module）不生成
            # SONAME 链接参数，导致库间 NEEDED 记录为构建树相对路径
            # （../IlmThread/libIlmThread-3_3.so），安装到平铺 lib/ 目录
            # 后加载器找不到。显式提供 soname flag 让 CMake 走标准
            # SONAME 机制（与 Linux 平台行为一致）。
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = \
                "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = \
                "-Wl,-soname,"
        tc.generate()
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    @staticmethod
    def _conan_comp(name):
        return "openexr_" + name.lower()

    def _add_component(self, name):
        component = self.cpp_info.components[self._conan_comp(name)]
        component.set_property("cmake_target_name", "OpenEXR::" + name)
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenEXR")
        self.cpp_info.set_property("pkg_config_name", "OpenEXR")

        lib_suffix = ""
        if not self.options.shared:
            v = Version(self.version)
            lib_suffix = "-%d_%d" % (v.major, v.minor)
        if self.settings.build_type == "Debug":
            lib_suffix += "_d"

        # OpenEXR::OpenEXRConfig (header-only config component)
        OpenEXRConfig = self._add_component("OpenEXRConfig")
        OpenEXRConfig.includedirs = [
            os.path.join("include", "OpenEXR")]

        # OpenEXR::IexConfig
        IexConfig = self._add_component("IexConfig")
        IexConfig.includedirs = OpenEXRConfig.includedirs

        # OpenEXR::IlmThreadConfig
        IlmThreadConfig = self._add_component("IlmThreadConfig")
        IlmThreadConfig.includedirs = OpenEXRConfig.includedirs

        # OpenEXR::Iex
        Iex = self._add_component("Iex")
        Iex.libs = ["Iex" + lib_suffix]
        Iex.requires = [self._conan_comp("IexConfig")]
        if self.settings.os in ("Linux", "OHOS"):
            Iex.system_libs = ["m"]

        # OpenEXR::IlmThread
        IlmThread = self._add_component("IlmThread")
        IlmThread.libs = ["IlmThread" + lib_suffix]
        IlmThread.requires = [
            self._conan_comp("IlmThreadConfig"), self._conan_comp("Iex")]
        if self.settings.os in ("Linux", "OHOS"):
            IlmThread.system_libs = ["pthread", "m"]

        # OpenEXR::OpenEXRCore
        # 上游 src/lib/OpenEXRCore/CMakeLists.txt 将 Imath::Imath 列为
        # PUBLIC DEPENDENCIES（openexr_config.h 公开包含 <ImathConfig.h>），
        # 组件依赖必须如实声明，否则消费者编译期缺 Imath 头。
        OpenEXRCore = self._add_component("OpenEXRCore")
        OpenEXRCore.libs = ["OpenEXRCore" + lib_suffix]
        OpenEXRCore.requires = [
            self._conan_comp("OpenEXRConfig"), "libdeflate::libdeflate",
            "imath::imath"]
        if self.settings.os in ("Linux", "OHOS"):
            OpenEXRCore.system_libs = ["m"]

        # OpenEXR::OpenEXR
        OpenEXR = self._add_component("OpenEXR")
        OpenEXR.libs = ["OpenEXR" + lib_suffix]
        OpenEXR.requires = [
            self._conan_comp("OpenEXRCore"), self._conan_comp("IlmThread"),
            self._conan_comp("Iex"), "imath::imath"]
        if self.settings.os in ("Linux", "OHOS"):
            OpenEXR.system_libs = ["m"]

        # OpenEXR::OpenEXRUtil
        OpenEXRUtil = self._add_component("OpenEXRUtil")
        OpenEXRUtil.libs = ["OpenEXRUtil" + lib_suffix]
        OpenEXRUtil.requires = [self._conan_comp("OpenEXR")]
        if self.settings.os in ("Linux", "OHOS"):
            OpenEXRUtil.system_libs = ["m"]
