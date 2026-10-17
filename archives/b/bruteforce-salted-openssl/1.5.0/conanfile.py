"""Conan recipe — bruteforce-salted-openssl 1.5.0 (brute force cracker for openssl encrypted files)"""
import os
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain


class BruteforceSaltedOpensslConan(ConanFile):
    name = "bruteforce-salted-openssl"
    version = "1.5.0"
    package_type = "application"
    license = "GPL-3"
    description = "Brute force cracker for openssl encrypted files"
    homepage = "https://github.com/glv2/bruteforce-salted-openssl"
    settings = "os", "arch", "compiler", "build_type"

    def build_requirements(self):
        # GitHub archive 只有 configure.ac，无预生成 configure，须 autoreconf 自举；
        # 设备缺 automake，故显式引入（build profile 解析）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("openssl/3.5.6")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # GitHub archive 不含 configure（autoreconf 产物、不进版本库），先自举
        if not os.path.isfile(os.path.join(self.build_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # 修补必须在 autoreconf 之后：自举会重新生成 configure
        import glob
        for _cfg in glob.glob(os.path.join(self.build_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        # 传依赖路径 + LIBS：openssl 在 conan 里是静态 libcrypto.a，
        # AC_CHECK_LIB(crypto) 单带 -lcrypto 链接不过（pthread 符号悬空），
        # 须补 -lpthread -lm 才能把 EVP_get_cipherbyname 探测过。
        cc_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = cc_execs.get("c", "clang")
        dep_libs = []
        dep_incs = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if pf:
                dep_libs.append(os.path.join(pf, "lib"))
                dep_incs.append(os.path.join(pf, "include"))
        ldflags = " ".join(f"-L{d}" for d in dep_libs)
        cppflags = " ".join(f"-I{d}" for d in dep_incs)
        self.run(
            f"CC={cc} CFLAGS='-O2 -fPIC' "
            f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' LIBS='-lpthread -lm' "
            f"./configure",
            cwd=self.build_folder)
        self.run("make -j1", cwd=self.build_folder)

    def package(self):
        copy(self, "bruteforce-salted-openssl", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
