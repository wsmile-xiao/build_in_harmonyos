#!/usr/bin/env python3
"""Conan recipe for laundrify-aio 1.2.2 — laundrify API client
(pure Python, aiohttp-based, PyPI source).

Dependencies:
- aiohttp (published on ohpcd: aiohttp/3.14.3) — conan requires.
- PyJWT (NOT published on ohpcd yet, R36 gap) — vendored from its
  official PyPI sdist into site-packages at build() time. Once
  pyjwt/<x.y.z> is adapted and released, switch to self.requires and
  drop the vendored step (recorded in notes.md).

Pure Python (noarch) — build() copies the laundrify_aio/ module into a
staged site-packages (pip/setuptools build avoided: setup.py has an
interactive DistWheelCommand that breaks non-interactive builds, same
rationale as python-dotenv/python-magic). No upstream tests exist
(Nix records doCheck=false); the real test is test_package import +
API construction.
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, download
from conan.tools.layout import basic_layout


class LaundrifyAioConan(ConanFile):
    name = "laundrify-aio"
    version = "1.2.2"
    description = "laundrify API client (aiohttp-based, for Home Assistant integration)"
    license = "MIT"
    homepage = "https://github.com/laundrify/laundrify-pypi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"
    package_type = "python-require"

    def requirements(self):
        # aiohttp published on ohpcd (laundrify-aio declares aiohttp, no cap)
        self.requires("aiohttp/3.14.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        stage = os.path.join(self.build_folder, "py-stage")
        os.makedirs(stage, exist_ok=True)

        # copy the pure-Python module into staged site-packages
        mod = os.path.join(self.source_folder, "laundrify_aio")
        if not os.path.isdir(mod):
            raise ConanException(f"laundrify_aio module missing: {mod}")
        shutil.copytree(mod, os.path.join(stage, "laundrify_aio"))

        # vendor pyjwt (not yet on ohpcd, R36 gap) from its official sdist
        vend = self.conan_data.get("vendored", {}).get("pyjwt")
        if not vend:
            raise ConanException("vendored.pyjwt missing in conandata.yml")
        jwt_tgz = os.path.join(self.build_folder, "pyjwt.tar.gz")
        download(self, vend["url"], jwt_tgz, sha256=vend["sha256"])
        extract_dir = os.path.join(self.build_folder, "pyjwt-src")
        os.makedirs(extract_dir, exist_ok=True)
        with tarfile.open(jwt_tgz) as tf:
            tf.extractall(extract_dir)
        # sdist unpacks to pyjwt-<ver>/jwt — locate the jwt package dir
        jwt_pkg = None
        for root, dirs, _files in os.walk(extract_dir):
            if os.path.basename(root) == "jwt" and os.path.isfile(
                    os.path.join(root, "__init__.py")):
                jwt_pkg = root
                break
        if not jwt_pkg:
            raise ConanException(f"jwt package missing under {extract_dir}")
        shutil.copytree(jwt_pkg, os.path.join(stage, "jwt"))

        # import smoke check with the staged path; conan dependencies'
        # site-packages must also be on PYTHONPATH (aiohttp imported at
        # module load) — same dependency-path lesson as airthings-cloud
        import subprocess
        import sys
        py = stage
        for dep in self.dependencies.values():
            for root, _dirs, _files in os.walk(dep.package_folder):
                if os.path.basename(root) == "site-packages":
                    py += os.pathsep + root
                    break
        env = dict(os.environ, PYTHONPATH=py)
        r = subprocess.run(
            [sys.executable, "-c",
             "import laundrify_aio; from laundrify_aio import LaundrifyAPI; "
             "import jwt; print('import ok')"],
            env=env, capture_output=True, text=True)
        self.output.info(r.stdout.strip())
        if r.returncode != 0:
            raise ConanException(f"import smoke check failed: {r.stderr}")

    def package(self):
        stage = os.path.join(self.build_folder, "py-stage")
        for entry in os.listdir(stage):
            s = os.path.join(stage, entry)
            d = os.path.join(self.package_folder, "site-packages", entry)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
        if not os.path.isdir(os.path.join(self.package_folder,
                                          "site-packages", "laundrify_aio")):
            raise ConanException("laundrify_aio missing in package")

    def package_info(self):
        sp = os.path.join(self.package_folder, "site-packages")
        self.output.info(f"PYTHONPATH={sp}")
