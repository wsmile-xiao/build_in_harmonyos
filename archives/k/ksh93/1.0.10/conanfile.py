from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.errors import ConanException
import os

class Ksh93Conan(ConanFile):
    name = "ksh93"
    version = "1.0.10"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        src = self.conan_data["sources"][0]
        get(self, **src, filename="ksh93-1.0.10.tar.gz", strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        ccflags = "-O2 -fPIC"
        ldflags = ""
        # HarmonyOS 禁止第三方应用创建符号链接，AST 构建动态库时依赖 ln -s
        # 设置 AST_NO_DYLIB=y 跳过动态库构建，只编译静态链接的 ksh
        self.run(
            f'AST_NO_DYLIB=y bash bin/package quiet make '
            f'CCFLAGS="{ccflags}" LDFLAGS="{ldflags}"'
        )

    def _hosttype_dir(self):
        arch_dir = os.path.join(self.build_folder, "arch")
        if not os.path.exists(arch_dir):
            raise ConanException("Build output directory 'arch' not found")
        hosttypes = [d for d in os.listdir(arch_dir)
                     if os.path.isdir(os.path.join(arch_dir, d))]
        if not hosttypes:
            raise ConanException("No hosttype directory found under 'arch'")
        return os.path.join(arch_dir, hosttypes[0])

    def package(self):
        hosttype_dir = self._hosttype_dir()
        bin_dir = os.path.join(hosttype_dir, "bin")
        if os.path.exists(bin_dir):
            copy(self, "*", src=bin_dir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def test(self):
        hosttype_dir = self._hosttype_dir()
        ksh_bin = os.path.join(hosttype_dir, "bin", "ksh")
        shcomp_bin = os.path.join(hosttype_dir, "bin", "shcomp")

        if not os.path.exists(ksh_bin):
            raise ConanException(f"ksh not found at {ksh_bin}")

        env_prefix = f'SHELL="{ksh_bin}" '
        if os.path.exists(shcomp_bin):
            env_prefix += f'SHCOMP="{shcomp_bin}" '

        self.run(f'{env_prefix}bash bin/package quiet test', cwd=self.build_folder)
