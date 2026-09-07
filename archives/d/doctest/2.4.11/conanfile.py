from conan import ConanFile
from conan.tools.cmake import CMake,CMakeToolchain,cmake_layout
from conan.tools.files import apply_conandata_patches,export_conandata_patches,get
class DoctestConan(ConanFile):
    name = "doctest"
    version = "2.4.11"
    description="Feature-rich C++ single-header testing framework"
    license="MIT"
    homepage="https://github.com/doctest/doctest"
    url="https://github.com/doctest/doctest"
    package_type="header-library"
    settings="os","compiler","build_type","arch"
    def export_sources(self): export_conandata_patches(self)
    def requirements(self): pass
    def layout(self): cmake_layout(self)
    def source(self): get(self,**self.conan_data["sources"],strip_root=True)
    def generate(self):
        tc=CMakeToolchain(self)
        for k,v in {"BUILD_SHARED_LIBS":"OFF","CMAKE_POLICY_VERSION_MINIMUM":"3.5","DOCTEST_WITH_TESTS":"ON","DOCTEST_NO_INSTALL":"OFF","DOCTEST_WITH_MAIN_IN_STATIC_LIB":"OFF"}.items(): tc.variables[k]=v
        tc.generate()
    def build(self):
        apply_conandata_patches(self)
        cm=CMake(self)
        cm.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM":"3.5","DOCTEST_WITH_TESTS":"ON","DOCTEST_NO_INSTALL":"OFF","DOCTEST_WITH_MAIN_IN_STATIC_LIB":"OFF"})
        cm.build()
        cm.test()
    def package(self): CMake(self).install()
    def package_info(self):
        self.cpp_info.set_property("cmake_file_name","doctest")
        self.cpp_info.set_property("cmake_target_name","doctest::doctest")
        self.cpp_info.includedirs=["include"]
