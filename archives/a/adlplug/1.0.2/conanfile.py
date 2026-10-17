import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file, save


class AdlplugConan(ConanFile):
    name = "adlplug"
    version = "1.0.2"
    description = "FM synthesizer core from the ADLplug audio plugin"
    license = "BSL-1.0"
    homepage = "https://github.com/jpcima/ADLplug"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "adlplug/1.0.2 currently supports only OHOS armv8"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)
        for info in self.conan_data["submodules"].values():
            get(
                self,
                url=info["url"],
                sha256=info["sha256"],
                destination=os.path.join(self.source_folder, info["destination"]),
                strip_root=True,
            )
        # CMake 4.x removed compatibility with CMake < 3.5. ADLplug and
        # submodules declare 3.1-3.3; HarmonyOS real-device CMake is 4.1.2.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
            'cmake_minimum_required(VERSION "3.3")', 'cmake_minimum_required(VERSION "3.5")')
        replace_in_file(self, os.path.join(self.source_folder, "thirdparty", "fmt", "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 3.1.0)", "cmake_minimum_required(VERSION 3.5)")
        replace_in_file(self, os.path.join(self.source_folder, "thirdparty", "libADLMIDI", "CMakeLists.txt"),
            "cmake_minimum_required (VERSION 3.2)", "cmake_minimum_required(VERSION 3.5)")
        replace_in_file(self, os.path.join(self.source_folder, "thirdparty", "libOPNMIDI", "CMakeLists.txt"),
            "cmake_minimum_required (VERSION 3.2)", "cmake_minimum_required(VERSION 3.5)")
        # JUCE-targets.cmake unconditionally find_package(ALSA/Freetype/X11)
        # on the Linux branch; HarmonyOS has none. Guard behind an explicit
        # cmake variable (CMAKE_SYSTEM_NAME is empty on HarmonyOS real-device).
        juce_targets = os.path.join(self.source_folder, "JUCE-targets.cmake")
        replace_in_file(self, juce_targets,
            "  endif()\nelse()\n  # Linux and others\n  include(FindPkgConfig)\n  #\n",
            "  endif()\nelse()\n  if(NOT ADLPLUG_OHOS)\n  # Linux and others\n  include(FindPkgConfig)\n  #\n")
        replace_in_file(self, juce_targets,
            "    link_directories(${GTK_LIBRARY_DIRS})\n  endif()\nendif()\n",
            "    link_directories(${GTK_LIBRARY_DIRS})\n  endif()\n  endif()\nendif()\n")
        # JUCE 编译错绕：ft2build.h 缺（OHOS 无 Freetype）→ 关 JUCE_USE_FREETYPE；
        # pthread_cancel/setcancelstate 鸿蒙 libc 无 → 加 OHOS 分支走 no-op；
        # _NL_IDENTIFICATION_LANGUAGE/TERRITORY 鸿蒙 locale.h 无此宏 → 兜底返回空。
        # 注意：JUCE 源用 CRLF 换行，pattern 改用单行精确匹配绕开 CRLF/LF 差异。
        juce_graphics = os.path.join(self.source_folder, "thirdparty", "JUCE",
            "modules", "juce_graphics", "juce_graphics.cpp")
        replace_in_file(self, juce_graphics,
            "  #define JUCE_USE_FREETYPE 1",
            "  #if defined(__OHOS__)\n   #define JUCE_USE_FREETYPE 0\n  #else\n   #define JUCE_USE_FREETYPE 1\n  #endif")
        posix_sh = os.path.join(self.source_folder, "thirdparty", "JUCE",
            "modules", "juce_core", "native", "juce_posix_SharedCode.h")
        replace_in_file(self, posix_sh,
            "        pthread_cancel ((pthread_t) threadHandle.get());",
            "        /* pthread_cancel not available on HarmonyOS — skipped */")
        replace_in_file(self, posix_sh,
            "        pthread_setcancelstate (PTHREAD_CANCEL_ENABLE, &dummy);",
            "        /* pthread_setcancelstate not available on HarmonyOS — skipped */")
        # juce_linux_Fonts.cpp 整文件硬用 Freetype 类（FreeTypeTypeface/FTTypefaceList），
        # 鸿蒙无 Freetype、ADLplug_core 不需要字体栈。注成空文件绕开整文件卫的 CRLF 拦点。
        linux_fonts = os.path.join(self.source_folder, "thirdparty", "JUCE",
            "modules", "juce_graphics", "native", "juce_linux_Fonts.cpp")
        save(self, linux_fonts, "")
        # juce_gui_extra.cpp 的 X11 是 #elif JUCE_LINUX 硬分支（无子卫），鸿蒙无 X11。
        # ADLplug_core 不真用这个模块（只 link），注成空文件绕开 X11 硬 include。
        juce_gui_extra = os.path.join(self.source_folder, "thirdparty", "JUCE",
            "modules", "juce_gui_extra", "juce_gui_extra.cpp")
        save(self, juce_gui_extra, "")
        # juce_gui_basics.cpp 的 X11 也是 #elif JUCE_LINUX 硬分支；鸿蒙无 X11。
        # 改 #elif JUCE_LINUX 卫加 __OHOS__ 跳（保 juce_gui_basics 其他平台逻辑）。
        juce_gui_basics = os.path.join(self.source_folder, "thirdparty", "JUCE",
            "modules", "juce_gui_basics", "juce_gui_basics.cpp")
        replace_in_file(self, juce_gui_basics,
            "#elif JUCE_LINUX",
            "#elif JUCE_LINUX && !defined(__OHOS__)")
        # juce_audio_devices.cpp 整模块就是 ALSA/Jack 桌面音频栈实现，鸿蒙无 ALSA/Jack。
        # ADLplug_core 不真用它的内容（只 link），注成空文件绕开 ALSA 硬依赖。
        juce_audio_devices = os.path.join(self.source_folder, "thirdparty", "JUCE",
            "modules", "juce_audio_devices", "juce_audio_devices.cpp")
        save(self, juce_audio_devices, "")
        linux_sys = os.path.join(self.source_folder, "thirdparty", "JUCE",
            "modules", "juce_core", "native", "juce_linux_SystemStats.cpp")
        replace_in_file(self, linux_sys,
            "String SystemStats::getUserLanguage()    { return getLocaleValue (_NL_IDENTIFICATION_LANGUAGE); }",
            "#if defined(__OHOS__)\n String SystemStats::getUserLanguage()    { return {}; }\n#else\n String SystemStats::getUserLanguage()    { return getLocaleValue (_NL_IDENTIFICATION_LANGUAGE); }\n#endif")
        replace_in_file(self, linux_sys,
            "String SystemStats::getUserRegion()      { return getLocaleValue (_NL_IDENTIFICATION_TERRITORY); }",
            "#if defined(__OHOS__)\n String SystemStats::getUserRegion()      { return {}; }\n#else\n String SystemStats::getUserRegion()      { return getLocaleValue (_NL_IDENTIFICATION_TERRITORY); }\n#endif")

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["ADLplug_VST2"] = False
        toolchain.variables["ADLplug_VST3"] = False
        toolchain.variables["ADLplug_LV2"] = False
        toolchain.variables["ADLplug_AU"] = False
        toolchain.variables["ADLplug_Standalone"] = False
        toolchain.variables["ADLplug_Jack"] = False
        toolchain.variables["ADLplug_PCH"] = False
        toolchain.variables["ADLPLUG_OHOS"] = (self.settings.os == "OHOS")
        # JUCE 桌面依赖绕：鸿蒙无 ALSA/Jack/WebBrowser/Freetype，关这些 flag 跳对应卫。
        toolchain.variables["JUCE_ALSA"] = False
        toolchain.variables["JUCE_JACK"] = False
        toolchain.variables["JUCE_WEB_BROWSER"] = False
        toolchain.variables["JUCE_USE_FREETYPE"] = False
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="ADLplug_core")

    def test(self):
        if not cross_building(self):
            cmake = CMake(self)
            cmake.build(target="ADLplug_core")

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        copy(self, "*.a", src=self.build_folder, dst=libdir, keep_path=False)
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "sources"),
            dst=os.path.join(self.package_folder, "include", "adlplug"),
            keep_path=True,
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "thirdparty", "libADLMIDI", "include"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "thirdparty", "wopl"),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=True,
        )

    def package_info(self):
        self.cpp_info.libs = ["ADLplug_core", "ADLMIDI"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "adlplug")]
        self.cpp_info.set_property("cmake_file_name", "adlplug")
        self.cpp_info.set_property("cmake_target_name", "adlplug::adlplug")
