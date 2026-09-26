#!/usr/bin/env python3
"""conanfile.py — libnss_nis 3.4 (HarmonyOS PC / aarch64 / musl / clang 15)

libnss_nis is a glibc NSS (Name Service Switch) module: it implements the
_nss_nis_*_r entry points that glibc's NSS framework dlopen()s from
libnss_nis.so.2. Three adaptation points for the OHOS musl libc:

1. glibc-only headers <nss.h>/<aliases.h>/<rpc/netdb.h> do not exist on
   musl. patches/0001-ohos-glibc-compat-headers.patch adds minimal compat
   headers under src/ (resolved via AM_CPPFLAGS -I$(srcdir)); see the
   patch_description in conandata.yml.
2. config.guess cannot identify `uname -s = HarmonyOS`; an explicit native
   GNU triplet (--build == --host) skips it entirely (same as libnsl/2.0.1,
   classads/1.0.10, cityhash/1.1.1 precedent).
3. The NIS/RPC client layer lives in libnsl (=libnsl/2.0.1) and TI-RPC
   (=libtirpc/1.3.7), both already published. PkgConfigDeps emits their .pc
   files into the generators folder and PKG_CONFIG_PATH points at it, so
   configure's PKG_CHECK_MODULES([TIRPC]/[LIBNSL]) resolves.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, rm
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps

required_conan_version = ">=1.52.0"


class LibnssnisConan(ConanFile):
    name = "libnss_nis"
    version = "3.4"
    description = "NIS/YP NSS module providing passwd, group, host and alias lookups"
    homepage = "https://github.com/thkukuk/libnss_nis"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/thkukuk/libnss_nis"
    topics = ("nis", "yp", "nss", "name-service")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # NSS modules are loaded via dlopen("libnss_nis.so.2"), never linked, so
    # the shared artifact is the meaningful one (same choice as nss-wrapper).
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # NIS(YP) client API (yp_match/yp_first/...) and rpcsvc/yp*.h
        self.requires("libnsl/2.0.1")

    def layout(self):
        # Autotools project: configure/make run in the source tree.
        pass

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], destination=self.source_folder, strip_root=True)

    def generate(self):
        # Emits libnsl.pc + libtirpc.pc (and -I/-L) into the generators folder.
        deps = PkgConfigDeps(self)
        deps.generate()

    def _relax_configure_temp_umask(self):
        """
        HMDFS/setgid portability (same as libnsl/2.0.1 and gmime/3.0.6):
        autoconf's configure scratch dir is created with umask 077 below a
        setgid dir and becomes unwritable by the next process on hmfs/hmdfs.
        Relaxing to 022 fixes config.status spurious Permission denied.
        """
        if str(self.settings.os) != "OHOS":
            return
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            from conan.tools.files import replace_in_file
            replace_in_file(self, cfg, "umask 077", "umask 022", strict=False)

    def build(self):
        apply_conandata_patches(self)
        self._relax_configure_temp_umask()
        src = self.source_folder
        shared_flag = ("--enable-shared --disable-static" if self.options.shared
                       else "--disable-shared --enable-static")
        self.run(
            f'cd "{src}" && umask 022 && '
            'CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            # PkgConfigDeps writes libnsl.pc/libtirpc.pc into the generators folder.
            f'PKG_CONFIG_PATH="{self.generators_folder}'
            f'${{PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}}" '
            f'sh "./configure" '
            f"--prefix=/ "
            f"'--bindir=${{prefix}}/bin' '--sbindir=${{prefix}}/bin' "
            f"'--libdir=${{prefix}}/lib' '--includedir=${{prefix}}/include' "
            f"'--oldincludedir=${{prefix}}/include' "
            f"--build=aarch64-unknown-linux-gnu "
            f"--host=aarch64-unknown-linux-gnu "
            f"{shared_flag} --disable-dependency-tracking",
            env="conanbuild",
        )
        self.run(f'cd "{src}" && make -j1', env="conanbuild")
        # Upstream test: src/Makefile.am declares check_PROGRAMS = nss_loader-test
        # and TESTS = $(check_PROGRAMS); the binary dlopen()s the freshly built
        # libnss_nis.so.2 and dlsym()s _nss_nis_getpwnam_r (no NIS server
        # needed). The compat nss.h __mempcpy mapping keeps the smoke test
        # green on musl. Recorded in test_package/MANIFEST.yml.
        self.run(f'cd "{src}" && make check', env="conanbuild")

    def package(self):
        src = self.source_folder
        # DESTDIR staging: configure was given --prefix=/ on purpose.
        self.run(f'cd "{src}" && make -j1 install DESTDIR="{self.package_folder}"',
                 env="conanbuild")
        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"))
        # libtool archives leak build paths and are useless to consumers.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libnss_nis")
        # NSS 模块不安装公共头文件，只有 lib/ 下的模块产物；
        # 显式清空 includedirs，避免 CMakeDeps 引用不存在的 ${pkg}/include
        # 导致 test_package find_package 报 "includes non-existent path"。
        self.cpp_info.includedirs = []
        self.cpp_info.libs = ["nss_nis"]
        # NSS modules are dlopen()ed by the NSS framework; consumers resolve
        # _nss_nis_* symbols via dlsym() rather than link-time references.
        self.cpp_info.bindirs = []