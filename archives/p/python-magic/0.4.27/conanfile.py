#!/usr/bin/env python3
"""Conan recipe for python-magic 0.4.27 — pure Python libmagic wrapper.

python-magic is a pure Python (noarch) binding to libmagic (the `file`
command's library), used to detect file types / MIME types. No C/C++
compilation — package installs the `magic` module. Runtime requires
`libmagic.so.1`, provided by the `file` Conan package (same pattern as
acronym/pyroute2 noarch adaptions).
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy


class PythonMagicConan(ConanFile):
    name = "python-magic"
    version = "0.4.27"
    description = "python-magic — file type / MIME detection via libmagic (pure Python binding)"
    license = "MIT"
    homepage = "https://github.com/ahupp/python-magic"
    url = ""

    # Pure Python noarch: no compiler needed
    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"
    # 运行时依赖 libmagic（file 包提供 libmagic.so.1）——test_package 消费验证
    requires = "file/5.48.1"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        # 纯 Python 包——无需 pip 构建（setuptools egg_info 在此环境加载
        # entry point 报 pbr 缺失实测）——直接拷贝源码 magic/ 模块到包内
        # 上游测试（rule 4 实测回填）：sdist 不含 test/——从 GitHub
        # 0.4.27 tag 下载 test/（python_magic_test.py 17 + libmagic_test.py
        # 3 = 20 用例）跑 unittest
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import shutil
        import subprocess
        import tarfile
        import urllib.request

        # 1. 下载 GitHub test/（sdist 不含——实测 0 测试文件）
        tests_dir = os.path.join(self.source_folder, "test")
        if not os.path.isdir(os.path.join(tests_dir, "python_magic_test.py")):
            url = ("https://codeload.github.com/ahupp/python-magic/"
                   "tar.gz/refs/tags/0.4.27")
            tarball = os.path.join(self.build_folder, "pymagic-gh.tar.gz")
            req = urllib.request.Request(url, headers={"User-Agent": "atomcode"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                with open(tarball, "wb") as f:
                    f.write(resp.read())
            with tarfile.open(tarball) as z:
                z.extractall(self.build_folder)
            sub = os.path.join(self.build_folder, "python-magic-0.4.27",
                               "test")
            if os.path.isdir(sub):
                shutil.copytree(sub, tests_dir)
                print("[python-magic tests] test/ downloaded from GitHub")
        # 2. 运行时 libmagic：file 包按 R26 只出静态库（libmagic.a）——
        # 构建 libmagic.so.1（C 层 magic_open/magic_load 实测可用）——
        # 放到可写目录并 LD_LIBRARY_PATH 指向
        file_pkg = next(
            (d.package_folder for d in self.dependencies.values()
             if d.ref.name == "file"), None)
        libmagic_dir = "/data/storage/el2/base/cache"
        os.makedirs(libmagic_dir, exist_ok=True)
        so = os.path.join(libmagic_dir, "libmagic.so.1")
        if file_pkg and not os.path.isfile(so):
            libmagic_a = os.path.join(file_pkg, "lib", "libmagic.a")
            if os.path.isfile(libmagic_a):
                r = subprocess.run(
                    # OHOS 沙箱 subprocess 相对名不搜 PATH（posix_spawn 差异
                    # 实测——CI 报 FileNotFoundError: 'clang'）——绝对路径
                    ["/data/service/hnp/bin/clang", "-shared",
                     "-Wl,--whole-archive", libmagic_a,
                     "-Wl,--no-whole-archive", "-o", so, "-lz"],
                    capture_output=True, text=True)
                print("[python-magic tests] libmagic.so.1 build rc=%d"
                      % r.returncode)
                # libmagic 默认数据库路径（~/.magic.mgc）——magic.mgc 拷贝
                # 过去让 magic_load(NULL) 找到（core dump 实测——默认路径
                # 不存在）
                mgc = os.path.join(file_pkg, "share", "misc", "magic.mgc")
                if os.path.isfile(mgc):
                    shutil.copy(mgc, os.path.join(
                        os.path.expanduser("~"), ".magic.mgc"))
                    print("[python-magic tests] magic.mgc -> ~/.magic.mgc")
        # 3. OHOS Python sys.platform='ohos'——python-magic 的 loader 只在
        # sys.platform=='linux' 时 yield 'libmagic.so.1'（加载失败实测）——
        # sitecustomize.py 强制（Python 启动自动加载）
        sc = os.path.join(self.build_folder, "sitecustomize.py")
        with open(sc, "w") as f:
            f.write("import sys\n"
                    "if sys.platform == 'ohos':\n"
                    "    sys.platform = 'linux'\n")
        # 4. 跑 unittest（LD_LIBRARY_PATH + sitecustomize + LC_ALL +
        # TMPDIR——沙箱 /tmp 只读实测）
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = libmagic_dir
        env["PYTHONPATH"] = os.pathsep.join([
            self.build_folder,
            self.source_folder,
        ])
        env["LC_ALL"] = "en_US.UTF-8"
        env["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(env["TMPDIR"], exist_ok=True)
        r = subprocess.run(
            [sys.executable, "-m", "unittest",
             "test.python_magic_test", "test.libmagic_test"],
            cwd=self.source_folder, capture_output=True, text=True,
            timeout=900, env=env)
        out = r.stdout + r.stderr
        print("[python-magic upstream tests] unittest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[python-magic upstream tests]", line)

    def package(self):
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        # 拷贝源码 magic/ 模块（__init__.py + loader.py + compat.py +
        # py.typed + .pyi）——conan copy 的 pattern 匹配不到目录内容，
        # 用 shutil.copytree 显式拷贝（与 libdebian-installer 同款解法）
        import shutil
        shutil.copytree(os.path.join(self.source_folder, "magic"),
                        os.path.join(site_dst, "magic"))

    def package_info(self):
        # Pure Python — expose the site-packages path via PYTHONPATH
        py_ver = self._py_ver()
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.env_info.PYTHONPATH.append(site)
        self.cpp_info.libs = []
