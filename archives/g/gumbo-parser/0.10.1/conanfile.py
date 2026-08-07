import glob
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class GumboParserConan(ConanFile):
    name = "gumbo-parser"
    version = "0.10.1"
    description = "An HTML5 parsing library in pure C99"
    license = "Apache-2.0"
    homepage = "https://github.com/google/gumbo-parser"
    url = "https://github.com/google/gumbo-parser"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["gumbo"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["gtest"],
            destination=os.path.join(self.source_folder, "gtest"),
            strip_root=True,
        )

    def _tools(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must define c and cpp"
            )

        compiler_dir = os.path.dirname(cc)
        ar = compilers.get("ar") or os.path.join(compiler_dir, "llvm-ar")
        if not os.path.isfile(ar):
            raise ConanInvalidConfiguration("OHOS llvm-ar was not found")
        return cc, cxx, ar

    def _build_type_flags(self):
        build_type = str(self.settings.build_type)
        flags = {
            "Debug": ["-O0", "-g"],
            "Release": ["-O2"],
            "RelWithDebInfo": ["-O2", "-g"],
            "MinSizeRel": ["-Os"],
        }.get(build_type)
        if flags is None:
            raise ConanInvalidConfiguration(f"Unsupported build type: {build_type}")
        return flags

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported operating system: {self.settings.os}"
            )

        cc, cxx, ar = self._tools()
        build_type_flags = self._build_type_flags()
        source_dir = self.source_folder
        build_dir = self.build_folder
        object_dir = os.path.join(build_dir, "objects")
        os.makedirs(object_dir, exist_ok=True)

        c_sources = sorted(glob.glob(os.path.join(source_dir, "src", "*.c")))
        if not c_sources:
            raise ConanInvalidConfiguration("Gumbo C sources were not found")

        object_files = []
        for source in c_sources:
            obj = os.path.join(object_dir, f"{os.path.basename(source)}.o")
            self.run(
                " ".join(
                    [
                        shlex.quote(cc),
                        "-std=c99",
                        *build_type_flags,
                        "-fPIC",
                        f"-I{shlex.quote(os.path.join(source_dir, 'src'))}",
                        "-c",
                        shlex.quote(source),
                        "-o",
                        shlex.quote(obj),
                    ]
                )
            )
            object_files.append(obj)

        library = os.path.join(build_dir, "libgumbo.a")
        self.run(
            " ".join(
                [shlex.quote(ar), "rcs", shlex.quote(library)]
                + [shlex.quote(obj) for obj in object_files]
            )
        )

        test_sources = sorted(glob.glob(os.path.join(source_dir, "tests", "*.cc")))
        if not test_sources:
            raise ConanInvalidConfiguration("Gumbo GoogleTest sources were not found")
        test_binary = os.path.join(build_dir, "gumbo_test")
        self.run(
            " ".join(
                [
                    shlex.quote(cxx),
                    "-std=c++11",
                    *build_type_flags,
                    "-pthread",
                    "-DGTEST_USE_OWN_TR1_TUPLE=1",
                    f"-I{shlex.quote(os.path.join(source_dir, 'gtest', 'include'))}",
                    f"-I{shlex.quote(os.path.join(source_dir, 'gtest'))}",
                    f"-I{shlex.quote(source_dir)}",
                    f"-I{shlex.quote(os.path.join(source_dir, 'src'))}",
                    shlex.quote(os.path.join(source_dir, "gtest", "src", "gtest-all.cc")),
                    shlex.quote(os.path.join(source_dir, "gtest", "src", "gtest_main.cc")),
                ]
                + [shlex.quote(source) for source in test_sources]
                + [shlex.quote(library), "-o", shlex.quote(test_binary)]
            )
        )
        self.run(f"{shlex.quote(test_binary)} --gtest_color=no")

    def package(self):
        copy(self, "libgumbo.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "gumbo.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "tag_enum.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["gumbo"]
        self.cpp_info.set_property("cmake_file_name", "gumbo")
        self.cpp_info.set_property("cmake_target_name", "gumbo::gumbo")
        self.cpp_info.set_property("pkg_config_name", "gumbo")
