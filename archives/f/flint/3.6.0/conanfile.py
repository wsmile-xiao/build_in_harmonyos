#!/usr/bin/env python3
"""Conan recipe — flint 3.6.0 (autotools)"""

import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FlintConan(ConanFile):
    name = "flint"
    version = "3.6.0"
    description = "FLINT (Fast Library for Number Theory) — fast number theory algorithms"
    license = "LGPL-3.0-or-later"
    url = "https://github.com/flintlib/flint"
    homepage = "https://flintlib.org/"
    topics = ("number-theory", "arbitrary-precision", "polynomials", "interval-arithmetic")
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

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # The OHOS musl fork declares pthread_getaffinity_np / cpu_set_t in
        # its headers but does not provide the symbols; the configure probe
        # only compiles (never links), so it would pass here and only fail
        # when a consumer links libflint. Cache the probe answer instead.
        tc.configure_args.append("flint_cv_check_cpu_set_t=no")
        tc.configure_args.append("--with-gmp-include={}".format(self.dependencies["gmp"].cpp_info.includedirs[0]))
        tc.configure_args.append("--with-gmp-lib={}".format(self.dependencies["gmp"].cpp_info.libdirs[0]))
        tc.configure_args.append("--with-mpfr-include={}".format(self.dependencies["mpfr"].cpp_info.includedirs[0]))
        tc.configure_args.append("--with-mpfr-lib={}".format(self.dependencies["mpfr"].cpp_info.libdirs[0]))
        tc.generate()

    def _fix_umask(self):
        # HMDFS (HarmonyOS distributed FS) breaks with configure's umask
        # 077: the conftest temporary directories become unusable. Patch
        # 0003 fixes the shipped configure; this covers the configure that
        # autoreconf regenerates on the archive-tarball path.
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
        # Conan 2 不会把 [buildenv] 变量注入 os.environ（挫折 24）。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc:
            with VirtualBuildEnv(self).vars().apply():
                cc = os.environ.get("CC")
        if not cc:
            raise ConanException(
                "flint: C compiler not found — set the "
                "tools.build:compiler_executables conf or the CC "
                "environment variable"
            )
        return cc

    def _build_ohos(self):
        # 挫折 1/3：profile 的 CONFIG_SHELL bash 在 HMDFS 上有 getcwd 缺陷
        # （configure 报 "working directory cannot be determined"）。改为
        # 用 /bin/sh 原位驱动 configure/make，绕过 Conan Autotools helper
        # 的 shell wrapper。
        # 挫折 23：/tmp 只读 —— TMPDIR 指向 $HOME/tmp（与 CI 脚本惯例一致）。
        tmp_root = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmp_root, exist_ok=True)
        os.environ["TMPDIR"] = tmp_root

        cc = self._resolve_cc()
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 1, check_type=int)

        args = ["--prefix={}".format(self.package_folder),
                "flint_cv_check_cpu_set_t=no",
                "--with-gmp-include={}".format(self.dependencies["gmp"].cpp_info.includedirs[0]),
                "--with-gmp-lib={}".format(self.dependencies["gmp"].cpp_info.libdirs[0]),
                "--with-mpfr-include={}".format(self.dependencies["mpfr"].cpp_info.includedirs[0]),
                "--with-mpfr-lib={}".format(self.dependencies["mpfr"].cpp_info.libdirs[0])]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--disable-shared", "--enable-static"]

        # The compiler executable comes from tools.build:compiler_executables as
        # an absolute path, but the official CI worker's PATH does not include
        # the toolchain directory — clang then cannot find its companions
        # (ld.lld, nm, m4, make...) and configure fails with
        # "C compiler cannot create executables" (CI #25792 实测). Derive the
        # toolchain dir from the compiler path itself (clang lives next to its
        # tools) instead of hardcoding any machine-specific PATH.
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

        self.output.info("flint: OHOS build driven by /bin/sh (bash getcwd workaround)")
        subprocess.check_call(["/bin/sh", script], cwd=self.source_folder)

    def build(self):
        # The GitHub release tarball ships a pre-generated configure; the
        # plain archive tarball does not (configure is an autoreconf
        # product, never committed). Support both sources.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("flint: source tree has no configure (GitHub archive), bootstrapping with autoreconf")
            Autotools(self).autoreconf()
            self._fix_umask()

        if str(self.settings.os) == "OHOS":
            self._build_ohos()
            return

        autotools = Autotools(self)
        # ~5400 non-test source files: a serial build is not viable.
        # Prefer the tools.build:jobs conf, fall back to the CPU count
        # (not hardcoded).
        jobs = self.conf.get("tools.build:jobs", default=os.cpu_count() or 1, check_type=int)
        autotools.configure()
        autotools.make(args=["-j{}".format(jobs)])

    def package(self):
        if str(self.settings.os) != "OHOS":
            autotools = Autotools(self)
            autotools.install(args=["-j1"])
        else:
            # OHOS: build() already ran 'make install' (--prefix)
            if not glob.glob(os.path.join(self.package_folder, "lib", "libflint.*")):
                raise ConanException(
                    "flint: no libflint.* in package folder — 'make install' "
                    "did not populate it"
                )
        # libtool .la files bake in an absolute libdir; the .pc file and
        # cpp_info already carry the link information. Remove them.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        copy(
            self,
            "COPYING.LESSER",
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
        # HarmonyOS PC XPM requires dlopen'd .so files (and executed
        # binaries) to be code-signed, otherwise Permission denied /
        # Operation not permitted. The signature is a content hash — any
        # byte change after linking invalidates it (libtool relink, strip,
        # objcopy...), so sign here, after install, as the last step.
        # str() guard: "OHOS" is only a valid settings.os enum on the
        # OHOS-adapted conan; plain conan raises on the bare comparison.
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
            if os.path.islink(f):  # sign real ELFs only, not version symlinks
                continue
            # `|| true`: a first-time sign has no .codesign section to
            # remove — that failure is expected and must not abort.
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["flint"]
        # 刻意不设 cpp_info.requires：制品仓的 gmp/mpfr 是静态包，已被
        # 整体链入 libflint.so（DT_NEEDED 只剩 libc.so），下游无需也不应
        # 再链一份（详见软件级 README「已知特性」）。
        self.cpp_info.set_property("cmake_file_name", "flint")
        self.cpp_info.set_property("cmake_target_name", "flint::flint")
        self.cpp_info.set_property("pkg_config_name", "flint")
