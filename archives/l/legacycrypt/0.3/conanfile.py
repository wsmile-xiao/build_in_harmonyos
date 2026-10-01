#!/usr/bin/env python3
"""Conan recipe for legacycrypt 0.3 — standalone backport of the Python
stdlib ``crypt`` module (pure Python, single file).

legacycrypt loads libcrypt/libxcrypt through ctypes at import time.  On
OHOS (musl) ctypes.util.find_library() always returns None, so a small
source patch adds a direct CDLL('libcrypt.so.2') fallback (the SONAME
libxcrypt installs) and this recipe requires libxcrypt (shared) to
provide that SONAME.  build() runs the upstream unittest suite
(tests.py) for a real pass rate (rule 4).
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class LegacycryptConan(ConanFile):
    name = "legacycrypt"
    version = "0.3"
    description = ("legacycrypt — standalone backport of the Python stdlib "
                   "crypt module (pure Python)")
    license = "PSF-2.0"
    homepage = "https://github.com/tiran/legacycrypt"
    url = ""

    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    # 运行时硬依赖 libcrypt SONAME——OHOS 设备未装任何 libcrypt，必须依赖
    # libxcrypt 并强制 shared（静态库无法被 ctypes CDLL 加载）。制品仓
    # libxcrypt/4.5.2 目前只有 static 二进制，shared 变体由 --build=missing
    # 从源码构建（其 recipe 含完整 OHOS 补丁与 make check）。
    default_options = {"libxcrypt/*:shared": True}

    def requirements(self):
        self.requires("libxcrypt/4.5.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 纯 Python——无编译；上游测试（rule 4 实测回填）：
        # python tests.py（stdlib unittest，sdist 自带）
        self._run_upstream_tests()

    def _xcrypt_libdirs(self):
        """libxcrypt shared 产物所在目录（CDLL 搜索路径需要）。"""
        try:
            info = self.dependencies["libxcrypt"]
        except Exception:
            return []
        libdirs = list(info.cpp_info.libdirs or [])
        if not libdirs and info.package_folder:
            libdirs = [os.path.join(info.package_folder, "lib")]
        return libdirs

    def _run_upstream_tests(self):
        # 上游测试入口：python tests.py（stdlib unittest.main()，无子进程）
        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder
        # 补丁后的 CDLL('libcrypt.so.2') 走动态加载器搜索路径——注入
        # libxcrypt 的 lib/（shared=True 构建产物所在）
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            self._xcrypt_libdirs() + [env.get("LD_LIBRARY_PATH", "")])
        # OHOS 沙箱 /tmp 只读（python-dotenv 实测沉淀）——本套件不落临时
        # 文件，防御性设置
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        try:
            os.makedirs(env["TMPDIR"], exist_ok=True)
        except OSError:
            pass
        r = subprocess.run(
            [sys.executable, "tests.py", "-v"],
            cwd=self.source_folder, capture_output=True, text=True,
            timeout=900, env=env)
        out = r.stdout + r.stderr
        print("[legacycrypt upstream tests] python tests.py -v rc=%d"
              % r.returncode)
        for line in out.splitlines():
            if ("ok" in line.split() or "FAIL" in line
                    or "ERROR" in line or "skipped" in line
                    or "Ran " in line):
                print("[legacycrypt upstream tests]", line.strip())
        print("[legacycrypt upstream tests] end")

    def package(self):
        # 纯 Python noarch：单文件模块直接拷贝到 site-packages
        # （flit 构建后端在 OHOS 不可用——同 python-dotenv 先例）
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copyfile(os.path.join(self.source_folder, "legacycrypt.py"),
                        os.path.join(site, "legacycrypt.py"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
