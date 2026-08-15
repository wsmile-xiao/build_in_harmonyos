#!/usr/bin/env python3
"""Conan recipe — luvit 2.18.1 (Lua runtime, Node.js-style)

luvit 是 Lua 异步运行时(元包): 本体是 Lua 代码(luvit/ 源码目录, deps/ 完整),
运行依赖 luvi(C 运行时, 自包含源码含 LuaJIT/libuv/lpeg/pcre2/lua-openssl/miniz)。

OHOS 适配要点:
- 不构建 lit/luvit 自执行 zip 二进制: luvi make 产出的自执行文件在 HMDFS 沙箱
  执行报 "Operation not permitted"(实测), 改用 termux 同款方案——
  bin/luvit 启动脚本 `exec luvi <prefix>/share/luvit -- "$@"`,
  luvit 源码目录作为 luvi 应用直接运行(实测 `luvi <luvit-src> -- --version` OK)。
- luvi-source.tar.gz 自包含全部 deps, 内嵌 libuv 1.48 需鸿蒙 patch
  (0001-ohos-libuv.patch: CPU 亲和性 API/mmsg 缺失 + CMake Linux 判定, 同
  main 仓库 libuv/1.52.1 的 4 个 patch 思路);
- luvi 完整构建需要 OpenSSL(lua-openssl 绑定): 用制品仓 openssl/3.5.6.1
  二进制注入(WithSharedOpenSSL=ON, find_package 而非 FetchContent 自下载)。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.build import cross_building


class LuvitConan(ConanFile):
    name = "luvit"
    version = "2.18.1"
    description = "Luvit — Asynchronous I/O for Lua (Node.js-style runtime)"
    license = "Apache-2.0"
    homepage = "https://luvit.io/"
    url = "https://github.com/luvit/luvit"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # conandata.yml 的 patches 由 export_conandata_patches 导出到
        # build 目录(0001-ohos-libuv.patch), build() 中应用到 luvi-src。
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def requirements(self):
        # luvi 完整构建的 lua-openssl 绑定需要 OpenSSL(制品仓已发布 armv8 二进制)
        self.requires("openssl/3.5.6.1")

    def layout(self):
        pass

    def source(self):
        # 1) luvit 本体(Lua 源码目录)
        get(self, **self.conan_data["sources"], strip_root=True)
        # 2) luvi 自包含源码(含 LuaJIT/libuv/lpeg/pcre2/lua-openssl/miniz)
        import os
        os.makedirs(os.path.join(self.source_folder, "luvi-src"), exist_ok=True)
        get(self, **self.conan_data["luvi_source"],
            destination=os.path.join(self.source_folder, "luvi-src"), strip_root=True)

    def _build_luvi(self):
        import os
        luvit_root = self.source_folder
        luvi_root = os.path.join(luvit_root, "luvi-src")
        self.output.info(f"luvi root: {luvi_root}")

        # 应用 libuv 鸿蒙 patch(内嵌 libuv 1.48: CPU 亲和性/mmsg + CMake Linux)
        # patch 在 conandata.yml 引用, 由 export_sources 导出后 apply。
        # apply_conandata_patches 默认在 source_folder 应用, 但 luvi 在子目录 →
        # 手动 cd 到 luvi-src 应用。
        self.run(f"cd {luvi_root} && patch -p1 < {os.path.join(luvit_root, 'patches', '0001-ohos-libuv.patch')}",
                 env="conanbuild")

        # openssl 依赖路径(制品仓二进制)
        import shlex
        openssl_dep = self.dependencies["openssl"]
        openssl_root = openssl_dep.package_folder
        self.output.info(f"openssl root: {openssl_root}")

        # 构建 luvi(完整模块: OpenSSL/PCRE2/LPEG/ZLIB)
        cmake_args = [
            "-DCMAKE_BUILD_TYPE=Release",
            "-DWITH_LUA_ENGINE=LuaJIT",
            "-DWithOpenSSL=ON",
            "-DWithSharedOpenSSL=ON",
            "-DWithPCRE2=ON",
            "-DWithLPEG=ON",
            "-DWithZLIB=ON",
            "-DWithSharedLibluv=OFF",
            f"-DOPENSSL_ROOT_DIR={openssl_root}",
            f"-DOPENSSL_INCLUDE_DIR={openssl_root}/include",
            f"-DOPENSSL_SSL_LIBRARY={openssl_root}/lib/libssl.a",
            f"-DOPENSSL_CRYPTO_LIBRARY={openssl_root}/lib/libcrypto.a",
        ]
        args = " ".join(shlex.quote(a) for a in cmake_args)
        self.run(f"cd {luvi_root} && cmake . -B build-ohos {args}", env="conanbuild")
        self.run(f"cd {luvi_root} && cmake --build build-ohos -j8", env="conanbuild")

    def build(self):
        self._build_luvi()

    def package(self):
        import os
        luvi_root = os.path.join(self.source_folder, "luvi-src")

        # 1) luvi 二进制 → bin/luvi
        copy(self, "luvi", os.path.join(luvi_root, "build-ohos"),
             os.path.join(self.package_folder, "bin"))

        # 2) luvit 源码目录 → share/luvit(Lua 应用, luvi 直接运行)
        copy(self, "*", self.source_folder,
             os.path.join(self.package_folder, "share", "luvit"),
             excludes=("luvi-src", "patches"))

        # 3) bin/luvit 启动脚本(termux 同款: exec luvi <share>/luvit -- "$@")
        launcher = os.path.join(self.package_folder, "bin", "luvit")
        with open(launcher, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write("# luvit launcher — run luvit source dir via luvi\n")
            f.write('exec "$(dirname "$0")/luvi" "$(dirname "$0")/../share/luvit" -- "$@"\n')
        os.chmod(launcher, 0o755)

    def package_info(self):
        self.output.info("luvit packaged: bin/luvi + bin/luvit(launcher) + share/luvit")
        self.cpp_info.bindirs = ["bin"]
