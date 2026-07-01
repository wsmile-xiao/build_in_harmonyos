from conan import ConanFile
from conan.tools.files import collect_libs, get
import glob
import os
import shutil
from conan.tools.layout import basic_layout


class GlfwConan(ConanFile):
    name = "glfw"
    version = "3.4.6"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports = "scripts/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def generate(self):
        # 自定义构建命令自带工具链设置（如 build-ohos.sh 用 ohos.toolchain.cmake）；
        # conan 的 buildenv（CC/CXX、OHOS_NDK_HOME 等）通过 self.run(env="conanbuild") 注入。
        pass

    def build(self):
        # 库自带的专属构建（可产多个 .so、两趟链接等）。cwd=源码根，注入 conan buildenv。
        self.run(r"""bash build-ohos.sh""", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # 自定义构建产物落在源码树内（非标准 cmake install）：按 artifacts glob 收集所有 .so 到 lib/，
        # 保留 soname 软链；再收 headers_dir 头文件到 include/。
        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        for pattern in ['build-ohos/src/libglfw.so*', 'build-bridge/libglfw_bridge.so']:
            for path in glob.glob(os.path.join(self.source_folder, pattern)):
                dst = os.path.join(libdir, os.path.basename(path))
                if os.path.islink(path):
                    target = os.path.basename(os.readlink(path))
                    if not os.path.lexists(dst):
                        os.symlink(target, dst)
                else:
                    shutil.copy2(path, dst)
        headers_dir = "include"
        if headers_dir:
            src = os.path.join(self.source_folder, headers_dir)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(self.package_folder, "include"), dirs_exist_ok=True)
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 鸿蒙 PC 对 dlopen 的 .so 强制校验签名：未签名时 dlopen 不报错但 dlsym 全返回 NULL。
        # 复用 recipe 自带 scripts/sign-so.sh（DevEco binary-sign-tool 自签），对 package 内所有 .so 就地签。
        import glob
        import os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        sign = os.path.join(self.recipe_folder, "scripts", "sign-so.sh")
        quoted = " ".join('"{}"'.format(s) for s in sos)
        self.run('bash "{}" {}'.format(sign, quoted))

    def package_info(self):
        explicit_libs = []
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "glfw")
        self.cpp_info.set_property("cmake_target_name", "glfw::glfw")
        pkg = "" or self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        # 未显式给 --pkgconfig-name 时，从 install 出的 lib/pkgconfig/*.pc 取第一个文件名 stem。
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
