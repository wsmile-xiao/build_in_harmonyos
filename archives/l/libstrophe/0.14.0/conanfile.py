#!/usr/bin/env python3
"""Conan recipe — libstrophe 0.14.0 (autotools)."""
import glob as _glob
import os as _os
import shutil as _shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration, ConanException


class LibstropheConan(ConanFile):
    name = "libstrophe"
    version = "0.14.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # configure 通过 pkg-config 探测 openssl / expat / zlib，全部为构建期真实依赖。
        self.requires("openssl/3.5.6.1.1")
        self.requires("expat/2.8.2.1.1")
        self.requires("zlib/1.3.1.1.1.1")

    def build_requirements(self):
        # GitHub archive tarball 不带 configure，必须 autoreconf 自举。
        # SDK 提供 autoconf/m4/perl 但缺 aclocal/automake/libtoolize；
        # automake/1.18 自带 aclocal+automake（PERL5LIB 指向其 share 目录），
        # libtool/2.5.4 自带 libtoolize（accel-config 同款 CI 已验证组合）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        arch_triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        triplet = arch_triplets.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _prepare_build_env(self):
        """Shared tmpdir + pkg.m4 aclocal 路径注入。

        ACLOCAL_PATH 指向 SDK pkg-config 安装前缀里的 pkg.m4
        （PKG_CHECK_MODULES 宏所在），以及 libtool 工具包的 share/aclocal，
        避免 aclocal 找不到 pkg 宏导致 configure 报 undefined macro。
        """
        tmpdir = _os.path.join(self.build_folder, "tmp")
        _os.makedirs(tmpdir, exist_ok=True)
        _os.chmod(tmpdir, 0o755)
        _os.environ["TMPDIR"] = tmpdir
        bash = _shutil.which("bash") or "/bin/sh"
        _os.environ.setdefault("CONFIG_SHELL", bash)
        _os.environ.setdefault("SHELL", bash)

        aclocal_dirs = []
        pkg_config = _shutil.which("pkg-config")
        if pkg_config:
            for cand in _glob.glob(_os.path.join(
                    _os.path.dirname(_os.path.dirname(pkg_config)),
                    "pkg-config.org", "pkg-config_*", "share", "aclocal")):
                if _os.path.isdir(cand):
                    aclocal_dirs.append(cand)
            cand = _os.path.join(
                _os.path.dirname(_os.path.dirname(pkg_config)), "share", "aclocal")
            if _os.path.isdir(cand):
                aclocal_dirs.append(cand)
        for dep in self.dependencies.build.values():
            if dep.ref.name == "libtool":
                cand = _os.path.join(dep.package_folder, "share", "aclocal")
                if _os.path.isdir(cand):
                    aclocal_dirs.append(cand)
        existing = _os.environ.get("ACLOCAL_PATH", "")
        extra = ":".join(d for d in aclocal_dirs if d)
        _os.environ["ACLOCAL_PATH"] = ":".join(
            [d for d in [extra, existing] if d])
        return bash

    def generate(self):
        bash = self._prepare_build_env()
        PkgConfigDeps(self).generate()
        host_triplet = self._gnu_triplet()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            # examples 用 getpass()，本平台编译器报 undeclared 编译失败；库交付不需要它们。
            "--disable-examples",
            "--disable-fuzzing",
        ])
        env = tc.environment()
        # 环境里可能已有 LDFLAGS（设备与 CI worker 的 ~/.zshrc 都导出了
        # -L$HOME/usr/local/lib）。conan 对 LDFLAGS 用 append，自己的 -L 排在
        # 它后面；链接器按 -L 顺序取第一个命中的目录，于是 -lssl 可能命中系统的
        # libssl.so 而不是 conan 包里的。把依赖的 libdir 前置（lcalc 同款修法）。
        _Lp = " ".join("-L{}".format(_d) for _ref, _dep in self.dependencies.items()
                       for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d))
        if _Lp:
            env.prepend("LDFLAGS", _Lp)
        tc.generate(env=env)
        return bash

    def build(self):
        bash = self._prepare_build_env()
        apply_conandata_patches(self)
        # GitHub archive tarball 从不含 configure（git tree 快照），先自举。
        if not _os.path.isfile(_os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure（GitHub archive），先 autoreconf 自举")
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        if not _os.path.isfile(_os.path.join(self.source_folder, "configure")):
            raise ConanException(
                "autoreconf 未生成 configure；详见构建日志")
        # umask 077 导致 config.status 创建临时目录时因 HMDFS 权限语义失败
        # （Permission denied），自举后 configure 已重新生成，此时修补为 007。
        _cfg = _os.path.join(self.source_folder, "configure")
        try:
            with open(_cfg, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 007"))
        except OSError:
            pass
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # libtool 的 .la 里烤死 libdir 绝对路径，conan 包按 prefix=/ 构建会导致
        # 下游 libtool 找不到 //lib/libstrophe.la（graphviz/lcalc 实撞），删除之。
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["strophe"]
        self.cpp_info.set_property("pkg_config_name", "libstrophe")