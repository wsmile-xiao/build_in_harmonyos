#!/usr/bin/env python3
"""Conan recipe for libogg 1.3.6."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get


class LiboggConan(ConanFile):
    name = "libogg"
    version = "1.3.6.1"
    description = "Ogg multimedia container library"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/ogg/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _sign_ohos_elf(self, path):
        tools = {}
        for name in ("llvm-readelf", "llvm-objcopy", "binary-sign-tool"):
            tools[name] = shutil.which(name) or os.path.join("/data/service/hnp/bin", name)
            if not os.path.isfile(tools[name]):
                raise ConanException(f"Required OHOS tool is missing: {name}")
        temporary = path + ".libogg-signed"
        subprocess.run(
            [tools["binary-sign-tool"], "sign", "-inFile", path,
             "-outFile", temporary, "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [tools["llvm-readelf"], "-SW", temporary], check=True,
            capture_output=True, text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = True
        tc.variables["INSTALL_DOCS"] = False
        tc.variables["INSTALL_PKG_CONFIG_MODULE"] = True
        tc.variables["INSTALL_CMAKE_PACKAGE_MODULE"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            suffix = ".exe" if self.settings.os == "Windows" else ""
            for name in ("test_bitwise", "test_framing"):
                executable = os.path.join(self.build_folder, name + suffix)
                if str(self.settings.os) == "OHOS":
                    self._sign_ohos_elf(executable)
                self.run(f'"{executable}"')

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared and can_run(self):
            self._sign_ohos_elf(os.path.join(self.package_folder, "lib", "libogg.so"))

        self._set_soname_and_resign(['libogg.so'])

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
        self.cpp_info.libs = ["ogg"]
        self.cpp_info.set_property("cmake_file_name", "Ogg")
        self.cpp_info.set_property("cmake_target_name", "Ogg::ogg")
        self.cpp_info.set_property("pkg_config_name", "ogg")
