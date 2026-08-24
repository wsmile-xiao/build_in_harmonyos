#!/usr/bin/env python3
"""Conan recipe for notmuch2 0.34.3 — Pythonic cffi bindings for notmuch.

notmuch2 是纯 Python cffi 绑定包（setup.py + cffi_modules），构建时编译
notmuch2/_capi 扩展（#include <notmuch.h> + -lnotmuch），运行时 dlopen
libnotmuch.so。

OHOS 适配要点：
- CI worker 网络受限 → 源码 tar 随 export_sources 提供（notmuch2-0.34.3-src.tar.gz，
  来自 PyPI sdist），本地解压（参照 lv 先例）。
- 依赖 notmuch/0.38.3（本仓库刚适配，libnotmuch.so + notmuch.h 随包分发）+
  glib（libnotmuch 运行时 NEEDED libglib-2.0.so 等）。
- cffi 构建：_build.py 硬编码 include_dirs=['../../lib']/library_dirs=['../../lib']，
  改为 notmuch 制品 include/lib 目录（replace_in_file）。
- 打包：pip wheel --no-deps 提取到 <prefix>/lib/python3.X/site-packages，
  package_info 设 runenv PYTHONPATH（参照 check-jsonschema 先例）。
"""
import os
import shutil
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, replace_in_file, get
from conan.tools.layout import basic_layout


class Notmuch2Conan(ConanFile):
    name = "notmuch2"
    version = "0.34.3"
    description = "Pythonic bindings for the notmuch mail database using CFFI"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/weilbith/notmuch2-python-bindings"
    url = ""  # CI fills this

    # L0p: OHOS profile 需要全部四项 settings（git-who 修复先例）
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # notmuch（libnotmuch.so + notmuch.h，cffi 构建与运行时依赖）
        self.requires("notmuch/0.38.3")
        # glib（libnotmuch.so 运行时 NEEDED libglib-2.0.so，随 notmuch 包分发）
        self.requires("glib/2.84.0")


    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # 源码 tar 优先用配方的 s/ 目录（CI worker 网络受限——files.pythonhosted.org
        # 不可达导致源码下载超时——预缓存 tar 到 s/ 目录，source() 本地解压）；
        # s/ 目录不存在时回退 conandata url 下载（PyPI sdist）
        recipe_tar = os.path.join(self.recipe_folder, "s", "notmuch2-0.34.3.post1.tar.gz")
        if os.path.isfile(recipe_tar):
            import tarfile
            with tarfile.open(recipe_tar, "r:gz") as tf:
                tf.extractall(self.source_folder)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        inner = os.path.join(self.source_folder, "notmuch2-0.34.3.post1")
        if not os.path.isdir(inner):
            inner = os.path.join(self.source_folder, "notmuch2-0.34.3")
        if os.path.isdir(inner):
            for _f in os.listdir(inner):
                shutil.move(os.path.join(inner, _f), self.source_folder)
            os.rmdir(inner)

    def build(self):
        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration("python3 is required to build notmuch2")
        # cffi 构建依赖：_build.py 的 include_dirs/library_dirs 硬编码 ../../lib
        # → 改为 notmuch 制品 include/lib（cffi 编译 #include <notmuch.h> + -lnotmuch）
        notmuch_pkg = self.dependencies["notmuch"]
        nm_inc = os.path.join(notmuch_pkg.package_folder, "include")
        nm_lib = os.path.join(notmuch_pkg.package_folder, "lib")
        build_py = os.path.join(self.source_folder, "notmuch2", "_build.py")
        replace_in_file(self, build_py,
                        "include_dirs=['../../lib'],",
                        f"include_dirs=['{nm_inc}'],")
        replace_in_file(self, build_py,
                        "library_dirs=['../../lib'],",
                        f"library_dirs=['{nm_lib}'],")
        # cffi 编译需要 libnotmuch 运行时库路径（编译期链接 -lnotmuch）
        # pip 的 build_ext 用 CC/PATH 找编译器；conanbuild 环境 PATH 无 clang →
        # 命令内联注入 /data/service/hnp/bin 与 CC/CXX（参照 aegean 内联 export 先例，
        # env="conanbuild" 会重置 PATH，env 参数不生效）
        clang_dir = "/data/service/hnp/bin"
        nm_lib = os.path.join(notmuch_pkg.package_folder, "lib")
        wheel_dir = os.path.join(self.build_folder, "wheel")
        os.makedirs(wheel_dir, exist_ok=True)
        # OHOS 加载 .so 需要签名（CI 实测 pip-build-env 的 _cffi_backend.so
        # 未签名——ImportError: Permission denied）→ 签名系统 _cffi_backend.so
        # + pip wheel --no-build-isolation（用系统已签名 cffi，不建临时隔离环境）
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        import subprocess
        cb = subprocess.run([python3, "-c",
                             "import _cffi_backend; print(_cffi_backend.__file__)"],
                            capture_output=True, text=True)
        cffi_so = cb.stdout.strip() if cb.returncode == 0 else ""
        if cffi_so and os.path.exists(cffi_so):
            # binary-sign-tool 正确调用：sign -inFile -outFile -selfSign 1
            # （直接传文件报 -101 is not trust command——acme-client 已合入用法）
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = cffi_so + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {cffi_so} 2>/dev/null || true")
            self.run(f"{signer} sign -inFile {cffi_so} -outFile {tmp_signed} -selfSign 1",
                     env="conanbuild", ignore_errors=True)
            if os.path.exists(tmp_signed):
                os.replace(tmp_signed, cffi_so)
                # os.replace 保留 tmp 权限（owner 20001006:file_manager——
                # 实测 770——当前用户 100 读不了 → Permission denied）——
                # chmod 777 确保所有用户可读可执行
                os.chmod(cffi_so, 0o777)
        # pip wheel 链接 _capi.abi3.so 时 -lpython3.12 找不到（CI 实测
        # ld.lld: unable to find library -lpython3.12——LIBDIR/../lib 均无
        # libpython3.12——CI 的 python3.12 安装在
        # OpenHarmonyPCDeveloper..._o_1.0.0/）——LDFLAGS 用 find 动态定位
        # libpython3.12 实际目录（跨环境最可靠——本地 /usr/local/lib、
        # CI OpenHarmonyPCDeveloper..._o_1.0.0/lib 都能找到）
        py_libdir = subprocess.run(
            "find /data/service/hnp /storage -name 'libpython3.12.so*' "
            "2>/dev/null | head -1 | xargs dirname 2>/dev/null",
            shell=True, capture_output=True, text=True).stdout.strip()
        py_ldflags = (f"-L{py_libdir} -lpython3.12") if py_libdir else ""
        # lld（clang 的链接器）需 libxml2.so.16（在 OHOS SDK 的 llvm/lib——
        # CI 实测 Error loading shared library libxml2.so.16——链接阶段崩溃）
        llvm_lib = subprocess.run(
            "find /data/service/hnp -name 'libxml2.so.16' 2>/dev/null "
            "| head -1 | xargs dirname 2>/dev/null",
            shell=True, capture_output=True, text=True).stdout.strip()
        # --no-build-isolation 用系统环境——CI 实测 Cannot import
        # 'setuptools.build_meta'（系统 setuptools 缺失/不可用）——
        # pip wheel 前确保系统 setuptools 可用
        self.run(f'"{python3}" -m pip install setuptools --quiet',
                 env="conanbuild", ignore_errors=True)
        self.run(
            f"export PATH={clang_dir}:$PATH "
            f"CC={clang_dir}/clang CXX={clang_dir}/clang++ "
            # lld 需 libxml2.so.16（在 OHOS SDK 的 llvm/lib——CI 实测
            # Error loading shared library libxml2.so.16——链接阶段崩溃）——
            # LD_LIBRARY_PATH 前置 llvm/lib
            f"LD_LIBRARY_PATH={llvm_lib}:{nm_lib}:$LD_LIBRARY_PATH "
            f"LDFLAGS=\"{py_ldflags}\"; "
            f'"{python3}" -m pip wheel "{self.source_folder}" --no-deps '
            f'--no-build-isolation --wheel-dir="{wheel_dir}"',
            env="conanbuild",
        )
        # 确保生成的 wheel 里 cffi 扩展链接了 libnotmuch（若失败则明确报错）
        whls = [f for f in os.listdir(wheel_dir) if f.endswith(".whl")]
        if not whls:
            raise ConanInvalidConfiguration(f"No .whl produced in {wheel_dir}")

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_pkg, exist_ok=True)
        wheel_dir = os.path.join(self.build_folder, "wheel")
        for whl in os.listdir(wheel_dir):
            if whl.endswith(".whl"):
                with zipfile.ZipFile(os.path.join(wheel_dir, whl)) as z:
                    z.extractall(site_pkg)
                break
        else:
            raise ConanInvalidConfiguration(f"No .whl file found in {wheel_dir}")
        # 打包的 _capi.abi3.so 未签名——test_package 加载实测
        # ImportError: Permission denied——提取 wheel 后签名 so
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        import glob as _glob
        for so in _glob.glob(os.path.join(site_pkg, "notmuch2", "_capi*.so")):
            # binary-sign-tool 正确调用：sign -inFile -outFile -selfSign 1
            # （直接传文件报 -101 is not trust command）
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = so + ".signed"
            self.run(f"{objcopy} --remove-section .codesign {so} 2>/dev/null || true")
            self.run(f"{signer} sign -inFile {so} -outFile {tmp_signed} -selfSign 1",
                     env="conanbuild", ignore_errors=True)
            if os.path.exists(tmp_signed):
                os.replace(tmp_signed, so)
                # os.replace 保留 tmp 权限（owner 20001006:file_manager——
                # 实测 770——当前用户 100 读不了 → Permission denied）——
                # chmod 777 确保所有用户可读可执行
                os.chmod(so, 0o777)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.runenv_info.append_path("PYTHONPATH", site_pkg)
        self.runenv_info.append_path("LD_LIBRARY_PATH",
                                     os.path.join(self.dependencies["notmuch"].package_folder, "lib"))
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
