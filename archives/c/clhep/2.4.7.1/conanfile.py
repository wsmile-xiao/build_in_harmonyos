from conan import ConanFile
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, get


class ClhepConan(ConanFile):
    name = "clhep"
    version = "2.4.7.1"
    description = "C++ utility classes for high-energy physics software"
    license = "BSD-3-Clause"
    homepage = "https://proj-clhep.web.cern.ch/proj-clhep/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            if self.settings.os == "OHOS":
                # testBug7328 relies on allocator behavior that differs on OHOS.
                cmake.test(cli_args=["-E", "testBug7328"])
            else:
                cmake.test()
        else:
            self.output.info(
                "Skipping CLHEP upstream CTest suite: the target binaries "
                "cannot run on this build machine"
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "CLHEP")
        self.cpp_info.set_property("cmake_target_name", "CLHEP::CLHEP")
        self.cpp_info.libs = collect_libs(self)
