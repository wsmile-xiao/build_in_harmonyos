from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, get
import os


class SkiparrayConan(ConanFile):
    name = "skiparray"
    version = "0.2.0"
    description = "An unrolled skiplist associative array for C"
    license = "ISC"
    homepage = "https://github.com/silentbicycle/skiparray"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False], "upstream_tests": [True, False]}
    default_options = {"fPIC": True, "upstream_tests": False}
    exports_sources = "conandata.yml"

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        if self.options.upstream_tests:
            # 上游 Greatest 套件的 test-only 依赖，仅在验证构建时进入依赖图，
            # 不进入默认生产包；生产库本身零外部依赖。
            self.requires("theft/0.4.5")

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "cc")
        ar = compilers.get("ar", "ar")
        include = os.path.join(self.source_folder, "include")
        src = os.path.join(self.source_folder, "src")
        os.makedirs(self.build_folder, exist_ok=True)
        pic = " -fPIC" if self.options.fPIC else ""
        objects = []
        for name in ("skiparray", "skiparray_fold", "skiparray_hof"):
            source = os.path.join(src, f"{name}.c")
            obj = os.path.join(self.build_folder, f"{name}.o")
            self.run(f"\"{cc}\" -std=c99 -O2 -Wall -Wextra -pedantic{pic} "
                     f"-I\"{include}\" -I\"{src}\" -c \"{source}\" -o \"{obj}\"")
            objects.append(obj)
        library = os.path.join(self.build_folder, "libskiparray.a")
        self.run(f"\"{ar}\" rcs \"{library}\" " + " ".join(f"\"{obj}\"" for obj in objects))

        if not self.options.upstream_tests:
            return
        if not can_run(self):
            self.output.info("upstream_tests=True 但为交叉编译，跳过上游套件执行")
            return

        # 按 upstream Makefile 的 TEST_OBJS 集合编译 Greatest 套件；
        # pkg-config libtheft 用 Conan 安装的 theft 包目录显式替换。
        vendor = os.path.join(self.source_folder, "vendor")
        theft = self.dependencies["theft"]
        t_inc = theft.cpp_info.includedirs[0]
        t_lib = theft.cpp_info.libdirs[0]
        if not os.path.isabs(t_inc):
            t_inc = os.path.join(theft.package_folder, t_inc)
        if not os.path.isabs(t_lib):
            t_lib = os.path.join(theft.package_folder, t_lib)
        test_names = (
            "test_skiparray",
            "test_skiparray_basic",
            "test_skiparray_builder",
            "test_skiparray_fold",
            "test_skiparray_hof",
            "test_skiparray_prop",
            "test_skiparray_integration",
            "test_skiparray_invariants",
            "type_info_skiparray_operations",
        )
        test_objs = list(objects)
        for name in test_names:
            source = os.path.join(self.source_folder, "test", f"{name}.c")
            obj = os.path.join(self.build_folder, f"{name}.o")
            self.run(f"\"{cc}\" -std=c99 -O2 -Wall -Wextra -pedantic "
                     f"-I\"{include}\" -I\"{src}\" -I\"{vendor}\" -I\"{t_inc}\" "
                     f"-c \"{source}\" -o \"{obj}\"")
            test_objs.append(obj)
        test_bin = os.path.join(self.build_folder, "test_skiparray")
        self.run(f"\"{cc}\" -o \"{test_bin}\" "
                 + " ".join(f"\"{obj}\"" for obj in test_objs)
                 + f" -L\"{t_lib}\" -ltheft -lm")
        self.run(f"\"{test_bin}\"", cwd=self.build_folder)

    def package(self):
        copy(self, "libskiparray.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "skiparray.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["skiparray"]
        self.cpp_info.set_property("cmake_file_name", "skiparray")
        self.cpp_info.set_property("cmake_target_name", "skiparray::skiparray")
