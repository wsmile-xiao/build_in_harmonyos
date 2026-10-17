#!/usr/bin/env python3
"""Conan recipe — hashrat 1.25 (autotools, CLI tool)

hashrat is a command-line hash tool (md5/sha1/sha2/jh/whirlpool/...)
that links libUseful-bundled + OpenSSL (ssl/crypto) + zlib.
The package is an application: it installs bin/hashrat + man page.
"""
import os

from conan import ConanFile
from conan.tools.files import chdir, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HashratConan(ConanFile):
    name = "hashrat"
    version = "1.25"
    description = "Hash files and strings with md5, sha1, sha2, jh, whirlpool, ..."
    license = "GPL-3.0"
    homepage = "https://github.com/ColumPaget/Hashrat"
    url = "https://github.com/ColumPaget/Hashrat"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # hashrat links -lssl -lcrypto -lz (configure checks deflate/crypto/ssl)
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 系统同名库静态链接由 conan 依赖链管理，配方不注入系统前缀
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            # OHOS fix: configure/config.status 用 `mktemp -d`（umask 077）
            # 生成 0700 临时目录；HMDFS 账户共享把属主映射为 account uid，
            # 与本进程 uid 不一致导致 Permission denied。改用 mkdir（4ti2 同款）。
            # 顶层 configure 与 libUseful-bundled 子 configure（AC_CONFIG_SUBDIRS）
            # 均有该模式，逐一替换。
            _old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
            _new = 'tmp="./conf$$-$RANDOM"\n  (mkdir "$tmp" 2>/dev/null)\n  test -d "$tmp"'
            for _cfg_rel in ("configure", os.path.join("libUseful-bundled", "configure")):
                _configure = os.path.join(self.source_folder, _cfg_rel)
                if not os.path.exists(_configure):
                    continue
                with open(_configure, "r", encoding="utf-8", errors="ignore") as f:
                    _text = f.read()
                if _old in _text:
                    _text = _text.replace(_old, _new)
                    with open(_configure, "w", encoding="utf-8") as f:
                        f.write(_text)
                else:
                    self.output.warn(f"OHOS mktemp patch: pattern not found in {_cfg_rel} "
                                     "(upstream text may have changed)")
            # openssl/zlib 头文件与库路径注入（configure 探测 ssl/crypto/z 需要）
            for dep_name in ("openssl", "zlib"):
                dep = self.dependencies[dep_name]
                _inc = os.path.join(dep.package_folder, "include")
                _lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(_inc):
                    os.environ["CPPFLAGS"] = f"-I{_inc} " + os.environ.get("CPPFLAGS", "")
                if os.path.isdir(_lib):
                    os.environ["LDFLAGS"] = f"-L{_lib} " + os.environ.get("LDFLAGS", "")
        autotools = Autotools(self)
        # hashrat 顶层 Makefile 仅支持 in-source 构建（无 VPATH：
        # `common.o: common.h common.c` 等规则引用同级源码文件），
        # 因此 configure/make 必须在源码目录内执行，不能在
        # basic_layout 的 build-release/ 子目录 out-of-source 构建。
        with chdir(self, self.source_folder):
            autotools.configure()
            # libUseful-bundled 的 `all` 目标会先 `-shared` 构建 libUseful.so，
            # 把非 PIC 的静态 libz.a/libcrypto.a 链入共享库 =>
            # ld.lld: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used
            # against symbol 'z_errmsg'. 顶层 hashrat 只链接 libUseful.a（静态），
            # 不需要该共享库；将 -shared 链接行降级为 no-op，仅保留归档构建。
            _bundle_mk = os.path.join(self.source_folder, "libUseful-bundled", "Makefile")
            if os.path.exists(_bundle_mk):
                with open(_bundle_mk, "r", encoding="utf-8", errors="ignore") as f:
                    _mk = f.read()
                _shared_line_old = "\t$(CC) $(FLAGS) -shared -o $(LIBFILE) $(OBJ) $(LIBS) $(LDFLAGS)"
                if _shared_line_old in _mk:
                    _mk = _mk.replace(
                        _shared_line_old,
                        "\t@echo 'skip shared libUseful build (static-only for hashrat)'",
                    )
                    with open(_bundle_mk, "w", encoding="utf-8") as f:
                        f.write(_mk)
                else:
                    self.output.warn(
                        "libUseful shared-link pattern not found; "
                        "shared build may fail if static deps are non-PIC"
                    )
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        with chdir(self, self.source_folder):
            autotools.install()

    def package_info(self):
        # CLI 工具：只装 bin/hashrat + man，无库文件
        self.cpp_info.bindirs = ["bin"]
