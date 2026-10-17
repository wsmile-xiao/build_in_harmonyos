#!/usr/bin/env python3
"""Conan recipe — udns 0.5 (custom autotools, static library).

udns: small async-capable stub DNS resolver library (libudns) by Michael
Tokarev. Supports synchronous and asynchronous DNS queries and parses most
common RR types without pulling in a full libresolv.

Build-system notes (why no `Autotools(self).configure()`):
- The bundled `configure` script is a hand-rolled autoconf-style script
  (uses configure.lib). Unlike GNU autoconf it does NOT accept --prefix,
  --host/--target or --sbindir; it only knows --enable-ipv6 / --disable-ipv6
  and --help.
- The generated `Makefile` is NOT VPATH-aware (SRCS are bare filenames) and
  has NO `check`/`test`/`install` target. It must therefore be built
  in-source (configure + make inside the source folder), and `package()` must
  stage the artifacts manually.
- Upstream ships no test suite (audited Makefile.in/configure: no check/test
  target, no test files) -> test_package carries the substantive verification,
  including a real end-to-end asynchronous DNS resolution round-trip.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class UdnsConan(ConanFile):
    name = "udns"
    version = "0.5"
    description = "Async/sync-capable stub DNS resolver library (libudns)"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.corpit.ru/mjt/udns.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Conan 2 requires a 'shared' option to be declared for package_type
    # "library". udns upstream only ships a static build (make staticlib ->
    # libudns.a), so we accept the option for compatibility but default to
    # static and always build static regardless of its value.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):  # R32
            raise ConanInvalidConfiguration(
                f"udns supports Linux and OHOS targets, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain produces the conanbuild env (CC/CFLAGS/AR/...)
        # that udns' configure reads. The configure script itself must be
        # invoked manually because it rejects GNU autoconf options such as
        # --prefix (udns' Makefile is in-source only).
        AutotoolsToolchain(self).generate()

    def _assert_probe_patched(self, src):
        """确定性断言补丁已生效（不依赖 apply 的返回值）。

        udns 0.5 的 configure 用一段 ill-formed 探测程序判断 inet_pton/ntop
        是否存在；补丁把它改成合法原型。若补丁**没**生效，clang 会让该探测
        失败，configure 就不写 HAVE_INET_PTON_NTOP，libudns.a 会导出
        udns_pton/udns_ntop 而非 dns_pton/dns_ntop —— 与 udns.h 不符。
        这里直接把该前提钉成构建期门禁。
        """
        cfg = os.path.join(src, "configure")
        if not os.path.isfile(cfg):
            raise ConanException(f"configure not found at {cfg}; cannot verify patch")
        with open(cfg, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        # 补丁后探测应使用 inet_pton 的合法原型（char*/const char*），
        # 不再是原来那个 `long x` + 传 &x 的写法。
        bad = "long x = 0;" in body and "inet_pton(AF_INET, &x," in body
        if bad:
            raise ConanException(
                "udns 0.5 inet_pton/inet_ntop configure probe is UNPATCHED "
                "(still passes `long *` as `const char *`). patches/0001 did not "
                "take effect — libudns.a would export udns_pton/udns_ntop while "
                "udns.h declares dns_pton/dns_ntop. Refusing to build a silently "
                "broken library.")
        # 若 config.h 已存在（例如源码目录被复用），必须已含该 define。
        hdr = os.path.join(src, "config.h")
        if os.path.isfile(hdr):
            with open(hdr, encoding="utf-8", errors="replace") as fh:
                hb = fh.read()
            if "HAVE_INET_PTON_NTOP" not in hb:
                raise ConanException(
                    "config.h has no HAVE_INET_PTON_NTOP: the inet_pton/ntop "
                    "probe failed or a stale config.h is being reused. The "
                    "resulting libudns.a would not match udns.h.")
        self.output.info("patch assertion OK: inet_pton/ntop probe is patched")

    def build(self):
        apply_conandata_patches(self)

        # ★ 不要信任 apply_conandata_patches 的返回值来判定"补丁生效了"。
        # 实测 patch_ng 的语义是"只要有一条 hunk 命中就整体返回成功"：
        #   · 干净源码          → True（正常打上）
        #   · 已完整应用后重打  → True（**静默 no-op**，不写文件）
        #   · 部分已应用        → False → 硬失败
        # 于是"源码树状态不同 → 结果不同"，而源码树一旦被污染，补丁是否真的
        # 生效就再没有独立证据 —— 偏偏 notes.md 把"补丁后 libudns.a 导出
        # dns_ntop"当作核心结论。这里在打补丁后加确定性断言：
        #   · configure 的探测程序必须已被改写（不再用 long * 传 inet_pton）
        #   · 若 config.h 已生成，必须含 HAVE_INET_PTON_NTOP
        # 二者任一不成立即硬失败，使"补丁真的生效"可被独立复核。
        src = self.source_folder
        self._assert_probe_patched(src)
        # HMBS platform diagnostics:
        #  - [missing_build_tool] the real-machine make lives at
        #    (HMBS_MAKE) /data/service/hnp/bin/make but is NOT guaranteed to be
        #    on the subprocess PATH. Resolve it via HMBS_MAKE (injected absolute
        #    path), then shutil.which("make"), then the bare "make" fallback;
        #    never assume "make" resolves on the subprocess PATH.
        #  - [readonly_tmp] OHOS /tmp is read-only. configure / its conftest
        #    probes and any mktemp write to the default /tmp, so point TMPDIR /
        #    TMP / TEMP at the HMBS-injected writable tmpdir.
        #  - do not hardcode an HNP shell; use the HMBS-injected CONFIG_SHELL /
        #    SHELL (true machine uses /bin/sh).
        make_bin = (os.environ.get("HMBS_MAKE")
                    or shutil.which("make")
                    or "make")
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        src = self.source_folder
        # udns's configure is a plain shell script (in-source build; its Makefile
        # has no VPATH support). The compiler comes from the AutotoolsToolchain
        # build env (not bare ${CC} in self.run).
        self.run(f"cd '{src}' && {shlex.quote(shell)} ./configure --enable-ipv6",
                 env="conanbuild")
        # staticlib builds only libudns.a (no example utils, no shared bloat)
        self.run(f"cd '{src}' && {shlex.quote(make_bin)} staticlib -j1",
                 env="conanbuild")

    def package(self):
        src = self.source_folder
        copy(self, "udns.h", src=src,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libudns.a", src=src,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "COPYING.LGPL", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["udns"]
        self.cpp_info.set_property("cmake_file_name", "udns")
        self.cpp_info.set_property("cmake_target_name", "udns::udns")
        self.cpp_info.set_property("pkg_config_name", "udns")
