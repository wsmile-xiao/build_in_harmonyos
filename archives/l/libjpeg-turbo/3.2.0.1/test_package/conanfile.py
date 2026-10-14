import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libjpeg-turbo"].cpp_info
        includes = " ".join('-I"{}"'.format(path) for path in dep.includedirs)
        libdir = dep.libdirs[0]
        cc = os.environ.get("CC", "clang")
        self.run('{} test.c -o test_consumer {} "{}/libturbojpeg.so" '
                 '-Wl,-rpath,"{}"'.format(cc, includes, libdir, libdir))
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self.run('{} test_ohos.c -o test_ohos {} "{}/libjpeg.so" '
                     '-Wl,-rpath,"{}"'.format(cc, includes, libdir, libdir))

    def test(self):
        if cross_building(self):
            raise RuntimeError("These functional tests require a native HarmonyOS runner")
        self.run("./test_consumer", env="conanrun")
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self.run("./test_ohos", env="conanrun")
