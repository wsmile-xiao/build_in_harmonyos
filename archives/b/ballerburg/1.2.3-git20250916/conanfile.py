import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps
from conan.tools.files import get


class BallerburgConan(ConanFile):
    name = "ballerburg"
    version = "1.2.3-git20250916"
    package_type = "application"
    license = "GPL-3.0"
    homepage = "https://github.com/ooxi/baller"
    description = ("Ballerburg SDL — classical castle combat game (C, "
                   "SDL2)")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "conandata.yml"
    # 依赖：SDL2（CMakeLists ENABLE_SDL2 开关——适配用 SDL2——已合入
    # sdl2/2.30.10——SDL1.2 未合入故用 SDL2）
    requires = "sdl2/2.30.10"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # lld 需要 libxml2.so.16（llvm/lib 目录——CI 的 LD_LIBRARY_PATH 没
        # 包含——'Error loading shared library libxml2.so.16' 实测 #6625——
        # lld 崩溃导致 CMake 编译器测试失败）——LD_LIBRARY_PATH 加 llvm/lib
        self.buildenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib")
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_SDL2"] = "ON"
        # ballerburg 的 CMakeLists 要求 CMake 2.8（太旧——当前 CMake 已
        # 移除 <3.5 兼容——'Compatibility with CMake < 3.5 has been
        # removed' 实测）——加 CMAKE_POLICY_VERSION_MINIMUM=3.5
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # src/CMakeLists.txt 的 include_directories 用 ${MATH_INCLUDE_DIR}
        # （find_package(Math) 的 include 目录——OHOS 未找到——
        # 'MATH_INCLUDE_DIR-NOTFOUND' 实测）——设为空
        tc.cache_variables["MATH_INCLUDE_DIR"] = ""
        # find_package(Math REQUIRED) 需要 MATH_LIBRARY + MATH_INCLUDE_DIR
        # ——MATH_LIBRARY 也 missing（'Could NOT find MATH (missing:
        # MATH_LIBRARY)' 实测）——设为空（Math 为系统数学库——链接 libm）
        tc.cache_variables["MATH_LIBRARY"] = ""
        # src/CMakeLists.txt 的 SDL_INCLUDE_DIR=SDL2_INCLUDE_DIR——但
        # SDL.h 在 sdl2 包的 include/SDL2/（include <SDL.h> 需要该路径——
        # 'SDL.h file not found' 实测）——显式设置 SDL_INCLUDE_DIR
        _sdl2 = self.dependencies["sdl2"].package_folder
        tc.cache_variables["SDL_INCLUDE_DIR"] = os.path.join(_sdl2, "include", "SDL2")
        # src/CMakeLists.txt 的 target_link_libraries 用 ${SDL_LIBRARY}
        # + ${SDLMAIN_LIBRARY}（=SDL2_LIBRARY/SDL2MAIN_LIBRARY——未设置
        # ——'undefined symbol: SDL_GetError' 链接失败实测）——显式设置
        # （sdl2 是静态库 libSDL2.a）
        _sdl2_lib = os.path.join(_sdl2, "lib")
        tc.cache_variables["SDL_LIBRARY"] = os.path.join(_sdl2_lib, "libSDL2.a")
        tc.cache_variables["SDLMAIN_LIBRARY"] = os.path.join(_sdl2_lib, "libSDL2main.a")
        # 注意：不链接 -lgettext（OHOS 无 gettext——libc 无符号 + libintl
        # 不存在——'unable to find library -lgettext' 实测）——build() patch
        # 源码去掉 gettext 调用（国际化非核心）
        tc.generate()
    def build(self):
        # OHOS 无 gettext（libc 无符号 + libintl 不存在——'undefined symbol:
        # gettext' 链接失败实测）——patch 源码去掉 gettext 调用（国际化
        # 非核心功能——注释掉）
        _src_dir = os.path.join(self.source_folder, "src")
        for _f in os.listdir(_src_dir):
            if _f.endswith((".c", ".h")):
                _p = os.path.join(_src_dir, _f)
                # errors="ignore"——部分源码文件非 UTF-8（'utf-8' codec
                # can't decode 实测）——忽略非 UTF-8 字节
                _t = open(_p, encoding="utf-8", errors="ignore").read()
                if "bindtextdomain" in _t or "textdomain" in _t or "?gettext(" in _t:
                    _t = _t.replace("bindtextdomain(", "// bindtextdomain(")
                    _t = _t.replace("textdomain(", "// textdomain(")
                    # 宏定义里的 gettext（i18n.h: #define _(string)
                    # ((string)[0]?gettext(string):(string))——替换成
                    # ?(string)——不注释（注释会破坏宏定义——'expected
                    # expression' 实测）
                    _t = _t.replace("?gettext(", "?(")
                    open(_p, "w").write(_t)
        # src/CMakeLists.txt 的 find_package(Gettext) 去掉
        _cm = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        _t = open(_cm, encoding="utf-8", errors="ignore").read()
        if "find_package(Gettext" in _t:
            _t = _t.replace("find_package(Gettext", "# find_package(Gettext", 1)
            open(_cm, "w").write(_t)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
