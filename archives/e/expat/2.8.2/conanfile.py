from conan import ConanFile
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class ExpatConan(ConanFile):
    name = "expat"
    version = "2.8.2"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}


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
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["EXPAT_BUILD_TOOLS"] = "OFF"
        tc.variables["EXPAT_BUILD_EXAMPLES"] = "OFF"
        tc.variables["EXPAT_BUILD_TESTS"] = "OFF"
        tc.variables["EXPAT_BUILD_DOCS"] = "OFF"
        tc.variables["EXPAT_SHARED_LIBS"] = "ON"
        tc.variables["EXPAT_BUILD_PKGCONFIG"] = "ON"
        # 熵源：设备上 getrandom 已被 cmake 检出（HAVE_GETRANDOM found），但 expat 默认 EXPAT_WITH_*=OFF
        # 不启用任何源 → 运行期缺熵。显式开 getrandom（由 expat 构建系统一致定义，避免手工 XML_DEV_URANDOM
        # 造成 writeRandomBytes_* 悬空符号）。
        tc.variables["EXPAT_WITH_GETRANDOM"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # git 归档源码树里 CMakeLists 在子目录 expat/（顶层是仓库根，非 expat 项目根）。
        cmake.configure(build_script_folder="expat")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()



    def package_info(self):
        explicit_libs = ['expat']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "expat")
        self.cpp_info.set_property("cmake_target_name", "expat::expat")
        pkg = "expat" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)
        import os
        for _env in []:
            _k, _v = _env.split("=", 1)
            self.runenv_info.define_path(_k, os.path.join(self.package_folder, _v))

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
