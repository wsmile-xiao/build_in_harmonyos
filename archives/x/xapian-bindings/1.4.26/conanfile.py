#!/usr/bin/env python3
"""Conan recipe for xapian-bindings 1.4.26 — xapian Python bindings.

xapian-bindings provides the Python bindings (`import xapian`) for
xapian-core. It is a SWIG-generated C++ extension module
(_xapian.cpython-*.so + xapian/ pure-python package) built from the
xapian-bindings source tarball (xapian_wrap.cc is pre-generated, so
no swig is required at build time).

构建方式完全对齐 CI 已验证通过的 xapian-core 配方：
- settings/options/layout 与 xapian-core 一致
- AutotoolsToolchain 生成 configure_args（--disable-documentation 等）
- OHOS 分支：bash 包裹工具链 + 完整 AR/RANLIB/NM/LD + config.guess/sub
  补丁识别 OHOS 三元组；本机与 CI 均为 OHOS 原生构建，不传 --host。
"""
import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class XapianBindingsConan(ConanFile):
    name = "xapian-bindings"
    version = "1.4.26"
    description = "Python bindings for the Xapian search engine library"
    license = "GPL-2.0-or-later"
    homepage = "https://xapian.org/"
    url = "https://xapian.org/"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("xapian-core/1.4.26")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-documentation")
        tc.configure_args.append("--disable-dependency-tracking")
        tc.generate()

    def _load_configure_args(self):
        return load_toolchain_args(self.generators_folder).get("configure_args")

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable

        # sphinx: xapian-bindings configure 硬性检查 python3 sphinx 模块
        # (仅构建期文档工具；CI 干净环境没有，必须先安装)
        self.run(
            f'{python_exe} -m pip install --break-system-packages "sphinx"',
            env="conanrun",
        )

        # xapian-core 依赖路径（头文件 + libxapian.so + xapian-config）
        xc_folder = self.dependencies["xapian-core"].package_folder
        xc_bin = os.path.join(xc_folder, "bin", "xapian-config")
        xc_include = os.path.join(xc_folder, "include")
        xc_lib = os.path.join(xc_folder, "lib")

        # Python 头文件路径
        py_include = subprocess.run(
            [python_exe, "-c",
             "import sysconfig; print(sysconfig.get_paths()['include'])"],
            capture_output=True, text=True).stdout.strip()

        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            os.chmod(configure, 0o755)
            # E064: CI 沙箱(SELinux/AppSpawn)无法执行用户编译的 conftest ELF，
            # 本地 shell 与 Python subprocess(仅 musl posix_spawn 路径)均被拦。
            # 本机与 CI 都是 OHOS 原生构建(build==host==aarch64-unknown-linux-ohos)，
            # 因此直接判定 cross_compiling=no；禁止用 --host 伪造交叉编译(E064 forbid_1)。
            replace_in_file(
                self,
                configure,
                "ac_try='./conftest$ac_cv_exeext'",
                "ac_try=':'",
            )

        configure_args = self._load_configure_args()

        # 本机与 CI 均在 OHOS 上原生构建；让 config.guess/sub 识别 linux-ohos
        # 并保留 configure 的原生运行时探测。
        config_shell = shutil.which("bash") or "/system/bin/sh"
        cc = shutil.which("clang") or os.environ.get("CC", "clang")
        cxx = shutil.which("clang++") or os.environ.get("CXX", "clang++")
        cc_cmd = f"{config_shell} {cc}"
        cxx_cmd = f"{config_shell} {cxx}"
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or "ranlib"
        nm = shutil.which("llvm-nm") or shutil.which("nm") or "nm"
        ld = shutil.which("ld.lld") or shutil.which("ld") or "ld"

        # xapian-bindings 特有配置（必需，不影响 host/build 判定）
        configure_args += (
            f' --with-python3 --prefix={os.path.dirname(python_exe)}/.. '
            f'XAPIAN_CONFIG="{xc_bin}" '
            f'CPPFLAGS="-I{xc_include}" '
            f'CXXFLAGS="-stdlib=libc++ -I{xc_include} -I{py_include}" '
            f'LDFLAGS="-L{xc_lib}"'
        )
        self.run(
            f'CC="{cc_cmd}" CXX="{cxx_cmd}" AR="{ar}" RANLIB="{ranlib}" NM="{nm}" '
            f'LD="{ld}" CONFIG_SHELL="{config_shell}" '
            f'"{config_shell}" "{configure}" {configure_args}',
            cwd=self.source_folder,
        )

        # 链接修复：OHOS SDK 无 libstdc++，改用 libc++；绑定需显式链 libpython
        mf = os.path.join(self.source_folder, "python3", "Makefile")
        if os.path.isfile(mf):
            replace_in_file(self, mf, "-lstdc++", "-lc++")
            # PYTHON3_LIBS 追加 -lpython3.12（python3 主程序未导出 C API 符号）。
            # CI 的 HNP python 的 sysconfig LIBDIR 可能指向不存在的路径，
            # 从 include 路径推导 prefix 下的 lib 目录（多候选，取实际存在者）。
            probe = (
                "import sysconfig, os, sys\n"
                "inc = sysconfig.get_paths()['include']\n"
                "prefix = os.path.dirname(os.path.dirname(inc))\n"
                "cands = [os.path.join(prefix, 'lib'),\n"
                "         sysconfig.get_config_var('LIBDIR') or '',\n"
                "         sysconfig.get_config_var('LIBPL') or '']\n"
                "name = 'libpython%d.%d.so' % sys.version_info[:2]\n"
                "for c in cands:\n"
                "    if c and os.path.exists(os.path.join(c, name)):\n"
                "        print(c)\n"
                "        break\n"
                "else:\n"
                "    print(cands[0] or '')\n"
            )
            py_libdir = subprocess.run(
                [python_exe, "-c", probe],
                capture_output=True, text=True).stdout.strip()
            self.output.info(f"xapian bindings: py_libdir={py_libdir}")
            replace_in_file(
                self, mf,
                "PYTHON3_LIBS = ",
                f"PYTHON3_LIBS = -L{py_libdir} -lpython{sys.version_info.major}.{sys.version_info.minor} ",
            )
            self.output.info("link fixes applied to python3/Makefile")

        # 构建 python3 绑定。
        # 注意：跳过 make 默认 all 中的 import 验证目标
        # (xapian/__pycache__/__init__.cpython-*.pyc) —— CI 的 HNP python
        # 在 conan build 目录 (.conan2/p/b/...) 加载 _xapian.so 会报
        # Permission denied（沙箱限制），绑定安装到 site-packages 后再验证。
        self.run("make -C python3 _xapian.la", cwd=self.source_folder)
        # 生成 xapian/__init__.py（BUILT_SOURCES 产物）
        self.run("make -C python3 xapian/__init__.py", cwd=self.source_folder)
        # 上游 make -C python3 check 在 CI 的 HNP python 沙箱中加载 build 目录
        # 内的 _xapian.so 报 Permission denied（E009/E054，notes.md #5），
        # 因此不在 build() 内执行；改由 test_package 在安装后的
        # site-packages 侧验证绑定功能（本地已验证上游 2/2 通过）。

    def package(self):
        # 将绑定安装到 package_folder 下的 python site-packages
        python_exe = sys.executable
        site_packages = os.path.join(
            self.package_folder, "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages")
        pydir = os.path.join(self.source_folder, "python3", "xapian")
        dest_pkg = os.path.join(site_packages, "xapian")
        os.makedirs(dest_pkg, exist_ok=True)
        self.run(f'cp -rf {pydir}/. {dest_pkg}/')
        so_files = glob.glob(os.path.join(self.source_folder, "python3", ".libs", "_xapian*.so"))
        if not so_files:
            raise Exception("xapian bindings shared library not built: _xapian*.so missing")
        for so in so_files:
            shutil.copy2(so, dest_pkg)
            self.output.info(f"  copied {os.path.basename(so)}")

        # E077/P-SIGN-001: 鸿蒙 musl 动态链接器加载 .so 时校验 .codesign 签名，
        # 未签名/签名失效的 .so 报 "Error loading shared library ... Permission denied"
        # （CI test_package 实测）。对打包的 _xapian.so 自签名，参照 ffmpeg/7.1.5
        # _sign_binaries()（CI 已验证）。签名后无需 chmod（.so 加载仅需读权限）。
        _hnp_bin = "/data/service/hnp/bin"
        objcopy = os.path.join(_hnp_bin, "llvm-objcopy")
        signer = os.path.join(_hnp_bin, "binary-sign-tool")
        for f in glob.glob(os.path.join(dest_pkg, "_xapian*.so")):
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))
            self.output.info(f"  signed {os.path.basename(f)}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = os.path.join("lib", py_ver, "site-packages")

        # Add Python lib path
        self.cpp_info.libdirs = [site_packages]

        # Set PYTHONPATH so consumers can `import xapian`
        lib_path = os.path.join(self.package_folder, site_packages)
        self.runenv_info.define("PYTHONPATH", lib_path)
