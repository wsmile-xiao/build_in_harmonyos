#!/usr/bin/env python3
"""Conan recipe for cmor 3.15.2 (Climate Model Output Rewriter).

Autotools C library.  The release tarball ships a generated configure, so no
autoreconf chain is needed.  configure.ac hard-requires netcdf, udunits2,
json-c and uuid (AC_MSG_ERROR when any is missing); all four are wired via
--with-* pointing at the Conan package folders.  The release tarball does not
include the three CMOR tables submodules (cmip6/mip/cmip7-cmor-tables) that
the upstream Test suite references; they are fetched from their official
GitHub archives in source().  The hand-written Makefile.in has no DESTDIR
support, so package() copies libcmor.a and the public headers explicitly.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CmorConan(ConanFile):
    name = "cmor"
    version = "3.15.2"
    description = "Climate Model Output Rewriter (CMOR) library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/PCMDI/cmor"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cmor supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "cmor OHOS support is validated for armv8/AArch64"
            )

    def requirements(self):
        # configure.ac: AC_CHECK_LIB([netcdf|udunits2|json-c|uuid], ...) all
        # with AC_MSG_ERROR on failure — none can be --without'ed.
        # headers=True：cmor 的公共头文件（include/cmor_func_def.h）直接
        # #include <udunits2.h>、<json-c/json.h>、<netcdf.h>、<uuid/uuid.h>，
        # 消费者编译时必须拿到依赖头路径，因此依赖头必须随 cmor 传递见。
        self.requires("netcdf/4.9.3", headers=True)
        self.requires("udunits/2.2.28.1", headers=True)
        self.requires("json-c/0.17", headers=True)
        self.requires("uuid/2.40.1", headers=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"]["cmor"], strip_root=True)
        # The three CMOR tables submodules are not part of the release
        # tarball; upstream Test scripts reference them by these top-level
        # paths (mip-cmor-tables/Tables, cmip7-cmor-tables/tables, ...).
        for sub in ("cmip6-cmor-tables", "mip-cmor-tables", "cmip7-cmor-tables"):
            get(self, **self.conan_data["sources"][sub],
                strip_root=True, destination=sub)

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        netcdf = self.dependencies["netcdf"]
        udunits = self.dependencies["udunits"]
        json_c = self.dependencies["json-c"]
        uuid = self.dependencies["uuid"]
        tc.configure_args.extend([
            # OHOS 无 gfortran；configure.ac 默认"尝试"启用 Fortran 并把
            # cmor_fortran_interface.o 加入 LIBFILES，因 FC 为空导致
            # make 用异常命令编译 .f90 失败。--enable-fortran=no 时
            # LIBFILES 仅含 C 目标（MODFILES 也置空）。
            "--enable-fortran=no",
            # netcdf 传 no：conan netcdf 包自带的 bin/nc-config 把构建期
            # 绝对路径写死（/p/b/.../p），在消费者缓存里该路径已不存在；
            # configure 走 nc-config 分支会得到失效的 -L。传 no 让
            # configure 使用 -lnetcdf，由 AutotoolsDeps 注入的
            # LDFLAGS（-L<netcdf>/lib）解析。
            "--with-netcdf=no",
            f"--with-udunits2={udunits.package_folder}",
            f"--with-json-c={json_c.package_folder}",
            f"--with-uuid={uuid.package_folder}",
            "--disable-dependency-tracking",
        ])
        tc.generate()

    def _inject_ohos_aux(self):
        """Inject OHOS (HarmonyOS) recognition into the root config.guess /
        config.sub shipped in the release tarball.  The tarball's configure
        (AC_CANONICAL_TARGET) runs these scripts; on OHOS uname -s reports
        HarmonyOS which the 2026-06-25 GNU scripts do not know, causing
        "cannot guess build type" in the clean CI worker.  Mirror of the
        udunits _inject_ohos_aux() (ding-libs 0.7.0 precedent), adapted to
        the newer config.guess/config.sub shipped with cmor."""
        guess_p = os.path.join(self.source_folder, "config.guess")
        sub_p = os.path.join(self.source_folder, "config.sub")

        if os.path.isfile(guess_p):
            with open(guess_p, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            if "HarmonyOS" not in txt:
                # Main-case anchor shared by recent GNU config.guess.
                anchor = ("case \"$UNAME_MACHINE:$UNAME_SYSTEM:"
                          "$UNAME_RELEASE:$UNAME_VERSION\" in\n")
                ohos_case = (
                    "case \"$UNAME_MACHINE:$UNAME_SYSTEM:"
                    "$UNAME_RELEASE:$UNAME_VERSION\" in\n"
                    "    *:HarmonyOS:*:*)\n"
                    "\techo \"$UNAME_MACHINE\"-unknown-linux-ohos\n"
                    "\texit ;;\n"
                )
                if anchor in txt:
                    txt = txt.replace(anchor, ohos_case, 1)
                else:
                    self.output.warning(
                        "  [skip] config.guess main-case anchor not found")
                with open(guess_p, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("  [ok] injected HarmonyOS into config.guess")

        if os.path.isfile(sub_p):
            with open(sub_p, "r", encoding="utf-8", errors="replace") as fh:
                txt = fh.read()
            if "linux-ohos" not in txt:
                # cmor 自带 config.sub (2021-01-08) 的 OS 校验列表不接受
                # `ohos`（config.guess 输出 aarch64-unknown-linux-ohos，
                # 被拆为 kernel=linux, os=ohos）。在 OS 校验列表加
                # `ohos*`，并在 kernel-os 组合校验加 `linux-ohos*`。
                old_os = ("gnu* | android* | bsd* | mach* | minix* | genix*"
                          " | ultrix* | irix* \\\n")
                new_os = ("gnu* | android* | ohos* | bsd* | mach* | minix*"
                          " | genix* | ultrix* | irix* \\\n")
                if old_os in txt:
                    txt = txt.replace(old_os, new_os, 1)
                else:
                    self.output.warning(
                        "  [skip] config.sub OS-list anchor not found")
                old_ko = ("\tlinux-gnu* | linux-dietlibc* | linux-android*"
                          " | linux-newlib* | linux-musl* | linux-uclibc* )\n")
                new_ko = ("\tlinux-gnu* | linux-dietlibc* | linux-android*"
                          " | linux-newlib* | linux-musl* | linux-uclibc*"
                          " | linux-ohos* )\n")
                if old_ko in txt:
                    txt = txt.replace(old_ko, new_ko, 1)
                else:
                    self.output.warning(
                        "  [skip] config.sub kernel-os anchor not found")
                with open(sub_p, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                self.output.info("  [ok] injected linux-ohos into config.sub")

    def _runtime_env(self):
        """Put the host dependencies' lib dirs on LD_LIBRARY_PATH so the
        configure-time conftest probes (configure.ac links
        netcdf/udunits2/json-c/uuid and their shared deps, and the NetCDF
        probe pulls in hdf5_cpp/hdf5_hl_cpp whose shared libs need
        libc++_shared.so) can run on OHOS.  Without this the cross-compile
        probe dies with "cannot run C compiled programs" (Error loading
        shared library libnetcdf.so.22 / libhdf5*.so / libc++_shared.so)."""
        env = Environment()
        for dep in self.dependencies.host.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if libdir and os.path.isdir(libdir):
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        # hdf5_cpp/hdf5_hl_cpp (built with the OHOS toolchain libc++) need
        # libc++_shared.so at runtime; it lives in the NDK clang lib dir.
        libcxx_dirs = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/"
            "lib/aarch64-linux-ohos"))
        for d in libcxx_dirs:
            if os.path.isdir(d):
                env.prepend_path("LD_LIBRARY_PATH", d)
        return env

    def build(self):
        # OHOS portability 修正（umask 077→022、netcdf 探测段保留
        # SV_LDFLAGS/SV_CFLAGS）由 conandata.yml 声明的
        # patches/0001-configure-ohos-portability.patch 静态应用（R6：
        # 生成文件改动走 patches/ 而非运行时改写）。
        apply_conandata_patches(self)
        # OHOS system-type recognition (see _inject_ohos_aux).
        self._inject_ohos_aux()
        # HMDFS: publish the logical PWD so configure's pwd probe works.
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        with self._runtime_env().vars(self).apply():
            autotools.configure()
        # configure (AC_CONFIG_FILES: include/cmor_locale.h) 生成的头文件
        # 落在 out-of-tree build 目录 (build-release/include/)，而
        # Makefile 的 CPPFLAGS 指向源码 include/（其中只有 .in 模板）；
        # 将生成的 cmor_locale.h 复制到源码 include/ 供编译引用。
        gen_locale = os.path.join(self.build_folder, "include", "cmor_locale.h")
        if not os.path.isfile(gen_locale):
            gen_locale = os.path.join(self.build_folder, "cmor_locale.h")
        if os.path.isfile(gen_locale):
            dst = os.path.join(self.source_folder, "include", "cmor_locale.h")
            shutil.copy(gen_locale, dst)
            self.output.info("  [ok] copied generated cmor_locale.h to "
                             "source include")
        autotools.make(args=["-j1"])

    def package(self):
        # The hand-written Makefile.in install target uses ${PREFIX} directly
        # (no DESTDIR support); copy the built archive and headers instead.
        copy(self, "libcmor.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # cmor 公共头 include/cdTime 子目录头（cdmsint.h 等）被
        # include/cmor_func_def.h 直接 `#include "cdmsint.h"` 引用且不带
        # 子目录前缀；上游 configure.ac 编译用 `-Iinclude/cdTime`。
        # 把子目录一并暴露给消费者。
        self.cpp_info.includedirs = ["include", "include/cdTime"]
        self.cpp_info.libs = ["cmor"]
        # Consumers link against the same netcdf/udunits2/json-c/uuid.
        self.cpp_info.requires = [
            "netcdf::netcdf",
            "udunits::udunits",
            "json-c::json-c",
            "uuid::uuid",
        ]
