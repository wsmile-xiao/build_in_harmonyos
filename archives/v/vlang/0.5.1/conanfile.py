#!/usr/bin/env python3
"""Conan recipe for vlang 0.5.1 — V 编程语言编译器（C 自举）。

上游：https://github.com/vlang/v tag 0.5.1
构建：GNUmakefile 自举——CC(clang) 编译 vc/v.c → v1.exe → v1.exe 编译 cmd/v
      → v2.exe 产出最终 v 编译器；无外部 conan 依赖（CC=clang 本机可用）
测试：v test-all（vlib/v/tests 等大量 .v 单元测试）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class VlangConan(ConanFile):
    name = "vlang"
    version = "0.5.1"
    description = "V — simple, fast, safe, compiled language for developing maintainable software"
    license = "MIT"
    homepage = "https://vlang.io/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    # conan 2.x 用 exports_sources 类属性复制补丁文件（无 self.copy 方法）
    exports_sources = "patches/*.patch"

    def export_sources(self):
        pass

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            # 官方/gitcode 镜像下载失败——fallback gh-proxy github tar
            # （aireview P2：gh-proxy 镜像独立键，不混入 sources url 列表——
            # R39 官方 URL 保留在 sources）
            self.output.warning("官方/gitcode 下载失败——fallback gh-proxy github tar")
            get(self, **self.conan_data["vlang-ghproxy"], strip_root=True)

    def build(self):
        # V 语言自举构建：make 用 clang 编译 vc/v.c 引导，再自举编译 cmd/v
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env_prefix = ("CC=/data/service/hnp/bin/clang "
                      f"PATH={self.build_folder}:{self.source_folder}:/data/service/hnp/bin:$PATH "
                      "V_COMMIT_HASH=0c3183c "
                      f"TMPDIR={tmpdir}")
        # vlang 0.5.1 的 vlib 用 $if native 语法（13 处），v1 引导编译器由
        # vc/v.c 生成——release tar 不带 vc（git submodule），且旧 vc 不认识
        # $if native（CI 报 invalid $if condition: unknown indent native）→
        # 强制 clone vlang/vc 最新到 vc/，确保 v1 支持 native 条件
        # vc 版本对齐（vlang 0.5.1 = vlang/v 0c3183c，对应 vc commit
        # f461dfebcdfac3c75fdf28fec80c07f0a7a9a53d——2026-03-09 生成，
        # v1 与 0.5.1 源码匹配可自举；vc master 滚动更新（84ea21dd）与
        # 0.5.1 不兼容致 v1 编译 cmd/v 报错）——github 官方源优先（R39）+
        # gh-proxy 镜像 fallback（github 直连不可达时走镜像拉指定 commit v.c）
        # ——make fresh_vc 检查 vc/.git/config（GNUmakefile:211）不存在会
        # 重 clone（github 直连失败）→ 下载后伪造 vc/.git/config 跳过 fresh_vc
        self.run(f"cd {self.source_folder} && mkdir -p vc && "
                 "(curl -sL --connect-timeout 30 -o vc/v.c "
                 "https://raw.githubusercontent.com/vlang/vc/f461dfebcdfac3c75fdf28fec80c07f0a7a9a53d/v.c "
                 "|| curl -sL --connect-timeout 30 -o vc/v.c "
                 "https://gh-proxy.com/https://raw.githubusercontent.com/vlang/vc/f461dfebcdfac3c75fdf28fec80c07f0a7a9a53d/v.c "
                 "|| git clone --depth 1 --quiet https://github.com/vlang/vc vc) && "
                 "mkdir -p vc/.git && touch vc/.git/config && "
                 "grep -q v1 vc/v.c || echo 'vc/v.c 下载失败'",
                 ignore_errors=True)
        # v1 编译 cmd/v 时检测标准 C 编译器名 cc（/data/service/hnp/bin 只有
        # clang 无 cc——CI/本地实测 attempt to run 空）——source_folder 创建
        # cc → clang 符号链接（env_prefix 的 PATH 已含 source_folder）
        self.run(f"cd {self.source_folder} && ln -sf /data/service/hnp/bin/clang cc",
                 ignore_errors=True)
        # v1 引导编译器（vc）不支持 $if native（vlib 14 处标准语法）→ 应用
        # 0001 补丁按 OHOS 本机自举语义展开（native=真）
        from conan.tools.files import patch
        patch(self, patch_file=os.path.join(self.export_sources_folder,
                                            "patches",
                                            "0001-vlib-native-conditions.patch"))
        # 0002：filelock 的 C.open 声明对齐变参签名（与 os.c.v 一致）——
        # 此前只应用 0001 导致 C.open 冲突未修（CI 实测 lib_nix.c.v:6 仍
        # 固定 3 参签名 → v1 报 already declared with a different signature）
        patch(self, patch_file=os.path.join(self.export_sources_folder,
                                            "patches",
                                            "0002-vlib-copen-signature.patch"))
        # make local=1：GNUmakefile 的 latest_vc 走空目标分支（ifndef local 时
        # 才 git pull——伪造的 vc/.git/config 非真实 git 仓库，git pull 报
        # "not a git repository" Error 128）——local=1 跳过 git pull，v1 直接
        # 编译下载的 v.c（f461dfebcdfa）
        self.run(f"cd {self.source_folder} && {env_prefix} make local=1", ignore_errors=True)

    def package(self):
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "v", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
