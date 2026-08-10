import os
from conan import ConanFile
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["clang"]
        clang = os.path.join(dep.package_folder, "bin", "clang")
        # R34 反空壳：必须真实调用被测包二进制（打包的 clang），而非仅检查存在。
        if not os.path.isfile(clang):
            raise Exception(f"clang binary not found at {clang}")
        if cross_building(self):
            # x86_64 CI worker 无法运行 aarch64 的 clang，仅验证二进制存在（W3 允许的妥协）
            self.output.info("cross-building：clang 二进制存在，跳过真实编译")
            return
        # 打包 clang 链接 test.c 时需要 libc/libunwind：LIBRARY_PATH 注入 SDK sysroot 库目录
        # （R33 合规：显式设置，非依赖未定义 shell 变量；包内 lib/ 也加入供 -L 解析）
        import glob
        _sysroots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"))
        _sysroot = _sysroots[-1] if _sysroots else ""
        _libpaths = [os.path.join(dep.package_folder, "lib")]
        if _sysroot:
            _sysroot_lib = os.path.join(_sysroot, "usr/lib/aarch64-linux-ohos")
            _libpaths.append(_sysroot_lib)
            # 打包 clang 无默认 sysroot → stdio.h 等头文件找不到：CPATH 注入 sysroot C 头
            # （对齐主配方 build() 的 CPATH 注入，R33 合规）
            _cpaths = [
                os.path.join(_sysroot, "usr/include/aarch64-linux-ohos"),
                os.path.join(_sysroot, "usr/include"),
            ]
            os.environ["CPATH"] = ":".join(_cpaths)
        os.environ["LIBRARY_PATH"] = ":".join(_libpaths)
        # 用打包的 clang 编译 test.c，校验编译器为 clang 20（__clang_major__ >= 20）
        self.run(f'"{clang}" -O1 test.c -o test_probe')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：跳过运行")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
