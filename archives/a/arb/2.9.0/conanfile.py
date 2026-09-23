#!/usr/bin/env python3
"""Conan recipe — arb 2.9.0 (autotools)

Arb: C library for arbitrary-precision interval arithmetic.
Depends on FLINT (which itself pulls GMP + MPFR).
"""

import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ArbConan(ConanFile):
    name = "arb"
    version = "2.9.0"
    description = "Arb — arbitrary-precision interval arithmetic (ball arithmetic)"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/fredrik-johansson/arb"
    homepage = "https://arblib.org/"
    topics = ("interval-arithmetic", "arbitrary-precision", "number-theory", "flint")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("flint/3.6.0")
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-gmp={}".format(self.dependencies["gmp"].package_folder))
        tc.configure_args.append("--with-mpfr={}".format(self.dependencies["mpfr"].package_folder))
        tc.configure_args.append("--with-flint={}".format(self.dependencies["flint"].package_folder))
        tc.generate()

    def _fix_umask(self):
        # HMDFS (HarmonyOS distributed FS) breaks with configure's umask
        # 077: the conftest temporary directories become unusable. Same
        # issue as flint 3.6.0 (knowledge E-pattern); fix in place.
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" not in text:
                continue
            with open(_cfg, "w", encoding="utf-8") as f:
                f.write(text.replace("umask 077", "umask 022"))

    def _resolve_cc(self):
        # 编译器解析链（R33，无硬编码）：tools.build:compiler_executables
        # conf → profile [buildenv] 的 CC（经 VirtualBuildEnv）→ 报错。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc:
            with VirtualBuildEnv(self).vars().apply():
                cc = os.environ.get("CC")
        if not cc:
            raise ConanException(
                "arb: C compiler not found — set the "
                "tools.build:compiler_executables conf or the CC "
                "environment variable"
            )
        return cc

    def _build_ohos(self):
        # OHOS：用 /bin/sh 原位驱动 configure/make（绕过 Conan Autotools
        # helper 的 bash wrapper，同 flint 的 HMDFS getcwd 规避）。/tmp 只读
        # —— TMPDIR 指向 $HOME/tmp（与 CI 脚本惯例一致）。
        tmp_root = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmp_root, exist_ok=True)
        os.environ["TMPDIR"] = tmp_root

        cc = self._resolve_cc()
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 1, check_type=int)

        args = ["--prefix={}".format(self.package_folder),
                "--with-gmp={}".format(self.dependencies["gmp"].package_folder),
                "--with-mpfr={}".format(self.dependencies["mpfr"].package_folder),
                "--with-flint={}".format(self.dependencies["flint"].package_folder)]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]

        # 工具链目录从编译器路径推导（CI worker PATH 不含 toolchain 目录）。
        toolchain_dir = os.path.dirname(cc)

        script = os.path.join(self.source_folder, "_build_ohos.sh")
        with open(script, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n")
            f.write("set -e\n")
            f.write('cd "{}"\n'.format(self.source_folder))
            f.write('PATH="{}:$PATH"\n'.format(toolchain_dir))
            f.write("CONFIG_SHELL=/bin/sh\nSHELL=/bin/sh\nTMPDIR={}\n".format(tmp_root))
            f.write("export PATH CONFIG_SHELL SHELL TMPDIR\n")
            f.write("CC={}\nexport CC\n".format(cc))
            f.write("./configure {}\n".format(" ".join(args)))
            f.write("make -j{}\n".format(jobs))
            f.write("make install\n")
        os.chmod(script, 0o755)

        self.output.info("arb: OHOS build driven by /bin/sh (bash getcwd workaround)")
        subprocess.check_call(["/bin/sh", script], cwd=self.source_folder)

    def build(self):
        self._fix_umask()
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
            return

        autotools = Autotools(self)
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 1, check_type=int)
        autotools.configure()
        autotools.make(args=["-j{}".format(jobs)])

    def package(self):
        if str(self.settings.os) != "OHOS":
            autotools = Autotools(self)
            autotools.install(args=["-j1"])
        else:
            # OHOS: build() 已运行 'make install'（--prefix）
            if not glob.glob(os.path.join(self.package_folder, "lib", "libarb.*")):
                raise ConanException(
                    "arb: no libarb.* in package folder — 'make install' "
                    "did not populate it"
                )
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS PC XPM 要求被 dlopen 的 .so 与可执行文件带代码签名。
        if str(self.settings.os) != "OHOS":
            return
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["arb"]
        # arb 的 libarb.so 链接时把 flint/gmp/mpfr 静态链入?不 —— arb 默认
        # 对依赖做动态链接（DT_NEEDED 指向 libflint.so 等），下游需要
        # flint 头文件与链接信息，因此显式声明 requires。
        self.cpp_info.requires = ["flint::flint", "gmp::gmp", "mpfr::mpfr"]
        self.cpp_info.set_property("cmake_file_name", "arb")
        self.cpp_info.set_property("cmake_target_name", "arb::arb")
        self.cpp_info.set_property("pkg_config_name", "arb")
