import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class HickleConan(ConanFile):
    """hickle 5.0.3 — HDF5 based version of pickle (纯 Python 包).

    产物：lib/python3.12/site-packages/hickle/，铺到 ~/usr/local 后系统 python3
    可直接 import。运行期依赖 h5py + numpy 由目标 Python 环境提供（OHOS 上
    numpy 已随 openblas 验证可用；h5py 需 HDF5，已发布到制品仓）。
    纯 Python 无 C 扩展，无需交叉编译/ELF 签名。
    """
    name = "hickle"
    version = "5.0.3"
    description = "Hickle - an HDF5 based version of pickle"
    license = "MIT"
    homepage = "https://github.com/telegraphic/hickle"
    url = "https://github.com/telegraphic/hickle"
    topics = ("pickle", "hdf5", "data-storage", "data-export")
    # 纯 Python 包：只需 os/arch 标识平台，无编译器依赖
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # strip_root=True：去掉 tar 内顶层 hickle-5.0.3/ 目录，使 source_folder
        # 直接含 setup.py + hickle/（conan 2.x get() 不默认 strip）
        get(self, strip_root=True, **self.conan_data["sources"])
        # numpy 2.x / astropy 8.x / setuptools(PEP 706) 兼容性补丁：
        # 修复后上游 pytest 102/102 全部通过（详见 manifest.yaml upstream_test_run）
        apply_conandata_patches(self)

    def build(self):
        # 纯 Python 包，无编译步骤
        pass

    def package(self):
        # 直接把 hickle/ 包目录铺到 site-packages（纯 .py，拷贝即用）。
        # 不走 pip install：避免对 setuptools/build isolation 的运行期依赖，
        # 也避免拉取 h5py/numpy（--no-deps 仍需解析 setup.py）。
        dst_sp = os.path.join(self.package_folder, "lib", "python3.12", "site-packages")
        os.makedirs(dst_sp, exist_ok=True)
        src_pkg = os.path.join(self.source_folder, "hickle")
        if not os.path.isdir(src_pkg):
            raise Exception("源码包内未找到 hickle/ 目录: " + src_pkg)
        shutil.copytree(src_pkg, os.path.join(dst_sp, "hickle"), dirs_exist_ok=True)

    def package_info(self):
        # 纯 Python 包：无 C 库/头/可执行，仅产出 site-packages 资源
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        site_packages = os.path.join(
            self.package_folder, "lib", "python3.12", "site-packages")
        self.cpp_info.resdirs = ["lib/python3.12/site-packages"]
