from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os

class MimallocConan(ConanFile):
    name = "mimalloc"
    version = "3.2.8.1"
    package_type = "library"
    license = "MIT"
    homepage = "https://github.com/microsoft/mimalloc"
    url = "https://github.com/microsoft/mimalloc"
    description = "mimalloc is a compact general purpose allocator"
    topics = ("allocator", "memory", "performance")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    generators = "CMakeDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["MI_OVERRIDE"] = "OFF"
        tc.cache_variables["MI_SECURE"] = "ON"
        # 上游测试套件在 OHOS 平台可用（本地 ctest 验：test-api/test-api-fill/test-stress/test-stress-dynamic 全过 4/4）
        tc.cache_variables["MI_BUILD_TESTS"] = "ON"
        tc.cache_variables["MI_LIBC_MUSL"] = "ON" if self.settings.os == "OHOS" else "OFF"
        tc.cache_variables["MI_DEBUG"] = "ON" if self.settings.build_type == "Debug" else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 跑上游 ctest 套件（MI_BUILD_TESTS=ON）：test-api/test-api-fill/test-stress/test-stress-dynamic
        cmake.test()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        self._set_soname_and_resign(['libmimalloc-secure.so'])

    def _set_soname_and_resign(self, sonames):
        """给缺 SONAME 的 .so 补上 SONAME 并**重新签名**。

        为何需要：本包产物无 DT_SONAME。后果不在本包，而在**下游** ——
        CMake 默认按完整路径链接无 SONAME 的库，于是把构建机的 conan cache
        绝对路径写进下游的 DT_NEEDED，换机器即无法加载。
        制品仓已实测到三个因此损坏的包（fontconfig / poppler / tbb）。

        为何用 patchelf 而不改构建系统：本包的 .so 本来就是**无版本名**
        （libfoo.so，没有 libfoo.so.X 实体），SONAME 设成文件名本身即完全正确，
        与上游本意一致；换构建方式的收益一样而风险更高。
        （若包里存在版本化实体文件，则说明上游有 SOVERSION 意图，
          那种情况应改构建方式而非 patchelf —— 见 skill 的 references/soname-repair.md）

        为何必须重签：改动 ELF 会破坏链接器自签，鸿蒙 PC 的 XPM 会拒绝 dlopen
        （报 Permission denied / Operation not permitted）。
        顺序必须是 patchelf → 剥旧签名段 → 自签。
        """
        import os
        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for name in sonames:
            f = os.path.join(self.package_folder, "lib", name)
            if not os.path.isfile(f) or os.path.islink(f):
                self.output.warning("补 SONAME：找不到 %s，跳过" % f)
                continue
            self.run('{pe} --set-soname "{n}" "{f}"'.format(pe=patchelf, n=name, f=f))
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=f))
            self.output.info("已设 SONAME=%s 并重签" % name)

    def package_info(self):
        # mimalloc with MI_SECURE=ON produces libmimalloc-secure
        self.cpp_info.libs = ["mimalloc-secure"]
        # Headers are installed to include/mimalloc-<version>/ by upstream CMake
        self.cpp_info.includedirs = ["include/mimalloc-3.2"]
        if self.settings.os in ["Linux", "OHOS"]:
            self.cpp_info.system_libs = ["pthread", "dl"]
