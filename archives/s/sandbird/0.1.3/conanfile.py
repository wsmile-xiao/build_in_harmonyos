from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
import os


class SandbirdConan(ConanFile):
    name = "sandbird"
    version = "0.1.3"
    description = "A tiny embeddable asynchronous HTTP server in C"
    license = "MIT"
    homepage = "https://github.com/rxi/sandbird"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "conandata.yml"

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "cc")
        ar = compilers.get("ar", "ar")
        os.makedirs(self.build_folder, exist_ok=True)
        src = os.path.join(self.source_folder, "src", "sandbird.c")
        obj = os.path.join(self.build_folder, "sandbird.o")
        lib = os.path.join(self.build_folder, "libsandbird.a")
        self.run(f'"{cc}" -std=c89 -Wall -Wextra -Wpedantic -I"{os.path.dirname(src)}" -c "{src}" -o "{obj}"')
        self.run(f'"{ar}" rcs "{lib}" "{obj}"')
        # Compile the official examples as source-level API smoke checks. They
        # intentionally run a long-lived server and are not launched here.
        for example in ("hello", "input"):
            source = os.path.join(self.source_folder, "example", f"{example}.c")
            output = os.path.join(self.build_folder, example)
            self.run(f'"{cc}" -std=c89 -Wall -Wextra -Wpedantic -I"{os.path.dirname(src)}" "{source}" "{lib}" -o "{output}"')

    def package(self):
        copy(self, "libsandbird.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "sandbird.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sandbird"]
        self.cpp_info.set_property("cmake_file_name", "sandbird")
        self.cpp_info.set_property("cmake_target_name", "sandbird::sandbird")
