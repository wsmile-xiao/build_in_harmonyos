from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.files import get, apply_conandata_patches
from conan.tools.layout import basic_layout
import os
import re
import shutil

class LibMegapixelsConan(ConanFile):
    name = "libmegapixels"
    version = "0.2.3"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libconfig/1.7.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def _find_ar(self):
        ar = shutil.which("llvm-ar")
        if ar:
            return ar
        for c in [
            "/data/service/hnp/bin/llvm-ar",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ar",
            "/storage/Users/currentUser/usr/local/bin/llvm-ar",
        ]:
            if os.path.exists(c):
                return c
        return shutil.which("ar")

    def generate(self):
        tc = MesonToolchain(self)

        dep = self.dependencies["libconfig"]
        pkg_path = os.path.join(dep.package_folder, "lib", "pkgconfig").replace("\\", "/")
        inc_dir = os.path.join(dep.package_folder, "include").replace("\\", "/")
        lib_dir = os.path.join(dep.package_folder, "lib").replace("\\", "/")

        tc.pkg_config_path = pkg_path
        self.output.info(f"pkg_config_path={pkg_path}")
        self.output.info(f"inc_dir={inc_dir}, lib_dir={lib_dir}")

        tc.generate()

        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.exists(native_file):
            return

        with open(native_file, "r") as f:
            content = f.read()

        # 1. 修复 ar 路径
        ar_path = self._find_ar()
        if ar_path:
            if re.search(r'^ar\s*=', content, flags=re.MULTILINE):
                content = re.sub(r'^ar\s*=\s*.*$', f'ar = {ar_path!r}', content, flags=re.MULTILINE)
            else:
                content = re.sub(r'(\[binaries\]\n)', rf'\1ar = {ar_path!r}\n', content, count=1)

        # 2. 注入 libconfig 的 include 和 lib 路径到 c_args/c_link_args
        c_args_line = f"c_args = ['-I{inc_dir}']"
        c_link_args_line = f"c_link_args = ['-L{lib_dir}', '-lconfig']"

        if '[built-in options]' in content:
            if re.search(r'^c_args\s*=', content, flags=re.MULTILINE):
                content = re.sub(r'^c_args\s*=\s*.*$', c_args_line, content, flags=re.MULTILINE)
            else:
                content = content.replace('[built-in options]', f'[built-in options]\n{c_args_line}', 1)

            if re.search(r'^c_link_args\s*=', content, flags=re.MULTILINE):
                content = re.sub(r'^c_link_args\s*=\s*.*$', c_link_args_line, content, flags=re.MULTILINE)
            else:
                content = content.replace('[built-in options]', f'[built-in options]\n{c_link_args_line}', 1)
        else:
            content += f'\n[built-in options]\n{c_args_line}\n{c_link_args_line}\n'

        with open(native_file, "w") as f:
            f.write(content)
        self.output.info(f"Injected c_args: {c_args_line}")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()

    def package_info(self):
        self.cpp_info.libs = ["megapixels"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libmegapixels")
        self.cpp_info.set_property("cmake_target_name", "libmegapixels::libmegapixels")
        self.cpp_info.set_property("pkg_config_name", "libmegapixels")
