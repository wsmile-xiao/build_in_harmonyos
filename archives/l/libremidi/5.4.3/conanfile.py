import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir


class LibremidiConan(ConanFile):
    name = "libremidi"
    version = "5.4.3"
    description = "Modern C++ MIDI 1 / MIDI 2 real-time and file I/O library"
    license = "MIT"
    homepage = "https://github.com/celtera/libremidi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    @property
    def _sources(self):
        return self.conan_data["sources"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        self.test_requires("catch2/3.16.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self._sources, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["LIBREMIDI_LIBRARY_MODE"] = "LIBRARY"
        tc.cache_variables["LIBREMIDI_EXAMPLES"] = False
        tc.cache_variables["LIBREMIDI_TESTS"] = True
        # OHOS 上没有 ALSA / JACK / PipeWire / udev，也没有 Boost.Asio：这些实时后端关掉后
        # 库回到自身的 DUMMY API（include/libremidi/backends.hpp 的 LIBREMIDI_DUMMY 分支），
        # MIDI 消息编解码与 SMF 读写仍是完整实现；keyboard 后端纯 C++，保留。
        for backend in ("ALSA", "UDEV", "JACK", "PIPEWIRE", "NETWORK", "BOOST", "ANDROID"):
            tc.cache_variables["LIBREMIDI_NO_" + backend] = True
        # 上游为无 MIDI 后端的机器准备的模式：midi_in/midi_out 的 creation 用例断言
        # API::KEYBOARD / API::JACK_MIDI，缺对应后端时上游自身 SKIP，否则必红。
        # 它同时打开 -Werror，故配 LIBREMIDI_NO_WARNINGS。
        tc.cache_variables["LIBREMIDI_CI"] = True
        tc.cache_variables["LIBREMIDI_NO_WARNINGS"] = True
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.get_safe("fPIC", True))
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游 ctest 套件必须真的注册了 7 个用例，否则说明测试被静默关掉
        self.run(
            'ctest --test-dir "{}" -N | grep -q "Total Tests: 7"'.format(self.build_folder),
            env="conanbuild",
        )
        self.run(
            'ctest --test-dir "{}" --output-on-failure'.format(self.build_folder),
            env="conanbuild",
        )

    def package(self):
        copy(self, "LICENSE.md", self.source_folder, os.path.join(self.package_folder, "licenses"))
        CMake(self).install()
        # 由 Conan 的 CMakeDeps 生成导入目标，避免与上游导出的 config 重名冲突
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libremidi")
        self.cpp_info.set_property("cmake_target_name", "libremidi::libremidi")
        self.cpp_info.set_property("pkg_config_name", "libremidi")
        # 上游 CMake target 就叫 libremidi，Linux 下产物是 liblibremidi.a，链接名要带 lib
        self.cpp_info.libs = ["libremidi"]
        # 上游把后端宏挂在 target 的 PUBLIC 上（消费者要靠它判断 kbd_input_configuration 等
        # 类型是否可用）。我们删掉了上游导出的 cmake config，这个信息必须由配方自己传出去。
        self.cpp_info.defines = ["LIBREMIDI_KEYBOARD"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "FreeBSD", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
