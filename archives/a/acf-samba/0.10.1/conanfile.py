#!/usr/bin/env python3
"""Conan recipe — acf-samba 0.10.1 (Alpine Configuration Framework Samba module).

Pure-Lua ACF application module: a single recursive Makefile copies Lua
controller/model scripts and HTML view templates (.lsp) into a
/usr/share/acf/app/samba layout via `make install DESTDIR=...`. No C sources
are compiled; `make all` is a no-op. The recipe mirrors that: source() fetches
the upstream tarball, build() runs `make all` (no-op, validates Makefile
syntax), and package() runs `make install DESTDIR=<pkg>`. The /usr-prefixed
layout is preserved and exposed via cpp_info.resdirs.

Runtime dependency: acf-core (the ACF framework mvc.lua that dispatches this
module's controller).
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AcfSambaConan(ConanFile):
    name = "acf-samba"
    version = "0.10.1"
    description = "Alpine Configuration Framework — Samba module (pure Lua ACF web admin for Samba)"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/acf/acf-samba"
    topics = ("acf", "samba", "web-admin", "lua", "alpine")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Runtime framework dependency; acf-core provides mvc.lua dispatch.
        # acf-core/0.24.1 已通过 PR #4363 合入 main 并发布到 ohpcd 制品仓。
        # requires 不带 @user/channel 后缀，与 acf-core 自身写法一致，
        # 让 conan 用调用方的 --user/--channel 隐式解析（匹配已合入包的惯例）。
        self.requires("acf-core/0.24.1")

    def validate(self):
        # R32: recipe supports Linux and OHOS targets only
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"acf-samba supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # `make all` is a no-op for pure-Lua modules; validates Makefile syntax.
        self.run("make -C {} -j1 all".format(self.source_folder))

    def package(self):
        # `make install DESTDIR=<pkg>` copies samba-controller.lua, samba-model.lua,
        # samba.menu, samba.roles + HTML view templates (.lsp) to <pkg>/usr/share/acf/app/samba/.
        # Dangling symlinks (samba-expert-html.lsp -> ../filedetails-html.lsp,
        # samba-status-html.lsp -> ../status-html.lsp) point to acf-lib shared templates
        # (not in this package) and are skipped by `cp -a samba*` — upstream intent.
        self.run(
            "make -C {} install DESTDIR={} -j1".format(
                self.source_folder, self.package_folder
            )
        )

    def package_info(self):
        # No compiled libraries; the package ships Lua scripts + HTML templates.
        # Expose the ACF application directory as a resource path so consumers
        # (the acf-core dispatcher) can locate samba-controller.lua.
        self.cpp_info.set_property("cmake_file_name", "acf-samba")
        self.cpp_info.set_property("cmake_target_name", "acf_samba::acf_samba")

        # The application scripts live at <pkg>/usr/share/acf/app/samba/
        app_dir = "usr/share/acf/app/samba"
        self.cpp_info.resdirs = [app_dir]

        # No system library of the same name (pure Lua app module).
        # R26 (static linking for system same-name libs) does not apply.
