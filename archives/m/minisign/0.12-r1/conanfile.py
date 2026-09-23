#!/usr/bin/env python3
"""Conan recipe — minisign 0.12-r1 (CMake, application).

minisign signs files and verifies signatures using the Ed25519 public-key
signature system.  Builds as a command-line tool (application package) and
links against libsodium.

libsodium/1.0.22 已发布到 ohpcd 制品仓（含 OHOS aarch64 静态二进制，
conan install --build=never 实测可解析），按 R36 直接声明 conan 依赖。
上游 CMakeLists.txt 通过 pkg-config + find_path/find_library 定位
libsodium；OHOS 交叉环境无系统 libsodium 的 .pc（E001/E075），故补丁
0001 将 find_package(PkgConfig) 放宽为可选，并在 generate() 里把依赖包
的 include/lib 路径直接注入 SODIUM_INCLUDE_DIR / SODIUM_LIBRARY 缓存
变量 —— find_path/find_library 见缓存变量已存在即跳过搜索，链路确定。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class MinisignConan(ConanFile):
    name = "minisign"
    version = "0.12-r1"
    description = "A dead simple tool to sign files and verify signatures"
    license = "ISC"
    homepage = "https://jedisct1.github.io/minisign/"
    url = "https://github.com/jedisct1/minisign"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libsodium/1.0.22")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # libsodium 1.0.22 包为纯静态（配方 --disable-shared --enable-static），
        # 直接把包内路径注入上游 CMakeLists 的缓存变量（find_path/find_library
        # 已有缓存值时不再搜索，pkg_check_modules 的 HINTS 为空也不影响）。
        sodium = self.dependencies["libsodium"]
        inc_dir = sodium.cpp_info.includedirs[0]
        lib_file = os.path.join(sodium.cpp_info.libdirs[0], "libsodium.a")
        if not os.path.isfile(lib_file):
            lib_file = os.path.join(sodium.cpp_info.libdirs[0], "libsodium.so")
        tc.variables["SODIUM_INCLUDE_DIR"] = inc_dir
        tc.variables["SODIUM_LIBRARY"] = lib_file
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游无测试套件（审计见 test_package/MANIFEST.yml），不调用 cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # E077: OHOS 内核要求可执行 ELF 含有效 .codesign 签名段；上游 CMakeLists 的
        # POST_BUILD strip（及 install 改写）会使链接期自签失效，内核拒绝执行
        # （Operation not permitted，chmod 无法恢复）。按 acme/acsccid/ad2vcf 先例
        # 剥旧签名段后 binary-sign-tool -selfSign 1 重签并恢复 755。
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in sorted(os.listdir(bin_dir)):
                self._sign_elf(os.path.join(bin_dir, name))

    def _sign_elf(self, path):
        """E077: 重新签名打包的可执行 ELF（剥旧 .codesign → sign → chmod 755）。"""
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        try:
            if open(path, "rb").read(4) != b"\x7fELF":
                return
        except OSError:
            return
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool 不可用，跳过 ELF 重签: %s" % path)
            return
        if os.path.isfile(objcopy):
            self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, path),
                     quiet=True)
        tmp = path + ".signed"
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, path, tmp),
                 quiet=True)
        if os.path.isfile(tmp):
            os.replace(tmp, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
