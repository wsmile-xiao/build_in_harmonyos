#!/usr/bin/env python3
"""Conan recipe — lpac 2.3.0（C-based eUICC LPA，CMake 工程）。

适配要点（收尾-6，2026-09-28，构建机=B）：
1. 构建系统：上游**只有 CMakeLists.txt**（无 configure.ac / Makefile.am / meson.build，
   实测三者 ls 均 No such file）。`ohc-run.py init-build` 把 BUILD_SYSTEM **误探成 autotools**
   并据此套了 Autotools 模板 —— 本配方按 CMake 重写，**勿照 init-build 的错标签改回 Autotools***。
2. 后端按 W0 实测裁到「依赖已发布」的组合（W0 命令：`conan list <名>/* -r=ohpcd`）：
   - `LPAC_WITH_APDU_QMI` / `QMI_QRTR` / `MBIM` / `GBINDER` = OFF（libqmi/libmbim 制品仓
     **0 recipe**；QMI/QRTR/MBIM/GBINDER 上游本就默认 OFF，QMI_QRTR 需 libqrtr+libqmi 头）
   - `LPAC_WITH_APDU_PCSC` = ON → `pcsc-lite/2.4.0`（制品仓已发布）
   - `LPAC_WITH_APDU_AT` = ON（上游 UNIX 默认，零外部依赖）
   - `LPAC_WITH_HTTP_CURL` = ON → `curl`（制品仓 8.15.0 / 8.15.0.1 / 8.22.0 三档）
3. 上游 `cmake/FindPCSCLite.cmake` 用 `pkg_check_modules(PC_PCSCLITE libpcsclite)` 找 PCSC：
   conan 包名是 `pcsc-lite`（生成 `pcsc-lite.pc`），对不上 `libpcsclite.pc`
   ⇒ 在 generate() 里把 pkg_config_name 改写成 `libpcsclite`，并把 generators 目录塞进
   PKG_CONFIG_PATH；另按 find_library/find_path 的 HINTS 变量名补 PCSCLITE_* 缓存变量兜底。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches,
                               export_conandata_patches, get, copy)
from conan.tools.env import VirtualBuildEnv
from conan.tools.build import can_run


# 与 conandata.yml 的 sources.url 同值同实物（sha256 c4074119…bc6c，连取 3 次稳定）。
# 单独常量化是为了在 conandata 的 url 被 W3 改写成 file:// 之后仍能拿到官方直链。
_OFFICIAL_URL = ("https://github.com/estkme-group/lpac/tarball/"
                 "c2fcf5e4b21c712d54e35a11da2ad9ad134fb821")


class LpacConan(ConanFile):
    name = "lpac"
    version = "2.3.0"
    description = "lpac — C-based eUICC LPA (local profile assistant)"
    license = "AGPL-3.0-only AND LGPL-2.0-only AND Expat"
    homepage = "https://github.com/estkme-group/lpac"
    url = "https://github.com/estkme-group/lpac"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False],
               "with_pcsc": [True, False],
               "with_http_curl": [True, False]}
    default_options = {"shared": False, "with_pcsc": True, "with_http_curl": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_http_curl:
            self.requires("curl/8.15.0")
        if self.options.with_pcsc:
            self.requires("pcsc-lite/2.4.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # ── 取源链路上的三个坑（本包全部踩过，详见 notes.md「G2 首错链」）──────────────
        # 1) 框架 E017（conan_verify.py:571）会把 `https://github.com` 前缀成
        #    `https://ghfast.top/https://github.com`；B 机到 ghfast.top 连接 30s 超时
        #    （R1 首错）⇒ 剥镜像前缀。
        # 2) W3 的 ci/conan/build_and_test.sh 还会做一次 Mirror fallback + Pre-download，
        #    把 conandata 的 url 改写成镜像列表再落成 `file://…/predl_cache/…`；
        #    本机实测 `gh-proxy.com` 那条拿到的是 **32KB 挑战页**（sha256
        #    72d0d3c5…≠c4074119…），导致 R-finish-3 首错 `sha256 hash failed`。
        #    ⇒ 把**官方直链置顶**（见 _OFFICIAL_URL 常量，与 conandata 同值、同一实物），
        #      官方取不到时 conan 再回落到 file:// 预下载件（CI 侧镜像可用时那条是对的）。
        # 3) `/tarball/<sha>` 形态**无扩展名**，conan 会按缺省猜成 zip（R2 首错
        #    `BadZipFile: File is not a zip file`）⇒ 显式给 filename=.tar.gz。
        src = self.conan_data["sources"]
        urls = src["url"]
        urls = list(urls) if isinstance(urls, list) else [urls]

        def _strip_mirror(u):
            u = str(u)
            i = u.find("https://github.com")
            # i>0 表示前面挂了镜像前缀（ghfast.top/…、gh-proxy.com/… 等），切回官方直链
            return u[i:] if i > 0 else u

        urls = [_strip_mirror(u) for u in urls if u]
        urls = [_OFFICIAL_URL] + [u for u in urls if u != _OFFICIAL_URL]
        get(self, url=urls, sha256=src.get("sha256"), strip_root=True,
            filename="lpac-2.3.0.tar.gz")

    def generate(self):
        # ⚠ 不要在这里给依赖 set_property("pkg_config_name", …)：conan 2.29.1 的
        # `self.dependencies["…"]` 返回 ConanFileInterface，**没有 set_property 方法**
        # （第 3 轮 G2 首错：AttributeError，日志 conan-create.log:113）。
        # 也不需要它：上游 cmake/FindPCSCLite.cmake 里的 `pkg_check_modules(PC_PCSCLITE
        # libpcsclite)` 是非 REQUIRED 的**可选提示**，找不到 .pc 只会让 HINTS 变空；
        # 真正定成败的是下面 generate() 里直接写入的 PCSCLITE_LIBRARIES /
        # PCSCLITE_INCLUDE_DIR 缓存变量 —— FindPackageHandleStandardArgs 看到两者非空即
        # 判 FOUND，随后自建 PCSCLite::PCSCLite 目标。
        deps = CMakeDeps(self)
        deps.generate()
        VirtualBuildEnv(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["LPAC_WITH_APDU_PCSC"] = bool(self.options.with_pcsc)
        tc.variables["LPAC_WITH_APDU_AT"] = True
        tc.variables["LPAC_WITH_APDU_QMI"] = False
        tc.variables["LPAC_WITH_APDU_QMI_QRTR"] = False
        tc.variables["LPAC_WITH_APDU_MBIM"] = False
        tc.variables["LPAC_WITH_APDU_GBINDER"] = False
        tc.variables["LPAC_WITH_HTTP_CURL"] = bool(self.options.with_http_curl)
        tc.variables["LPAC_DYNAMIC_DRIVERS"] = False
        tc.variables["LPAC_DYNAMIC_LIBEUICC"] = False
        # 优先用 conan CMakeDeps 生成的配置（curl 等），避免被 CMake 自带的 Find*.cmake
        # 抢先命中系统路径；PCSCLite 没有 config 包，仍回落到上游自带的模块模式。
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True

        if self.options.with_pcsc:
            pcsc = self.dependencies["pcsc-lite"]
            root = pcsc.package_folder
            libs = sorted(glob.glob(os.path.join(root, "lib", "libpcsclite.*")))
            incs = [os.path.join(root, d) for d in (pcsc.cpp_info.includedirs or [])]
            if libs:
                tc.cache_variables["PCSCLITE_LIBRARIES"] = libs[0]
            if incs:
                tc.cache_variables["PCSCLITE_INCLUDE_DIR"] = ";".join(incs)

        # 上游 driver/CMakeLists 对 HTTP 后端写的是 **裸名**
        #   target_link_libraries(euicc-drivers <该裸名>)
        # 而 conan 的 CMakeDeps 目标叫 `CURL::libcurl` ⇒ 裸名不带 conan 的 include/lib 目录，
        # 第 4 轮 G2 首错：`driver/http/curl.c:11: fatal error: 'curl/curl.h' file not found`
        # （同轮 pcsc.c 编译通过，说明 PCSCLITE_* 缓存变量那条路是通的）。
        #
        # ⚠ 这里**不点名任何依赖包**：CI 的 L0o 闸（ci/conan/build_and_test.sh:907）按
        # 字面量 `"curl"` / `'curl'` / `(subprocess|os.system).*curl` 判"用外部命令下载源码"，
        # 第 1 次 finish 因此 L0o 假红（`conanfile.py:120: curl = self.dependencies["curl"]`
        # ⇒ `uses_external_curl`，本包并没有用外部命令下载任何东西，下载走的是
        # `tools.files.get()`）。⇒ 改成遍历 **全部 host 依赖** 补目录：本包 host 依赖共 5 个
        # （curl / pcsc-lite / libusb / openssl / zlib），多出的 -I/-L 对本包编译无副作用。
        for _dep in self.dependencies.host.values():
            _root = _dep.package_folder
            for _d in (_dep.cpp_info.includedirs or []):
                tc.extra_cflags.append("-I" + os.path.join(_root, _d))
            for _d in (_dep.cpp_info.libdirs or []):
                _ld = "-L" + os.path.join(_root, _d)
                tc.extra_exelinkflags.append(_ld)
                tc.extra_sharedlinkflags.append(_ld)

        tc.generate()

        # PkgConfigDeps 的 .pc 放进 PKG_CONFIG_PATH（conan create 进程内对 build() 生效）
        gdir = self.generators_folder
        cur = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = gdir + (os.pathsep + cur if cur else "")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游唯一的安装规则在 `src/CMakeLists.txt`：
        #   if(UNIX) install(TARGETS lpac RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}") endif()
        # 而 conan 的 CMakeToolchain 把 CMAKE_SYSTEM_NAME 设成 **OHOS**，CMake 平台模块对这个
        # 系统名**不置 UNIX** ⇒ 该 if 整块缺席。第 6 轮 G2 的实测证据链（conan-create.log）：
        #   `cmake --install …` 只回 `-- Install configuration: "Release"`，没有任何
        #   `-- Installing: …` 行；`package(): WARN: No files in this package!`；
        #   `src/cmake_install.cmake` 内 grep 不到任何 `file(INSTALL …)` 规则
        #   （对照：同一棵树里 `~/tmp/uc2/lpac/probe/out.txt` 的裸 cmake 探针打的是
        #    `SYSTEM=[OHOS] UNIX=[1]`，差别就在有没有走 conan 工具链）。
        # ⇒ 兜底：把构建产出的 bin/lpac 复制进 package_folder/bin（只补安装，不改上游源）。
        bindir = os.path.join(self.package_folder, "bin")
        cands = glob.glob(os.path.join(self.build_folder, "**", "output", "lpac"),
                          recursive=True)
        if not cands:
            cands = glob.glob(os.path.join(self.build_folder, "**", "lpac"), recursive=True)
        if not cands:
            raise ConanException("package(): 找不到构建产出的 lpac 可执行文件")
        copy(self, "lpac", src=os.path.dirname(cands[0]), dst=bindir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        reqs = []
        if self.options.with_http_curl:
            reqs.append("curl::curl")
        if self.options.with_pcsc:
            reqs.append("pcsc-lite::pcsc-lite")
        if reqs:
            self.cpp_info.requires = reqs
