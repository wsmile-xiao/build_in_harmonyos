#!/usr/bin/env python3
"""Conan recipe — mygui 3.4.4 (CMake, HarmonyOS PC / OHOS arm64).

MyGUI is a cross-platform GUI library (MyGUIEngine + render-system platform).
Official upstream: https://github.com/MyGUI/mygui tag MyGUI3.4.4.

Adaptation notes (OHOS):
- Rendersystem: MYGUI_RENDERSYSTEM=1 (Dummy) for this first-round local
  validation — the Dummy platform has no GL dependency, so the engine +
  platform build cleanly headless. Real OHOS rendering (OpenGLES platform,
  MYGUI_RENDERSYSTEM=8, links OHOS SDK libEGL/libGLESv3) is the identified
  follow-up, out of scope for local W3 validation here.
- Engine font rendering: MYGUI_USE_FREETYPE=ON via freetype + zlib (ohpcd).
- Demos/tools/tests/docs/wrapper disabled: they need SDL2_image / OGRE and
  an interactive display, which break a headless local W3 validation.
- CMake's FindFreetype/FindZLIB module variables (FREETYPE_*/ZLIB_*) are
  satisfied by pointing CMAKE_PREFIX_PATH at the conan package folders
  and pre-setting the legacy cache variables.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
    patch,
)


class MyguiConan(ConanFile):
    name = "mygui"
    version = "3.4.4"
    description = "MyGUI — cross-platform GUI library (MyGUIEngine + OpenGLES platform)"
    license = "MIT"
    homepage = "https://github.com/MyGUI/mygui"
    url = ""  # CI fills this

    package_type = "library"

    # E017 镜像注入流程会把工作区 conandata.yml 的 patches 抹回 {}，
    # 导致 export_conandata_patches 导不出补丁、conan create 内 apply_conandata_patches
    # 无事可做（G2 仍报 SDL2::Main not found）。这里固定携带补丁 + build() 显式兜底：
    exports_sources = "patches/*"

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
        self.requires("freetype/2.14.3.1", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        # r03: UnitTests（mygui_app 目标）无条件 include/link SDL2
        # （CMake/Utils/MyGUIConfigTargets.cmake mygui_app: SDL2_INCLUDE_DIRS/SDL2_LIB_DIR）。
        # ohpcd 已发布 sdl2/2.30.10（sdl2_mixer 2.8.1 配方亦引用同版本）。
        self.requires("sdl2/2.30.10", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)

        # OHOS: CMake's FindFreetype / FindZLIB modules need the conan package
        # dirs on the prefix path; pre-set the legacy cache variables so
        # MyGUI's Dependencies.cmake / MyGUIEngine/CMakeLists.txt link fine.
        prefix_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                prefix_paths.append(dep.package_folder)
        if prefix_paths:
            tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefix_paths)

        # FindFreetype/FindZLIB 通过 CMAKE_PREFIX_PATH（上方已注入 conan 包目录）
        # 自动定位依赖，无需手工覆盖 FREETYPE_LIBRARY/ZLIB_LIBRARY。
        # （曾误用 ${CONAN_LIB_DIRS_*}，该变量在 toolchain 中不存在，会解析成
        #   /libfreetype.so 导致 "No rule to make target" —— 已移除。）

        # r03: UnitTests（mygui_app 目标）使用大写 SDL2_* 模块变量
        # （CMake/Utils/MyGUIConfigTargets.cmake: include_directories(SYSTEM
        #   ${SDL2_INCLUDE_DIRS}) / link_directories(${SDL2_LIB_DIR})），
        # 而 CMakeDeps 只生成小写 sdl2_* 变量。用依赖真实路径预置大写变量，
        # 避免 "Found relative path ... SDL2_INCLUDE_DIR-NOTFOUND" 配置失败。
        sdl2 = self.dependencies["sdl2"]
        sdl2_incl = []
        for d in sdl2.cpp_info.includedirs:
            p = os.path.join(sdl2.package_folder, d) if not os.path.isabs(d) else d
            if p not in sdl2_incl:
                sdl2_incl.append(p)
        sdl2_libdir = ""
        for d in sdl2.cpp_info.libdirs:
            p = os.path.join(sdl2.package_folder, d) if not os.path.isabs(d) else d
            if os.path.isdir(p):
                sdl2_libdir = p
                break
        tc.variables["SDL2_INCLUDE_DIRS"] = ";".join(sdl2_incl) or "${sdl2_INCLUDE_DIRS}"
        tc.variables["SDL2_LIB_DIR"] = sdl2_libdir or "${sdl2_LIB_DIRS}"
        tc.variables["SDL2_LIBRARIES"] = "SDL2"
        tc.variables["SDL2_LIBRARY"] = "SDL2"
        # SDL2::Main 目标由 patches/0001-common-link-sdl2-target.patch 处理
        # （Common/CMakeLists.txt 改链 sdl2::sdl2，见 conandata.yml patches）

        # Build scope: engine + Dummy platform only (OHOS 无头本地验证)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["MYGUI_STATIC"] = "OFF" if self.options.shared else "ON"
        tc.variables["MYGUI_RENDERSYSTEM"] = "1"  # Dummy；OpenGLES(8)为后续适配项
        tc.variables["MYGUI_USE_FREETYPE"] = "ON"
        tc.variables["MYGUI_MSDF_FONTS"] = "OFF"
        tc.variables["MYGUI_DONT_USE_OBSOLETE"] = "OFF"
        tc.variables["MYGUI_BUILD_DEMOS"] = "OFF"
        tc.variables["MYGUI_BUILD_PLUGINS"] = "OFF"
        tc.variables["MYGUI_BUILD_TOOLS"] = "OFF"
        tc.variables["MYGUI_BUILD_UNITTESTS"] = "ON"
        tc.variables["MYGUI_BUILD_TEST_APP"] = "ON"
        tc.variables["MYGUI_BUILD_WRAPPER"] = "OFF"
        tc.variables["MYGUI_BUILD_DOCS"] = "OFF"
        tc.variables["MYGUI_INSTALL_DOCS"] = "OFF"
        tc.variables["MYGUI_INSTALL_DEMOS"] = "OFF"
        tc.variables["MYGUI_INSTALL_TOOLS"] = "OFF"

        # r06: UnitTests 运行时布局修复（r05 诊断根因）——二进制 DT_NEEDED 为
        # 路径形式 ../../lib/libMyGUIEngine.so（musl 对含 '/' 的 NEEDED 不作 RPATH
        # 搜索），从 build/Release/bin 解析到 build/lib。实测 RPATH 无法改变路径
        # 形式 NEEDED，故采用统一输出布局：把共享库输出目录设为 build/lib，使
        # 相对路径 NEEDED 与实际库落点一致（等价于 r05 验证过的软链布局，但为
        # 配方内正规输出布局，非临时软链）。
        _lib_out = os.path.join(self.build_folder, "lib").replace("\\", "/")
        tc.variables["CMAKE_LIBRARY_OUTPUT_DIRECTORY"] = _lib_out
        tc.variables["CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE"] = _lib_out
        tc.variables["CMAKE_ARCHIVE_OUTPUT_DIRECTORY"] = os.path.join(self.build_folder, "lib").replace("\\", "/")
        tc.variables["CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE"] = os.path.join(self.build_folder, "lib").replace("\\", "/")
        # 保留 $ORIGIN/../lib RPATH（对名字形式 NEEDED 生效，双保险）
        tc.variables["CMAKE_BUILD_RPATH"] = "\\$ORIGIN/../lib"
        tc.variables["CMAKE_INSTALL_RPATH"] = "\\$ORIGIN/../lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E017 可能抹掉 conandata.yml 的 patches -> 若 Common/CMakeLists.txt 仍引用
        # SDL2::Main 则显式应用补丁（配方自包含兜底，patch 由 exports_sources 携带）。
        common_make = os.path.join(self.source_folder, "Common", "CMakeLists.txt")
        if os.path.isfile(common_make):
            with open(common_make, encoding="utf-8", errors="replace") as _f:
                if "SDL2::Main" in _f.read():
                    self.output.warning("E017 抹除 conandata patches，显式应用 SDL2::Main 补丁")
                    patch(self, base_path=self.source_folder,
                          patch_file=os.path.join(self.export_sources_folder, "patches",
                                                  "0001-common-link-sdl2-target.patch"))
        # r10: E017 兜底（同 0001 模式）——若 Dummy 后端 addResourceLocation 仍为空实现
        # （DummyDataManager 无 mPaths 注册逻辑）则显式应用 0002 资源注册补丁。
        _dummy_impl = os.path.join(self.source_folder, "Platforms", "Dummy", "DummyPlatform",
                                   "src", "MyGUI_DummyDataManager.cpp")
        if os.path.isfile(_dummy_impl):
            with open(_dummy_impl, encoding="utf-8", errors="replace") as _f:
                if "void DummyDataManager::addResourceLocation" not in _f.read():
                    self.output.warning("E017 抹除 conandata patches，显式应用 Dummy 资源注册补丁")
                    patch(self, base_path=self.source_folder,
                          patch_file=os.path.join(self.export_sources_folder, "patches",
                                                  "0002-dummy-resource-registration.patch"))
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # r06: UnitTests 二进制 DT_NEEDED 为路径形式 ../../lib/libMyGUIEngine.so
        # （musl 对含 '/' 的 NEEDED 不做 RPATH 搜索，按 cwd 相对解析），而 MyGUI
        # 顶层 CMakeLists 用 set() 把共享库输出到 build/Release/lib。配方内动态
        # 布局修复：按二进制实际位置计算 NEEDED 解析目标（bin/../../lib），
        # 把构建出的 libMyGUIEngine.so 复制到该处（等价于 r05 验证布局，非临时软链）。
        _bins = glob.glob(os.path.join(self.build_folder, "**", "TestApp"), recursive=True)
        if _bins:
            _bin_dir = os.path.dirname(_bins[0])
            _need_target = os.path.normpath(os.path.join(_bin_dir, "..", "..", "lib"))
            os.makedirs(_need_target, exist_ok=True)
            _libs = glob.glob(os.path.join(self.build_folder, "**", "libMyGUIEngine.so*"), recursive=True)
            _libs += glob.glob(os.path.join(self.build_folder, "**", "libMyGUI.DummyPlatform.so*"), recursive=True)
            _seen = set()
            for _so in _libs:
                _n = os.path.basename(_so)
                if _n in _seen:
                    continue
                _seen.add(_n)
                shutil.copy2(_so, os.path.join(_need_target, _n))
            self.output.info("r06 layout fix: copied libs to {}".format(_need_target))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        # MyGUI installs headers into include/MYGUI
        self.cpp_info.includedirs = ["include/MYGUI", "include"]
        self.cpp_info.requires = ["freetype::freetype", "zlib::zlib", "sdl2::sdl2"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
        self.cpp_info.set_property("cmake_file_name", "MyGUI")
        self.cpp_info.set_property("cmake_target_name", "MyGUI::MyGUI")
        self.cpp_info.set_property("pkg_config_name", "MYGUI")