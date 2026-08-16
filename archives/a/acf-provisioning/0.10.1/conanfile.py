#!/usr/bin/env python3
"""Conan recipe — acf-provisioning 0.10.1 (Alpine Configuration Framework provisioning module).

Pure-Lua ACF application module: a recursive Makefile copies Lua
controller/model scripts, HTML view templates (.lsp) and cgi-bin scripts
into a /usr-prefixed layout via `make install DESTDIR=...`. No C
sources are compiled; `make all` is a no-op. The recipe mirrors that:
source() fetches the upstream tarball, build() runs `make all` (no-op,
validates Makefile syntax), and package() runs `make install DESTDIR=<pkg>`.
The /usr-prefixed layout is preserved and exposed via cpp_info.resdirs.

Runtime dependency: acf-core (the ACF framework mvc.lua that dispatches this
module's controller).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfProvisioningConan(ConanFile):
    name = "acf-provisioning"
    version = "0.10.1"
    description = "Alpine Configuration Framework provisioning module — ACF for provisioning templated configs to devices"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-provisioning"
    url = "https://gitlab.alpinelinux.org/acf/acf-provisioning"

    # Pure-Lua module package (no binary, no library)
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime framework dependency; acf-core provides mvc.lua dispatch.
        # acf-core/0.24.1 已合入 main 并发布到 ohpcd 制品仓。
        # requires 不带 @user/channel 后缀，与 acf-core 自身写法一致，
        # 让 conan 用调用方的 --user/--channel 隐式解析（匹配已合入包的惯例）。
        self.requires("acf-core/0.24.1")

    def layout(self):
        basic_layout(self)

    def configure(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-provisioning does not support os={self.settings.os}")

    def source(self):
        # gitlab.alpinelinux.org 按 User-Agent 反爬拦截（Conan 默认 UA 返回 418），
        # 使用 curl 风格 UA 获取官方源码（R39: 保持官方 URL 不变）。
        get(self, **self.conan_data["sources"], strip_root=True,
            headers={"User-Agent": "curl/8.5.0"})

    def build(self):
        apply_conandata_patches(self)
        # `make all` is a no-op (Makefile `all:` empty); validates Makefile parse.
        # basic_layout keeps sources in source_folder — run make there.
        self.run(f"make -C {self.source_folder} -j1 all", env="conanbuild")

    def package(self):
        # `make install DESTDIR=<pkg>` copies provisioning* into
        # <pkg>/usr/share/acf/app/provisioning, config/* into <pkg>/etc/provisioning,
        # cgi-bin/* into <pkg>/var/www/provisioning/htdocs/cgi-bin and the
        # logrotate file into <pkg>/etc/logrotate.d; config.mk bakes prefix=/usr.
        self.run(
            f"make -C {self.source_folder} install DESTDIR={self.package_folder} -j1",
            env="conanbuild",
        )

    def package_info(self):
        # Pure-Lua module: no cpp_info.libs, no bindirs.
        # Expose share/acf/app/provisioning as resdir for consumers (acf-core mvc dispatch).
        self.cpp_info.resdirs = ["usr/share/acf/app/provisioning"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
