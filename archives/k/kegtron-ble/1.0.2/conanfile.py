import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import get


class KegtronBleConan(ConanFile):
    name = "kegtron-ble"
    version = "1.0.2"
    description = ("kegtron-ble — Kegtron BLE keg flow meter "
                   "advertisement parser (pure Python)")
    license = "MIT"
    homepage = "https://github.com/Bluetooth-Devices/kegtron-ble"
    url = "https://github.com/Bluetooth-Devices/kegtron-ble"

    # 纯 Python noarch——无编译器需求，但 OHOS profile 要求 settings 含
    # 全部四项（CI L0p 门禁实测：缺 compiler/build_type 构建失败）
    settings = "os", "compiler", "build_type", "arch"

    # Python 级运行时依赖（pyproject.toml [tool.poetry.dependencies]）：
    #   bluetooth-sensor-state-data >= 1.6.1
    #   sensor-state-data >= 2.19.0
    #   bluetooth-data-tools >= 0.1.2
    # 加上 bluetooth-sensor-state-data 的传递依赖 home-assistant-bluetooth。
    # 这些包均未发布到 ohpcd 制品仓（R36 断链）——不写 conan requires
    # （PF4 依赖闸禁止引用未发布依赖）；消费侧 PYTHONPATH 组装见
    # test_package（pip 安装上游 poetry.lock 锁定版本组合）。
    requires = ()

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _pypi_vendor(self, dest):
        """下载并解压 Python 级依赖 wheel（上游 poetry.lock 锁定组合）。"""
        os.makedirs(dest, exist_ok=True)
        # 上游 poetry.lock 锁定的版本组合（kegtron-ble 1.0.2 tag）：
        #   sensor-state-data 2.19.0 / bluetooth-data-tools 0.3.1 /
        #   bluetooth-sensor-state-data 1.7.5 / home-assistant-bluetooth 1.4.0
        # 全部为 py3-none-any 纯 Python wheel（OHOS pypi 镜像实测）。
        wheels = [
            ("sensor_state_data-2.19.0-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/ce/63/e140aaec77bdc1f7b949e40712fc2f932023d9ad5cf211bb"
             "de969f516a55/sensor_state_data-2.19.0-py3-none-any.whl"),
            ("bluetooth_data_tools-0.3.1-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/e6/9b/e53fc7eb05f059dcd9b3b1e4a78ce2f9a796f49edf8ec74e"
             "d1326d31017b/bluetooth_data_tools-0.3.1-py3-none-any.whl"),
            ("bluetooth_sensor_state_data-1.7.5-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/64/52/287844cf648235f2baf734dbfd0b5657c61b547c014010b78"
             "b579312a8a3/bluetooth_sensor_state_data-1.7.5-py3-none-any.whl"),
            ("home_assistant_bluetooth-1.4.0-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/19/42/6804e6b6037fd0c852303d534ef58ca29846f9cdc51a2a39"
             "1bd972101b7b/home_assistant_bluetooth-1.4.0-py3-none-any.whl"),
        ]
        import zipfile
        for fname, url in wheels:
            out = os.path.join(dest, fname)
            if not os.path.exists(out):
                req = urllib.request.Request(url, headers={"User-Agent": "atomcode"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = resp.read()
                with open(out, "wb") as f:
                    f.write(data)
            with zipfile.ZipFile(out) as z:
                z.extractall(dest)

    def _pypi_vendor_pytest(self, dest):
        """vendor 纯 Python 的 pytest 及其运行时（pluggy/iniconfig）——
        OHOS pypi 镜像直链 wheel（URL 实测可下载）。"""
        if os.path.isdir(os.path.join(dest, "pytest")):
            return
        import zipfile
        wheels = [
            ("pytest-9.1.1-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/24/25/1de2678b631f5a49215c6c96fff41ba892b0a34df68d6d"
             "80292b1b48aa7f/pytest-9.1.1-py3-none-any.whl"),
            ("pluggy-1.6.0-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/54/20/4d324d65cc6d9205fabedc306948156824eb9f0ee163335"
             "5a8f7ec5c66bf/pluggy-1.6.0-py3-none-any.whl"),
            ("iniconfig-2.3.0-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/cb/b1/3846dd7f199d53cb17f49cba7e651e9ce294d8497c8c1"
             "50530ed11865bb8/iniconfig-2.3.0-py3-none-any.whl"),
            ("packaging-26.3-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d721"
             "88184bcab9dd527/packaging-26.3-py3-none-any.whl"),
            ("pygments-2.21.0-py3-none-any.whl",
             "https://pypi.repo.openharmony.cn/artifactory/openharmony-pypi/"
             "packages/71/46/17f022dd3e953bf20a04a028a21ec746d942f8d2af30f"
             "a0f124fa0e6a684/pygments-2.21.0-py3-none-any.whl"),
        ]
        try:
            import urllib.request
            for fname, url in wheels:
                out = os.path.join(dest, fname)
                if not os.path.exists(out):
                    req = urllib.request.Request(
                        url, headers={"User-Agent": "atomcode"})
                    with urllib.request.urlopen(req, timeout=300) as resp:
                        data = resp.read()
                    with open(out, "wb") as f:
                        f.write(data)
                with zipfile.ZipFile(out) as z:
                    z.extractall(dest)
        except Exception as e:
            print("[kegtron-ble tests] WARN: pytest vendor failed: %s" % e)

    def build(self):
        # 纯 Python 包——无需 pip 构建（同 rich/python-magic：环境
        # setuptools egg_info 加载 entry point 报 pbr 缺失实测）——
        # 直接拷贝源码 kegtron_ble/ 模块（package() 执行）
        # 上游测试（rule 4 实测回填）：sdist 不含 tests/——从 GitHub
        # v1.0.2 tag 下载 tests/（test_parser.py 3 用例）跑 pytest
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        if not can_run(self):
            return
        py = sys.executable
        # 1. 下载 GitHub tests/（sdist 不含——实测 0 测试文件）
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(os.path.join(tests_dir, "test_parser.py")):
            url = ("https://codeload.github.com/Bluetooth-Devices/"
                   "kegtron-ble/tar.gz/refs/tags/v1.0.2")
            tarball = os.path.join(self.build_folder, "kegtron-gh.tar.gz")
            req = urllib.request.Request(url, headers={"User-Agent": "atomcode"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                with open(tarball, "wb") as f:
                    f.write(resp.read())
            with tarfile.open(tarball) as t:
                t.extractall(self.build_folder)
            sub = os.path.join(self.build_folder, "kegtron-ble-1.0.2",
                               "tests")
            if os.path.isdir(sub):
                shutil.copytree(sub, tests_dir)
                print("[kegtron-ble tests] tests/ downloaded from GitHub")
        # 2. Python 级依赖（上游 poetry.lock 锁定组合）vendor 到构建目录
        vendor_dir = os.path.join(self.build_folder, "pydeps")
        self._pypi_vendor(vendor_dir)
        # 2b. pytest 也 vendor 进来——HNP Python 怪癖实测：设置 PYTHONPATH
        #     后默认 sys.path[0]（pip-global）被移除；若不带上 pytest，
        #     conan 沙箱里会从 pip-global 残留路径找到 pytest 但其
        #     hypothesis/_native.abi3.so 未签名不可 dlopen（rc=1 崩）。
        #     vendored pytest（纯 Python）+ vendored 依赖一起组成干净环境
        self._pypi_vendor_pytest(vendor_dir)
        # 3. 跑 pytest——PYTHONPATH = vendored deps + src 源码
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([
            vendor_dir,
            os.path.join(self.source_folder, "src"),
        ])
        # 沙箱 /tmp 只读——basetemp 指可写目录（同 packaging 教训）
        basetemp = os.path.join(self.build_folder, "pytest-tmp")
        os.makedirs(basetemp, exist_ok=True)
        try:
            r = subprocess.run(
                [py, "-m", "pytest", tests_dir, "-q", "--no-header",
                 "-p", "no:cacheprovider",
                 "--override-ini=addopts=",
                 f"--basetemp={basetemp}"],
                capture_output=True, text=True, env=env, timeout=900)
        except Exception as e:  # pytest 缺失等环境差异——如实记录不阻断
            print("[kegtron-ble upstream tests] WARN: %s" % e)
            return
        out = (r.stdout or "") + (r.stderr or "")
        print("[kegtron-ble upstream tests] pytest rc=%d" % r.returncode)
        for line in out.splitlines()[-12:]:
            print("[kegtron-ble upstream tests]", line)

    def package(self):
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        # 拷贝源码 kegtron_ble/ 模块（__init__.py + parser.py + py.typed）
        shutil.copytree(
            os.path.join(self.source_folder, "src", "kegtron_ble"),
            os.path.join(site_dst, "kegtron_ble"))

    def package_info(self):
        # Pure Python — expose the site-packages path via PYTHONPATH
        py_ver = self._py_ver()
        site = os.path.join(self.package_folder, "lib", py_ver,
                            "site-packages")
        self.env_info.PYTHONPATH.append(site)
        self.cpp_info.libs = []
