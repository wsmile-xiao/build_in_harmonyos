#!/usr/bin/env python3
"""Conan recipe for blepvco 0.1.0 — raw GNU Makefile LADSPA plugin set.

blepvco builds three hard-sync minBLEP oscillator LADSPA plugins into a
single dlopen-able ``blepvco.so``. The upstream Makefile has no configure
step; objects compile through make's built-in rules using $(CC)/$(CXX) and
the upstream ``CPPFLAGS += -I. -fPIC -D_REENTRANT -Wall -O3``. The only
source adaptation is a minimal portability patch replacing the hardcoded
``g++`` linker invocation with overridable ``$(CXX)``; the compilers are
injected from the Conan profile (R33: never bare ${CC}/${CXX}).
"""
import json
import os
import shutil
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class BlepvcoConan(ConanFile):
    name = "blepvco"
    version = "0.1.0"
    description = (
        "LADSPA hard-sync minBLEP oscillator plugins "
        "(Sync-Saw/Rect/Tri VCO)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.smbolton.com/linux.html"
    url = ""
    topics = ("ladspa", "audio", "plugin", "synth", "oscillator")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # library 包必须声明 shared 选项（conan 2 校验；avldrums.lv2 同款先例）。
    # 产物本身就是宿主 dlopen 的共享对象，默认 shared。
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一依赖：ladspa.h API 头文件（制品仓已发布，R27/R36）
        self.requires("ladspa-sdk/1.17")

    def layout(self):
        basic_layout(self)

    def generate(self):
        # profile [buildenv]（PATH、OHOS lld 所需的 LD_LIBRARY_PATH）只有在
        # VirtualBuildEnv 真正生成后才会进入 conanbuild；
        # self.run(env="conanbuild") 对缺失脚本会静默跳过（Conan 2.29 行为）
        VirtualBuildEnv(self).generate()

    def source(self):
        data = self.conan_data["sources"]
        try:
            get(self, **data, strip_root=True)
            return
        except ConanException as exc:
            # 上游服务器（Apache AddEncoding x-gzip）对 .tar.gz 响应附带
            # Content-Encoding: x-gzip：urllib3 按声明透明解压，读到的
            # 解压后字节数与 Content-Length（压缩尺寸）不一致，conan 下载器
            # 误判"传输中断"。urllib 不做 Content-Encoding 解码，原始字节
            # 落地即与 Content-Length/sha256 一致；哈希校验兜底完整性。
            self.output.warning(
                "conan downloader failed ({}); retrying with urllib "
                "(server responds Content-Encoding: x-gzip)".format(exc)
            )
        filename = data.get("filename", "blepvco-0.1.0.tar.gz")
        archive = os.path.join(self.source_folder, filename)
        with urllib.request.urlopen(data["url"], timeout=120) as resp:
            payload = resp.read()
        with open(archive, "wb") as handler:
            handler.write(payload)
        check_sha256(self, archive, data["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)
        os.remove(archive)

    def _compiler(self, kind, fallback):
        """解析工具链编译器：优先 profile conf，其次 PATH，最后 HNP 常见位置。
        profile 里的绝对路径在构建环境中可能是死符号链接，仅在其为真实
        可执行文件时使用（ladspa-sdk 同款防护）。"""
        ce = self.conf.get("tools.build:compiler_executables", default=None)
        path = None
        if ce:
            try:
                data = json.loads(ce) if isinstance(ce, str) else ce
                path = data.get(kind)
            except (ValueError, AttributeError):
                path = None
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        return shutil.which("clang++" if kind == "cpp" else "clang") or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "/data/service/hnp/bin/clang")
        cxx = self._compiler("cpp", "/data/service/hnp/bin/clang++")
        # 原生 make 不消费依赖的 cpp_info：ladspa.h 的 include 路径须显式注入。
        # 经 CFLAGS/CXXFLAGS 传递（内建编译规则均含 $(CPPFLAGS) $(CFLAGS/CXXFLAGS)），
        # 与上游 Makefile 的 CPPFLAGS += ... 追加语义无冲突。
        sdk_inc = os.path.join(
            self.dependencies["ladspa-sdk"].package_folder, "include")
        # 上游 Makefile 无 configure：目标文件经 make 内建规则（$(CC)/$(CXX)
        # + 上游 CPPFLAGS += -I. -fPIC -D_REENTRANT -Wall -O3）编译，链接规则
        # 已由补丁改为 $(CXX)。配方只覆盖编译器变量。R9：固定 -j1。
        self.run(
            (
                'make -C "{src}" -j1 CC="{cc}" CXX="{cxx}" '
                'CFLAGS="-I{inc}" CXXFLAGS="-I{inc}"'
            ).format(src=self.source_folder, cc=cc, cxx=cxx, inc=sdk_inc),
            env="conanbuild",
        )
        self.output.info("blepvco.so build completed")

    def package(self):
        # LADSPA 插件目录层级：插件由宿主 dlopen，安装到 lib/ladspa/
        copy(
            self,
            "blepvco.so",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib", "ladspa"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # 插件由宿主 dlopen 加载，消费方既不链接也不 include：
        # 不导出头文件/库，仅暴露插件目录作为资源目录
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib/ladspa"]
